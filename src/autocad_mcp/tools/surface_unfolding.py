"""Closed metadata for caller-supplied surface unfolding; no AutoCAD dependency."""

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_DEADLINE_SECONDS,
    MAX_ADVANCED_ITEMS,
    MAX_ADVANCED_ITERATIONS,
    MAX_CANCELLATION_CHECK_INTERVAL,
    MAX_JSON_INTEGER,
)
from autocad_mcp.advanced.unfolding.models import MAX_FACES, MAX_SEAMS, MAX_VERTICES
from mcp.types import Tool, ToolAnnotations

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
            "request_id", "units_label", "vertices", "faces", "seam_edges", "root_face_id", "policy"
        ],
        "properties": {
            "request_id": {
                "type": "string", "minLength": 1, "maxLength": 128, "not": _DISALLOWED_TEXT
            },
            "units_label": {
                "type": "string", "minLength": 1, "maxLength": 64, "not": _DISALLOWED_TEXT
            },
            "vertices": {
                "type": "array", "minItems": 3, "maxItems": MAX_VERTICES,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["vertex_id", "point"],
                    "properties": {
                        "vertex_id": _ID,
                        "point": {
                            "type": "array", "minItems": 3, "maxItems": 3,
                            "items": {"type": "number"},
                        },
                    },
                },
            },
            "faces": {
                "type": "array", "minItems": 1, "maxItems": MAX_FACES,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["face_id", "vertex_ids"],
                    "properties": {
                        "face_id": _ID,
                        "vertex_ids": {
                            "type": "array", "minItems": 3, "maxItems": 3, "items": _ID,
                        },
                    },
                },
            },
            "seam_edges": {
                "type": "array", "maxItems": MAX_SEAMS,
                "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": _ID},
            },
            "root_face_id": _ID,
            "policy": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "max_items", "max_iterations", "deadline_seconds",
                    "cancellation_check_interval", "deterministic_seed",
                ],
                "properties": {
                    "max_items": {
                        "type": "integer", "minimum": 1, "maximum": MAX_ADVANCED_ITEMS,
                    },
                    "max_iterations": {
                        "type": "integer", "minimum": 1, "maximum": MAX_ADVANCED_ITERATIONS,
                    },
                    "deadline_seconds": {
                        "type": "number", "exclusiveMinimum": 0,
                        "maximum": MAX_ADVANCED_DEADLINE_SECONDS,
                    },
                    "cancellation_check_interval": {
                        "type": "integer", "minimum": 1,
                        "maximum": MAX_CANCELLATION_CHECK_INTERVAL,
                    },
                    "deterministic_seed": _ID,
                },
            },
        },
    },
)
