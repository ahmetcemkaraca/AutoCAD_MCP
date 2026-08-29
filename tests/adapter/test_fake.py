from __future__ import annotations

from dataclasses import replace

import pytest
from autocad_mcp.adapter.capabilities import AdapterCapability
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode, EntityDetails


def test_fake_returns_deterministic_existing_identity_and_immutable_tuples() -> None:
    adapter = FakeAutoCADAdapter()

    entities = adapter.list_entities()

    assert entities[0].object_id == 1001
    assert entities[0].handle == "10"
    assert adapter.get_entity_info(1001).properties == {"color": 256, "linetype": "ByLayer"}
    with pytest.raises(AttributeError):
        entities.append(entities[0])  # type: ignore[attr-defined]


def test_fake_records_each_adapter_operation_in_order() -> None:
    adapter = FakeAutoCADAdapter()

    adapter.status()
    adapter.reconnect()
    adapter.list_entities()
    adapter.get_entity_info(1001)

    assert adapter.calls == (
        ("status", None),
        ("reconnect", None),
        ("list_entities", None),
        ("get_entity_info", 1001),
    )


def test_fake_reports_disconnected_state_and_rejects_document_operations() -> None:
    adapter = FakeAutoCADAdapter(connected=False)

    status = adapter.status()
    assert status.connected is False
    assert status.active_document is None
    assert status.capabilities.available == frozenset()
    with pytest.raises(AdapterError) as raised:
        adapter.list_entities()
    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert raised.value.retryable is True


def test_fake_reports_no_document_state_and_rejects_entity_operations() -> None:
    adapter = FakeAutoCADAdapter(document_name=None)

    status = adapter.status()
    assert status.connected is True
    assert status.active_document is None
    assert status.capabilities.available == frozenset({AdapterCapability.CONNECTION})
    with pytest.raises(AdapterError) as raised:
        adapter.get_entity_info(1001)
    assert raised.value.code is AdapterErrorCode.NO_ACTIVE_DOCUMENT


@pytest.mark.parametrize("code", tuple(AdapterErrorCode))
def test_fail_next_raises_each_public_error_once_then_clears(code: AdapterErrorCode) -> None:
    adapter = FakeAutoCADAdapter()
    injected = AdapterError(code, "public failure", retryable=True, details={"code": str(code)})
    adapter.fail_next(injected)

    with pytest.raises(AdapterError) as raised:
        adapter.status()
    assert raised.value is injected
    assert adapter.status().connected is True


def test_fake_has_no_creation_or_editing_surface() -> None:
    adapter = FakeAutoCADAdapter()
    forbidden = {
        "add_entity",
        "create_entity",
        "delete_entity",
        "edit_entity",
        "execute",
        "open_drawing",
        "save_drawing",
        "send_command",
        "set_property",
    }

    assert not forbidden & set(dir(adapter))
    assert set(adapter.__class__.__dict__) >= {
        "status",
        "reconnect",
        "list_entities",
        "get_entity_info",
    }


def test_fake_uses_supplied_immutable_entity_records() -> None:
    entity = EntityDetails(2002, "20", "AcDbCircle", "circles", {"radius": 2.5})
    adapter = FakeAutoCADAdapter(entities=(entity,))

    assert adapter.get_entity_info(2002) == entity
    assert adapter.list_entities()[0].handle == "20"
    assert replace(entity, layer="changed").layer == "changed"


def test_fake_preserves_an_explicit_empty_entity_tuple() -> None:
    adapter = FakeAutoCADAdapter(entities=())

    assert adapter.list_entities() == ()
