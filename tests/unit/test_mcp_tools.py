"""Contract tests for the active MCP tool catalog and input parser."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from autocad_mcp.core.models import (
    GetEntityInfoInput,
    ListEntitiesInput,
    ServerStatusInput,
    ToolName,
)
from autocad_mcp.core.tools import (
    TOOL_DEFINITIONS,
    InvalidToolArguments,
    UnknownToolName,
    parse_tool_input,
)


def test_core_imports_are_hermetic_from_com_modules() -> None:
    """A COM import in the pure core would break platform-independent clients."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(  # noqa: S603 -- sys.executable and a fixed import probe are trusted.
        [
            sys.executable,
            "-c",
            "import autocad_mcp.core.models, autocad_mcp.core.tools, sys; "
            "forbidden = {'pythoncom', 'win32com', 'win32com.client', 'pyautocad', 'comtypes'}; "
            "loaded = forbidden & set(sys.modules); "
            "raise SystemExit(f'COM modules loaded: {sorted(loaded)}' if loaded else 0)",
        ],
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "name",
    (
        "server_status",
        "list_entities",
        "get_entity_info",
    ),
)
def test_tool_definitions_are_ordered_closed_object_schemas(name: str) -> None:
    """Catalog drift or open schemas would expose undocumented tool inputs."""
    definitions = {definition.name: definition for definition in TOOL_DEFINITIONS}
    definition = definitions[name]

    assert tuple(item.name for item in TOOL_DEFINITIONS) == tuple(ToolName)
    assert definition.inputSchema["type"] == "object"
    assert definition.inputSchema["additionalProperties"] is False


def test_empty_tool_schemas_accept_no_properties() -> None:
    """Giving status or list properties would allow unsupported inputs through the API."""
    definitions = {definition.name: definition for definition in TOOL_DEFINITIONS}

    for name in ("server_status", "list_entities"):
        assert definitions[name].inputSchema["properties"] == {}
        assert "required" not in definitions[name].inputSchema


def test_entity_info_schema_requires_a_non_negative_integer_identifier() -> None:
    """Weakening this schema permits entity identifiers the runtime must reject."""
    schema = TOOL_DEFINITIONS[2].inputSchema

    assert schema["properties"] == {"entity_id": {"type": "integer", "minimum": 0}}
    assert schema["required"] == ["entity_id"]


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    (
        ("server_status", {}, ServerStatusInput()),
        ("list_entities", {}, ListEntitiesInput()),
        ("get_entity_info", {"entity_id": 0}, GetEntityInfoInput(0)),
        ("get_entity_info", {"entity_id": 42}, GetEntityInfoInput(42)),
    ),
)
def test_parse_tool_input_accepts_only_valid_active_requests(
    name: str, arguments: dict[str, object], expected: object
) -> None:
    """Breaking an active valid request would prevent normal client calls."""
    assert parse_tool_input(name, arguments) == expected


@pytest.mark.parametrize(
    ("name", "arguments", "field"),
    (
        ("server_status", {"unexpected": 1}, "unexpected"),
        ("list_entities", {"unexpected": 1}, "unexpected"),
        ("get_entity_info", {}, "entity_id"),
        ("get_entity_info", {"entity_id": True}, "entity_id"),
        ("get_entity_info", {"entity_id": 1.5}, "entity_id"),
        ("get_entity_info", {"entity_id": -1}, "entity_id"),
        ("get_entity_info", {"entity_id": 1, "unexpected": 2}, "unexpected"),
        ("server_status", None, None),
        ("list_entities", [], None),
    ),
)
def test_parse_tool_input_rejects_malformed_arguments(
    name: str, arguments: object, field: str | None
) -> None:
    """Missing or malformed input must never reach the service layer."""
    with pytest.raises(InvalidToolArguments) as error:
        parse_tool_input(name, arguments)  # type: ignore[arg-type]

    assert error.value.tool_name == name
    assert error.value.field == field


@pytest.mark.parametrize(
    "name", ("draw_line", "draw_circle", "extrude_profile", "revolve_profile", "not_a_tool")
)
def test_parse_tool_input_distinguishes_unknown_tools_from_invalid_arguments(name: str) -> None:
    """Treating an unknown name as invalid prevents dispatch from returning UNKNOWN_TOOL."""
    with pytest.raises(UnknownToolName) as error:
        parse_tool_input(name, {})

    assert error.value.tool_name == name


def test_basic_parser_never_converts_a_codegen_name_to_an_entity_read() -> None:
    with pytest.raises(UnknownToolName):
        parse_tool_input("generate_constrained_code", {"entity_id": 7})


def test_basic_parser_never_converts_unfolding_to_an_entity_read() -> None:
    with pytest.raises(UnknownToolName):
        parse_tool_input("unfold_surface", {"entity_id": 7})
