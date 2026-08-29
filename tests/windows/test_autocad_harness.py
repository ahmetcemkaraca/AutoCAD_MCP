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

from tests import conftest as smoke_conftest


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
    evidence = harness.close()

    assert opened == [(str(guard.copy_path), True)]
    assert opened[0][0] != str(guard.source_path)
    assert lease.assertions >= 2
    assert verified == [guard.copy_path.parent] * 4
    assert document.close_calls == [False]
    assert evidence.cleanup_succeeded is True


def test_harness_refuses_writable_document_and_preserves_evidence(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    with pytest.raises(RuntimeError, match="read-only"):
        ReadOnlyAutoCADHarness(
            lease=_Lease(),
            guard=guard,
            opener=lambda path, readonly: _Document(Path(path), read_only=False),
            acl_verifier=lambda path: None,
        ).open()

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert evidence.cleanup_succeeded is False
    assert guard.copy_path.exists()


def test_harness_requires_unchanged_copy_and_drawing_fingerprint(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=lambda path: None,
    )
    harness.open()
    document.DBMOD = 1

    with pytest.raises(RuntimeError, match="fingerprint changed"):
        harness.close()

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert evidence.cleanup_succeeded is False
    assert document.close_calls == [False]


def test_harness_preserves_guard_evidence_when_acl_verification_fails(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)

    calls = 0

    def reject_acl(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError(f"unsafe ACL: {path}")

    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=reject_acl,
    )
    harness.open()

    with pytest.raises(RuntimeError, match="unsafe ACL"):
        harness.close()

    evidence = guard.finalize(preserve=False, reason="normal cleanup")
    assert evidence.preserved is True
    assert document.close_calls == []


def test_pre_open_acl_failure_never_calls_opener(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    calls: list[tuple[str, bool]] = []

    with pytest.raises(RuntimeError, match="unsafe ACL"):
        ReadOnlyAutoCADHarness(
            lease=_Lease(),
            guard=guard,
            opener=lambda path, readonly: calls.append((path, readonly)),
            acl_verifier=lambda path: (_ for _ in ()).throw(RuntimeError("unsafe ACL")),
        ).open()

    assert calls == []
    assert guard.copy_path.exists()


def test_close_does_not_call_document_after_lease_loss(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    class LostLease(_Lease):
        def __init__(self) -> None:
            super().__init__()
            self.live = True

        def assert_owned(self) -> None:
            super().assert_owned()
            if not self.live:
                raise RuntimeError("lease lost")

    lease = LostLease()
    document = _Document(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=lease,
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=lambda path: None,
    )
    harness.open()
    lease.live = False

    with pytest.raises(RuntimeError, match="lease lost"):
        harness.close()

    assert document.close_calls == []
    assert guard.copy_path.exists()


def test_open_file_mutation_is_detected_and_preserved(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)

    def mutating_opener(path: str, readonly: bool) -> _Document:
        Path(path).write_bytes(b"mutated by open")
        return document

    with pytest.raises(RuntimeError, match="file fingerprint changed"):
        ReadOnlyAutoCADHarness(
            lease=_Lease(), guard=guard, opener=mutating_opener, acl_verifier=lambda path: None
        ).open()

    assert document.close_calls == [False]
    assert guard.copy_path.exists()


def test_close_file_mutation_is_detected_and_preserved(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    class MutatingCloseDocument(_Document):
        def Close(self, save_changes: bool) -> None:  # noqa: N802 - COM member spelling
            super().Close(save_changes)
            guard.copy_path.write_bytes(b"mutated by close")

    document = MutatingCloseDocument(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=lambda path: None,
    )
    harness.open()

    with pytest.raises(RuntimeError, match="file fingerprint changed"):
        harness.close()

    assert document.close_calls == [False]
    assert guard.copy_path.exists()


def test_close_failure_preserves_without_retrying_close(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    class FailingCloseDocument(_Document):
        def Close(self, save_changes: bool) -> None:  # noqa: N802 - COM member spelling
            super().Close(save_changes)
            raise RuntimeError("close failed")

    document = FailingCloseDocument(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=lambda path: None,
    )
    harness.open()

    with pytest.raises(RuntimeError, match="close failed"):
        harness.close()

    assert document.close_calls == [False]
    assert guard.copy_path.exists()


def test_close_rejects_arbitrary_document_substitution(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    document = _Document(guard.copy_path)
    harness = ReadOnlyAutoCADHarness(
        lease=_Lease(),
        guard=guard,
        opener=lambda path, readonly: document,
        acl_verifier=lambda path: None,
    )
    harness.open()

    with pytest.raises(TypeError):
        harness.close(_Document(guard.copy_path))  # type: ignore[call-arg]


def test_opt_in_invalid_environment_fails_not_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    class Config:
        def getoption(self, name: str) -> bool:
            assert name == "--run-autocad"
            return True

    class Request:
        config = Config()

    monkeypatch.setattr(smoke_conftest.sys, "platform", "win32")
    monkeypatch.delenv("AUTOCAD_MCP_SMOKE_DISPOSABLE", raising=False)

    with pytest.raises(pytest.fail.Exception, match="AUTOCAD_MCP_SMOKE_DISPOSABLE=YES"):
        next(smoke_conftest.autocad_smoke_session.__wrapped__(Request()))


def test_writable_direct_environment_source_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.dwg"
    source.write_bytes(b"writable")
    monkeypatch.setattr(smoke_conftest.sys, "platform", "win32")

    with pytest.raises(pytest.fail.Exception, match="immutable"):
        smoke_conftest._assert_readonly_source(source)


def test_marked_test_is_auto_gated_by_smoke_fixture() -> None:
    class Config:
        def getoption(self, name: str) -> bool:
            assert name == "--run-autocad"
            return True

    class Item:
        fixturenames: list[str] = []

        @staticmethod
        def get_closest_marker(name: str) -> object | None:
            return object() if name == "autocad" else None

    item = Item()
    smoke_conftest.pytest_collection_modifyitems(Config(), [item])

    assert item.fixturenames == ["autocad_smoke_session"]


def test_fixture_releases_lease_after_guard_finalization_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.dwg"
    installation = tmp_path / "acad.exe"
    source.write_bytes(b"fixture")
    installation.write_bytes(b"binary")
    root = tmp_path / "guard-root"
    copy_path = root / "run" / "drawing-copy.dwg"
    copy_path.parent.mkdir(parents=True)
    copy_path.write_bytes(b"copy")

    class Lease:
        released = 0

        def assert_owned(self) -> None:
            return None

        def release(self) -> None:
            self.released += 1

    class Guard:
        def __init__(self) -> None:
            self.copy_path = copy_path

        def finalize(self, *, preserve: bool, reason: str) -> None:
            raise RuntimeError("guard finalization failed")

    class Config:
        @staticmethod
        def getoption(name: str) -> bool:
            return name == "--run-autocad"

    class Request:
        config = Config()

    lease = Lease()
    monkeypatch.setattr(smoke_conftest.sys, "platform", "win32")
    monkeypatch.setenv("AUTOCAD_MCP_SMOKE_DISPOSABLE", "YES")
    monkeypatch.setenv("AUTOCAD_MCP_SMOKE_SOURCE_DWG", str(source))
    monkeypatch.setenv("AUTOCAD_MCP_AUTOCAD_INSTALLATION", str(installation))
    monkeypatch.setattr(smoke_conftest, "_assert_readonly_source", lambda path: None)
    monkeypatch.setattr(smoke_conftest, "build_autocad_lease_key", lambda **kwargs: "key")
    monkeypatch.setattr(smoke_conftest.AutoCADLease, "acquire", lambda key: lease)
    monkeypatch.setattr(smoke_conftest, "create_guard_run_temp_root", lambda: root)
    monkeypatch.setattr(smoke_conftest.DrawingCopyGuard, "prepare", lambda *args, **kwargs: Guard())
    monkeypatch.setattr(
        smoke_conftest, "assert_guard_run_current_user_system_acl", lambda path: None
    )

    fixture = smoke_conftest.autocad_smoke_session.__wrapped__(Request())
    next(fixture)
    with pytest.raises(RuntimeError, match="guard finalization failed"):
        next(fixture)

    assert lease.released == 1


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
    assert "$PSScriptRoot" in runner_source
    assert "Push-Location" in runner_source
    assert "Pop-Location" in runner_source
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


def test_opted_in_marked_test_cannot_bypass_smoke_fixture(tmp_path: Path) -> None:
    real_test = tmp_path / "test_real_autocad.py"
    real_test.write_text(
        "import pytest\n\n@pytest.mark.autocad\ndef test_real_autocad():\n    assert False\n",
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - fixed current interpreter and local test file
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-rs",
            "-p",
            "tests.conftest",
            "--run-autocad",
            str(real_test),
        ],
        capture_output=True,
        cwd=Path(__file__).parents[2],
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires Windows" in result.stdout
    assert "assert False" not in result.stdout
