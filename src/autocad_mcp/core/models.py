"""Immutable, AutoCAD-independent MCP request and response models."""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str  # noqa: UP040
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]  # noqa: UP040


class ToolName(StrEnum):
    """Names of the canonical read-only MCP tools."""

    SERVER_STATUS = "server_status"
    LIST_ENTITIES = "list_entities"
    GET_ENTITY_INFO = "get_entity_info"
    GENERATE_CONSTRAINED_CODE = "generate_constrained_code"


@dataclass(frozen=True)
class ServerStatusInput:
    tool_name: ClassVar[ToolName] = ToolName.SERVER_STATUS


@dataclass(frozen=True)
class ListEntitiesInput:
    tool_name: ClassVar[ToolName] = ToolName.LIST_ENTITIES


@dataclass(frozen=True)
class GetEntityInfoInput:
    entity_id: int
    tool_name: ClassVar[ToolName] = ToolName.GET_ENTITY_INFO


BasicToolInput: TypeAlias = (  # noqa: UP040
    ServerStatusInput | ListEntitiesInput | GetEntityInfoInput
)


class ErrorCode(StrEnum):
    """Stable, redacted error codes returned to MCP clients."""

    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    AUTOCAD_UNAVAILABLE = "AUTOCAD_UNAVAILABLE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    COM_BUSY = "COM_BUSY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AUTOCAD_OPERATION_FAILED = "AUTOCAD_OPERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNSUPPORTED_TARGET = "UNSUPPORTED_TARGET"
    UNSUPPORTED_TEMPLATE = "UNSUPPORTED_TEMPLATE"
    UNSUPPORTED_TEMPLATE_VERSION = "UNSUPPORTED_TEMPLATE_VERSION"
    PAYLOAD_LIMIT = "PAYLOAD_LIMIT"
    STATIC_VALIDATION_FAILED = "STATIC_VALIDATION_FAILED"


@dataclass(frozen=True)
class ToolError:
    code: ErrorCode
    message: str
    retryable: bool = False
    details: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSuccess:
    data: Mapping[str, JsonValue]


@dataclass(frozen=True)
class ToolFailure:
    error: ToolError


ToolResponse: TypeAlias = ToolSuccess | ToolFailure  # noqa: UP040


def response_payload(response: ToolResponse) -> dict[str, JsonValue]:
    """Convert a structured response to the stable MCP JSON payload shape."""
    if isinstance(response, ToolSuccess):
        if "success" in response.data:
            raise ValueError("ToolSuccess data must not contain reserved key 'success'")
        return {"success": True, **response.data}
    return {
        "success": False,
        "error": {
            "code": response.error.code,
            "message": response.error.message,
            "retryable": response.error.retryable,
            "details": dict(response.error.details),
        },
    }


def response_json(response: ToolResponse) -> str:
    """Serialize a response deterministically as valid JSON."""
    return json.dumps(
        response_payload(response),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
