"""Freeze the adopted mutating schemas until the canonical catalog replaces it."""

import asyncio
import importlib
import json
from pathlib import Path

import pytest

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


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _current_server_module():
    return importlib.import_module("src.server")


def _current_runtime_tools():
    return asyncio.run(_current_server_module().handle_list_tools())


def test_01_fixture_equals_observed_current_handler_schemas() -> None:
    """A changed adopted handler must not silently rewrite the frozen evidence."""
    fixture = _fixture()
    observed = {
        tool.name: tool.inputSchema
        for tool in _current_runtime_tools()
        if tool.name in LEGACY_MUTATING_TOOL_NAMES
    }

    assert fixture["source_commit"] == "00207ed084e9ef81538b5283615e689d483632d1"
    assert fixture["source_path"] == "src/server.py"
    assert set(fixture) == {"source_commit", "source_path", "tools"}
    assert set(fixture["tools"]) == LEGACY_MUTATING_TOOL_NAMES
    assert observed == fixture["tools"]


@pytest.mark.parametrize(
    ("surface", "names"),
    (
        ("runtime list_tools", lambda: {tool.name for tool in _current_runtime_tools()}),
        (
            "mcp.json manifest",
            lambda: {
                tool["name"]
                for tool in json.loads(
                    (PROJECT_ROOT / "mcp.json").read_text(encoding="utf-8")
                )["tools"]
            },
        ),
        (
            "autocad-help prompt",
            lambda: {
                name
                for name in LEGACY_MUTATING_TOOL_NAMES
                if name
                in asyncio.run(
                    _current_server_module().handle_get_prompt("autocad-help", None)
                ).messages[0].content.text
            },
        ),
    ),
)
def test_02_active_catalog_excludes_legacy_mutations(surface, names) -> None:
    """The final three-tool catalog must not advertise a legacy mutation."""
    exposed = names()

    assert LEGACY_MUTATING_TOOL_NAMES.isdisjoint(exposed), (
        f"{surface} still exposes legacy mutations: "
        f"{sorted(LEGACY_MUTATING_TOOL_NAMES & exposed)}"
    )
