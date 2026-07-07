"""Per-installation persistence layer (SQLite, MVP).

Tables
------
installations   one row per GHL location that installed the app. Holds the
                (encrypted) Bulkgate credentials, the (encrypted) GHL OAuth
                tokens, the sender config and a unique inbound webhook token.
message_map     GHL messageId <-> Bulkgate smsID mapping, used for DLR
                status routing and idempotency / dedupe.
optouts         (location_id, phone) pairs that sent STOP/LEIRATKOZÁS.
events          processed external-event keys for idempotency.

Secrets are encrypted with Fernet (see app.crypto) before being stored, so the
.db file never contains plaintext credentials.
"""
from __future__ import annotations

import secrets
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from app.config import get_settings
from app.crypto import decrypt, encrypt

_SCHEMA = """
CREATE TABLE IF NOT EXISTS installations (
    location_id            TEXT PRIMARY KEY,
    company_id              TEXT,
    bulkgate_app_id_enc    TEXT,
    bulkgate_app_token_enc TEXT,
    sender_id              TEXT DEFAULT 'gSystem',
    sender_id_value        TEXT,
    country                TEXT DEFAULT 'hu',
    unicode_mode           TEXT DEFAULT 'never',
    webhook_confirmed_at   INTEGER DEFAULT 0,
    conversation_provider_id TEXT,
    access_token_enc       TEXT,
    refresh_token_enc      TEXT,
    token_expires_at       INTEGER DEFAULT 0,
    webhook_token          TEXT UNIQUE,
    created_at             INTEGER,
    updated_at             INTEGER
);

CREATE TABLE IF NOT EXISTS message_map (
    ghl_message_id      TEXT,
    bulkgate_message_id TEXT,
    location_id         TEXT,
    direction           TEXT,
    status              TEXT,
    created_at          INTEGER,
    UNIQUE(ghl_message_id),
    UNIQUE(bulkgate_message_id)
);
CREATE INDEX IF NOT EXISTS idx_msgmap_bulkgate ON message_map(bulkgate_message_id);

CREATE TABLE IF NOT EXISTS optouts (
    location_id TEXT,
    phone       TEXT,
    created_at  INTEGER,
    UNIQUE(location_id, phone)
);

CREATE TABLE IF NOT EXISTS events (
    event_key  TEXT PRIMARY KEY,
    created_at INTEGER
);
"""


def _now() -> int:
    return int(time.time())


