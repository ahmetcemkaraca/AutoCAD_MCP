"""MCP service mapping for the synchronous read-only AutoCAD adapter."""

import asyncio
from typing import assert_never

from autocad_mcp.adapter.protocol import AdapterError, ConnectionInfo, EntityDetails, EntitySummary
from autocad_mcp.adapter.provider import AdapterProvider
from autocad_mcp.core.models import (
    BasicToolInput,
    ErrorCode,
    GetEntityInfoInput,
    ListEntitiesInput,
    ServerStatusInput,
    ToolError,
    ToolFailure,
    ToolResponse,
    ToolSuccess,
)


class AdapterToolService:
    """Map adapter values and public errors into the stable MCP contract."""

    def __init__(self, provider: AdapterProvider) -> None:
        self._provider = provider

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        """Run exactly one synchronous adapter operation outside the event loop."""
        adapter = self._provider.get()
        try:
            if isinstance(request, ServerStatusInput):
                return ToolSuccess(_status_data(await asyncio.to_thread(adapter.status)))
            if isinstance(request, ListEntitiesInput):
                entities = await asyncio.to_thread(adapter.list_entities)
                return ToolSuccess(
                    {
                        "count": len(entities),
                        "entities": [_summary_data(entity) for entity in entities],
                    }
                )
            if isinstance(request, GetEntityInfoInput):
                entity = await asyncio.to_thread(adapter.get_entity_info, request.entity_id)
                return ToolSuccess({"entity": _details_data(entity)})
            assert_never(request)
        except AdapterError as error:
            return ToolFailure(
                ToolError(
                    ErrorCode(error.code.value),
                    error.public_message,
                    retryable=error.retryable,
                    details=dict(error.details),
                )
            )


def _status_data(connection: ConnectionInfo) -> dict[str, object]:
    return {
        "mcp_server": "running",
        "autocad_connected": connection.connected,
        "active_document": connection.active_document,
        "product": connection.product,
        "version": connection.version,
        "release_hint": connection.release_hint,
        "read_only": connection.read_only,
        "tools_available": 3,
        "transport": "stdio",
        "capabilities": sorted(
            capability.value for capability in connection.capabilities.available
        ),
        "capability_issues": [
            {
                "code": issue.code.value,
                "capability": issue.capability.value,
                "member": issue.member,
                "message": issue.message,
            }
            for issue in connection.capabilities.issues
        ],
    }


def _summary_data(entity: EntitySummary) -> dict[str, object]:
    return {
        "id": entity.object_id,
        "handle": entity.handle,
        "type": entity.object_name,
        "layer": entity.layer,
    }


def _details_data(entity: EntityDetails) -> dict[str, object]:
    return {**_summary_data(entity), "properties": dict(entity.properties)}
