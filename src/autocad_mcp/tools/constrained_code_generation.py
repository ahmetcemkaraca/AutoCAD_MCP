"""Closed recipe schema and output-only code-generation handler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autocad_mcp.core.models import ToolResponse
from mcp.types import Tool


def _closed(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_TEXT = {"type": "string", "pattern": r"^[^\u0000\uD800-\uDFFF]*$"}
_HANDLE = {"type": "string", "minLength": 1, "maxLength": 16, "not": {"pattern": "[^0-9A-Fa-f]"}}
_NUMBER = {"type": "number", "minimum": -1e15, "maximum": 1e15}
_POINT = {"type": "array", "minItems": 3, "maxItems": 3, "items": _NUMBER}
_SCALAR = {
    "anyOf": [
        {"type": "null"},
        {"type": "boolean"},
        {"type": "integer", "minimum": -(2**53 - 1), "maximum": 2**53 - 1},
        _NUMBER,
        {**_TEXT, "maxLength": 1024},
    ]
}
_GEOMETRY = {
    **_closed(
        {
            "lines": {
                "type": "array",
                "maxItems": 64,
                "items": _closed({"start": _POINT, "end": _POINT}),
            },
            "circles": {
                "type": "array",
                "maxItems": 64,
                "items": _closed(
                    {
                        "center": _POINT,
                        "radius": {"type": "number", "exclusiveMinimum": 0, "maximum": 1e15},
                    }
                ),
            },
        }
    ),
    "anyOf": [
        {"properties": {"lines": {"minItems": 1}}},
        {"properties": {"circles": {"minItems": 1}}},
    ],
}
_FACTS = _closed(
    {
        "facts": {
            "type": "array",
            "minItems": 1,
            "maxItems": 64,
            "items": _closed(
                {
                    "handle": _HANDLE,
                    "object_name": {**_TEXT, "minLength": 1, "maxLength": 255},
                    "layer": {**_TEXT, "minLength": 1, "maxLength": 255},
                    "properties": {
                        "type": "object",
                        "maxProperties": 16,
                        "propertyNames": {**_TEXT, "minLength": 1, "maxLength": 128},
                        "additionalProperties": _SCALAR,
                    },
                }
            ),
        }
    }
)
_HANDLES = _closed(
    {
        "handles": {
            "type": "array",
            "minItems": 1,
            "maxItems": 256,
            "uniqueItems": True,
            "items": _HANDLE,
        }
    }
)

CONSTRAINED_CODE_GENERATION_TOOL = Tool(
    name="generate_constrained_code",
    description="Generate reviewed source text from bounded literal recipes; never execute it.",
    inputSchema={
        **_closed(
            {
                "schema_version": {"const": "1"},
                "template_id": {
                    "enum": ["literal_geometry", "serialize_entity_facts", "iterate_handles"]
                },
                "template_version": {"const": "1.0.0"},
                "target": {"enum": ["python", "autolisp", "vba"]},
                "literals": {"type": "object"},
            }
        ),
        "oneOf": [
            {"properties": {"template_id": {"const": name}, "literals": schema}}
            for name, schema in (
                ("literal_geometry", _GEOMETRY),
                ("serialize_entity_facts", _FACTS),
                ("iterate_handles", _HANDLES),
            )
        ],
    },
)

_MESSAGES = {
    "INVALID_ARGUMENT": "Invalid code recipe",
    "UNSUPPORTED_TARGET": "Unsupported code target",
    "UNSUPPORTED_TEMPLATE": "Unsupported code template",
    "UNSUPPORTED_TEMPLATE_VERSION": "Unsupported code template version",
    "PAYLOAD_LIMIT": "Code generation payload limit exceeded",
    "STATIC_VALIDATION_FAILED": "Generated source failed static validation",
}


def generate_constrained_code(arguments: object) -> ToolResponse:
    """Map private C failures to fixed core errors without invoking a basic service."""
    from autocad_mcp.advanced.codegen.models import CodeGenerationError
    from autocad_mcp.advanced.codegen.service import artifact_payload, generate_code
    from autocad_mcp.core.models import ErrorCode, ToolError, ToolFailure, ToolSuccess

    try:
        artifact = generate_code(arguments)
        return ToolSuccess({"artifact": artifact_payload(artifact)})
    except CodeGenerationError as error:
        return ToolFailure(ToolError(ErrorCode(error.code), _MESSAGES[error.code]))
