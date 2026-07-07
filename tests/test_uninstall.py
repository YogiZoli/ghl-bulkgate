"""GHL app-level webhook: signature enforcement + UNINSTALL purges credentials.

We can't forge GHL's real signature, so the signed-path test monkeypatches the
Ed25519 verification key with a throwaway keypair and signs the exact raw body.
"""
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

import app.ghl_webhook as ghl_webhook
from app.main import app
from app.store import get_store

client = TestClient(app)


def test_webhook_rejects_unsigned_request():
    r = client.post("/ghl/webhook", json={"type": "UNINSTALL", "locationId": "X"})
    assert r.status_code == 401


def test_webhook_rejects_bad_signature():
    r = client.post(
        "/ghl/webhook",
        json={"type": "UNINSTALL", "locationId": "X"},
        headers={"x-ghl-signature": "bm90LXZhbGlk"},
    )
    assert r.status_code == 401


def test_uninstall_purges_credentials(monkeypatch):
    # Install a location into the app's live store singleton.
    store = get_store()
    store.upsert_installation(location_id="LOC_UNINSTALL", company_id="CO")
    store.set_bulkgate_credentials(
        location_id="LOC_UNINSTALL", app_id="APPID", app_token="SECRET_TOKEN"
    )
    assert store.get_installation("LOC_UNINSTALL") is not None

    # Swap GHL's public key for a test key we control, then sign the raw body.
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(ghl_webhook, "_ed25519_key", priv.public_key())

    raw = json.dumps({"type": "UNINSTALL", "locationId": "LOC_UNINSTALL"}).encode()
    import base64

    sig = base64.b64encode(priv.sign(raw)).decode()

    r = client.post(
        "/ghl/webhook", content=raw,
        headers={"content-type": "application/json", "x-ghl-signature": sig},
    )
    assert r.status_code == 200
    assert r.json()["purged"] is True
    # Encrypted credentials are gone.
    assert store.get_installation("LOC_UNINSTALL") is None
