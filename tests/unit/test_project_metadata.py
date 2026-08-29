"""Regression tests for the active development metadata contract."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

from packaging.requirements import Requirement


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _synchronized_python() -> str:
    """Return the project virtualenv interpreter after proving its boundary."""
    assert Path(sys.prefix).resolve() == (REPOSITORY_ROOT / ".venv").resolve()
    return sys.executable


def _source_version_from_synchronized_venv() -> str:
    """Import the source module without relying on PYTHONPATH."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [_synchronized_python(), "-c", "from src import __version__; print(__version__)"],
        capture_output=True,
        check=False,
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _project_metadata() -> dict[str, object]:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as metadata_file:
        return tomllib.load(metadata_file)


def _manifest() -> dict[str, object]:
    return json.loads((REPOSITORY_ROOT / "mcp.json").read_text(encoding="utf-8"))


def test_active_metadata_agrees_on_the_supported_baseline() -> None:
    """Catch a version or target-platform drift across active metadata."""
    project = _project_metadata()
    manifest = _manifest()

    assert (
        project["project"]["version"]
        == manifest["version"]
        == _source_version_from_synchronized_venv()
        == "0.1.0"
    )
    assert "tool" not in project or "poetry" not in project["tool"]


def test_manifest_uses_the_temporary_module_launch_without_pythonpath() -> None:
    """Catch a return to the ambiguous script-path/PYTHONPATH launch path."""
    server = _manifest()["mcpServers"]["autocad-mcp"]

    assert server["command"] == "uv"
    assert server["args"] == ["run", "python", "-m", "src.server"]
    assert "PYTHONPATH" not in server.get("env", {})


def test_com_dependencies_are_windows_only() -> None:
    """Catch a dependency migration that installs COM packages on Linux."""
    _synchronized_python()
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
