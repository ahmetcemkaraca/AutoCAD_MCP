"""Regression tests for the active development metadata contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib

from packaging.requirements import Requirement

from src import __version__


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _project_metadata() -> dict[str, object]:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as metadata_file:
        return tomllib.load(metadata_file)


def _manifest() -> dict[str, object]:
    return json.loads((REPOSITORY_ROOT / "mcp.json").read_text(encoding="utf-8"))


def test_active_metadata_agrees_on_the_supported_baseline() -> None:
    """Catch a version or target-platform drift across active metadata."""
    project = _project_metadata()
    manifest = _manifest()

    assert project["project"]["version"] == manifest["version"] == __version__ == "0.1.0"
    assert project["project"]["description"] == (
        "An experimental Model Context Protocol bridge for full AutoCAD 2021-2026 on Windows"
    )
    assert "tool" not in project or "poetry" not in project["tool"]


def test_manifest_uses_the_temporary_module_launch_without_pythonpath() -> None:
    """Catch a return to the ambiguous script-path/PYTHONPATH launch path."""
    server = _manifest()["mcpServers"]["autocad-mcp"]

    assert server["args"] == ["run", "python", "-m", "src.server"]
    assert "PYTHONPATH" not in server.get("env", {})


def test_com_dependencies_are_windows_only() -> None:
    """Catch a dependency migration that installs COM packages on Linux."""
    dependencies = _project_metadata()["project"]["dependencies"]
    requirements = {requirement.name: requirement for requirement in map(Requirement, dependencies)}

    assert "pypiwin32" not in requirements
    for package_name in ("pyautocad", "pywin32"):
        assert str(requirements[package_name].marker) == 'sys_platform == "win32"'

    pythoncom_available = importlib.util.find_spec("pythoncom") is not None
    if sys.platform == "win32":
        assert pythoncom_available
    else:
        assert not pythoncom_available
