"""Contracts for mapping the synchronous AutoCAD adapter into MCP responses."""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest
from autocad_mcp.adapter.capabilities import (
    AdapterCapability,
    AdapterCapabilityIssue,
    AdapterCapabilityIssueCode,
    AdapterCapabilityReport,
)
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode, ConnectionInfo
from autocad_mcp.adapter.provider import StaticAdapterProvider
from autocad_mcp.core.models import (
    ErrorCode,
    GetEntityInfoInput,
    ListEntitiesInput,
    ServerStatusInput,
    ToolFailure,
    ToolSuccess,
)


def _service(adapter: FakeAutoCADAdapter):
    from autocad_mcp.adapter.service import AdapterToolService

    return AdapterToolService(StaticAdapterProvider(adapter))


@pytest.mark.anyio
async def test_status_maps_connection_and_capabilities() -> None:
    """Dropping a status field would break the established status contract."""
    response = await _service(FakeAutoCADAdapter()).invoke(ServerStatusInput())

    assert response == ToolSuccess(
        {
            "mcp_server": "running",
            "autocad_connected": True,
            "active_document": "contract.dwg",
            "product": "AutoCAD",
            "version": "contract",
            "release_hint": "contract",
            "read_only": True,
            "tools_available": 3,
            "transport": "stdio",
            "capabilities": [
                "active_document",
                "connection",
                "get_entity_info",
                "list_entities",
            ],
            "capability_issues": [],
        }
    )


@pytest.mark.anyio
async def test_status_maps_structured_capability_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flattening a capability issue would hide why an operation is unavailable."""
    adapter = FakeAutoCADAdapter()
    issue = AdapterCapabilityIssue(
        AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE,
        AdapterCapability.GET_ENTITY_INFO,
        "ObjectID",
        "Required AutoCAD member is unavailable",
    )
    monkeypatch.setattr(
        adapter,
        "_connection_info",
        lambda: ConnectionInfo(
            True,
            "AutoCAD",
            "contract",
            "contract",
            "contract.dwg",
            True,
            AdapterCapabilityReport(frozenset({AdapterCapability.CONNECTION}), (issue,)),
        ),
    )

    response = await _service(adapter).invoke(ServerStatusInput())

    assert response == ToolSuccess(
        {
            "mcp_server": "running",
            "autocad_connected": True,
            "active_document": "contract.dwg",
            "product": "AutoCAD",
            "version": "contract",
            "release_hint": "contract",
            "read_only": True,
            "tools_available": 3,
            "transport": "stdio",
            "capabilities": ["connection"],
            "capability_issues": [
                {
                    "code": "MEMBER_UNAVAILABLE",
                    "capability": "get_entity_info",
                    "member": "ObjectID",
                    "message": "Required AutoCAD member is unavailable",
                }
            ],
        }
    )


@pytest.mark.anyio
async def test_list_maps_ordered_entity_identities() -> None:
    """Changing summary order or omitting identity fields would break list clients."""
    response = await _service(FakeAutoCADAdapter()).invoke(ListEntitiesInput())

    assert response == ToolSuccess(
        {
            "count": 1,
            "entities": [{"id": 1001, "handle": "10", "type": "AcDbLine", "layer": "0"}],
        }
    )


@pytest.mark.anyio
async def test_detail_maps_identity_and_allowlisted_properties() -> None:
    """Omitting an adapter-provided allowlisted property would break detail clients."""
    response = await _service(FakeAutoCADAdapter()).invoke(GetEntityInfoInput(1001))

    assert response == ToolSuccess(
        {
            "entity": {
                "id": 1001,
                "handle": "10",
                "type": "AcDbLine",
                "layer": "0",
                "properties": {"color": 256, "linetype": "ByLayer"},
            }
        }
    )


@pytest.mark.anyio
@pytest.mark.parametrize("code", tuple(AdapterErrorCode))
async def test_adapter_errors_preserve_public_error_fields(code: AdapterErrorCode) -> None:
    """A mismatched adapter error code or leaked error fields would break the public boundary."""
    adapter = FakeAutoCADAdapter()
    adapter.fail_next(
        AdapterError(
            code,
            "Public adapter failure",
            retryable=True,
            details={"context": {"operation": "status"}},
        )
    )

    response = await _service(adapter).invoke(ServerStatusInput())

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode(code.value)
    assert response.error.message == "Public adapter failure"
    assert response.error.retryable is True
    assert response.error.details == {"context": {"operation": "status"}}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_input", "expected_call"),
    [
        (ServerStatusInput(), ("status", None)),
        (ListEntitiesInput(), ("list_entities", None)),
        (GetEntityInfoInput(1001), ("get_entity_info", 1001)),
    ],
)
async def test_each_adapter_operation_crosses_to_thread_once(
    monkeypatch: pytest.MonkeyPatch, tool_input: object, expected_call: tuple[str, object]
) -> None:
    """Running a synchronous adapter call on the event loop would block MCP clients."""
    original_to_thread = asyncio.to_thread
    crossings: list[object] = []

    async def recording_to_thread(function, /, *args, **kwargs):
        crossings.append(function)
        return await original_to_thread(function, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", recording_to_thread)
    adapter = FakeAutoCADAdapter()

    response = await _service(adapter).invoke(tool_input)  # type: ignore[arg-type]

    assert isinstance(response, ToolSuccess)
    assert len(crossings) == 1
    assert adapter.calls == (expected_call,)


def test_production_runtime_imports_canonical_and_shim_without_com_modules() -> None:
    """Eager COM loading would make the production stdio entrypoint non-portable."""
    com_modules = {"pythoncom", "win32com", "win32com.client", "pyautocad"}
    for name in (*com_modules, "src.server", "autocad_mcp.server"):
        sys.modules.pop(name, None)

    canonical = importlib.import_module("autocad_mcp.server")
    shim = importlib.import_module("src.server")

    assert shim.server is canonical.server
    assert com_modules.isdisjoint(sys.modules)
