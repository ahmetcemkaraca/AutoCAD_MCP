"""Runtime composition for the local AutoCAD MCP server."""

from autocad_mcp.adapter.provider import WindowsAdapterProvider
from autocad_mcp.adapter.service import AdapterToolService
from autocad_mcp.core.service import BasicToolService


def create_tool_service() -> BasicToolService:
    """Build the delayed Windows AutoCAD adapter service."""
    return AdapterToolService(WindowsAdapterProvider())
