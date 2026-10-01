"""End-to-end contracts for the canonical MCP stdio server and its shim."""

import asyncio
import importlib
import json
import sys
import tempfile
from pathlib import Path

import anyio
import mcp.types as types
import pytest
from autocad_mcp.core.models import (
    BasicToolInput,
    ErrorCode,
    ToolError,
    ToolFailure,
    ToolResponse,
)
from autocad_mcp.core.tools import TOOL_DEFINITIONS
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).parents[2]
ACTIVE_TOOL_NAMES = ("server_status", "list_entities", "get_entity_info")
LEGACY_MUTATING_TOOL_NAMES = frozenset(
    {"draw_line", "draw_circle", "extrude_profile", "revolve_profile"}
)
COM_MODULE_NAMES = {"pythoncom", "win32com", "win32com.client", "pyautocad"}


class RecordingToolService:
    """Deterministic service used to exercise the registered handler path."""

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        return ToolFailure(
            error=ToolError(
                code=ErrorCode.AUTOCAD_UNAVAILABLE,
                message="Full AutoCAD is unavailable",
                retryable=True,
                details={"handled": request.tool_name},
            )
        )


def _import_servers():
    """Load both public entry modules after clearing only their cached modules."""
    for name in ("src.server", "autocad_mcp.server"):
        sys.modules.pop(name, None)
    canonical = importlib.import_module("autocad_mcp.server")
    shim = importlib.import_module("src.server")
    return canonical, shim


def _server_result(server, request):
    return asyncio.run(server.request_handlers[type(request)](request)).root


def _help_tool_names(help_text: str) -> tuple[str, ...]:
    return tuple(
        line.removeprefix("- ").split(":", maxsplit=1)[0]
        for line in help_text.splitlines()
        if line.startswith("- ")
    )


def test_canonical_and_shim_exports_share_one_com_free_server() -> None:
    """A duplicate or COM-bound shim would break portable stdio compatibility."""
    canonical, shim = _import_servers()

    assert shim.server is canonical.server
    assert shim.create_server is canonical.create_server
    assert shim.main is canonical.main
    assert COM_MODULE_NAMES.isdisjoint(sys.modules)


def test_registered_catalog_resource_prompt_and_errors_share_the_core_contract() -> None:
    """Registration drift would advertise operations the canonical core cannot safely serve."""
    canonical, _ = _import_servers()
    server = canonical.create_server(RecordingToolService())

    tools = _server_result(server, types.ListToolsRequest()).tools
    assert tuple(tool.name for tool in tools) == ACTIVE_TOOL_NAMES
    assert tuple(tool.name for tool in tools) == tuple(tool.name for tool in TOOL_DEFINITIONS)

    resources = _server_result(server, types.ListResourcesRequest()).resources
    assert [(str(resource.uri), resource.name) for resource in resources] == [
        ("autocad://server-status", "AutoCAD MCP Server Status")
    ]
    status = _server_result(
        server,
        types.ReadResourceRequest(
            params=types.ReadResourceRequestParams(uri="autocad://server-status")
        ),
    )
    assert json.loads(status.contents[0].text)["error"]["code"] == "AUTOCAD_UNAVAILABLE"

    prompts = _server_result(server, types.ListPromptsRequest()).prompts
    assert [prompt.name for prompt in prompts] == ["autocad-help"]
    help_result = _server_result(
        server,
        types.GetPromptRequest(
            params=types.GetPromptRequestParams(name="autocad-help")
        ),
    )
    help_text = help_result.messages[0].content.text
    assert _help_tool_names(help_text) == ACTIVE_TOOL_NAMES
    assert not any(name in help_text for name in LEGACY_MUTATING_TOOL_NAMES)

    status_call = _server_result(
        server,
        types.CallToolRequest(
            params=types.CallToolRequestParams(name="server_status", arguments={})
        ),
    )
    assert json.loads(status_call.content[0].text)["error"]["code"] == "AUTOCAD_UNAVAILABLE"
    legacy_call = _server_result(
        server,
        types.CallToolRequest(
            params=types.CallToolRequestParams(name="draw_line", arguments={})
        ),
    )
    assert json.loads(legacy_call.content[0].text) == {
        "error": {
            "code": "UNKNOWN_TOOL",
            "details": {},
            "message": "Unknown tool",
            "retryable": False,
        },
        "success": False,
    }


async def _exercise_stdio_entrypoint(module_name: str) -> tuple[dict[str, object], str]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", module_name],
        cwd=PROJECT_ROOT,
    )
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as diagnostics:
        async with stdio_client(parameters, errlog=diagnostics) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                resources = await session.list_resources()
                prompts = await session.list_prompts()
                status_resource = await session.read_resource("autocad://server-status")
                help_result = await session.get_prompt("autocad-help")
                status_call = await session.call_tool("server_status", {})
                legacy_call = await session.call_tool("draw_line", {})
                for name, arguments in (
                    ("get_entity_info", {"entity_id": -1}),
                    ("get_entity_info", {"entity_id": "1"}),
                    ("get_entity_info", {"entity_id": True}),
                    ("get_entity_info", {}),
                    ("server_status", {"extra": "private-value"}),
                    ("list_entities", {"extra": "private-value"}),
                ):
                    invalid_call = await session.call_tool(name, arguments)
                    failure = json.loads(invalid_call.content[0].text)
                    assert failure["success"] is False
                    assert failure["error"]["code"] == "INVALID_ARGUMENT"
                    assert "private-value" not in invalid_call.content[0].text

        diagnostics.seek(0)
        return {
            "tools": [tool.name for tool in tools.tools],
            "resources": [str(resource.uri) for resource in resources.resources],
            "prompts": [prompt.name for prompt in prompts.prompts],
            "status_resource": json.loads(status_resource.contents[0].text),
            "help": help_result.messages[0].content.text,
            "status_call": json.loads(status_call.content[0].text),
            "legacy_call": json.loads(legacy_call.content[0].text),
        }, diagnostics.read()


@pytest.mark.parametrize("module_name", ("autocad_mcp.server", "src.server"))
def test_stdio_entrypoints_expose_only_the_canonical_protocol_catalog(module_name: str) -> None:
    """Any stdout diagnostic or shim drift would prevent a real MCP client session."""
    result, diagnostics = anyio.run(_exercise_stdio_entrypoint, module_name)

    assert result["tools"] == list(ACTIVE_TOOL_NAMES)
    assert result["resources"] == ["autocad://server-status"]
    assert result["prompts"] == ["autocad-help"]
    assert result["status_resource"]["error"]["code"] == "AUTOCAD_UNAVAILABLE"
    assert result["status_call"]["error"]["code"] == "AUTOCAD_UNAVAILABLE"
    assert result["legacy_call"]["error"]["code"] == "UNKNOWN_TOOL"
    assert _help_tool_names(result["help"]) == ACTIVE_TOOL_NAMES
    assert not any(name in result["help"] for name in LEGACY_MUTATING_TOOL_NAMES)
    assert "Starting AutoCAD MCP stdio server" in diagnostics
