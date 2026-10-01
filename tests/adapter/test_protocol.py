from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest
from autocad_mcp.adapter.capabilities import AdapterCapability, AdapterCapabilityReport
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.protocol import (
    AdapterError,
    AdapterErrorCode,
    AutoCADAdapter,
    ConnectionInfo,
    EntityDetails,
    EntitySummary,
)
from autocad_mcp.adapter.provider import StaticAdapterProvider


def accepts_adapter(adapter: AutoCADAdapter) -> AutoCADAdapter:
    return adapter


def exercise_basic_adapter_contract(adapter: AutoCADAdapter) -> None:
    status = adapter.status()
    assert status.connected is True
    assert status.active_document == "contract.dwg"
    assert status.capabilities.supports(AdapterCapability.CONNECTION)
    assert status.capabilities.supports(AdapterCapability.ACTIVE_DOCUMENT)
    assert status.capabilities.supports(AdapterCapability.LIST_ENTITIES)
    assert status.capabilities.supports(AdapterCapability.GET_ENTITY_INFO)
    assert adapter.reconnect() == status

    entities = adapter.list_entities()
    assert entities == (
        EntitySummary(1001, "10", "AcDbLine", "0"),
    )
    assert adapter.get_entity_info(1001) == EntityDetails(
        1001,
        "10",
        "AcDbLine",
        "0",
        {"color": 256, "linetype": "ByLayer"},
    )
    with pytest.raises(AdapterError) as raised:
        adapter.get_entity_info(9999)
    assert raised.value.code is AdapterErrorCode.ENTITY_NOT_FOUND
    assert raised.value.details == {"object_id": 9999}


def test_fake_conforms_to_the_four_method_adapter_contract() -> None:
    fake = accepts_adapter(FakeAutoCADAdapter())

    exercise_basic_adapter_contract(fake)
    assert StaticAdapterProvider(fake).get() is fake


def test_protocol_values_and_error_are_immutable() -> None:
    capabilities = AdapterCapabilityReport(frozenset({AdapterCapability.CONNECTION}))
    connection = ConnectionInfo(True, "AutoCAD", "2026", "2026", "contract.dwg", True, capabilities)
    summary = EntitySummary(1001, "10", "AcDbLine", "0")
    properties = {"metadata": {"tags": ["original"]}}
    details = EntityDetails(1001, "10", "AcDbLine", "0", properties)
    error = AdapterError(AdapterErrorCode.COM_BUSY, "AutoCAD is busy", details=properties)

    for value, field, replacement in (
        (connection, "connected", False),
        (summary, "handle", "11"),
        (details, "layer", "other"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field, replacement)
    with pytest.raises(TypeError):
        details.properties["metadata"] = {}  # type: ignore[index]
    with pytest.raises(AttributeError):
        error.code = AdapterErrorCode.AUTOCAD_UNAVAILABLE
    with pytest.raises(TypeError):
        error.details["metadata"] = {}  # type: ignore[index]

    properties["metadata"]["source"] = "source mutation"
    properties["metadata"]["tags"].append("source mutation")

    assert details.properties == {"metadata": {"tags": ["original"]}}
    assert error.details == {"metadata": {"tags": ["original"]}}
    with pytest.raises(TypeError):
        details.properties["metadata"]["source"] = "exposed mutation"  # type: ignore[index]
    with pytest.raises(TypeError):
        error.details["metadata"]["source"] = "exposed mutation"  # type: ignore[index]
    with pytest.raises(TypeError):
        details.properties["metadata"]["tags"].append("exposed mutation")  # type: ignore[index]
    with pytest.raises(TypeError):
        error.details["metadata"]["tags"].append("exposed mutation")  # type: ignore[index]
    assert json.dumps(details.properties, sort_keys=True) == '{"metadata": {"tags": ["original"]}}'
    assert json.dumps(error.details, sort_keys=True) == '{"metadata": {"tags": ["original"]}}'


def test_public_protocol_exposes_only_read_only_adapter_methods() -> None:
    method_names = {
        name
        for name, member in AutoCADAdapter.__dict__.items()
        if callable(member) and not name.startswith("_")
    }

    assert method_names == {"status", "reconnect", "list_entities", "get_entity_info"}
