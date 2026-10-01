"""Installed distribution boundary tests for the canonical package."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

import autocad_mcp

PROJECT_ROOT = Path(__file__).parents[2]


def test_autocad_mcp_is_an_installed_distribution_without_pythonpath() -> None:
    """Removing the package installation must make this import boundary fail."""
    assert importlib.util.find_spec("autocad_mcp") is not None
    assert version("autocad-mcp") == "0.1.0"
    assert autocad_mcp.__version__ == version("autocad-mcp")

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import autocad_mcp; from importlib.metadata import version; "
            "assert autocad_mcp.__version__ == version('autocad-mcp') == '0.1.0'",
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_hatchling_wheel_configuration_is_the_package_boundary() -> None:
    """Replacing the declared wheel package must fail this release boundary."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    assert pyproject["build-system"] == {
        "requires": ["hatchling>=1.27,<2"],
        "build-backend": "hatchling.build",
    }
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"] == {
        "packages": ["src/autocad_mcp"],
    }
    assert "package" not in pyproject.get("tool", {}).get("uv", {})
