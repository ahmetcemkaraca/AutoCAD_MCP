"""Pure service port and transport-neutral MCP dispatch."""

import logging
from collections.abc import Mapping
from typing import Protocol
from uuid import uuid4

from autocad_mcp.tools.constrained_code_generation import generate_constrained_code
from autocad_mcp.tools.surface_unfolding import handle_unfold_surface

from .models import (
    BasicToolInput,
    ErrorCode,
    ToolError,
    ToolFailure,
    ToolName,
    ToolResponse,
)
from .tools import InvalidToolArguments, UnknownToolName, parse_tool_input

logger = logging.getLogger(__name__)


class BasicToolService(Protocol):
    """The service seam consumed by the MCP transport."""

    async def invoke(self, request: BasicToolInput) -> ToolResponse: ...


class UnavailableToolService:
    """Report the honest pre-adapter AutoCAD availability state without COM."""

    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        return ToolFailure(
            ToolError(
                code=ErrorCode.AUTOCAD_UNAVAILABLE,
                message="Full AutoCAD is unavailable",
                retryable=True,
                details={
                    "mcp_server": "running",
                    "autocad_connected": False,
                    "tools_available": len(ToolName),
                    "transport": "stdio",
                },
            )
        )


async def dispatch_tool(
    service: BasicToolService, name: str, arguments: Mapping[str, object] | None
) -> ToolResponse:
    """Validate an MCP call, invoke its service, and return a structured response."""
    if arguments is None and name in (ToolName.SERVER_STATUS, ToolName.LIST_ENTITIES):
        arguments = {}

    try:
        if name == ToolName.GENERATE_CONSTRAINED_CODE:
            return generate_constrained_code(arguments)
        if name == ToolName.UNFOLD_SURFACE:
            return await handle_unfold_surface(arguments)
        return await service.invoke(parse_tool_input(name, arguments))
    except InvalidToolArguments:
        return ToolFailure(ToolError(ErrorCode.INVALID_ARGUMENT, "Invalid tool arguments"))
    except UnknownToolName:
        return ToolFailure(ToolError(ErrorCode.UNKNOWN_TOOL, "Unknown tool"))
    except Exception as error:
        incident_id = uuid4().hex
        logger.error(
            "Unexpected tool dispatch failure; incident_id=%s; error_type=%s",
            incident_id,
            type(error).__name__,
        )
        return ToolFailure(
            ToolError(
                ErrorCode.INTERNAL_ERROR,
                "An internal error occurred",
                details={"incident_id": incident_id},
            )
        )
