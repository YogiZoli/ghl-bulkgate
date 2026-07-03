"""Shared test fixtures. No network is used anywhere in the suite.

A real Fernet key is generated for the test session and a temporary SQLite file
backs the store, so encryption + persistence are exercised for real while the
HTTP clients are replaced with fakes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session", autouse=True)
def _test_env(tmp_path_factory):
    """Set env BEFORE app modules read settings, then clear settings cache."""
    db = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["FERNET_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_PATH"] = str(db)
    os.environ["GHL_CONVERSATION_PROVIDER_ID"] = "CONVPROV_TEST"
    os.environ["GHL_STATUS_ON_ACCEPT"] = "pending"

    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store(tmp_path):
    from app.store import Store

    return Store(path=str(tmp_path / "store.db"))


@pytest.fixture
def installed_store(store):
    """A store with one fully-configured installation."""
    store.upsert_installation(
        location_id="LOC_TEST_1",
        company_id="CO_1",
        access_token="ACCESS_1",
        refresh_token="REFRESH_1",
        token_expires_at=9999999999,  # far future -> no refresh
        conversation_provider_id="CONVPROV_TEST",
    )
    store.set_bulkgate_credentials(
        location_id="LOC_TEST_1",
        app_id="BG_APP_ID",
        app_token="BG_APP_TOKEN",
        sender_id="gText",
        sender_id_value="MyBrand",
        country="hu",
    )
    return store


class FakeBulkgate:
    """Drop-in for BulkgateClient.send_sms — records calls, returns canned result."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    async def send_sms(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeGHL:
    """Drop-in for GHLClient — records status updates / inbound pushes."""

    def __init__(self, contact_id="CONTACT_1"):
        self.status_updates = []
        self.inbound = []
        self.upserts = []
        self.contact_id = contact_id

    async def update_message_status(self, **kwargs):
        self.status_updates.append(kwargs)
        return {"ok": True}

    async def add_inbound_message(self, **kwargs):
        self.inbound.append(kwargs)
        return {"messageId": "INBOUND_1"}

    async def upsert_contact(self, **kwargs):
        self.upserts.append(kwargs)
        return self.contact_id

    async def exchange_token(self, **kwargs):  # pragma: no cover - not hit in tests
        from app.ghl_client import TokenBundle

        return TokenBundle(
            access_token="ACCESS_NEW",
            refresh_token="REFRESH_NEW",
            expires_at=9999999999,
            location_id="LOC_TEST_1",
        )
