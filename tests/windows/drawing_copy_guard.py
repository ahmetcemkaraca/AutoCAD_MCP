"""COM-free disposable drawing-copy guard for real AutoCAD test policies."""

from __future__ import annotations

import hashlib
import ntpath
import shutil
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True)
class DrawingCopyEvidence:
    run_id: str
    source_path: Path
    copy_path: Path
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
    ) -> None:
        self._run_id = run_id
        self._source_path = source_path
        self._copy_path = copy_path
        self._source_sha256_before = source_sha256_before
        self._copy_sha256_before = copy_sha256_before
        self._active_full_name: str | None = None
        self._close_without_save_attempted = False

    @classmethod
    def prepare(cls, source_path: Path, *, temp_root: Path | None = None) -> Self:
        source = Path(source_path).resolve()
        if source.suffix.lower() != ".dwg" or not source.is_file():
            raise ValueError("source_path must be a regular .dwg file")

        root = Path(tempfile.gettempdir()) if temp_root is None else Path(temp_root)
        root.mkdir(parents=True, exist_ok=True)
        run_id = str(uuid.uuid4())
        run_directory = root.resolve() / f"autocad-mcp-{run_id}"
        run_directory.mkdir()
        copy_path = run_directory / "drawing-copy.dwg"
        try:
            shutil.copy2(source, copy_path)
            copy_path = copy_path.resolve(strict=True)
            if source == copy_path:
                raise ValueError("source and disposable copy must differ")
            source_hash = _sha256(source)
            copy_hash = _sha256(copy_path)
            if source_hash != copy_hash:
                raise ValueError("source and disposable copy hashes must match")
        except BaseException:
            shutil.rmtree(run_directory, ignore_errors=True)
            raise
        return cls(
            run_id=run_id,
            source_path=source,
            copy_path=copy_path,
            source_sha256_before=source_hash,
            copy_sha256_before=copy_hash,
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
        if source_after != self._source_sha256_before:
            evidence = self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason="source changed during guarded run",
                cleanup_succeeded=False,
            )
            raise DrawingCopyViolation("source changed during guarded run", evidence)

        if preserve:
            if not reason.strip():
                raise ValueError("preserve reason must be non-empty")
            return self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason=reason,
                cleanup_succeeded=False,
            )

        try:
            shutil.rmtree(self._copy_path.parent)
        except OSError as error:
            evidence = self._evidence(
                source_after=source_after,
                copy_after=copy_after,
                preserved=True,
                preserve_reason=f"cleanup failed: {error}",
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

    def _raise_violation(self, message: str) -> None:
        evidence = self._evidence(
            source_after=_maybe_sha256(self._source_path),
            copy_after=_maybe_sha256(self._copy_path),
            preserved=True,
            preserve_reason=message,
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
            source_path=self._source_path,
            copy_path=self._copy_path,
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
    return ntpath.normcase(ntpath.normpath(path.replace("/", "\\")))
