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


class DrawingCopyViolation(RuntimeError):  # noqa: N818 - public contract name
    """A guard invariant failed; the associated disposable copy is preserved."""

    evidence: DrawingCopyEvidence

    def __init__(self, message: str, evidence: DrawingCopyEvidence) -> None:
        super().__init__(message)
        self.evidence = evidence


class DrawingCopyGuard:
    """Create and account for one disposable source-derived drawing copy."""

    def __init__(
        self,
        *,
        run_id: str,
        source_path: Path,
        copy_path: Path,
        source_sha256_before: str,
        copy_sha256_before: str,
        temp_root: Path,
        run_directory: Path,
        marker_token: str,
        creation_key: object,
    ) -> None:
        if creation_key is not _CREATION_KEY:
            raise TypeError("DrawingCopyGuard instances must be created with prepare()")
        self._run_id = run_id
        self._source_path = source_path
        self._copy_path = copy_path
        self._source_sha256_before = source_sha256_before
        self._copy_sha256_before = copy_sha256_before
        self._temp_root = temp_root
        self._run_directory = run_directory
        self._marker_token = marker_token
        self._active_full_name: str | None = None
        self._close_without_save_attempted = False
        self._preserve_reason: str | None = None

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
        marker_token = secrets.token_urlsafe(32)
        (run_directory / _MARKER_NAME).write_text(marker_token, encoding="utf-8")
        copy_path = run_directory / _COPY_NAME

        try:
            shutil.copy2(source, copy_path)
            resolved_copy = copy_path.resolve(strict=True)
            source_after = _maybe_sha256(source)
            copy_after = _maybe_sha256(resolved_copy)
        except OSError as error:
            evidence = _preparation_evidence(
                run_id=run_id,
                source_path=source,
                copy_path=copy_path,
                source_before=source_before,
                source_after=_maybe_sha256(source),
                copy_before=_maybe_sha256(copy_path),
                copy_after=_maybe_sha256(copy_path),
                reason=f"copy preparation failed: {error}",
            )
            raise DrawingCopyViolation("copy preparation failed", evidence) from error

        if source == resolved_copy:
            evidence = _preparation_evidence(
                run_id=run_id,
                source_path=source,
                copy_path=resolved_copy,
                source_before=source_before,
                source_after=source_after,
                copy_before=copy_after,
                copy_after=copy_after,
                reason="source and disposable copy must differ",
            )
            raise DrawingCopyViolation("source and disposable copy must differ", evidence)
        if source_after != source_before:
            evidence = _preparation_evidence(
                run_id=run_id,
                source_path=source,
                copy_path=resolved_copy,
                source_before=source_before,
                source_after=source_after,
                copy_before=copy_after,
                copy_after=copy_after,
                reason="source changed during preparation",
            )
            raise DrawingCopyViolation("source changed during preparation", evidence)
        if copy_after != source_before:
            evidence = _preparation_evidence(
                run_id=run_id,
                source_path=source,
                copy_path=resolved_copy,
                source_before=source_before,
                source_after=source_after,
                copy_before=copy_after,
                copy_after=copy_after,
                reason="initial copy hash does not match source",
            )
            raise DrawingCopyViolation("initial copy hash does not match source", evidence)
        return cls(
            run_id=run_id,
            source_path=source,
            copy_path=resolved_copy,
            source_sha256_before=source_before,
            copy_sha256_before=copy_after,
            temp_root=root,
            run_directory=run_directory,
            marker_token=marker_token,
            creation_key=_CREATION_KEY,
        )

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def copy_path(self) -> Path:
        return self._copy_path

    def assert_active_full_name(self, active_full_name: str) -> None:
        self._active_full_name = active_full_name
        active_path = _normalized_windows_path(active_full_name)
        if active_path == _normalized_windows_path(str(self._source_path)):
            self._raise_violation("active document is the source drawing")
        if active_path != _normalized_windows_path(str(self._copy_path)):
            self._raise_violation("active document does not match the disposable copy")

    def close_without_save(self, close_document: Callable[[bool], None]) -> None:
        self._close_without_save_attempted = True
        close_document(False)

    def finalize(self, *, preserve: bool, reason: str) -> DrawingCopyEvidence:
        source_after = _maybe_sha256(self._source_path)
        copy_after = _maybe_sha256(self._copy_path)
        if self._preserve_reason is not None:
            return self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason=self._preserve_reason,
                cleanup_succeeded=False,
            )
        if source_after != self._source_sha256_before:
            self._latch_preservation("source changed during guarded run")
            evidence = self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason=self._preserve_reason,
                cleanup_succeeded=False,
            )
            raise DrawingCopyViolation("source changed during guarded run", evidence)
        if preserve:
            if not reason.strip():
                raise ValueError("preserve reason must be non-empty")
            self._latch_preservation(reason)
            return self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason=self._preserve_reason,
                cleanup_succeeded=False,
            )
        if not self._owns_run_directory():
            self._latch_preservation("cleanup refused: guard ownership validation failed")
            evidence = self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=False,
                preserve_reason=self._preserve_reason,
                cleanup_succeeded=False,
            )
            raise DrawingCopyViolation(
                "cleanup refused: guard ownership validation failed", evidence
            )
        try:
            shutil.rmtree(self._run_directory)
        except OSError as error:
            preserved = self._owns_run_directory()
            self._latch_preservation(f"cleanup failed: {error}")
            evidence = self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=preserved,
                preserve_reason=self._preserve_reason,
                cleanup_succeeded=False,
            )
            raise DrawingCopyViolation(
                "cleanup failed; disposable copy preserved", evidence
            ) from error
        return self._evidence(
            source_after=source_after,
            copy_after=copy_after,
            preserved=False,
            preserve_reason=None,
            cleanup_succeeded=True,
        )

    def _owns_run_directory(self) -> bool:
        try:
            expected_directory = self._temp_root / f"{_RUN_PREFIX}{self._run_id}"
            expected_copy = expected_directory / _COPY_NAME
            marker = expected_directory / _MARKER_NAME
            return (
                str(uuid.UUID(self._run_id)) == self._run_id
                and self._run_directory == expected_directory
                and self._run_directory.parent == self._temp_root
                and self._run_directory.is_dir()
                and self._run_directory.resolve(strict=True) == self._run_directory
                and self._copy_path == expected_copy
                and expected_copy.is_file()
                and expected_copy.resolve(strict=True) == expected_copy
                and self._source_path.resolve(strict=True) != expected_copy.resolve(strict=True)
                and marker.is_file()
                and marker.read_text(encoding="utf-8") == self._marker_token
            )
        except (OSError, ValueError):
            return False

    def _latch_preservation(self, reason: str) -> None:
        if self._preserve_reason is None:
            self._preserve_reason = reason

    def _raise_violation(self, message: str) -> None:
        self._latch_preservation(message)
        evidence = self._evidence(
            source_after=_maybe_sha256(self._source_path),
            copy_after=_maybe_sha256(self._copy_path),
            preserved=True,
            preserve_reason=self._preserve_reason,
            cleanup_succeeded=False,
        )
        raise DrawingCopyViolation(message, evidence)

    def _evidence(
        self,
        *,
        source_after: str | None,
        copy_after: str | None,
        preserved: bool,
        preserve_reason: str | None,
        cleanup_succeeded: bool,
    ) -> DrawingCopyEvidence:
        return DrawingCopyEvidence(
            run_id=self._run_id,
            source_path=str(self._source_path),
            copy_path=str(self._copy_path),
            source_sha256_before=self._source_sha256_before,
            source_sha256_after=source_after,
            copy_sha256_before=self._copy_sha256_before,
            copy_sha256_after=copy_after,
            active_full_name=self._active_full_name,
            close_without_save_attempted=self._close_without_save_attempted,
            preserved=preserved,
            preserve_reason=preserve_reason,
            cleanup_succeeded=cleanup_succeeded,
        )


def _preparation_evidence(
    *,
    run_id: str,
    source_path: Path,
    copy_path: Path,
    source_before: str,
    source_after: str | None,
    copy_before: str | None,
    copy_after: str | None,
    reason: str,
) -> DrawingCopyEvidence:
    return DrawingCopyEvidence(
        run_id=run_id,
        source_path=str(source_path),
        copy_path=str(copy_path),
        source_sha256_before=source_before,
        source_sha256_after=source_after,
        copy_sha256_before=copy_before or "",
        copy_sha256_after=copy_after,
        active_full_name=None,
        close_without_save_attempted=False,
        preserved=True,
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
