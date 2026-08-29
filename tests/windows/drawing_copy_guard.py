"""COM-free disposable drawing-copy guard for real AutoCAD test policies."""

from __future__ import annotations

import hashlib
import ntpath
import secrets
import shutil
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

_COPY_NAME = "drawing-copy.dwg"
_MARKER_NAME = ".drawing-copy-guard-token"
_QUARANTINE_PREFIX = "autocad-mcp-quarantine-"
_RUN_PREFIX = "autocad-mcp-"
_CREATION_KEY = object()


@dataclass(frozen=True)
class DrawingCopyEvidence:
    run_id: str
    source_path: str
    copy_path: str
    source_sha256_before: str
    source_sha256_after: str | None
    copy_sha256_before: str
    copy_sha256_after: str | None
    active_full_name: str | None
    close_without_save_attempted: bool
    preserved: bool
    preserve_reason: str | None
    cleanup_succeeded: bool


@dataclass(frozen=True)
class _Ownership:
    run_id: str
    source_path: Path
    source_sha256_before: str
    copy_sha256_before: str
    temp_root: Path
    run_directory: Path
    copy_path: Path
    marker_token: str


class DrawingCopyViolation(RuntimeError):  # noqa: N818 - public contract name
    """A guard invariant failed; the associated disposable copy is preserved."""

    evidence: DrawingCopyEvidence

    def __init__(self, message: str, evidence: DrawingCopyEvidence) -> None:
        super().__init__(message)
        self.evidence = evidence


