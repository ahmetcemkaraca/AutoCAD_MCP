"""Manifest, registered catalogue, resource and help agreement for the canonical server."""

import json
from pathlib import Path

import mcp.types as types
from autocad_mcp.core.tools import TOOL_DEFINITIONS

from tests.contract.test_stdio_server import (
    ACTIVE_TOOL_NAMES,
    LEGACY_MUTATING_TOOL_NAMES,
    RecordingToolService,
    _help_tool_names,
    _import_servers,
    _server_result,
)


def test_manifest_catalog_matches_the_canonical_tool_definitions() -> None:
    """Manifest drift would advertise tools unavailable from the canonical server."""
    manifest = json.loads((Path(__file__).parents[2] / "mcp.json").read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["autocad-mcp"]

    assert [
        {"name": tool["name"], "description": tool["description"]} for tool in manifest["tools"]
    ] == [
        {"name": definition.name, "description": definition.description}
        for definition in TOOL_DEFINITIONS
    ]
    assert server == {"command": "uv", "args": ["run", "python", "-m", "autocad_mcp.server"]}


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
        types.GetPromptRequest(params=types.GetPromptRequestParams(name="autocad-help")),
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
        types.CallToolRequest(params=types.CallToolRequestParams(name="draw_line", arguments={})),
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
