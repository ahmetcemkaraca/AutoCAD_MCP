"""Closed metadata for caller-supplied surface unfolding; no AutoCAD dependency."""

from __future__ import annotations

import asyncio
from threading import Event
from typing import TYPE_CHECKING

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_DEADLINE_SECONDS,
    MAX_ADVANCED_ITEMS,
    MAX_ADVANCED_ITERATIONS,
    MAX_CANCELLATION_CHECK_INTERVAL,
    MAX_JSON_INTEGER,
)
from autocad_mcp.advanced.unfolding.models import MAX_FACES, MAX_SEAMS, MAX_VERTICES
from mcp.types import Tool, ToolAnnotations

if TYPE_CHECKING:
    from autocad_mcp.core.models import JsonValue, ToolResponse

_ID = {"type": "integer", "minimum": 0, "maximum": MAX_JSON_INTEGER}
_DISALLOWED_TEXT = {"pattern": r"[\u0000-\u001f\u007f-\u009f\ud800-\udfff]"}

SURFACE_UNFOLDING_TOOL = Tool(
    name="unfold_surface",
    description=(
        "Unfold a supplied bounded triangular mesh into an independently verified 2D layout. "
        "Uses explicit seams and units; does not read or modify AutoCAD."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False),
    inputSchema={
        "type": "object",
        "additionalProperties": False,
        "required": [
            "request_id",
            "units_label",
            "vertices",
            "faces",
            "seam_edges",
            "root_face_id",
            "policy",
        ],
        "properties": {
            "request_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "not": _DISALLOWED_TEXT,
            },
            "units_label": {
                "type": "string",
                "minLength": 1,
                "maxLength": 64,
                "not": _DISALLOWED_TEXT,
            },
            "vertices": {
                "type": "array",
                "minItems": 3,
                "maxItems": MAX_VERTICES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["vertex_id", "point"],
                    "properties": {
                        "vertex_id": _ID,
                        "point": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "number"},
                        },
                    },
                },
            },
            "faces": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_FACES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["face_id", "vertex_ids"],
                    "properties": {
                        "face_id": _ID,
                        "vertex_ids": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": _ID,
                        },
                    },
                },
            },
            "seam_edges": {
                "type": "array",
                "maxItems": MAX_SEAMS,
                "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": _ID},
            },
            "root_face_id": _ID,
            "policy": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "max_items",
                    "max_iterations",
                    "deadline_seconds",
                    "cancellation_check_interval",
                    "deterministic_seed",
                ],
                "properties": {
                    "max_items": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_ADVANCED_ITEMS,
                    },
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_ADVANCED_ITERATIONS,
                    },
                    "deadline_seconds": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "maximum": MAX_ADVANCED_DEADLINE_SECONDS,
                    },
                    "cancellation_check_interval": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_CANCELLATION_CHECK_INTERVAL,
                    },
                    "deterministic_seed": _ID,
                },
            },
        },
    },
)


class EventCancellationProbe:
    """Carry transport cancellation into the existing cooperative work budget."""

    def __init__(self) -> None:
        self._event = Event()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()


_MESSAGES = {
    "INVALID_ARGUMENT": "Invalid unfolding request",
    "RESOURCE_LIMIT": "Unfolding resource limit exceeded",
    "INVALID_FACE": "Invalid mesh face",
    "INVALID_SEAM": "Invalid mesh seam",
    "DEGENERATE_FACE": "Mesh contains a degenerate face",
    "NON_MANIFOLD_EDGE": "Mesh contains a non-manifold edge",
    "NON_MANIFOLD_VERTEX": "Mesh contains a non-manifold vertex",
    "INCONSISTENT_WINDING": "Mesh winding is inconsistent",
    "DISCONNECTED_MESH": "Mesh is disconnected",
    "CYCLIC_ISLAND": "Seams must leave acyclic face islands",
    "SELF_INTERSECTION": "Mesh triangles intersect",
    "NUMERICAL_FAILURE": "Unfolding cannot be represented numerically",
    "VERIFICATION_FAILED": "Independent unfolding verification rejected the layout",
    "CANCELLED": "Unfolding was cancelled",
    "DEADLINE_EXCEEDED": "Unfolding cooperative deadline exceeded",
}


async def handle_unfold_surface(arguments: object) -> ToolResponse:
    """Call the accepted service once in a cooperative, transport-cancellable thread."""
    from autocad_mcp.advanced.bounds import BoundedExecutionFailure
    from autocad_mcp.advanced.unfolding.models import MeshValidationError
    from autocad_mcp.advanced.unfolding.service import result_payload, unfold_surface
    from autocad_mcp.core.models import ErrorCode, ToolError, ToolFailure, ToolSuccess

    cancellation = EventCancellationProbe()
    try:
        result = await asyncio.to_thread(unfold_surface, arguments, cancellation=cancellation)
    except asyncio.CancelledError:
        cancellation.cancel()
        raise
    except MeshValidationError as error:
        details: dict[str, JsonValue] = {}
        if error.issues:
            details["issues"] = [
                {"code": issue.code, "face_ids": list(issue.face_ids), "message": issue.message}
                for issue in error.issues
            ]
        return ToolFailure(ToolError(ErrorCode(error.code), _MESSAGES[error.code], details=details))
    if isinstance(result, BoundedExecutionFailure):
        return ToolFailure(
            ToolError(
                ErrorCode(result.code.value),
                _MESSAGES[result.code.value],
                details={"completed_iterations": result.completed_iterations},
            )
        )
    return ToolSuccess({"result": result_payload(result)})
