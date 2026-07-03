"""HTTP-level smoke tests using FastAPI's TestClient (no outbound network)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_oauth_callback_missing_code():
    r = client.get("/oauth/callback")
    assert r.status_code == 400


def test_inbound_unknown_token_still_200():
    # Webhooks must always 200 so Bulkgate doesn't retry-storm.
    r = client.get("/bulkgate/inbound/not-a-real-token", params={"status": "1"})
    assert r.status_code == 200
    assert r.json()["ignored"] == "unknown token"
