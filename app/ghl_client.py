"""GoHighLevel API v2 client (OAuth, inbound message, message-status, contacts).

Base    : https://services.leadconnectorhq.com
Version : 2021-04-15 (conversations endpoints)
Docs    :
  OAuth token      https://marketplace.gohighlevel.com/docs/oauth/...
  Inbound message  /conversations/messages/inbound
  Update status    /conversations/messages/{messageId}/status
  Upsert contact   /contacts/upsert

Only the conversation-provider marketplace app token may update message status,
which is exactly the token we obtain per-installation via OAuth.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_at: int
    location_id: str | None = None
    company_id: str | None = None
    scope: str | None = None
    raw: dict | None = None


class GHLClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        version: str | None = None,
        timeout: float = 15.0,
    ):
        s = get_settings()
        self.base_url = (base_url or s.ghl_api_base).rstrip("/")
        self.version = version or s.ghl_api_version
        self.timeout = timeout

    def _headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Version": self.version,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ----------------------------------------------------------------- OAuth
    async def exchange_token(
        self,
        *,
        grant_type: str,
        code: str | None = None,
        refresh_token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> TokenBundle:
        """Exchange an auth ``code`` (or ``refresh_token``) for tokens."""
        s = get_settings()
        form = {
            "client_id": s.ghl_client_id,
            "client_secret": s.ghl_client_secret,
            "grant_type": grant_type,
            "user_type": "Location",
        }
        if grant_type == "authorization_code":
            form["code"] = code
            form["redirect_uri"] = s.ghl_redirect_uri
        elif grant_type == "refresh_token":
            form["refresh_token"] = refresh_token

        owns = client is None
        client = client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                f"{self.base_url}/oauth/token",
                data=form,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return TokenBundle(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token or ""),
                expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
                location_id=data.get("locationId"),
                company_id=data.get("companyId"),
                scope=data.get("scope"),
                raw=data,
            )
        finally:
            if owns:
                await client.aclose()

    # ------------------------------------------------------------- contacts
    async def upsert_contact(
        self,
        *,
        access_token: str,
        location_id: str,
        phone: str,
        name: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> str | None:
        """Find-or-create a contact by phone; returns the contactId.

        Used on inbound SMS so a reply lands on the right (or a new) contact.
        """
        body: dict = {"locationId": location_id, "phone": phone}
        if name:
            body["name"] = name

        owns = client is None
        client = client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                f"{self.base_url}/contacts/upsert",
                json=body,
                headers=self._headers(access_token),
            )
            resp.raise_for_status()
            data = resp.json()
            contact = data.get("contact") or {}
            return contact.get("id") or data.get("id")
        finally:
            if owns:
                await client.aclose()

    # ------------------------------------------------------- inbound message
    async def add_inbound_message(
        self,
        *,
        access_token: str,
        contact_id: str,
        message: str,
        conversation_provider_id: str | None = None,
        message_type: str = "SMS",
        client: httpx.AsyncClient | None = None,
    ) -> dict:
        """POST /conversations/messages/inbound — push a received SMS into GHL."""
        body: dict = {
            "type": message_type,
            "contactId": contact_id,
            "message": message,
            "direction": "inbound",
        }
        # conversationProviderId is required only for the "Add new conversation
        # channel" model; harmless to include when known.
        if conversation_provider_id:
            body["conversationProviderId"] = conversation_provider_id

        owns = client is None
        client = client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                f"{self.base_url}/conversations/messages/inbound",
                json=body,
                headers=self._headers(access_token),
            )
            resp.raise_for_status()
            return resp.json()
        finally:
            if owns:
                await client.aclose()

    # --------------------------------------------------------- message status
    async def update_message_status(
        self,
        *,
        access_token: str,
        message_id: str,
        status: str,
        error: dict | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict:
        """PUT /conversations/messages/{messageId}/status.

        Valid ``status`` values: delivered | failed | pending | read.
        """
        body: dict = {"status": status}
        if error:
            body["error"] = error

        owns = client is None
        client = client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.put(
                f"{self.base_url}/conversations/messages/{message_id}/status",
                json=body,
                headers=self._headers(access_token),
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {"ok": True}
        finally:
            if owns:
                await client.aclose()
