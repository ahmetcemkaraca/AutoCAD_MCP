"""Pure contracts for the read-only AutoCAD smoke harness."""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import autocad_harness
import pytest
from autocad_harness import ReadOnlyAutoCADHarness
from drawing_copy_guard import DrawingCopyGuard


class _Lease:
    def __init__(self) -> None:
        self.assertions = 0

    def assert_owned(self) -> None:
        self.assertions += 1


class _Entity:
    ObjectID = 7
    Handle = "A"
    ObjectName = "AcDbLine"
    Layer = "0"


class _Document:
    def __init__(self, path: Path, *, read_only: bool = True) -> None:
        self.FullName = str(path)
        self.ReadOnly = read_only
        self.DBMOD = 0
        self.ModelSpace = [_Entity()]
        self.close_calls: list[bool] = []

    def Close(self, save_changes: bool) -> None:  # noqa: N802 - COM member spelling
        self.close_calls.append(save_changes)


def _guard(tmp_path: Path) -> DrawingCopyGuard:
    source = tmp_path / "source.dwg"
    source.write_bytes(b"read-only fixture")
    return DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")


def test_harness_requires_owned_lease(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    class ReleasedLease(_Lease):
        def assert_owned(self) -> None:
            super().assert_owned()
            raise RuntimeError("lease is not owned")

    with pytest.raises(RuntimeError, match="lease is not owned"):
        ReadOnlyAutoCADHarness(
            lease=ReleasedLease(), guard=guard, opener=lambda path, readonly: _Document(Path(path))
        ).open()


def test_harness_opens_guard_copy_not_source_and_uses_true_readonly_flag(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    lease = _Lease()
    opened: list[tuple[str, bool]] = []
    verified: list[Path] = []

    def opener(path: str, read_only: bool) -> _Document:
        opened.append((path, read_only))
        return _Document(Path(path))

    harness = ReadOnlyAutoCADHarness(
        lease=lease,
        guard=guard,
        opener=opener,
        acl_verifier=verified.append,
    )
    document = harness.open()
    evidence = harness.close(document)

    assert opened == [(str(guard.copy_path), True)]
    assert opened[0][0] != str(guard.source_path)
    assert lease.assertions >= 2
    assert verified == [guard.copy_path.parent]
    assert document.close_calls == [False]
    assert evidence.cleanup_succeeded is True


def test_harness_refuses_writable_document_and_preserves_evidence(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    with pytest.raises(RuntimeError, match="read-only"):
        ReadOnlyAutoCADHarness(
            lease=_Lease(),
            guard=guard,
            opener=lambda path, readonly: _Document(Path(path), read_only=False),
        ).open()

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert evidence.cleanup_succeeded is False
    assert guard.copy_path.exists()


def test_harness_requires_unchanged_copy_and_drawing_fingerprint(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(), guard=guard, opener=lambda path, readonly: document
    )
    harness.open()
    document.DBMOD = 1

    with pytest.raises(RuntimeError, match="fingerprint changed"):
        harness.close(document)

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert evidence.cleanup_succeeded is False
    assert document.close_calls == [False]


def test_harness_preserves_guard_evidence_when_acl_verification_fails(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)

    def reject_acl(path: Path) -> None:
        raise RuntimeError(f"unsafe ACL: {path}")

    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=reject_acl,
    )
    harness.open()

    with pytest.raises(RuntimeError, match="unsafe ACL"):
        harness.close(document)

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert document.close_calls == [False]


def test_harness_has_no_writable_policy_class_or_mutation_apis() -> None:
    classes = [
        value
        for _, value in inspect.getmembers(autocad_harness, inspect.isclass)
        if value.__module__ == autocad_harness.__name__
    ]
    assert not any("writable" in value.__name__.lower() for value in classes)
    source = inspect.getsource(autocad_harness)
    for forbidden in ("SendCommand", "Undo", "AddLine", "SaveAs"):
        assert forbidden not in source


def test_opt_in_fixture_and_runner_are_constrained() -> None:
    conftest_source = (Path(__file__).parents[1] / "conftest.py").read_text(encoding="utf-8")
    runner_source = (
        Path(__file__).parents[2] / "scripts" / "run_autocad_2026_smoke.ps1"
    ).read_text(encoding="utf-8")

    assert '"requires explicit disposable-DWG authorization"' in conftest_source
    assert "--run-autocad" in conftest_source
    assert "AUTOCAD_MCP_SMOKE_DISPOSABLE" in conftest_source
    assert "build_autocad_lease_key" in conftest_source
    assert "create_guard_run_temp_root" in conftest_source
    assert "assert_owned" in conftest_source
    assert "finally:" in conftest_source
    assert "[Parameter(Mandatory = $true)]" in runner_source
    assert "uv sync --frozen --group dev" in runner_source
    command = "uv run pytest tests/windows/test_autocad_2026_smoke.py -m autocad"
    assert f"{command} --run-autocad -vv --tb=short" in runner_source
    for forbidden in ("LeaseKey", "Salt", "Isolation", "Concurrency", "Copy-Item", "Start-Process"):
        assert forbidden not in runner_source


def test_autocad_marker_skips_without_explicit_opt_in(tmp_path: Path) -> None:
    real_test = tmp_path / "test_real_autocad.py"
    real_test.write_text(
        "import pytest\n\n@pytest.mark.autocad\ndef test_real_autocad():\n    assert False\n",
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - fixed current interpreter and local test file
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "tests.conftest", str(real_test)],
        capture_output=True,
        cwd=Path(__file__).parents[2],
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "1 skipped" in result.stdout
    assert "requires explicit disposable-DWG authorization" in result.stdout
