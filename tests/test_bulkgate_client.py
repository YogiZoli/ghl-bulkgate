"""Bulkgate client payload-building and response-parsing tests (no network)."""
from app.bulkgate_client import BulkgateClient
from tests.conftest import load_fixture


def test_build_payload_sets_sender_and_country():
    c = BulkgateClient()
    p = c.build_payload(
        app_id="A",
        app_token="T",
        number="36301234567",
        text="Hello",
        country="hu",
        sender_id="gText",
        sender_id_value="MyBrand",
    )
    assert p["application_id"] == "A"
    assert p["application_token"] == "T"
    assert p["number"] == "36301234567"
    assert p["country"] == "hu"
    assert p["channel"]["sms"]["sender_id"] == "gText"
    assert p["channel"]["sms"]["sender_id_value"] == "MyBrand"
    assert p["channel"]["sms"]["unicode"] is False


def test_build_payload_unicode_never_by_default():
    """Cost-protection rule: unicode stays false so Bulkgate transliterates
    accents (ő→o) and GSM-7 pricing is preserved."""
    c = BulkgateClient()
    p = c.build_payload(
        app_id="A", app_token="T", number="36301234567", text="Üdvözlő ű"
    )
    assert p["channel"]["sms"]["unicode"] is False


def test_build_payload_unicode_auto_detects_accents():
    c = BulkgateClient()
    p = c.build_payload(
        app_id="A",
        app_token="T",
        number="36301234567",
        text="Üdvözlő ű",
        unicode_mode="auto",
    )
    assert p["channel"]["sms"]["unicode"] is True


def test_build_payload_default_sender_is_gsystem():
    """HU carriers do not support gText — gSystem must be the default."""
    c = BulkgateClient()
    p = c.build_payload(app_id="A", app_token="T", number="36301234567", text="Hi")
    assert p["channel"]["sms"]["sender_id"] == "gSystem"
    assert "sender_id_value" not in p["channel"]["sms"]


def test_build_payload_ignores_sender_value_for_gsystem():
    c = BulkgateClient()
    p = c.build_payload(
        app_id="A",
        app_token="T",
        number="36301234567",
        text="Hi",
        sender_id="gSystem",
        sender_id_value="MyBrand",
    )
    assert "sender_id_value" not in p["channel"]["sms"]


def test_parse_success():
    c = BulkgateClient()
    data = load_fixture("bulkgate_send_success.json")
    r = c.parse_response(200, data, text="Hello")
    assert r.ok is True
    assert r.message_id == "transactional-64afe5f28ffc2-0"
    assert r.status == "sent"
    assert r.number == "36301234567"


def test_parse_error_envelope():
    c = BulkgateClient()
    data = load_fixture("bulkgate_send_error.json")
    r = c.parse_response(400, data, text="Hello")
    assert r.ok is False
    assert r.error_type == "invalid_phone_number"
