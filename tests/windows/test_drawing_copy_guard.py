"""Behavior tests for the COM-free disposable drawing copy guard."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, replace
from pathlib import Path
from typing import get_type_hints

import drawing_copy_guard
import pytest
from drawing_copy_guard import DrawingCopyEvidence, DrawingCopyGuard, DrawingCopyViolation


def _source_dwg(tmp_path: Path, name: str = "fixture.dwg") -> Path:
    source = tmp_path / name
    source.write_bytes(b"safe fake DWG bytes\x00\x01")
    return source


def test_prepare_creates_unique_guid_copy(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)

    first = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")
    second = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")

    assert first.source_path == source.resolve()
    assert first.copy_path.name == "drawing-copy.dwg"
    assert first.copy_path.parent != second.copy_path.parent
    assert re.fullmatch(r"autocad-mcp-[0-9a-f-]{36}", first.copy_path.parent.name)
    assert first.copy_path.read_bytes() == source.read_bytes()
    assert first.copy_path.resolve() != first.source_path
    first_evidence = first.finalize(preserve=False, reason="completed")
    second_evidence = second.finalize(preserve=False, reason="completed")
    assert isinstance(first_evidence.source_path, str)
    assert isinstance(first_evidence.copy_path, str)
    assert first_evidence.source_path == str(source.resolve())
    assert first_evidence.copy_path.endswith("drawing-copy.dwg")
    assert second_evidence.cleanup_succeeded is True


def test_evidence_is_json_native_and_violation_declares_it(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    evidence = guard.finalize(preserve=True, reason="serialize evidence")

    assert get_type_hints(DrawingCopyEvidence)["source_path"] is str
    assert get_type_hints(DrawingCopyEvidence)["copy_path"] is str
    assert get_type_hints(DrawingCopyViolation)["evidence"] is DrawingCopyEvidence
    assert json.dumps(asdict(evidence))


def test_prepare_rejects_same_or_non_dwg_path(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)
    directory_dwg = tmp_path / "directory.dwg"
    directory_dwg.mkdir()

    with pytest.raises(ValueError, match="regular .dwg"):
        DrawingCopyGuard.prepare(tmp_path / "missing.dwg")
    with pytest.raises(ValueError, match="regular .dwg"):
        DrawingCopyGuard.prepare(directory_dwg)
    with pytest.raises(ValueError, match="regular .dwg"):
        DrawingCopyGuard.prepare(source.with_suffix(".txt"))


def test_source_hash_change_fails_and_preserves_copy(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)
    guard = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")
    source.write_bytes(b"source changed")

    with pytest.raises(DrawingCopyViolation) as raised:
        guard.finalize(preserve=False, reason="completed")

    evidence = raised.value.evidence
    assert evidence.source_sha256_before != evidence.source_sha256_after
    assert evidence.preserved is True
    assert evidence.preserve_reason == "source changed during guarded run"
    assert evidence.cleanup_succeeded is False
    assert guard.copy_path.exists()


def test_active_full_name_must_equal_copy(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)
    guard = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")

    active_copy = str(guard.copy_path).replace("/", "\\").upper()
    guard.assert_active_full_name(active_copy)

    with pytest.raises(DrawingCopyViolation) as source_error:
        guard.assert_active_full_name(str(source))
    assert source_error.value.evidence.active_full_name == str(source)
    run_directory = guard.copy_path.parent

    with pytest.raises(DrawingCopyViolation):
        guard.assert_active_full_name(str(tmp_path / "unexpected.dwg"))
    evidence = guard.finalize(preserve=False, reason="completed")
    assert evidence.preserved is True
    assert evidence.preserve_reason == "active document is the source drawing"
    assert run_directory.exists()


def test_active_full_name_resolves_supported_symlink_aliases(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    alias = tmp_path / "copy-alias.dwg"
    try:
        alias.symlink_to(guard.copy_path)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    guard.assert_active_full_name(str(alias))
    evidence = guard.finalize(preserve=True, reason="alias evidence")
    assert evidence.active_full_name == str(alias)


def test_close_without_save_passes_false(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    calls: list[bool] = []

    guard.close_without_save(calls.append)
    evidence = guard.finalize(preserve=True, reason="capture close evidence")

    assert calls == [False]
    assert evidence.close_without_save_attempted is True
    assert evidence.preserved is True
    assert evidence.preserve_reason == "capture close evidence"
    assert guard.copy_path.exists()


def test_close_without_save_records_attempt_when_callback_raises(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    calls: list[bool] = []

    def fail_after_call(save_changes: bool) -> None:
        calls.append(save_changes)
        raise RuntimeError("close failed")

    with pytest.raises(RuntimeError, match="close failed"):
        guard.close_without_save(fail_after_call)

    evidence = guard.finalize(preserve=True, reason="close callback failed")
    assert calls == [False]
    assert evidence.close_without_save_attempted is True


def test_finalize_records_cleanup_or_preservation(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)
    cleanup_guard = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")
    cleanup_directory = cleanup_guard.copy_path.parent

    cleaned = cleanup_guard.finalize(preserve=False, reason="completed")

    assert cleaned.copy_sha256_before == cleaned.copy_sha256_after
    assert cleaned.source_sha256_before == cleaned.source_sha256_after
    assert cleaned.preserved is False
    assert cleaned.preserve_reason is None
    assert cleaned.cleanup_succeeded is True
    assert not cleanup_directory.exists()

    preserved_guard = DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")
    preserved_guard.copy_path.write_bytes(b"copy changed by a policy")
    preserved = preserved_guard.finalize(preserve=True, reason="policy requested evidence")

    assert preserved.copy_sha256_before != preserved.copy_sha256_after
    assert preserved.preserved is True
    assert preserved.preserve_reason == "policy requested evidence"
    assert preserved.cleanup_succeeded is False
    assert preserved_guard.copy_path.exists()


def test_finalize_refuses_coherent_ownership_retarget_without_deleting_unrelated_directory(
    tmp_path: Path,
) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    sentinel = unrelated / "keep.txt"
    sentinel.write_text("must survive", encoding="utf-8")
    ownership = guard._ownership

    with pytest.raises(AttributeError):
        guard._ownership = replace(
            ownership,
            temp_root=tmp_path,
            run_directory=unrelated,
            copy_path=unrelated / "drawing-copy.dwg",
        )

    evidence = guard.finalize(preserve=False, reason="completed")
    assert evidence.cleanup_succeeded is True
    assert sentinel.read_text(encoding="utf-8") == "must survive"


def test_prepare_detects_source_change_during_copy_and_preserves_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source_dwg(tmp_path)
    real_copy = drawing_copy_guard._copy_source_to_new_file

    def copy_then_change_source(source_path: Path, copy_path: Path) -> None:
        real_copy(source_path, copy_path)
        source.write_bytes(b"source changed during copy")

    monkeypatch.setattr(drawing_copy_guard, "_copy_source_to_new_file", copy_then_change_source)

    with pytest.raises(DrawingCopyViolation, match="source changed during preparation") as raised:
        DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")

    evidence = raised.value.evidence
    assert evidence.source_sha256_before != evidence.source_sha256_after
    assert evidence.copy_sha256_before == evidence.copy_sha256_after
    assert evidence.preserved is True
    assert Path(evidence.copy_path).exists()


def test_prepare_marker_setup_failure_reports_no_copy_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source_dwg(tmp_path)

    def fail_marker_write(path: Path, token: str) -> None:
        raise OSError("marker failure")

    monkeypatch.setattr(drawing_copy_guard, "_write_private_token", fail_marker_write)

    with pytest.raises(DrawingCopyViolation, match="guard setup failed") as raised:
        DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")

    assert raised.value.evidence.preserved is False
    assert Path(raised.value.evidence.copy_path).exists() is False


def test_prepare_copy_failure_reports_no_copy_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source_dwg(tmp_path)

    def fail_copy(source_path: Path, copy_path: Path) -> None:
        raise OSError("copy failure")

    monkeypatch.setattr(drawing_copy_guard, "_copy_source_to_new_file", fail_copy)

    with pytest.raises(DrawingCopyViolation, match="copy preparation failed") as raised:
        DrawingCopyGuard.prepare(source, temp_root=tmp_path / "runs")

    assert raised.value.evidence.preserved is False
    assert Path(raised.value.evidence.copy_path).exists() is False


def test_finalize_preserves_copy_after_marker_removal_and_latches_actual_state(
    tmp_path: Path,
) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    marker = guard.copy_path.parent / ".drawing-copy-guard-token"
    marker.unlink()

    with pytest.raises(DrawingCopyViolation, match="cleanup refused") as raised:
        guard.finalize(preserve=False, reason="completed")

    assert raised.value.evidence.preserved is True
    assert guard.copy_path.exists()
    later = guard.finalize(preserve=False, reason="completed")
    assert later.preserved is True


def test_finalize_refuses_unexpected_run_contents_without_deleting_them(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    sentinel = guard.copy_path.parent / "unexpected.txt"
    sentinel.write_text("must survive", encoding="utf-8")

    with pytest.raises(DrawingCopyViolation, match="cleanup refused") as raised:
        guard.finalize(preserve=False, reason="completed")

    evidence = raised.value.evidence
    assert evidence.preserved is True
    assert Path(evidence.copy_path).exists()
    assert sentinel.read_text(encoding="utf-8") == "must survive"


def test_partial_cleanup_reports_missing_copy_and_never_flips_to_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    real_unlink = Path.unlink

    def fail_marker_unlink(path: Path, **kwargs: object) -> None:
        if path.name == ".drawing-copy-guard-token":
            raise OSError("partial cleanup failure")
        real_unlink(path, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_marker_unlink)

    with pytest.raises(DrawingCopyViolation, match="copy unavailable") as raised:
        guard.finalize(preserve=False, reason="completed")

    assert raised.value.evidence.preserved is False
    later = guard.finalize(preserve=False, reason="completed")
    assert later.preserved is False


def test_exclusive_copy_destination_refuses_preexisting_or_symlinked_files(tmp_path: Path) -> None:
    source = _source_dwg(tmp_path)
    destination = tmp_path / "drawing-copy.dwg"
    destination.write_bytes(b"existing sentinel")

    with pytest.raises(FileExistsError):
        drawing_copy_guard._copy_source_to_new_file(source, destination)
    assert destination.read_bytes() == b"existing sentinel"

    target = tmp_path / "unrelated.txt"
    target.write_text("must survive", encoding="utf-8")
    alias = tmp_path / "alias.dwg"
    try:
        alias.symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    with pytest.raises(FileExistsError):
        drawing_copy_guard._copy_source_to_new_file(source, alias)
    assert target.read_text(encoding="utf-8") == "must survive"


def test_latched_violation_reports_replaced_copy_as_unavailable(tmp_path: Path) -> None:
    guard = DrawingCopyGuard.prepare(_source_dwg(tmp_path), temp_root=tmp_path / "runs")
    with pytest.raises(DrawingCopyViolation):
        guard.assert_active_full_name(str(tmp_path / "unexpected.dwg"))
    guard.copy_path.unlink()
    sentinel = tmp_path / "unrelated.txt"
    sentinel.write_text("must survive", encoding="utf-8")
    try:
        guard.copy_path.symlink_to(sentinel)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    evidence = guard.finalize(preserve=False, reason="completed")
    assert evidence.preserved is False
    assert sentinel.read_text(encoding="utf-8") == "must survive"


def test_guard_source_does_not_import_com() -> None:
    module_path = Path(DrawingCopyGuard.__module__.replace(".", "/") + ".py")
    source = (Path(__file__).parent / module_path.name).read_text(encoding="utf-8")

    assert "pythoncom" not in source
    assert "win32com" not in source
    assert "pyautocad" not in source
