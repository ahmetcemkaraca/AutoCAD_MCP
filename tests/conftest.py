"""Opt-in safety gate for real, disposable-DWG AutoCAD tests."""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.windows.autocad_lease import (
    AutoCADLease,
    assert_guard_run_current_user_system_acl,
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
    for item in items:
        if item.get_closest_marker("autocad") is None:
            continue
        if not config.getoption("--run-autocad"):
            item.add_marker(pytest.mark.skip(reason=_AUTHORIZATION_REASON))
        elif "autocad_smoke_session" not in item.fixturenames:
            item.fixturenames.append("autocad_smoke_session")


@pytest.fixture(scope="session")
def autocad_smoke_session(request: pytest.FixtureRequest) -> AutoCADSmokeSession:
    """Yield the only real-test controller state after fail-closed preflight."""
    if not request.config.getoption("--run-autocad"):
        pytest.skip(_AUTHORIZATION_REASON)
    if sys.platform != "win32":
        pytest.fail("requires Windows")
    if os.environ.get("AUTOCAD_MCP_SMOKE_DISPOSABLE") != "YES":
        pytest.fail("AUTOCAD_MCP_SMOKE_DISPOSABLE=YES is required")

    source_path = _required_absolute_file("AUTOCAD_MCP_SMOKE_SOURCE_DWG", suffix=".dwg")
    _assert_readonly_source(source_path)
    installation_path = _required_absolute_file(
        "AUTOCAD_MCP_AUTOCAD_INSTALLATION", filename="acad.exe"
    )
    lease_key = build_autocad_lease_key(installation_path=installation_path)
    lease = AutoCADLease.acquire(lease_key)
    guard: DrawingCopyGuard | None = None
    guard_root: Path | None = None
    primary_error: BaseException | None = None
    try:
        lease.assert_owned()
        guard_root = create_guard_run_temp_root()
        guard = DrawingCopyGuard.prepare(source_path, temp_root=guard_root)
        assert_guard_run_current_user_system_acl(guard.copy_path.parent)
        lease.assert_owned()
        yield AutoCADSmokeSession(source_path, installation_path, lease, guard)
    except BaseException as error:
        primary_error = error
        raise
    finally:
        cleanup_errors: list[tuple[str, BaseException]] = []
        _attempt_cleanup(
            cleanup_errors,
            "guard preservation",
            lambda: _preserve_existing_guard(guard),
        )
        _attempt_cleanup(
            cleanup_errors,
            "guard-root cleanup",
            lambda: _remove_empty_guard_root(guard_root, lease),
        )
        _attempt_cleanup(cleanup_errors, "lease release", lease.release)
        _raise_or_note_cleanup_errors(primary_error, cleanup_errors)


def _required_absolute_file(
    name: str, *, suffix: str | None = None, filename: str | None = None
) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.fail(f"{name} is required")
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        pytest.fail(f"{name} must be an absolute existing file")
    if suffix is not None and path.suffix.lower() != suffix:
        pytest.fail(f"{name} must name a {suffix} file")
    if filename is not None and path.name.lower() != filename:
        pytest.fail(f"{name} must name {filename}")
    return path


def _assert_readonly_source(source_path: Path) -> None:
    source_stat = source_path.stat()
    readonly_attribute = getattr(stat, "FILE_ATTRIBUTE_READONLY", 0x1)
    attributes = getattr(source_stat, "st_file_attributes", 0)
    if not attributes & readonly_attribute and source_stat.st_mode & stat.S_IWUSR:
        pytest.fail("AUTOCAD_MCP_SMOKE_SOURCE_DWG must be immutable (read-only)")


def _preserve_existing_guard(guard: DrawingCopyGuard | None) -> None:
    if guard is not None and guard.copy_path.exists():
        guard.finalize(preserve=True, reason="session fixture ended")


def _remove_empty_guard_root(guard_root: Path | None, lease: AutoCADLease) -> None:
    if guard_root is None or not guard_root.exists():
        return
    assert_guard_run_current_user_system_acl(guard_root)
    if next(guard_root.iterdir(), None) is None:
        lease.assert_owned()
        guard_root.rmdir()


def _attempt_cleanup(
    cleanup_errors: list[tuple[str, BaseException]], name: str, operation: Callable[[], object]
) -> None:
    try:
        operation()
    except BaseException as error:
        cleanup_errors.append((name, error))


def _raise_or_note_cleanup_errors(
    primary_error: BaseException | None, cleanup_errors: list[tuple[str, BaseException]]
) -> None:
    if primary_error is not None:
        for name, error in cleanup_errors:
            primary_error.add_note(f"{name} also failed: {error}")
        return
    if not cleanup_errors:
        return
    _, first_error = cleanup_errors[0]
    for name, error in cleanup_errors[1:]:
        first_error.add_note(f"{name} also failed: {error}")
    raise first_error
