"""Inbound SMS + DLR callback handling (Bulkgate status codes)."""
import pytest

from app.services import handle_bulkgate_callback
from tests.conftest import FakeGHL, load_fixture


def _seed_outbound_mapping(store):
    store.save_message_map(
        ghl_message_id="MSG_GHL_001",
        bulkgate_message_id="transactional-64afe5f28ffc2-0",
        location_id="LOC_TEST_1",
        direction="outbound",
        status="sent",
    )


@pytest.mark.asyncio
async def test_dlr_delivered_updates_status(installed_store):
    _seed_outbound_mapping(installed_store)
    ghl = FakeGHL()
    params = load_fixture("bulkgate_dlr_delivered.json")
    inst = installed_store.get_installation("LOC_TEST_1")

    res = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert res["dlr"] == "delivered"
    assert ghl.status_updates[0]["message_id"] == "MSG_GHL_001"
    assert ghl.status_updates[0]["status"] == "delivered"


@pytest.mark.asyncio
async def test_dlr_failed_marks_undelivered(installed_store):
    _seed_outbound_mapping(installed_store)
    ghl = FakeGHL()
    params = load_fixture("bulkgate_dlr_failed.json")
    inst = installed_store.get_installation("LOC_TEST_1")

    res = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert res["dlr"] == "not_delivered"
    assert ghl.status_updates[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_dlr_idempotent(installed_store):
    _seed_outbound_mapping(installed_store)
    ghl = FakeGHL()
    params = load_fixture("bulkgate_dlr_delivered.json")
    inst = installed_store.get_installation("LOC_TEST_1")

    await handle_bulkgate_callback(params, store=installed_store, ghl=ghl, installation=inst)
    res2 = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert "deduped" in res2
    assert len(ghl.status_updates) == 1  # not double-applied


@pytest.mark.asyncio
async def test_incoming_message_pushed_to_ghl(installed_store):
    ghl = FakeGHL()
    params = load_fixture("bulkgate_incoming.json")
    inst = installed_store.get_installation("LOC_TEST_1")

    res = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert res["inbound"] is True
    assert ghl.upserts[0]["phone"] == "+36301234567"
    assert ghl.inbound[0]["message"].startswith("Köszönöm")
    assert ghl.inbound[0]["conversation_provider_id"] == "CONVPROV_TEST"


@pytest.mark.asyncio
async def test_incoming_stop_sets_optout(installed_store):
    ghl = FakeGHL()
    params = load_fixture("bulkgate_incoming_stop.json")
    inst = installed_store.get_installation("LOC_TEST_1")

    res = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert res["opted_out"] is True
    assert installed_store.is_opted_out("LOC_TEST_1", "36301234567") is True


@pytest.mark.asyncio
async def test_dlr_unknown_smsid_ignored(installed_store):
    ghl = FakeGHL()
    inst = installed_store.get_installation("LOC_TEST_1")
    params = {"status": "1", "smsID": "does-not-exist"}
    res = await handle_bulkgate_callback(
        params, store=installed_store, ghl=ghl, installation=inst
    )
    assert res["ignored"] == "unknown smsID"
    assert ghl.status_updates == []
