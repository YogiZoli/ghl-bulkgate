"""Business logic shared by the HTTP handlers.

Kept separate from main.py so it can be unit-tested with fixture payloads and
no live network (the GHL/Bulkgate clients are injected and mocked in tests).
"""
from __future__ import annotations

import hashlib
import logging
import time

from app.bulkgate_client import BulkgateClient
from app.config import get_settings
from app.ghl_client import GHLClient
from app.optout import is_start, is_stop
from app.phone import InvalidPhoneNumber, normalize
from app.store import Store

log = logging.getLogger("ghl_bulkgate.services")

# Bulkgate DLR status codes (GET callback `status` param).
BULKGATE_STATUS = {
    1: "delivered",
    2: "buffered",       # transient: recipient temporarily unavailable
    3: "not_delivered",
    10: "incoming",      # inbound SMS / reply
    13: "seen",          # Viber only
}

# Map Bulkgate DLR -> GHL message status string.
# GHL's status-update API accepts: delivered | failed | pending | read
# ("undelivered" is NOT a valid value there).
DLR_TO_GHL_STATUS = {
    1: "delivered",
    3: "failed",
}


async def ensure_access_token(store: Store, ghl: GHLClient, location_id: str) -> str | None:
    """Return a valid access token for a location, refreshing if near expiry."""
    inst = store.get_installation(location_id)
    if not inst or not inst.get("access_token"):
        return None
    if inst["token_expires_at"] - int(time.time()) > 120:
        return inst["access_token"]
    # Refresh.
    if not inst.get("refresh_token"):
        return inst["access_token"]
    bundle = await ghl.exchange_token(
        grant_type="refresh_token", refresh_token=inst["refresh_token"]
    )
    store.update_oauth_tokens(
        location_id=location_id,
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        token_expires_at=bundle.expires_at,
    )
    return bundle.access_token


async def handle_outbound(
    payload: dict,
    *,
    store: Store,
    bulkgate: BulkgateClient,
    ghl: GHLClient,
) -> dict:
    """Process a GHL Conversation-Provider outbound webhook.

    Always returns a small dict and never raises — the caller responds 200 so
    GHL does not retry-storm us. Real failures are recorded as GHL message
    status updates instead.
    """
    s = get_settings()
    location_id = payload.get("locationId")
    message_id = payload.get("messageId")
    phone = payload.get("phone")
    text = payload.get("message") or ""

    if not location_id:
        log.warning("outbound: missing locationId")
        return {"ignored": "missing locationId"}

    inst = store.get_installation(location_id)
    if not inst or not inst.get("bulkgate_app_id"):
        log.warning("outbound: no Bulkgate creds for location %s", location_id)
        return {"ignored": "location not configured"}

    # Idempotency — GHL may redeliver the same messageId.
    if message_id and store.ghl_message_seen(message_id):
        return {"deduped": message_id}

    country = inst.get("country") or s.default_country

    # Normalize the destination.
    try:
        number = normalize(phone, country)
    except InvalidPhoneNumber as exc:
        log.warning("outbound: invalid number %r (%s)", phone, exc)
        access = await ensure_access_token(store, ghl, location_id)
        if access and message_id:
            try:
                await ghl.update_message_status(
                    access_token=access,
                    message_id=message_id,
                    status="failed",
                    error={"code": "invalid_number", "message": str(exc)},
                )
            except Exception as e:  # noqa: BLE001
                log.error("outbound: status update failed: %s", e)
        return {"ignored": "invalid number"}

    # Respect opt-outs (EU compliance).
    if store.is_opted_out(location_id, number):
        log.info("outbound: %s is opted out; not sending", number)
        access = await ensure_access_token(store, ghl, location_id)
        if access and message_id:
            try:
                await ghl.update_message_status(
                    access_token=access,
                    message_id=message_id,
                    status="failed",
                    error={"code": "opted_out", "message": "Recipient opted out"},
                )
            except Exception as e:  # noqa: BLE001
                log.error("outbound: status update failed: %s", e)
        return {"ignored": "opted out"}

    # Send via Bulkgate.
    result = await bulkgate.send_sms(
        app_id=inst["bulkgate_app_id"],
        app_token=inst["bulkgate_app_token"],
        number=number,
        text=text,
        country=country,
        sender_id=inst.get("sender_id") or s.default_sender_id,
        sender_id_value=inst.get("sender_id_value") or s.default_sender_id_value or None,
        unicode_mode=inst.get("unicode_mode") or s.unicode_mode,
    )

    # Persist mapping for DLR routing + dedupe.
    store.save_message_map(
        ghl_message_id=message_id,
        bulkgate_message_id=result.message_id,
        location_id=location_id,
        direction="outbound",
        status=result.status or ("sent" if result.ok else "failed"),
    )

    # Report status to GHL.
    access = await ensure_access_token(store, ghl, location_id)
    if access and message_id:
        try:
            if result.ok:
                await ghl.update_message_status(
                    access_token=access,
                    message_id=message_id,
                    status=s.ghl_status_on_accept,
                )
            else:
                await ghl.update_message_status(
                    access_token=access,
                    message_id=message_id,
                    status="failed",
                    error={
                        "code": result.error_type or "send_failed",
                        "message": result.error or "Bulkgate send failed",
                    },
                )
        except Exception as e:  # noqa: BLE001
            log.error("outbound: GHL status update failed: %s", e)

    return {
        "sent": result.ok,
        "bulkgate_message_id": result.message_id,
        "segments": result.segments,
        "status": result.status,
    }


