"""Contract tests for pure MCP service dispatch and unavailable composition."""

import asyncio
import logging
import sys
from collections.abc import Mapping

import pytest
from autocad_mcp.core.models import (
    BasicToolInput,
    ErrorCode,
    GetEntityInfoInput,
    ListEntitiesInput,
    ServerStatusInput,
    ToolFailure,
    ToolResponse,
    ToolSuccess,
)
from autocad_mcp.core.service import UnavailableToolService, dispatch_tool
from autocad_mcp.runtime import create_tool_service


class RecordingToolService:
    """In-process service double that records validated immutable requests."""

    def __init__(self) -> None:
        self.requests: list[BasicToolInput] = []

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        self.requests.append(request)
        return ToolSuccess({"handled": request.tool_name})


class RaisingToolService:
    """In-process service double for the dispatcher exception boundary."""

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        raise RuntimeError("secret COM detail")


@pytest.mark.parametrize(
    ("name", "arguments", "expected_request"),
    (
        ("server_status", {}, ServerStatusInput()),
        ("list_entities", {}, ListEntitiesInput()),
        ("get_entity_info", {"entity_id": 7}, GetEntityInfoInput(7)),
    ),
)
def test_dispatch_delivers_each_valid_immutable_request(
    name: str, arguments: Mapping[str, object], expected_request: BasicToolInput
) -> None:
    """Skipping parser output or mutating it would send an invalid service request."""
    service = RecordingToolService()

    response = asyncio.run(dispatch_tool(service, name, arguments))

    assert response == ToolSuccess({"handled": expected_request.tool_name})
    assert service.requests == [expected_request]


@pytest.mark.parametrize(
    ("name", "expected_request"),
    (
        ("server_status", ServerStatusInput()),
        ("list_entities", ListEntitiesInput()),
    ),
)
def test_dispatch_normalizes_missing_no_argument_calls(
    name: str, expected_request: BasicToolInput
) -> None:
    """Rejecting MCP's omitted no-argument payload would block valid tool calls."""
    service = RecordingToolService()

    response = asyncio.run(dispatch_tool(service, name, None))

    assert response == ToolSuccess({"handled": expected_request.tool_name})
    assert service.requests == [expected_request]


@pytest.mark.parametrize(
    ("name", "arguments"),
    (
        ("server_status", {"unexpected": 1}),
        ("list_entities", {"unexpected": 1}),
        ("get_entity_info", None),
        ("get_entity_info", {}),
        ("get_entity_info", {"entity_id": True}),
        ("get_entity_info", {"entity_id": -1}),
        ("get_entity_info", {"entity_id": 1.5}),
    ),
)
def test_dispatch_rejects_invalid_arguments_before_the_service(
    name: str, arguments: object
) -> None:
    """Forwarding malformed transport input would bypass the trust boundary."""
    service = RecordingToolService()

    response = asyncio.run(dispatch_tool(service, name, arguments))  # type: ignore[arg-type]

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode.INVALID_ARGUMENT
    assert service.requests == []


@pytest.mark.parametrize(
    "name", ("draw_line", "draw_circle", "extrude_profile", "revolve_profile", "not_a_tool")
)
def test_dispatch_rejects_unknown_and_legacy_tools_before_the_service(name: str) -> None:
    """Treating retired mutations as valid would reintroduce a write-capable API."""
    service = RecordingToolService()

    response = asyncio.run(dispatch_tool(service, name, {}))

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode.UNKNOWN_TOOL
    assert service.requests == []


def test_dispatch_redacts_unexpected_errors_and_logs_an_incident(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Returning a service exception would expose COM internals to MCP clients."""
    with caplog.at_level(logging.ERROR):
        response = asyncio.run(dispatch_tool(RaisingToolService(), "server_status", {}))

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode.INTERNAL_ERROR
    assert set(response.error.details) == {"incident_id"}
    incident_id = response.error.details["incident_id"]
    assert isinstance(incident_id, str)
    assert incident_id
    assert "secret COM detail" not in response.error.message
    assert "secret COM detail" not in str(response.error.details)
    assert caplog.records[0].exc_info is not None
    assert incident_id in caplog.text
    assert "secret COM detail" in caplog.text


@pytest.mark.parametrize(
    "tool_input",
    (ServerStatusInput(), ListEntitiesInput(), GetEntityInfoInput(7)),
)
def test_unavailable_service_returns_a_structured_failure_for_every_active_request(
    tool_input: BasicToolInput,
) -> None:
    """Returning a success before an adapter exists would falsely imply AutoCAD access."""
    response = asyncio.run(UnavailableToolService().invoke(tool_input))

    assert isinstance(response, ToolFailure)
    assert response.error.code is ErrorCode.AUTOCAD_UNAVAILABLE


def test_unavailable_status_reports_the_running_server_and_capabilities() -> None:
    """An incomplete status response would hide the server's usable limited state."""
    response = asyncio.run(UnavailableToolService().invoke(ServerStatusInput()))

    assert isinstance(response, ToolFailure)
    assert response.error.details == {
        "mcp_server": "running",
        "autocad_connected": False,
        "tools_available": 3,
        "transport": "stdio",
    }


def test_runtime_uses_unavailable_service_without_loading_com_modules() -> None:
    """Eager adapter imports would make the pure local runtime unusable off Windows."""
    assert isinstance(create_tool_service(), UnavailableToolService)
    assert {"pythoncom", "win32com", "win32com.client", "pyautocad"}.isdisjoint(sys.modules)
