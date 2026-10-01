"""COM-free disposable drawing-copy guard for real AutoCAD test policies.

The default temporary directory is the real runner's per-user namespace.  A
``temp_root`` is a controlled test/infrastructure input and must not be writable
by an untrusted principal.  A hostile same-user writer is not a supported caller;
Task16's Windows lease/ACL verification is the real-run gate for that boundary.
"""

from __future__ import annotations

import hashlib
import ntpath
import os
import secrets
import shutil
import stat
import tempfile
import uuid
from collections.abc import Callable
from contextlib import ExitStack
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


class _FileIdentity:
    """Pin an original file until ownership accounting ends; writes remain allowed."""

    def __init__(self, descriptor: int) -> None:
        self.descriptor = descriptor

    def close(self) -> None:
        if self.descriptor != -1:
            descriptor, self.descriptor = self.descriptor, -1
            os.close(descriptor)

    def __del__(self) -> None:
        self.close()


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
    source_identity: _FileIdentity
    marker_identity: _FileIdentity
    copy_identity: _FileIdentity


class _CleanupRefusedError(Exception):
    """A pre-unlink identity check failed without deleting the target."""


class _CopyTransferError(OSError):
    """A transfer failed after an exclusively created destination was identified."""

    def __init__(self, copy_identity: _FileIdentity) -> None:
        super().__init__("copy transfer failed")
        self.copy_identity = copy_identity


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
        "_ownership",
        "_preservation_existed",
        "_preserve_reason",
    )

    def __init__(self, *, ownership: _Ownership, creation_key: object) -> None:
        if creation_key is not _CREATION_KEY:
            raise TypeError("DrawingCopyGuard instances must be created with prepare()")
        object.__setattr__(self, "_ownership", ownership)
        self._active_full_name: str | None = None
        self._close_without_save_attempted = False
        self._preserve_reason: str | None = None
        self._preservation_existed: bool | None = None

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_ownership" and hasattr(self, "_ownership"):
            raise AttributeError("DrawingCopyGuard ownership cannot be reassigned")
        object.__setattr__(self, name, value)

    @classmethod
    def prepare(  # noqa: C901
        cls,
        source_path: Path,
        *,
        temp_root: Path | None = None,
        create_run_directory: Callable[[Path], None] | None = None,
    ) -> Self:
        with ExitStack() as pins:
            source = Path(source_path).resolve()
            if source.suffix.lower() != ".dwg" or not _is_regular_file(source):
                raise ValueError("source_path must be a regular .dwg file")
            root = Path(tempfile.gettempdir()) if temp_root is None else Path(temp_root)
            run_id = str(uuid.uuid4())
            run_directory = root / f"{_RUN_PREFIX}{run_id}"
            copy_path = run_directory / _COPY_NAME
            try:
                source_before, source_identity = _sha256_and_identity_regular_file(source)
                pins.callback(source_identity.close)
            except OSError as error:
                raise _preparation_violation(
                    run_id, source, copy_path, "", None, "source preparation failed"
                ) from error
            try:
                root.mkdir(parents=True, exist_ok=True)
                root = root.resolve()
                run_directory = root / f"{_RUN_PREFIX}{run_id}"
                copy_path = run_directory / _COPY_NAME
                if create_run_directory is None:
                    os.mkdir(run_directory, mode=0o700)
                    os.chmod(run_directory, 0o700)
                else:
                    create_run_directory(run_directory)
                marker_path = run_directory / _MARKER_NAME
                marker_token = secrets.token_urlsafe(32)
                marker_identity = _write_private_token(marker_path, marker_token)
                pins.callback(marker_identity.close)
            except (OSError, UnicodeError, ValueError) as error:
                raise _preparation_violation(
                    run_id,
                    source,
                    copy_path,
                    source_before,
                    _maybe_sha256_regular_file(source),
                    "guard setup failed",
                ) from error
            copy_identity: _FileIdentity | None = None
            try:
                copy_identity = _copy_source_to_new_file(source, copy_path)
                pins.callback(copy_identity.close)
                source_after = _maybe_sha256_regular_file(source)
                copy_after = _maybe_sha256_regular_file(copy_path)
                if not _same_private_regular_file(copy_path, copy_identity):
                    raise _CleanupRefusedError("copy changed during preparation")
                if source == copy_path.resolve(strict=True):
                    raise _CleanupRefusedError("source and disposable copy must differ")
                if not _same_regular_file(source, source_identity):
                    raise _CleanupRefusedError("source changed during preparation")
                if not _same_private_regular_file(marker_path, marker_identity):
                    raise _CleanupRefusedError("marker changed during preparation")
                if source_after != source_before:
                    raise _CleanupRefusedError("source changed during preparation")
                if copy_after != source_before:
                    raise _CleanupRefusedError("initial copy hash does not match source")
            except _CleanupRefusedError as error:
                raise _preparation_violation(
                    run_id,
                    source,
                    copy_path,
                    source_before,
                    _maybe_sha256_regular_file(source),
                    str(error),
                    copy_identity=copy_identity,
                ) from error
            except _CopyTransferError as error:
                pins.callback(error.copy_identity.close)
                raise _preparation_violation(
                    run_id,
                    source,
                    copy_path,
                    source_before,
                    _maybe_sha256_regular_file(source),
                    "copy preparation failed",
                    copy_identity=error.copy_identity,
                ) from error
            except (OSError, UnicodeError, ValueError) as error:
                raise _preparation_violation(
                    run_id,
                    source,
                    copy_path,
                    source_before,
                    _maybe_sha256_regular_file(source),
                    "copy preparation failed",
                    copy_identity=copy_identity,
                ) from error
            pins.pop_all()
            return cls(
                ownership=_Ownership(
                    run_id=run_id,
                    source_path=source,
                    source_sha256_before=source_before,
                    copy_sha256_before=copy_after,
                    temp_root=root,
                    run_directory=run_directory,
                    copy_path=copy_path,
                    marker_token=marker_token,
                    source_identity=source_identity,
                    marker_identity=marker_identity,
                    copy_identity=copy_identity,
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
        try:
            active_path = _normalized_windows_path(active_full_name)
            source_path = _normalized_windows_path(str(self.source_path))
            copy_path = _normalized_windows_path(str(self.copy_path))
        except (OSError, ValueError, RuntimeError) as error:
            self._latch_preservation("active document path is invalid")
            evidence = self._evidence(
                _maybe_sha256_regular_file(self.source_path),
                _maybe_sha256_regular_file(self.copy_path),
                cleanup_succeeded=False,
            )
            raise DrawingCopyViolation("active document path is invalid", evidence) from error
        if active_path == source_path:
            self._raise_violation("active document is the source drawing")
        if active_path != copy_path:
            self._raise_violation("active document does not match the disposable copy")

    def close_without_save(self, close_document: Callable[[bool], None]) -> None:
        self._close_without_save_attempted = True
        close_document(False)

    def finalize(self, *, preserve: bool, reason: str) -> DrawingCopyEvidence:  # noqa: C901
        source_after = _maybe_sha256_regular_file(self.source_path)
        copy_after = _maybe_sha256_regular_file(self.copy_path)
        if self._preserve_reason is not None:
            return self._evidence(source_after, copy_after, cleanup_succeeded=False)
        if source_after != self._ownership.source_sha256_before or not _same_regular_file(
            self.source_path, self._ownership.source_identity
        ):
            self._latch_preservation("source changed during guarded run")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation("source changed during guarded run", evidence)
        if preserve:
            if not reason.strip():
                raise ValueError("preserve reason must be non-empty")
            self._latch_preservation(reason)
            return self._evidence(source_after, copy_after, cleanup_succeeded=False)
        if not self._valid_owned_run():
            self._latch_preservation("cleanup refused: guard ownership validation failed")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation(
                "cleanup refused: guard ownership validation failed", evidence
            )
        try:
            unexpected_contents = self._unexpected_run_contents()
        except (OSError, UnicodeError, ValueError) as error:
            self._latch_preservation(f"cleanup refused: unable to inspect run directory: {error}")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation(
                "cleanup refused: unable to inspect run directory", evidence
            ) from error
        if unexpected_contents:
            self._latch_preservation("cleanup refused: run directory contains unexpected contents")
            evidence = self._evidence(source_after, copy_after, cleanup_succeeded=False)
            raise DrawingCopyViolation("cleanup refused: unexpected run contents", evidence)
        try:
            if not _same_private_regular_file(self.copy_path, self._ownership.copy_identity):
                raise _CleanupRefusedError("copy changed immediately before cleanup")
            self.copy_path.unlink()
            self._ownership.copy_identity.close()
            if not _same_private_regular_file(self._marker_path(), self._ownership.marker_identity):
                raise _CleanupRefusedError("marker changed immediately before cleanup")
            self._marker_path().unlink()
            self._ownership.marker_identity.close()
            self._ownership.run_directory.rmdir()
        except _CleanupRefusedError as error:
            self._latch_preservation(f"cleanup refused: {error}")
            evidence = self._evidence(
                source_after, _maybe_sha256_regular_file(self.copy_path), cleanup_succeeded=False
            )
            raise DrawingCopyViolation("cleanup refused: identity changed", evidence) from error
        except (OSError, UnicodeError, ValueError) as error:
            self._latch_preservation(f"cleanup failed: {error}")
            evidence = self._evidence(
                source_after, _maybe_sha256_regular_file(self.copy_path), cleanup_succeeded=False
            )
            raise DrawingCopyViolation(self._cleanup_failure_message(), evidence) from error
        self._ownership.source_identity.close()
        return self._evidence(source_after, copy_after, cleanup_succeeded=True)

    def _marker_path(self) -> Path:
        return self._ownership.run_directory / _MARKER_NAME

    def _valid_owned_run(self) -> bool:
        try:
            directory = self._ownership.run_directory
            return (
                directory.parent == self._ownership.temp_root
                and directory.name == f"{_RUN_PREFIX}{self._ownership.run_id}"
                and _is_private_directory(directory)
                and self.source_path.resolve(strict=True) != self.copy_path.resolve(strict=True)
                and _same_private_regular_file(self.copy_path, self._ownership.copy_identity)
                and _same_private_regular_file(self._marker_path(), self._ownership.marker_identity)
                and _read_private_token(self._marker_path()) == self._ownership.marker_token
            )
        except (OSError, UnicodeError, ValueError):
            return False

    def _unexpected_run_contents(self) -> bool:
        return {path.name for path in self._ownership.run_directory.iterdir()} != {
            _COPY_NAME,
            _MARKER_NAME,
        }

    def _latch_preservation(self, reason: str) -> None:
        if self._preserve_reason is None:
            self._preserve_reason = reason
            self._preservation_existed = self._owned_copy_exists()

    def _owned_copy_exists(self) -> bool:
        return _same_private_regular_file(self.copy_path, self._ownership.copy_identity)

    def _is_preserved(self) -> bool:
        if self._preservation_existed is None:
            return self._owned_copy_exists()
        return self._preservation_existed and self._owned_copy_exists()

    def _cleanup_failure_message(self) -> str:
        if self._is_preserved():
            return "cleanup failed; disposable copy preserved"
        return "cleanup failed; disposable copy unavailable"

    def _raise_violation(self, message: str) -> None:
        self._latch_preservation(message)
        evidence = self._evidence(
            _maybe_sha256_regular_file(self.source_path),
            _maybe_sha256_regular_file(self.copy_path),
            cleanup_succeeded=False,
        )
        raise DrawingCopyViolation(message, evidence)

    def _evidence(
        self, source_after: str | None, copy_after: str | None, *, cleanup_succeeded: bool
    ) -> DrawingCopyEvidence:
        return DrawingCopyEvidence(
            run_id=self._ownership.run_id,
            source_path=str(self.source_path),
            copy_path=str(self.copy_path),
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


def _preparation_violation(
    run_id: str,
    source_path: Path,
    copy_path: Path,
    source_before: str,
    source_after: str | None,
    reason: str,
    copy_identity: _FileIdentity | None = None,
) -> DrawingCopyViolation:
    return DrawingCopyViolation(
        reason,
        _preparation_evidence(
            run_id, source_path, copy_path, source_before, source_after, reason, copy_identity
        ),
    )


def _preparation_evidence(
    run_id: str,
    source_path: Path,
    copy_path: Path,
    source_before: str,
    source_after: str | None,
    reason: str,
    copy_identity: _FileIdentity | None = None,
) -> DrawingCopyEvidence:
    copy_hash = _maybe_sha256_regular_file(copy_path)
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
        preserved=(
            copy_identity is not None and _same_private_regular_file(copy_path, copy_identity)
        ),
        preserve_reason=reason,
        cleanup_succeeded=False,
    )


def _copy_source_to_new_file(source_path: Path, destination: Path) -> _FileIdentity:
    """Copy through exclusively created, no-follow descriptors; never overwrite a destination."""
    source_fd = os.open(source_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise OSError("source is not a regular file")
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except BaseException:
        os.close(source_fd)
        raise
    try:
        destination_stat = os.fstat(destination_fd)
        if not stat.S_ISREG(destination_stat.st_mode) or destination_stat.st_nlink != 1:
            raise OSError("destination is not a private regular file")
        identity = _pin_file(destination, destination_fd)
        try:
            with os.fdopen(source_fd, "rb", closefd=False) as source, os.fdopen(
                destination_fd, "wb", closefd=False
            ) as destination_file:
                shutil.copyfileobj(source, destination_file)
        except Exception as error:
            raise _CopyTransferError(identity) from error
        return identity
    finally:
        os.close(source_fd)
        os.close(destination_fd)


def _write_private_token(path: Path, token: str) -> _FileIdentity:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
            raise OSError("marker is not a private regular file")
        os.write(descriptor, token.encode("utf-8"))
        return _pin_file(path, descriptor)
    finally:
        os.close(descriptor)


def _read_private_token(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
            raise OSError("marker is not a private regular file")
        return os.read(descriptor, 4096).decode("utf-8")
    finally:
        os.close(descriptor)


def _pin_file(path: Path, descriptor: int) -> _FileIdentity:
    if os.name != "nt":
        return _FileIdentity(os.dup(descriptor))
    # Retain identity metadata while allowing writers and deletion.
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    handle = create_file(str(path), 0, 1 | 2 | 4, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        pinned_descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    except BaseException:
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        close_handle(handle)
        raise
    return _FileIdentity(pinned_descriptor)


def _same_private_regular_file(path: Path, identity: _FileIdentity) -> bool:
    return _same_regular_file(path, identity, private=True)


def _same_regular_file(path: Path, identity: _FileIdentity, *, private: bool = False) -> bool:
    try:
        original = os.fstat(identity.descriptor)
        current = path.lstat()
        return (
            stat.S_ISREG(current.st_mode)
            and (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino)
            and original.st_nlink > 0
            and (not private or current.st_nlink == original.st_nlink == 1)
        )
    except OSError:
        return False


def _is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _is_private_directory(path: Path) -> bool:
    try:
        directory_stat = path.lstat()
        if os.name == "nt":
            reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            attributes = getattr(directory_stat, "st_file_attributes", 0)
            return stat.S_ISDIR(directory_stat.st_mode) and not attributes & reparse_point
        owner_matches = not hasattr(os, "geteuid") or directory_stat.st_uid == os.geteuid()
        return (
            stat.S_ISDIR(directory_stat.st_mode)
            and stat.S_IMODE(directory_stat.st_mode) & 0o077 == 0
            and owner_matches
        )
    except OSError:
        return False


def _sha256_regular_file(path: Path) -> str:
    digest, identity = _sha256_and_identity_regular_file(path)
    identity.close()
    return digest


def _sha256_and_identity_regular_file(path: Path) -> tuple[str, _FileIdentity]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError("path is not a regular file")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        return digest.hexdigest(), _pin_file(path, descriptor)
    finally:
        os.close(descriptor)


def _maybe_sha256_regular_file(path: Path) -> str | None:
    try:
        return _sha256_regular_file(path)
    except OSError:
        return None


def _normalized_windows_path(path: str) -> str:
    if "\x00" in path:
        raise ValueError("document path contains NUL")
    candidate = Path(path)
    try:
        normalized = candidate.resolve(strict=True)
    except OSError:
        normalized = candidate
    return ntpath.normcase(ntpath.normpath(str(normalized).replace("/", "\\")))
