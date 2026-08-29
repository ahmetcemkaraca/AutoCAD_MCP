"""Canonical MCP tool definitions and trust-boundary request parsing."""

from collections.abc import Mapping

from mcp.types import Tool

from .models import (
    BasicToolInput,
    GetEntityInfoInput,
    ListEntitiesInput,
    ServerStatusInput,
    ToolName,
)

TOOL_DEFINITIONS: tuple[Tool, ...] = (
    Tool(
        name=ToolName.SERVER_STATUS,
        description="Report MCP server and AutoCAD availability.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name=ToolName.LIST_ENTITIES,
        description="List entities in the active AutoCAD document.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name=ToolName.GET_ENTITY_INFO,
        description="Get information for an entity by its session-local identifier.",
        inputSchema={
            "type": "object",
            "properties": {"entity_id": {"type": "integer", "minimum": 0}},
            "required": ["entity_id"],
            "additionalProperties": False,
        },
    ),
)


class InvalidToolArguments(ValueError):  # noqa: N818
    """Raised when arguments do not meet a known tool's input contract."""

    def __init__(self, tool_name: str, field: str | None = None) -> None:
        self.tool_name = tool_name
        self.field = field
        location = f" for field {field!r}" if field is not None else ""
        super().__init__(f"Invalid arguments for tool {tool_name!r}{location}")


class UnknownToolName(ValueError):  # noqa: N818
    """Raised separately so dispatch can map an unrecognized name to UNKNOWN_TOOL."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Unknown tool {tool_name!r}")


def _validated_arguments(name: str, arguments: Mapping[str, object] | None) -> Mapping[str, object]:
    if arguments is None or not isinstance(arguments, Mapping):
        raise InvalidToolArguments(name)
    return arguments


def _reject_extra_arguments(
    name: str, arguments: Mapping[str, object], allowed: frozenset[str]
) -> None:
    for key in arguments:
        if key not in allowed:
            raise InvalidToolArguments(name, str(key))


def parse_tool_input(name: str, arguments: Mapping[str, object] | None) -> BasicToolInput:
    """Validate untrusted MCP arguments and create an immutable request model."""
    try:
        tool_name = ToolName(name)
    except ValueError as error:
        raise UnknownToolName(name) from error

    checked_arguments = _validated_arguments(name, arguments)
    if tool_name is ToolName.SERVER_STATUS:
        _reject_extra_arguments(name, checked_arguments, frozenset())
        return ServerStatusInput()
    if tool_name is ToolName.LIST_ENTITIES:
        _reject_extra_arguments(name, checked_arguments, frozenset())
        return ListEntitiesInput()

    _reject_extra_arguments(name, checked_arguments, frozenset({"entity_id"}))
    if "entity_id" not in checked_arguments:
        raise InvalidToolArguments(name, "entity_id")
    entity_id = checked_arguments["entity_id"]
    if isinstance(entity_id, bool) or not isinstance(entity_id, int) or entity_id < 0:
        raise InvalidToolArguments(name, "entity_id")
    return GetEntityInfoInput(entity_id)
