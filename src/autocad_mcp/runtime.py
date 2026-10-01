"""Runtime composition for the local AutoCAD MCP server."""

from autocad_mcp.core.models import BasicToolInput, ToolResponse
from autocad_mcp.core.service import BasicToolService


class _LazyBasicToolService:
    """Keep adapter imports/construction behind the first validated basic call."""

    def __init__(self) -> None:
        self._service: BasicToolService | None = None

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        if self._service is None:
            from autocad_mcp.adapter.provider import WindowsAdapterProvider
            from autocad_mcp.adapter.service import AdapterToolService

            self._service = AdapterToolService(WindowsAdapterProvider())
        return await self._service.invoke(request)


def create_tool_service() -> BasicToolService:
    """Construct the existing basic port without loading its adapter boundary."""
    return _LazyBasicToolService()
