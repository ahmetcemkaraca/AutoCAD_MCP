"""Contracts for mapping the synchronous AutoCAD adapter into MCP responses."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

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
    response_json,
)


def _service(adapter: FakeAutoCADAdapter):
    from autocad_mcp.adapter.service import AdapterToolService

    return AdapterToolService(StaticAdapterProvider(adapter))


class RaisingAdapterProvider:
    """Provider double that exposes a public adapter error before an operation starts."""

    def __init__(self, error: AdapterError) -> None:
        self._error = error

    def get(self) -> NoReturn:
        raise self._error


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
            "tools_available": 4,
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
            "tools_available": 4,
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
@pytest.mark.parametrize("code", tuple(AdapterErrorCode))
async def test_provider_errors_preserve_public_error_fields(code: AdapterErrorCode) -> None:
    """A provider error must not be reclassified as an internal dispatch failure."""
    from autocad_mcp.adapter.service import AdapterToolService

    response = await AdapterToolService(
        RaisingAdapterProvider(
            AdapterError(
                code,
                "Public provider failure",
                retryable=True,
                details={"context": {"operation": "provider_get"}},
            )
        )
    ).invoke(ServerStatusInput())

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode(code.value)
    assert response.error.message == "Public provider failure"
    assert response.error.retryable is True
    assert response.error.details == {"context": {"operation": "provider_get"}}


@pytest.mark.anyio
async def test_detail_properties_are_detached_to_plain_json_values() -> None:
    """Returning adapter-private frozen containers would leak an adapter implementation detail."""
    from autocad_mcp.adapter.protocol import EntityDetails

    adapter = FakeAutoCADAdapter(
        entities=(
            EntityDetails(
                1001,
                "10",
                "AcDbLine",
                "0",
                {"nested": {"points": [(1, 2), {"coordinate": [3, 4]}]}},  # type: ignore[list-item]
            ),
        )
    )

    response = await _service(adapter).invoke(GetEntityInfoInput(1001))

    assert isinstance(response, ToolSuccess)
    properties = response.data["entity"]["properties"]  # type: ignore[index]
    assert type(properties) is dict
    assert type(properties["nested"]) is dict
    assert type(properties["nested"]["points"]) is list
    assert type(properties["nested"]["points"][0]) is list
    assert type(properties["nested"]["points"][1]) is dict
    assert json.loads(response_json(response))["entity"]["properties"] == {
        "nested": {"points": [[1, 2], {"coordinate": [3, 4]}]}
    }


@pytest.mark.anyio
async def test_adapter_error_details_are_detached_to_plain_json_values() -> None:
    """Returning frozen adapter error details would leak private container subclasses."""
    adapter = FakeAutoCADAdapter()
    adapter.fail_next(
        AdapterError(
            AdapterErrorCode.COM_BUSY,
            "AutoCAD is busy",
            retryable=True,
            details={"nested": [{"attempts": (1, 2)}]},  # type: ignore[list-item]
        )
    )

    response = await _service(adapter).invoke(ServerStatusInput())

    assert isinstance(response, ToolFailure)
    details = response.error.details
    assert type(details) is dict
    assert type(details["nested"]) is list
    assert type(details["nested"][0]) is dict
    assert type(details["nested"][0]["attempts"]) is list
    assert json.loads(response_json(response))["error"]["details"] == {
        "nested": [{"attempts": [1, 2]}]
    }


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
    command = (
        "import autocad_mcp.server, src.server, sys; "
        "assert not {'pythoncom', 'win32com', 'win32com.client', 'pyautocad'} & set(sys.modules)"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and inline import assertion
        [
            sys.executable,
            "-c",
            command,
        ],
        capture_output=True,
        check=False,
        cwd=Path(__file__).parents[2],
        text=True,
    )

    assert result.returncode == 0, result.stderr
