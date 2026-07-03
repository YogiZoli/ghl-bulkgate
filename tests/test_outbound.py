"""Outbound flow: GHL webhook -> Bulkgate send -> GHL status update."""
import pytest

from app.bulkgate_client import BulkgateResult
from app.services import handle_outbound
from tests.conftest import FakeBulkgate, FakeGHL, load_fixture


@pytest.mark.asyncio
async def test_outbound_happy_path(installed_store):
    payload = load_fixture("ghl_outbound_sms.json")
    bulkgate = FakeBulkgate(
        BulkgateResult(ok=True, message_id="BG1", status="sent", number="36301234567")
    )
    ghl = FakeGHL()

    result = await handle_outbound(
        payload, store=installed_store, bulkgate=bulkgate, ghl=ghl
    )

    assert result["sent"] is True
    # Bulkgate called with normalized number + sender name.
    assert bulkgate.calls[0]["number"] == "36301234567"
    assert bulkgate.calls[0]["sender_id_value"] == "MyBrand"
    # GHL status set to configured accept status ("pending" until the DLR
    # confirms — Bulkgate "accepted" is not delivery).
    assert ghl.status_updates[0]["status"] == "pending"
    # Mapping stored for DLR routing.
    assert installed_store.find_by_bulkgate_id("BG1")["ghl_message_id"] == "MSG_GHL_001"


@pytest.mark.asyncio
async def test_outbound_dedupe(installed_store):
    payload = load_fixture("ghl_outbound_sms.json")
    bulkgate = FakeBulkgate(BulkgateResult(ok=True, message_id="BG1", status="sent"))
    ghl = FakeGHL()

    await handle_outbound(payload, store=installed_store, bulkgate=bulkgate, ghl=ghl)
    # Second delivery of same messageId must NOT call Bulkgate again.
    res2 = await handle_outbound(
        payload, store=installed_store, bulkgate=bulkgate, ghl=ghl
    )
    assert "deduped" in res2
    assert len(bulkgate.calls) == 1


@pytest.mark.asyncio
async def test_outbound_invalid_number_marks_undelivered(installed_store):
    payload = dict(load_fixture("ghl_outbound_sms.json"))
    payload["phone"] = "not-a-number"
    bulkgate = FakeBulkgate(BulkgateResult(ok=True, message_id="BGX"))
    ghl = FakeGHL()

    res = await handle_outbound(
        payload, store=installed_store, bulkgate=bulkgate, ghl=ghl
    )
    assert res["ignored"] == "invalid number"
    assert bulkgate.calls == []  # never sent
    assert ghl.status_updates[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_outbound_opted_out_blocks_send(installed_store):
    installed_store.add_optout("LOC_TEST_1", "36301234567")
    payload = load_fixture("ghl_outbound_sms.json")
    bulkgate = FakeBulkgate(BulkgateResult(ok=True, message_id="BGY"))
    ghl = FakeGHL()

    res = await handle_outbound(
        payload, store=installed_store, bulkgate=bulkgate, ghl=ghl
    )
    assert res["ignored"] == "opted out"
    assert bulkgate.calls == []
    assert ghl.status_updates[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_outbound_bulkgate_failure_sets_failed(installed_store):
    payload = load_fixture("ghl_outbound_sms.json")
    bulkgate = FakeBulkgate(
        BulkgateResult(ok=False, error_type="invalid_sender", error="invalid_sender")
    )
    ghl = FakeGHL()

    res = await handle_outbound(
        payload, store=installed_store, bulkgate=bulkgate, ghl=ghl
    )
    assert res["sent"] is False
    assert ghl.status_updates[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_outbound_unconfigured_location_is_ignored(store):
    # store has no installation at all
    payload = load_fixture("ghl_outbound_sms.json")
    bulkgate = FakeBulkgate(BulkgateResult(ok=True))
    ghl = FakeGHL()
    res = await handle_outbound(payload, store=store, bulkgate=bulkgate, ghl=ghl)
    assert res["ignored"] == "location not configured"
    assert bulkgate.calls == []
