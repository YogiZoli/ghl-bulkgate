"""FastAPI entrypoint for the Bulkgate <-> GHL SMS Conversation Provider.

Endpoints
---------
GET  /health                     liveness probe (Railway healthcheck)
GET  /privacy                    standalone Privacy Policy (Marketplace listing)
GET  /terms                      standalone Terms of Service (Marketplace listing)
GET  /setup                      onboarding Custom Page (Bulkgate credentials + webhook)
POST /setup/confirm              installer confirms webhook is wired up in Bulkgate
GET  /oauth/callback             GHL OAuth install redirect
POST /ghl/webhook                GHL app webhook (UNINSTALL purges credentials)
POST /ghl/outbound               GHL Conversation-Provider outbound webhook
GET  /bulkgate/inbound/{token}   Bulkgate DLR + incoming SMS (per-install token)
POST /bulkgate/inbound/{token}   (same, in case Bulkgate is set to POST)
POST /admin/credentials          set a location's Bulkgate app_id/token (setup)

All webhook handlers respond 200 quickly; downstream errors are logged and, for
outbound, surfaced as GHL message-status updates rather than HTTP errors.
"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import __version__
from app.bulkgate_client import BulkgateClient
from app.config import get_settings
from app.ghl_client import GHLClient
from app.legal import PRIVACY_HTML, TERMS_HTML
from app.ghl_webhook import verify_webhook
from app.services import handle_bulkgate_callback, handle_outbound
from app.setup_page import render_setup_page
from app.store import get_store

logging.basicConfig(level=get_settings().log_level)
log = logging.getLogger("ghl_bulkgate")

app = FastAPI(title="ghl-bulkgate", version=__version__)

_bulkgate = BulkgateClient(api_url=get_settings().bulkgate_api_url)
_ghl = GHLClient()


def _store():
    return get_store()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "ghl-bulkgate", "version": __version__}


@app.get("/privacy")
async def privacy() -> HTMLResponse:
    return HTMLResponse(PRIVACY_HTML)


@app.get("/terms")
async def terms() -> HTMLResponse:
    return HTMLResponse(TERMS_HTML)


@app.get("/setup")
async def setup_page(locationId: str | None = None, location_id: str | None = None):
    """Onboarding Custom Page: Bulkgate credentials form + webhook URL + confirm step.

    GHL Custom Pages append the sub-account context as a `locationId` query
    param when the iframe is opened from inside the sub-account. We also
    accept `location_id` as a fallback for manual testing.
    """
    loc = locationId or location_id
    installation = _store().get_installation(loc) if loc else None
    webhook_url = None
    if installation:
        s = get_settings()
        base = (s.public_base_url or s.ghl_redirect_uri.rsplit("/oauth", 1)[0]).rstrip("/")
        webhook_url = f"{base}/bulkgate/inbound/{installation['webhook_token']}"
    html = render_setup_page(location_id=loc, installation=installation, webhook_url=webhook_url)
    return HTMLResponse(html)


@app.post("/setup/confirm")
async def setup_confirm(request: Request):
    """Installer clicked "I've connected the webhook in Bulkgate"."""
    body = await request.json()
    location_id = body.get("location_id")
    if not location_id or not _store().get_installation(location_id):
        raise HTTPException(status_code=404, detail="install the app first")
    _store().confirm_webhook(location_id)
    return {"ok": True}


@app.get("/oauth/callback")
async def oauth_callback(code: str | None = None, error: str | None = None):
    """Handle the GHL OAuth redirect after a sub-account installs the app."""
    if error:
        return HTMLResponse(f"<h3>Authorization failed</h3><p>{error}</p>", status_code=400)
    if not code:
        raise HTTPException(status_code=400, detail="missing code")

    bundle = await _ghl.exchange_token(grant_type="authorization_code", code=code)
    if not bundle.location_id:
        return HTMLResponse(
            "<h3>Installed, but no locationId returned.</h3>"
            "<p>Re-install with a Location-level token.</p>",
            status_code=400,
        )

    webhook_token = _store().upsert_installation(
        location_id=bundle.location_id,
        company_id=bundle.company_id,
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        token_expires_at=bundle.expires_at,
        conversation_provider_id=get_settings().ghl_conversation_provider_id or None,
    )
    s = get_settings()
    base = (s.public_base_url or s.ghl_redirect_uri.rsplit("/oauth", 1)[0]).rstrip("/")
    setup_url = f"{base}/setup?locationId={bundle.location_id}"
    log.info("Installed location %s", bundle.location_id)
    return HTMLResponse(
        "<h2>✅ Bulkgate SMS connected to GoHighLevel</h2>"
        f'<p>Finish setup on the <a href="{setup_url}">setup page</a> — '
        "enter your Bulkgate Application ID + token and connect the webhook.</p>"
    )


@app.post("/ghl/webhook")
async def ghl_webhook(request: Request):
    """GHL Marketplace app-level webhook (default webhook URL).

    Receives INSTALL / UNINSTALL (and any other subscribed) events. On
    UNINSTALL we hard-delete the installation so the user's encrypted Bulkgate
    credentials and OAuth tokens are not retained after they remove the app.

    The signature is verified against GHL's published public key over the raw
    body bytes; unverified requests are rejected so nobody can spoof a wipe.
    Always returns 200 on accepted events so GHL does not retry needlessly.
    """
    raw = await request.body()
    if not verify_webhook(raw, request.headers):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        payload = {}

    event_type = (payload.get("type") or "").upper()
    location_id = payload.get("locationId") or payload.get("location_id")

    if event_type == "UNINSTALL" and location_id:
        deleted = _store().delete_installation(location_id)
        log.info("Uninstall for location %s (purged=%s)", location_id, deleted)
        return JSONResponse({"received": True, "type": event_type, "purged": deleted})

    return JSONResponse({"received": True, "type": event_type or "unknown"})


@app.post("/ghl/outbound")
async def ghl_outbound(request: Request):
    """GHL Conversation-Provider outbound message webhook -> Bulkgate send."""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}
    try:
        result = await handle_outbound(
            payload, store=_store(), bulkgate=_bulkgate, ghl=_ghl
        )
    except Exception as e:  # noqa: BLE001 - never 5xx the webhook
        log.exception("outbound handler error: %s", e)
        result = {"error": "handled"}
    return JSONResponse({"received": True, **result})


@app.api_route("/bulkgate/inbound/{token}", methods=["GET", "POST"])
async def bulkgate_inbound(token: str, request: Request):
    """Bulkgate DLR + incoming SMS callback (per-installation webhook token).

    Bulkgate delivers DLR/incoming via GET query params by default; POST
    (form or JSON) is also accepted for flexibility.
    """
    params: dict = dict(request.query_params)
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                params = {**params, **body}
        except Exception:  # noqa: BLE001
            try:
                form = await request.form()
                params = {**params, **{k: v for k, v in form.items()}}
            except Exception:  # noqa: BLE001
                pass

    installation = _store().get_installation_by_webhook_token(token)
    if not installation:
        log.warning("inbound: unknown webhook token")
        # Still 200 so Bulkgate doesn't retry forever, but signal ignored.
        return JSONResponse({"received": True, "ignored": "unknown token"})

    try:
        result = await handle_bulkgate_callback(
            params, store=_store(), ghl=_ghl, installation=installation
        )
    except Exception as e:  # noqa: BLE001
        log.exception("inbound handler error: %s", e)
        result = {"error": "handled"}
    return JSONResponse({"received": True, **result})


@app.post("/admin/credentials")
async def set_credentials(request: Request, x_admin_token: str | None = Header(default=None)):
    """Set a location's Bulkgate credentials (simple setup endpoint).

    Body: {location_id, bulkgate_app_id, bulkgate_app_token,
           sender_id_value?, sender_id?, country?}

    Used both by the /setup Custom Page and for manual admin testing.
    """
    body = await request.json()
    location_id = body.get("location_id")
    if not location_id or not _store().get_installation(location_id):
        raise HTTPException(status_code=404, detail="install the app first")

    s = get_settings()
    sender_id = body.get("sender_id", s.default_sender_id)
    sender_id_value = body.get("sender_id_value")
    warnings: list[str] = []

    if sender_id == "gText":
        # Alphanumeric sender rules (Bulkgate/carrier): max 11 chars,
        # letters+digits only, no spaces or special characters. Hungarian
        # carriers do not support text senders at all (silent drop) — warn.
        if not sender_id_value:
            raise HTTPException(
                status_code=422, detail="sender_id=gText requires sender_id_value"
            )
        if len(sender_id_value) > 11 or not sender_id_value.isalnum():
            raise HTTPException(
                status_code=422,
                detail="sender_id_value must be alphanumeric, max 11 chars, no spaces",
            )
        country = body.get("country", s.default_country)
        if country.lower() == "hu":
            warnings.append(
                "Text sender IDs are not supported for Hungary — messages may be "
                "silently dropped. Use gSystem unless Bulkgate whitelisted your sender."
            )

    unicode_mode = body.get("unicode_mode", s.unicode_mode)
    if unicode_mode not in ("never", "auto"):
        raise HTTPException(status_code=422, detail="unicode_mode must be never|auto")

    _store().set_bulkgate_credentials(
        location_id=location_id,
        app_id=body["bulkgate_app_id"],
        app_token=body["bulkgate_app_token"],
        sender_id=sender_id,
        sender_id_value=sender_id_value,
        country=body.get("country", s.default_country),
        unicode_mode=unicode_mode,
    )
    resp: dict = {"ok": True, "location_id": location_id}
    if warnings:
        resp["warnings"] = warnings
    return resp
