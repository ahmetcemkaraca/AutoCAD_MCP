"""MCP service mapping for the synchronous read-only AutoCAD adapter."""

import asyncio
from collections.abc import Mapping
from typing import assert_never, cast

from autocad_mcp.adapter.protocol import AdapterError, ConnectionInfo, EntityDetails, EntitySummary
from autocad_mcp.adapter.provider import AdapterProvider
from autocad_mcp.core.models import (
    BasicToolInput,
    ErrorCode,
    GetEntityInfoInput,
    JsonValue,
    ListEntitiesInput,
    ServerStatusInput,
    ToolError,
    ToolFailure,
    ToolName,
    ToolResponse,
    ToolSuccess,
)


class AdapterToolService:
    """Map adapter values and public errors into the stable MCP contract."""

    def __init__(self, provider: AdapterProvider) -> None:
        self._provider = provider

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        """Run exactly one synchronous adapter operation outside the event loop."""
        try:
            adapter = self._provider.get()
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
                    details=_plain_json_mapping(error.details),
                )
            )


def _status_data(connection: ConnectionInfo) -> dict[str, JsonValue]:
    return {
        "mcp_server": "running",
        "autocad_connected": connection.connected,
        "active_document": connection.active_document,
        "product": connection.product,
        "version": connection.version,
        "release_hint": connection.release_hint,
        "read_only": connection.read_only,
        "tools_available": len(ToolName),
        "transport": "stdio",
        "capabilities": [
            cast(JsonValue, capability.value)
            for capability in sorted(connection.capabilities.available)
        ],
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


def _summary_data(entity: EntitySummary | EntityDetails) -> dict[str, JsonValue]:
    return {
        "id": entity.object_id,
        "handle": entity.handle,
        "type": entity.object_name,
        "layer": entity.layer,
    }


def _details_data(entity: EntityDetails) -> dict[str, JsonValue]:
    return {**_summary_data(entity), "properties": _plain_json_mapping(entity.properties)}


def _plain_json_mapping(values: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: _plain_json_value(value) for key, value in values.items()}


def _plain_json_value(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain_json_value(item) for item in value]
    return value  # type: ignore[return-value]
