"""Bulkgate Advanced Transactional API v2 client.

Endpoint : POST https://portal.bulkgate.com/api/2.0/advanced/transactional
Auth     : application_id + application_token in the JSON body.
Docs     : https://help.bulkgate.com/docs/en/http-advanced-transactional-v2.html

We send a single recipient per request (the GHL outbound webhook is one
contact at a time).

Sender ID — hard-won field lessons (Bulkgate support ticket HZL-CTQKD-699):
  * For Hungary, TEXT sender IDs (``gText``) are NOT supported by the carriers /
    Bulkgate pricelist — sends are silently dropped (API still says "accepted").
  * Default is therefore ``gSystem``. ``gText`` + ``sender_id_value`` may be
    configured per install ONLY where the destination country supports it and
    the sender name has been whitelisted with Bulkgate (max 11 chars,
    alphanumeric, no spaces/special characters).

Unicode — cost protection (Hungarian market):
  * Hungarian ``ő``/``ű`` force UCS-2 → the 160-char budget drops to 70 and an
    average message bills as 2-3 SMS.
  * With ``unicode=false`` Bulkgate transliterates accents (``ő`` → ``o``) and
    keeps GSM-7 pricing. That is the default business rule here
    (``unicode_mode="never"``); ``"auto"`` enables real UCS-2 detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.sms_text import needs_unicode, segment_count

DEFAULT_API_URL = "https://portal.bulkgate.com/api/2.0/advanced/transactional"


@dataclass
class BulkgateResult:
    ok: bool
    message_id: str | None = None
    status: str | None = None          # bulkgate per-number status (sent/accepted/...)
    number: str | None = None
    error_type: str | None = None
    error: str | None = None
    http_status: int | None = None
    segments: int = 1
    raw: dict = field(default_factory=dict)


class BulkgateClient:
    def __init__(self, api_url: str = DEFAULT_API_URL, timeout: float = 15.0):
        self.api_url = api_url
        self.timeout = timeout

    def build_payload(
        self,
        *,
        app_id: str,
        app_token: str,
        number: str,
        text: str,
        country: str = "hu",
        sender_id: str | None = "gSystem",
        sender_id_value: str | None = None,
        schedule: str | None = None,
        unicode_mode: str = "never",
    ) -> dict:
        """Construct the request body.

        ``unicode_mode="auto"``  -> unicode flag follows GSM-7 detection.
        ``unicode_mode="never"`` -> unicode always false; Bulkgate transliterates
        accents (ő→o) and GSM-7 pricing is preserved (default business rule).
        """
        use_unicode = needs_unicode(text) if unicode_mode == "auto" else False
        sms_obj: dict = {"unicode": use_unicode}
        if sender_id:
            sms_obj["sender_id"] = sender_id
        # sender_id_value is only meaningful for gText (and gOwn/gProfile
        # variants); never attach it to the system sender.
        if sender_id_value and sender_id == "gText":
            sms_obj["sender_id_value"] = sender_id_value

        payload: dict = {
            "application_id": app_id,
            "application_token": app_token,
            "number": number,
            "text": text,
            "country": country,
            "channel": {"sms": sms_obj},
        }
        if schedule:
            payload["schedule"] = schedule
        return payload

    @staticmethod
    def parse_response(http_status: int, data: dict, text: str = "") -> BulkgateResult:
        """Map a Bulkgate JSON response to a :class:`BulkgateResult`.

        Success shape::

            {"data": {"response": [{"status": "...", "message_id": "...",
                                    "number": "..."}], "total": {...}}}

        Error shape::

            {"type": "...", "code": 400, "error": "...", "detail": null}
        """
        segments = segment_count(text) if text else 1

        # Error envelope (top-level type/error).
        if "type" in data and "data" not in data:
            return BulkgateResult(
                ok=False,
                error_type=data.get("type"),
                error=data.get("error"),
                http_status=http_status,
                segments=segments,
                raw=data,
            )

        responses = (data.get("data") or {}).get("response") or []
        if not responses:
            return BulkgateResult(
                ok=False,
                error="empty response from bulkgate",
                http_status=http_status,
                segments=segments,
                raw=data,
            )

        first = responses[0]
        status = (first.get("status") or "").lower()
        # "error"/"invalid_number"/"invalid_sender"/"blacklisted" are failures;
        # "sent"/"accepted"/"scheduled" are successes.
        ok = status not in {
            "error",
            "invalid_number",
            "invalid_sender",
            "blacklisted",
        }
        return BulkgateResult(
            ok=ok and 200 <= http_status < 300,
            message_id=first.get("message_id"),
            status=status,
            number=first.get("number"),
            error=None if ok else status,
            http_status=http_status,
            segments=segments,
            raw=data,
        )

    async def send_sms(
        self,
        *,
        app_id: str,
        app_token: str,
        number: str,
        text: str,
        country: str = "hu",
        sender_id: str | None = "gSystem",
        sender_id_value: str | None = None,
        schedule: str | None = None,
        unicode_mode: str = "never",
        client: httpx.AsyncClient | None = None,
    ) -> BulkgateResult:
        payload = self.build_payload(
            app_id=app_id,
            app_token=app_token,
            number=number,
            text=text,
            country=country,
            sender_id=sender_id,
            sender_id_value=sender_id_value,
            schedule=schedule,
            unicode_mode=unicode_mode,
        )
        owns_client = client is None
        client = client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                data = resp.json()
            except ValueError:
                data = {"type": "non_json_response", "error": resp.text[:500]}
            return self.parse_response(resp.status_code, data, text=text)
        except httpx.HTTPError as exc:
            return BulkgateResult(
                ok=False, error=f"http_error: {exc}", segments=segment_count(text)
            )
        finally:
            if owns_client:
                await client.aclose()