class Store:
    """Thin SQLite wrapper. One instance is shared across the app."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or get_settings().database_path
        self._init_db()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            # Lightweight migrations for DBs created before these columns existed.
            for ddl in (
                "ALTER TABLE installations ADD COLUMN unicode_mode TEXT DEFAULT 'never'",
                "ALTER TABLE installations ADD COLUMN webhook_confirmed_at INTEGER DEFAULT 0",
            ):
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass  # column already exists

    # ----------------------------------------------------------------- install
    def upsert_installation(
        self,
        *,
        location_id: str,
        company_id: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: int | None = None,
        conversation_provider_id: str | None = None,
    ) -> str:
        """Create/update an installation row. Returns its inbound webhook token."""
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT webhook_token FROM installations WHERE location_id = ?",
                (location_id,),
            ).fetchone()
            webhook_token = (
                existing["webhook_token"]
                if existing and existing["webhook_token"]
                else secrets.token_urlsafe(24)
            )
            conn.execute(
                """
                INSERT INTO installations (
                    location_id, company_id, access_token_enc, refresh_token_enc,
                    token_expires_at, conversation_provider_id, webhook_token,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location_id) DO UPDATE SET
                    company_id      = COALESCE(excluded.company_id, company_id),
                    access_token_enc  = COALESCE(excluded.access_token_enc, access_token_enc),
                    refresh_token_enc = COALESCE(excluded.refresh_token_enc, refresh_token_enc),
                    token_expires_at  = COALESCE(excluded.token_expires_at, token_expires_at),
                    conversation_provider_id = COALESCE(
                        excluded.conversation_provider_id, conversation_provider_id),
                    updated_at = excluded.updated_at
                """,
                (
                    location_id,
                    company_id,
                    encrypt(access_token),
                    encrypt(refresh_token),
                    token_expires_at or 0,
                    conversation_provider_id or None,
                    webhook_token,
                    _now(),
                    _now(),
                ),
            )
            return webhook_token

    def set_bulkgate_credentials(
        self,
        *,
        location_id: str,
        app_id: str,
        app_token: str,
        sender_id: str = "gSystem",
        sender_id_value: str | None = None,
        country: str = "hu",
        unicode_mode: str = "never",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE installations SET
                    bulkgate_app_id_enc = ?,
                    bulkgate_app_token_enc = ?,
                    sender_id = ?,
                    sender_id_value = ?,
                    country = ?,
                    unicode_mode = ?,
                    updated_at = ?
                WHERE location_id = ?
                """,
                (
                    encrypt(app_id),
                    encrypt(app_token),
                    sender_id,
                    sender_id_value,
                    country,
                    unicode_mode,
                    _now(),
                    location_id,
                ),
            )

    def confirm_webhook(self, location_id: str) -> None:
        """Mark that the installer has confirmed pasting the inbound URL into Bulkgate."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE installations SET webhook_confirmed_at = ?, updated_at = ? "
                "WHERE location_id = ?",
                (_now(), _now(), location_id),
            )

    def update_oauth_tokens(
        self,
        *,
        location_id: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: int,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE installations SET
                    access_token_enc = ?, refresh_token_enc = ?,
                    token_expires_at = ?, updated_at = ?
                WHERE location_id = ?
                """,
                (
                    encrypt(access_token),
                    encrypt(refresh_token),
                    token_expires_at,
                    _now(),
                    location_id,
                ),
            )

    def _row_to_installation(self, row: sqlite3.Row) -> dict:
        return {
            "location_id": row["location_id"],
            "company_id": row["company_id"],
            "bulkgate_app_id": decrypt(row["bulkgate_app_id_enc"]),
            "bulkgate_app_token": decrypt(row["bulkgate_app_token_enc"]),
            "sender_id": row["sender_id"] or "gSystem",
            "sender_id_value": row["sender_id_value"],
            "country": row["country"] or "hu",
            "unicode_mode": row["unicode_mode"] or "never",
            "webhook_confirmed_at": row["webhook_confirmed_at"] or 0,
            "conversation_provider_id": row["conversation_provider_id"],
            "access_token": decrypt(row["access_token_enc"]),
            "refresh_token": decrypt(row["refresh_token_enc"]),
            "token_expires_at": row["token_expires_at"] or 0,
            "webhook_token": row["webhook_token"],
        }

    def get_installation(self, location_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM installations WHERE location_id = ?", (location_id,)
            ).fetchone()
            return self._row_to_installation(row) if row else None

    def get_installation_by_webhook_token(self, token: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM installations WHERE webhook_token = ?", (token,)
            ).fetchone()
            return self._row_to_installation(row) if row else None

    def delete_installation(self, location_id: str) -> bool:
        """Hard-delete an installation and all data tied to it.

        Called on the GHL ``UNINSTALL`` webhook so we never retain a user's
        (encrypted) Bulkgate credentials or OAuth tokens after they remove the
        app. Also purges the location's message map and opt-out list. Returns
        True if an installation row was actually deleted.
        """
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM installations WHERE location_id = ?", (location_id,)
            )
            conn.execute(
                "DELETE FROM message_map WHERE location_id = ?", (location_id,)
            )
            conn.execute(
                "DELETE FROM optouts WHERE location_id = ?", (location_id,)
            )
            return cur.rowcount > 0

    # -------------------------------------------------------------- message map
    def save_message_map(
        self,
        *,
        ghl_message_id: str | None,
        bulkgate_message_id: str | None,
        location_id: str,
        direction: str,
        status: str = "",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO message_map (
                    ghl_message_id, bulkgate_message_id, location_id,
                    direction, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ghl_message_id,
                    bulkgate_message_id,
                    location_id,
                    direction,
                    status,
                    _now(),
                ),
            )

    def find_by_bulkgate_id(self, bulkgate_message_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM message_map WHERE bulkgate_message_id = ?",
                (bulkgate_message_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_status_by_bulkgate_id(
        self, bulkgate_message_id: str, status: str
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE message_map SET status = ? WHERE bulkgate_message_id = ?",
                (status, bulkgate_message_id),
            )

    def ghl_message_seen(self, ghl_message_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM message_map WHERE ghl_message_id = ?",
                (ghl_message_id,),
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------ optouts
    def add_optout(self, location_id: str, phone: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO optouts (location_id, phone, created_at) "
                "VALUES (?, ?, ?)",
                (location_id, phone, _now()),
            )

    def remove_optout(self, location_id: str, phone: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM optouts WHERE location_id = ? AND phone = ?",
                (location_id, phone),
            )

    def is_opted_out(self, location_id: str, phone: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM optouts WHERE location_id = ? AND phone = ?",
                (location_id, phone),
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------- idempotency
    def mark_event(self, event_key: str) -> bool:
        """Record an event key. Returns True if NEW, False if already seen."""
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO events (event_key, created_at) VALUES (?, ?)",
                    (event_key, _now()),
                )
                return True
            except sqlite3.IntegrityError:
                return False


# Module-level singleton, lazily created.
_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