async def handle_bulkgate_callback(
    params: dict,
    *,
    store: Store,
    ghl: GHLClient,
    installation: dict | None = None,
) -> dict:
    """Process a Bulkgate DLR (status 1/2/3) or incoming SMS (status 10).

    ``installation`` is the location resolved from the per-install webhook token
    in the URL; for DLRs we can also fall back to the smsID->location mapping.
    """
    try:
        status_code = int(params.get("status"))
    except (TypeError, ValueError):
        return {"ignored": "missing/invalid status"}

    sms_id = params.get("smsID") or params.get("smsId") or params.get("sms_id")

    # --- Incoming SMS / reply (status 10) ---
    if status_code == 10:
        return await _handle_incoming(params, store=store, ghl=ghl, installation=installation)

    # --- Delivery report (status 1/2/3/13) ---
    if not sms_id:
        return {"ignored": "DLR without smsID"}

    # Idempotency on (smsID, status).
    if not store.mark_event(f"dlr:{sms_id}:{status_code}"):
        return {"deduped": sms_id}

    mapping = store.find_by_bulkgate_id(sms_id)
    location_id = (installation or {}).get("location_id") or (
        mapping or {}
    ).get("location_id")
    if not mapping or not location_id:
        log.info("DLR: no mapping for smsID %s", sms_id)
        return {"ignored": "unknown smsID"}

    store.update_status_by_bulkgate_id(sms_id, BULKGATE_STATUS.get(status_code, str(status_code)))

    ghl_message_id = mapping.get("ghl_message_id")
    ghl_status = DLR_TO_GHL_STATUS.get(status_code)  # None for buffered/seen
    if ghl_status and ghl_message_id:
        access = await ensure_access_token(store, ghl, location_id)
        if access:
            try:
                err = (
                    {"code": "not_delivered", "message": "Carrier did not deliver"}
                    if status_code == 3
                    else None
                )
                await ghl.update_message_status(
                    access_token=access,
                    message_id=ghl_message_id,
                    status=ghl_status,
                    error=err,
                )
            except Exception as e:  # noqa: BLE001
                log.error("DLR: GHL status update failed: %s", e)
    return {"dlr": BULKGATE_STATUS.get(status_code), "smsID": sms_id}


async def _handle_incoming(
    params: dict,
    *,
    store: Store,
    ghl: GHLClient,
    installation: dict | None,
) -> dict:
    """Inbound SMS (status 10): opt-out handling + push into GHL inbox."""
    s = get_settings()
    from_ = params.get("from")
    body = params.get("message") or ""

    if not installation:
        log.warning("incoming: no installation (use per-location webhook token)")
        return {"ignored": "unresolved tenant"}
    location_id = installation["location_id"]
    country = installation.get("country") or s.default_country

    try:
        from_e164 = normalize(from_, country)
    except InvalidPhoneNumber:
        log.warning("incoming: invalid sender %r", from_)
        return {"ignored": "invalid sender"}

    # Idempotency: dedupe identical inbound bursts (stable digest — Python's
    # hash() is process-salted and would change across restarts).
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    if not store.mark_event(f"in:{location_id}:{from_e164}:{body_digest}"):
        return {"deduped": True}

    # Opt-out / opt-in keyword handling.
    if is_stop(body):
        store.add_optout(location_id, from_e164)
        log.info("incoming: %s opted OUT", from_e164)
    elif is_start(body):
        store.remove_optout(location_id, from_e164)
        log.info("incoming: %s opted IN", from_e164)

    access = await ensure_access_token(store, ghl, location_id)
    if not access:
        return {"ignored": "no access token"}

    provider_id = installation.get("conversation_provider_id") or (
        s.ghl_conversation_provider_id or None
    )
    try:
        contact_id = await ghl.upsert_contact(
            access_token=access, location_id=location_id, phone="+" + from_e164
        )
        if not contact_id:
            return {"ignored": "could not resolve contact"}
        await ghl.add_inbound_message(
            access_token=access,
            contact_id=contact_id,
            message=body,
            conversation_provider_id=provider_id,
        )
    except Exception as e:  # noqa: BLE001
        log.error("incoming: GHL push failed: %s", e)
        return {"error": "ghl push failed"}

    return {"inbound": True, "from": from_e164, "opted_out": is_stop(body)}
