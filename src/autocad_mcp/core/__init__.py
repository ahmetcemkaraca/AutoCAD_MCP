"""Pure MCP request, response, and tool-definition interfaces."""

from .models import (
    BasicToolInput,
    ErrorCode,
    GetEntityInfoInput,
    JsonScalar,
    JsonValue,
    ListEntitiesInput,
    ServerStatusInput,
    ToolError,
    ToolFailure,
    ToolName,
    ToolResponse,
    ToolSuccess,
    response_json,
    response_payload,
)
from .tools import (
    TOOL_DEFINITIONS,
    InvalidToolArguments,
    UnknownToolName,
    parse_tool_input,
)

__all__ = [
    "BasicToolInput",
    "ErrorCode",
    "GetEntityInfoInput",
    "InvalidToolArguments",
    "JsonScalar",
    "JsonValue",
    "ListEntitiesInput",
    "ServerStatusInput",
    "TOOL_DEFINITIONS",
    "ToolError",
    "ToolFailure",
    "ToolName",
    "ToolResponse",
    "ToolSuccess",
    "UnknownToolName",
    "parse_tool_input",
    "response_json",
    "response_payload",
]
