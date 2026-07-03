"""Symmetric encryption for credentials at rest (Fernet / AES-128-CBC + HMAC).

The Bulkgate application_id / application_token and the GHL OAuth tokens are
encrypted before being written to SQLite so the database file never contains
plaintext secrets.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().fernet_key
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt(plaintext: str | None) -> str | None:
    """Encrypt a string; ``None`` passes through unchanged."""
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str | None) -> str | None:
    """Decrypt a previously :func:`encrypt`-ed string; ``None`` passes through."""
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - defensive
        raise ValueError("Could not decrypt value (wrong FERNET_KEY?)") from exc
