"""Canonical low-level MCP stdio server for the safe local core."""

import asyncio
import logging
import sys
from collections.abc import Mapping

import mcp.types as types
from autocad_mcp import __version__
from autocad_mcp.core.models import ToolResponse, response_json
from autocad_mcp.core.service import BasicToolService, dispatch_tool
from autocad_mcp.core.tools import TOOL_DEFINITIONS
from autocad_mcp.runtime import create_tool_service
from mcp.server import NotificationOptions, Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

logger = logging.getLogger(__name__)
_STATUS_RESOURCE_URI = "autocad://server-status"
_HELP_PROMPT_NAME = "autocad-help"


def _help_text() -> str:
    tools = "\n".join(f"- {tool.name}: {tool.description}" for tool in TOOL_DEFINITIONS)
    return f"# AutoCAD MCP Server Help\n\nAvailable tools:\n{tools}"


def _text_response(response: ToolResponse) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=response_json(response))]


def create_server(service: BasicToolService) -> Server:
    """Create the only active MCP registration surface around an injected service."""
    mcp_server = Server("autocad-mcp")

    @mcp_server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return list(TOOL_DEFINITIONS)

    @mcp_server.call_tool(validate_input=False)
    async def call_tool(
        name: str, arguments: Mapping[str, object] | None
    ) -> list[types.TextContent]:
        return _text_response(await dispatch_tool(service, name, arguments))

    @mcp_server.list_resources()
    async def list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=types.AnyUrl(_STATUS_RESOURCE_URI),
                name="AutoCAD MCP Server Status",
                description="Current MCP server and AutoCAD connection status",
                mimeType="application/json",
            )
        ]

    @mcp_server.read_resource()
    async def read_resource(uri: str) -> list[ReadResourceContents]:
        if str(uri) != _STATUS_RESOURCE_URI:
            raise ValueError("Unknown resource")
        return [
            ReadResourceContents(
                content=response_json(await dispatch_tool(service, "server_status", {})),
                mime_type="application/json",
            )
        ]

    @mcp_server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(
                name=_HELP_PROMPT_NAME,
                description="Get help with registered AutoCAD MCP tools",
            )
        ]

    @mcp_server.get_prompt()
    async def get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        if name != _HELP_PROMPT_NAME:
            raise ValueError("Unknown prompt")
        return types.GetPromptResult(
            description="AutoCAD MCP Server help information",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=_help_text()),
                )
            ],
        )

    return mcp_server


server = create_server(create_tool_service())


async def main() -> None:
    """Run the canonical MCP transport with stdout reserved for JSON-RPC."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    options = InitializationOptions(
        server_name="autocad-mcp",
        server_version=__version__,
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    logger.info("Starting AutoCAD MCP stdio server")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(main())
