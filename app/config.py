"""Application configuration loaded from environment variables.

All secrets (GHL OAuth creds, Fernet key) come from the environment so nothing
sensitive is ever committed. See .env.example for the full list.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- GHL OAuth (public Marketplace app) ---
    ghl_client_id: str = "test-client-id"
    ghl_client_secret: str = "test-client-secret"
    ghl_redirect_uri: str = "http://localhost:8080/oauth/callback"
    ghl_api_base: str = "https://services.leadconnectorhq.com"
    ghl_api_version: str = "2021-04-15"

    # Conversation provider id. Empty when using the "replace default SMS
    # provider" model (then it is not required by the inbound API).
    ghl_conversation_provider_id: str = ""

    # Status to write back to GHL when Bulkgate ACCEPTS the message.
    # "accepted" is NOT delivery (Bulkgate can accept and the carrier still
    # silently drops it — see support ticket HZL-CTQKD-699), so we report
    # "pending" here and only set delivered/failed from the DLR callback.
    # Valid GHL statuses: delivered | failed | pending | read.
    ghl_status_on_accept: str = "pending"

    # Public base URL of this service (e.g. https://<railway-host>). Used to
    # build the per-install inbound webhook URL. Falls back to deriving it
    # from ghl_redirect_uri when empty.
    public_base_url: str = ""

    # --- Crypto ---
    # 32-byte url-safe base64 Fernet key. A throwaway default is used in tests;
    # production MUST set a real key via env.
    fernet_key: str = "dGVzdC1rZXktMzItYnl0ZXMtZm9yLXVuaXQtdGVzdHM="

    # --- Storage ---
    database_path: str = "./ghl_bulkgate.db"

    # --- Bulkgate ---
    bulkgate_api_url: str = (
        "https://portal.bulkgate.com/api/2.0/advanced/transactional"
    )
    default_country: str = "hu"
    # HU carriers do not support text sender IDs (gText) — Bulkgate support
    # confirmed sends are silently dropped. gSystem is the safe default;
    # gText only per-install where the destination supports it AND the sender
    # name is whitelisted (max 11 chars, alphanumeric, no spaces).
    default_sender_id: str = "gSystem"
    default_sender_id_value: str = ""
    # "never" (default): unicode always false -> Bulkgate transliterates
    # accents (ő→o), GSM-7 pricing preserved (cost-protection rule).
    # "auto": set unicode flag from real GSM-7 detection.
    unicode_mode: str = "never"

    # --- App ---
    log_level: str = "INFO"
    port: int = 8080


@lru_cache
def get_settings() -> Settings:
    return Settings()
