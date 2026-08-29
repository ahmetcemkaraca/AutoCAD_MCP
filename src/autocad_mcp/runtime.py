"""Runtime composition for the pure local MCP server."""

from autocad_mcp.core.service import BasicToolService, UnavailableToolService


def create_tool_service() -> BasicToolService:
    """Build the initial no-COM service implementation."""
    return UnavailableToolService()
