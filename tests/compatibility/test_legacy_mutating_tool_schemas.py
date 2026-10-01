"""Preserve legacy schema evidence while excluding mutations from active surfaces."""

import hashlib
import json
from pathlib import Path

from autocad_mcp.core.tools import TOOL_DEFINITIONS

LEGACY_MUTATING_TOOL_NAMES = frozenset(
    {"draw_line", "draw_circle", "extrude_profile", "revolve_profile"}
)
ACTIVE_TOOL_NAMES = ("server_status", "list_entities", "get_entity_info")
PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "compatibility"
    / "legacy-mutating-tool-schemas.json"
)
EXPECTED_LEGACY_TOOL_SCHEMAS = {
    "draw_line": {
        "type": "object",
        "properties": {
            "start_point": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Starting point [x, y, z]",
            },
            "end_point": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Ending point [x, y, z]",
            },
        },
        "required": ["start_point", "end_point"],
    },
    "draw_circle": {
        "type": "object",
        "properties": {
            "center": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Center point [x, y, z]",
            },
            "radius": {
                "type": "number",
                "minimum": 0,
                "description": "Circle radius",
            },
        },
        "required": ["center", "radius"],
    },
    "extrude_profile": {
        "type": "object",
        "properties": {
            "profile_points": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                },
                "description": "List of 2D/3D points defining the profile",
            },
            "extrude_height": {"type": "number", "description": "Height to extrude the profile"},
        },
        "required": ["profile_points", "extrude_height"],
    },
    "revolve_profile": {
        "type": "object",
        "properties": {
            "profile_points": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
                "description": "List of points defining the profile",
            },
            "axis_start": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Start point of revolution axis",
            },
            "axis_end": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "End point of revolution axis",
            },
            "angle": {"type": "number", "description": "Revolution angle in degrees"},
        },
        "required": ["profile_points", "axis_start", "axis_end", "angle"],
    },
}


def test_fixture_is_the_frozen_verbatim_legacy_schema_record() -> None:
    """Fixture metadata or schema edits would corrupt the compatibility evidence."""
    fixture_bytes = FIXTURE_PATH.read_bytes()
    fixture = json.loads(fixture_bytes)

    assert hashlib.sha256(fixture_bytes).hexdigest() == (
        "695ecf23340d9d804ac393c13e2421e47c038ecf8f5324647adabca23177c06b"
    )
    assert fixture["source_commit"] == "00207ed084e9ef81538b5283615e689d483632d1"
    assert fixture["source_path"] == "src/server.py"
    assert set(fixture) == {"source_commit", "source_path", "tools"}
    assert set(fixture["tools"]) == LEGACY_MUTATING_TOOL_NAMES
    assert fixture["tools"] == EXPECTED_LEGACY_TOOL_SCHEMAS


def test_active_catalog_and_manifest_exclude_legacy_mutations() -> None:
    """Re-registering a frozen mutation would reintroduce an unsafe public API."""
    manifest = json.loads((PROJECT_ROOT / "mcp.json").read_text(encoding="utf-8"))
    catalog_names = tuple(tool.name for tool in TOOL_DEFINITIONS)
    manifest_names = tuple(tool["name"] for tool in manifest["tools"])

    assert catalog_names == ACTIVE_TOOL_NAMES
    assert manifest_names == ACTIVE_TOOL_NAMES
    assert LEGACY_MUTATING_TOOL_NAMES.isdisjoint(catalog_names)
    assert LEGACY_MUTATING_TOOL_NAMES.isdisjoint(manifest_names)