class DrawingCopyGuard:
    """Create and account for one disposable source-derived drawing copy."""

    __slots__ = (
        "_active_full_name",
        "_close_without_save_attempted",
        "_current_copy_path",
        "_current_directory",
        "_ownership",
        "_preservation_existed",
        "_preserve_reason",
    )

    def __init__(self, *, ownership: _Ownership, creation_key: object) -> None:
        if creation_key is not _CREATION_KEY:
            raise TypeError("DrawingCopyGuard instances must be created with prepare()")
        object.__setattr__(self, "_ownership", ownership)
        self._current_directory = ownership.run_directory
        self._current_copy_path = ownership.copy_path
        self._active_full_name: str | None = None
        self._close_without_save_attempted = False
        self._preserve_reason: str | None = None
        self._preservation_existed: bool | None = None

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_ownership" and hasattr(self, "_ownership"):
            raise AttributeError("DrawingCopyGuard ownership cannot be reassigned")
        object.__setattr__(self, name, value)

    @classmethod
    def prepare(cls, source_path: Path, *, temp_root: Path | None = None) -> Self:
        source = Path(source_path).resolve()
        if source.suffix.lower() != ".dwg" or not source.is_file():
            raise ValueError("source_path must be a regular .dwg file")
        source_before = _sha256(source)
        root = Path(tempfile.gettempdir()) if temp_root is None else Path(temp_root)
        root.mkdir(parents=True, exist_ok=True)
        root = root.resolve()
        run_id = str(uuid.uuid4())
        run_directory = root / f"{_RUN_PREFIX}{run_id}"
        run_directory.mkdir()
        copy_path = run_directory / _COPY_NAME
        marker_token = secrets.token_urlsafe(32)
        try:
            (run_directory / _MARKER_NAME).write_text(marker_token, encoding="utf-8")
        except OSError as error:
            evidence = _preparation_evidence(
                run_id,
                source,
                copy_path,
                source_before,
                _maybe_sha256(source),
                "guard setup failed",
            )
            raise DrawingCopyViolation("guard setup failed", evidence) from error

        try:
            shutil.copy2(source, copy_path)
            resolved_copy = copy_path.resolve(strict=True)
        except OSError as error:
            evidence = _preparation_evidence(
                run_id,
                source,
                copy_path,
                source_before,
                _maybe_sha256(source),
                f"copy preparation failed: {error}",
            )
            raise DrawingCopyViolation("copy preparation failed", evidence) from error

        source_after = _maybe_sha256(source)
        copy_after = _maybe_sha256(resolved_copy)
        if source == resolved_copy:
            evidence = _preparation_evidence(
                run_id,
                source,
                resolved_copy,
                source_before,
                source_after,
                "source and disposable copy must differ",
            )
            raise DrawingCopyViolation("source and disposable copy must differ", evidence)
        if source_after != source_before:
            evidence = _preparation_evidence(
                run_id,
                source,
                resolved_copy,
                source_before,
                source_after,
                "source changed during preparation",
            )
            raise DrawingCopyViolation("source changed during preparation", evidence)
        if copy_after != source_before:
            evidence = _preparation_evidence(
                run_id,
                source,
                resolved_copy,
                source_before,
                source_after,
                "initial copy hash does not match source",
            )
            raise DrawingCopyViolation("initial copy hash does not match source", evidence)
        return cls(
            ownership=_Ownership(
                run_id=run_id,
                source_path=source,
                source_sha256_before=source_before,
                copy_sha256_before=copy_after,
                temp_root=root,
                run_directory=run_directory,
                copy_path=resolved_copy,
                marker_token=marker_token,
            ),
            creation_key=_CREATION_KEY,
        )

    @property
    def source_path(self) -> Path:
        return self._ownership.source_path

    @property
    def copy_path(self) -> Path:
        return self._ownership.copy_path

    def assert_active_full_name(self, active_full_name: str) -> None:
        self._active_full_name = active_full_name
        active_path = _normalized_windows_path(active_full_name)
        if active_path == _normalized_windows_path(str(self.source_path)):
            self._raise_violation("active document is the source drawing")
        if active_path != _normalized_windows_path(str(self.copy_path)):
            self._raise_violation("active document does not match the disposable copy")

    def close_without_save(self, close_document: Callable[[bool], None]) -> None:
        self._close_without_save_attempted = True
        close_document(False)

    def finalize(self, *, preserve: bool, reason: str) -> DrawingCopyEvidence:
        source_after = _maybe_sha256(self.source_path)
        copy_after = _maybe_sha256(self._current_copy_path)
        if self._preserve_reason is not None:
            return self._evidence(source_after, copy_after, cleanup_succeeded=False)
        if source_after != self._ownership.source_sha256_before:
            self._latch_preservation("source changed during guarded run")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation("source changed during guarded run", evidence)
        if preserve:
            if not reason.strip():
                raise ValueError("preserve reason must be non-empty")
            self._latch_preservation(reason)
            return self._evidence(source_after, copy_after, cleanup_succeeded=False)
        if not self._valid_owned_directory(self._ownership.run_directory, _RUN_PREFIX):
            self._latch_preservation("cleanup refused: guard ownership validation failed")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation(
                "cleanup refused: guard ownership validation failed", evidence
            )

        quarantine = self._new_quarantine_directory()
        try:
            self._ownership.run_directory.replace(quarantine)
        except OSError as error:
            self._set_current_location(
                quarantine if quarantine.exists() else self._ownership.run_directory
            )
            self._latch_preservation(f"cleanup move failed: {error}")
            evidence = self._evidence(source_after, _maybe_sha256(self._current_copy_path), False)
            raise DrawingCopyViolation(self._cleanup_failure_message(), evidence) from error
        self._set_current_location(quarantine)
        if not self._valid_owned_directory(quarantine, _QUARANTINE_PREFIX):
            self._latch_preservation(
                "cleanup refused after quarantine: ownership validation failed"
            )
            evidence = self._evidence(source_after, _maybe_sha256(self._current_copy_path), False)
            raise DrawingCopyViolation("cleanup refused after quarantine", evidence)
        try:
            shutil.rmtree(quarantine)
        except OSError as error:
            self._latch_preservation(f"cleanup failed: {error}")
            evidence = self._evidence(source_after, _maybe_sha256(self._current_copy_path), False)
            raise DrawingCopyViolation(self._cleanup_failure_message(), evidence) from error
        return self._evidence(source_after, copy_after, True)

    def _new_quarantine_directory(self) -> Path:
        return self._ownership.temp_root / f"{_QUARANTINE_PREFIX}{uuid.uuid4()}"

    def _set_current_location(self, directory: Path) -> None:
        self._current_directory = directory
        self._current_copy_path = directory / _COPY_NAME

    def _valid_owned_directory(self, directory: Path, prefix: str) -> bool:
        try:
            expected_copy = directory / _COPY_NAME
            marker = directory / _MARKER_NAME
            run_id = directory.name.removeprefix(prefix)
            return (
                directory.name == f"{prefix}{run_id}"
                and str(uuid.UUID(run_id)) == run_id
                and directory.parent == self._ownership.temp_root
                and directory.is_dir()
                and directory.resolve(strict=True) == directory
                and expected_copy.is_file()
                and expected_copy.resolve(strict=True) == expected_copy
                and self.source_path.resolve(strict=True) != expected_copy.resolve(strict=True)
                and marker.is_file()
                and marker.read_text(encoding="utf-8") == self._ownership.marker_token
            )
        except (OSError, ValueError):
            return False

    def _latch_preservation(self, reason: str) -> None:
        if self._preserve_reason is None:
            self._preserve_reason = reason
            self._preservation_existed = self._current_copy_path.is_file()

    def _is_preserved(self) -> bool:
        if self._preservation_existed is None:
            return self._current_copy_path.is_file()
        return self._preservation_existed and self._current_copy_path.is_file()

    def _cleanup_failure_message(self) -> str:
        if self._is_preserved():
            return "cleanup failed; disposable copy preserved"
        return "cleanup failed; disposable copy unavailable"

    def _raise_violation(self, message: str) -> None:
        self._latch_preservation(message)
        evidence = self._evidence(
            _maybe_sha256(self.source_path), _maybe_sha256(self._current_copy_path), False
        )
        raise DrawingCopyViolation(message, evidence)

    def _evidence(
        self, source_after: str | None, copy_after: str | None, cleanup_succeeded: bool
    ) -> DrawingCopyEvidence:
        return DrawingCopyEvidence(
            run_id=self._ownership.run_id,
            source_path=str(self.source_path),
            copy_path=str(self._current_copy_path),
            source_sha256_before=self._ownership.source_sha256_before,
            source_sha256_after=source_after,
            copy_sha256_before=self._ownership.copy_sha256_before,
            copy_sha256_after=copy_after,
            active_full_name=self._active_full_name,
            close_without_save_attempted=self._close_without_save_attempted,
            preserved=self._is_preserved(),
            preserve_reason=self._preserve_reason,
            cleanup_succeeded=cleanup_succeeded,
        )


def _preparation_evidence(
    run_id: str,
    source_path: Path,
    copy_path: Path,
    source_before: str,
    source_after: str | None,
    reason: str,
) -> DrawingCopyEvidence:
    copy_hash = _maybe_sha256(copy_path)
    return DrawingCopyEvidence(
        run_id=run_id,
        source_path=str(source_path),
        copy_path=str(copy_path),
        source_sha256_before=source_before,
        source_sha256_after=source_after,
        copy_sha256_before=copy_hash or "",
        copy_sha256_after=copy_hash,
        active_full_name=None,
        close_without_save_attempted=False,
        preserved=copy_path.is_file(),
        preserve_reason=reason,
        cleanup_succeeded=False,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _maybe_sha256(path: Path) -> str | None:
    try:
        return _sha256(path)
    except OSError:
        return None


def _normalized_windows_path(path: str) -> str:
    candidate = Path(path)
    try:
        normalized = candidate.resolve(strict=True)
    except OSError:
        normalized = candidate
    return ntpath.normcase(ntpath.normpath(str(normalized).replace("/", "\\")))
