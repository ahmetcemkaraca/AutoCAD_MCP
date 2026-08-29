"""Opt-in safety gate for real, disposable-DWG AutoCAD tests."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.windows.autocad_lease import (
    AutoCADLease,
    build_autocad_lease_key,
    create_guard_run_temp_root,
)
from tests.windows.drawing_copy_guard import DrawingCopyGuard

_AUTHORIZATION_REASON = "requires explicit disposable-DWG authorization"


@dataclass(frozen=True)
class AutoCADSmokeSession:
    source_path: Path
    installation_path: Path
    lease: AutoCADLease
    guard: DrawingCopyGuard


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-autocad",
        action="store_true",
        default=False,
        help="authorize explicitly configured disposable-DWG AutoCAD tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "autocad: requires explicit disposable-DWG authorization")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-autocad"):
        return
    skip = pytest.mark.skip(reason=_AUTHORIZATION_REASON)
    for item in items:
        if item.get_closest_marker("autocad") is not None:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def autocad_smoke_session(request: pytest.FixtureRequest) -> AutoCADSmokeSession:
    """Yield the only real-test controller state after fail-closed preflight."""
    if not request.config.getoption("--run-autocad"):
        pytest.skip(_AUTHORIZATION_REASON)
    if sys.platform != "win32":
        pytest.skip("requires Windows")
    if os.environ.get("AUTOCAD_MCP_SMOKE_DISPOSABLE") != "YES":
        pytest.skip("AUTOCAD_MCP_SMOKE_DISPOSABLE=YES is required")

    source_path = _required_absolute_file("AUTOCAD_MCP_SMOKE_SOURCE_DWG", suffix=".dwg")
    installation_path = _required_absolute_file(
        "AUTOCAD_MCP_AUTOCAD_INSTALLATION", filename="acad.exe"
    )
    lease_key = build_autocad_lease_key(installation_path=installation_path)
    lease = AutoCADLease.acquire(lease_key)
    guard: DrawingCopyGuard | None = None
    try:
        lease.assert_owned()
        guard = DrawingCopyGuard.prepare(source_path, temp_root=create_guard_run_temp_root())
        lease.assert_owned()
        yield AutoCADSmokeSession(source_path, installation_path, lease, guard)
    finally:
        if guard is not None:
            guard.finalize(preserve=True, reason="session fixture ended")
        lease.release()


def _required_absolute_file(
    name: str, *, suffix: str | None = None, filename: str | None = None
) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is required")
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        pytest.skip(f"{name} must be an absolute existing file")
    if suffix is not None and path.suffix.lower() != suffix:
        pytest.skip(f"{name} must name a {suffix} file")
    if filename is not None and path.name.lower() != filename:
        pytest.skip(f"{name} must name {filename}")
    return path
