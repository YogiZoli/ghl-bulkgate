"""Store: encryption round-trip, dedupe, opt-outs, idempotency."""
import sqlite3

from app.crypto import decrypt


def test_credentials_encrypted_at_rest(installed_store):
    # Raw DB column must NOT contain plaintext token.
    conn = sqlite3.connect(installed_store.path)
    row = conn.execute(
        "SELECT bulkgate_app_token_enc FROM installations WHERE location_id=?",
        ("LOC_TEST_1",),
    ).fetchone()
    conn.close()
    enc = row[0]
    assert enc != "BG_APP_TOKEN"
    assert decrypt(enc) == "BG_APP_TOKEN"


def test_installation_roundtrip(installed_store):
    inst = installed_store.get_installation("LOC_TEST_1")
    assert inst["bulkgate_app_id"] == "BG_APP_ID"
    assert inst["sender_id_value"] == "MyBrand"
    assert inst["webhook_token"]


def test_webhook_token_lookup(installed_store):
    inst = installed_store.get_installation("LOC_TEST_1")
    found = installed_store.get_installation_by_webhook_token(inst["webhook_token"])
    assert found["location_id"] == "LOC_TEST_1"


def test_message_map_dedupe(installed_store):
    installed_store.save_message_map(
        ghl_message_id="M1",
        bulkgate_message_id="B1",
        location_id="LOC_TEST_1",
        direction="outbound",
    )
    assert installed_store.ghl_message_seen("M1") is True
    assert installed_store.ghl_message_seen("M2") is False
    assert installed_store.find_by_bulkgate_id("B1")["ghl_message_id"] == "M1"


def test_optouts(installed_store):
    installed_store.add_optout("LOC_TEST_1", "36301234567")
    assert installed_store.is_opted_out("LOC_TEST_1", "36301234567") is True
    installed_store.remove_optout("LOC_TEST_1", "36301234567")
    assert installed_store.is_opted_out("LOC_TEST_1", "36301234567") is False


def test_event_idempotency(installed_store):
    assert installed_store.mark_event("evt:1") is True
    assert installed_store.mark_event("evt:1") is False


def test_delete_installation_purges_everything(installed_store):
    installed_store.save_message_map(
        ghl_message_id="M1",
        bulkgate_message_id="B1",
        location_id="LOC_TEST_1",
        direction="outbound",
    )
    installed_store.add_optout("LOC_TEST_1", "36301234567")

    assert installed_store.delete_installation("LOC_TEST_1") is True

    # Credentials/tokens gone.
    assert installed_store.get_installation("LOC_TEST_1") is None
    # Raw DB rows for this location gone too (no lingering secrets).
    conn = sqlite3.connect(installed_store.path)
    assert conn.execute(
        "SELECT COUNT(*) FROM installations WHERE location_id=?", ("LOC_TEST_1",)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM message_map WHERE location_id=?", ("LOC_TEST_1",)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM optouts WHERE location_id=?", ("LOC_TEST_1",)
    ).fetchone()[0] == 0
    conn.close()

    # Deleting a non-existent install is a harmless no-op.
    assert installed_store.delete_installation("NOPE") is False
