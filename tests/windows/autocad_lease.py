"""Exclusive, Windows-only ownership for real AutoCAD verification controllers.

This module deliberately has no AutoCAD/COM dependency.  It is test
infrastructure: callers first derive a key from local Windows facts, then hold
one controller lease while they attach to an already-running AutoCAD instance.

Windows path resolution necessarily has a residual pathname TOCTOU window.
Every existing component is reparse-checked and ACL-verified, and any failed
check fails closed; this is a Windows-ACL-gated controller boundary, never a
caller-selectable namespace or concurrency override.
"""

from __future__ import annotations

import ctypes
import hashlib
import importlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Literal, Self

_KEY_PATTERN = re.compile(r"[0-9a-f]{64}")
_SYSTEM_SID = "S-1-5-18"
_METADATA_NAME = "owner.json"
_LOCK_NAME = "owner.lock"
_SID_PATTERN = re.compile(r"S-\d+(?:-\d+)+")
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_UTC_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z")


class _FileTime(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


class _Guid(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    ]


_FOLDERID_LOCAL_APP_DATA = _Guid(
    0xF1B32785,
    0x6FBA,
    0x4FCF,
    (ctypes.c_ubyte * 8)(0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91),
)


class AutoCADLeaseError(RuntimeError):
    """A real-AutoCAD controller lease could not be safely established."""


class AutoCADLeaseUnavailableError(AutoCADLeaseError):
    """The required local Windows facilities are unavailable."""


class AutoCADLeaseContendedError(AutoCADLeaseError):
    """Another controller may own the same protected lease."""

    def __init__(self, message: str, owner: LeaseOwner | None = None) -> None:
        super().__init__(message)
        self.owner = owner


@dataclass(frozen=True)
class LeaseOwner:
    lease_key: str
    pid: int
    process_created_at_100ns: int
    user_sid: str
    computer_name: str
    windows_session_id: int
    acquired_at_utc: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class LeaseEvidence:
    owner: LeaseOwner
    metadata_path: str
    acquired_at_utc: str
    released_at_utc: str | None
    stale_owner_recovered: LeaseOwner | None


@dataclass(frozen=True)
class _TrustedLeaseFacts:
    machine_identity: str
    user_sid: str
    windows_session_id: int
    normalized_installation_path: str
    file_identity: str
    version_build: str


@dataclass(frozen=True)
class _OwnerBindings:
    user_sid: str
    computer_name: str
    windows_session_id: int


def build_autocad_lease_key(*, installation_path: Path) -> str:
    """Return the non-overridable key for this real local AutoCAD installation."""
    _require_windows()
    facts = _trusted_key_facts(installation_path)
    material = json.dumps(asdict(facts), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def assert_current_user_system_only_acl(path: Path) -> None:
    """Fail unless *path* is protected for precisely the current user and SYSTEM.

    Task 17 uses this narrow helper before it cleans a drawing-guard run
    directory.  It intentionally verifies an existing path; it never relaxes
    or repairs a caller-owned path.
    """
    _require_windows()
    candidate = Path(path)
    if not candidate.exists():
        raise AutoCADLeaseError("protected Windows path does not exist")
    _assert_not_reparse(candidate)
    _verify_lease_acl(candidate, _current_user_sid())


def create_guard_run_temp_root() -> Path:
    """Create one exclusive inheritable protected root for DrawingCopyGuard.prepare()."""
    _require_windows()
    user_sid = _current_user_sid()
    root = _windows_temp_directory()
    _assert_not_reparse(root)
    for _ in range(128):
        candidate = root / f"autocad-mcp-guard-{os.urandom(16).hex()}"
        if _create_guard_temp_root(candidate, user_sid):
            return candidate
    raise AutoCADLeaseError("unable to create an exclusive protected temporary directory")


def assert_guard_run_current_user_system_acl(path: Path) -> None:
    """Verify a guard root or its inherited child without repairing any path."""
    _require_windows()
    candidate = Path(path)
    if not candidate.exists():
        raise AutoCADLeaseError("protected Windows guard path does not exist")
    _assert_not_reparse(candidate)
    _verify_guard_run_acl(candidate, _current_user_sid())


def create_guard_run_directory(path: Path) -> None:
    """Exclusively create a guard child with current-user ownership and private ACLs."""
    _require_windows()
    if not _create_guard_temp_root(Path(path), _current_user_sid()):
        raise AutoCADLeaseError("Windows guard run directory already exists")


class AutoCADLease:
    """A non-blocking OS-file-lock lease with auditable owner metadata."""

    __slots__ = (
        "_acquired_at_utc",
        "_evidence",
        "_lock_file",
        "_lock_path",
        "_metadata_path",
        "_owned",
        "_owner",
        "_stale_owner_recovered",
    )

    def __init__(
        self,
        *,
        owner: LeaseOwner,
        lock_file: BinaryIO,
        lock_path: Path,
        metadata_path: Path,
        stale_owner_recovered: LeaseOwner | None,
    ) -> None:
        self._owner = owner
        self._lock_file = lock_file
        self._lock_path = lock_path
        self._metadata_path = metadata_path
        self._stale_owner_recovered = stale_owner_recovered
        self._acquired_at_utc = owner.acquired_at_utc
        self._evidence = LeaseEvidence(
            owner=owner,
            metadata_path=str(metadata_path),
            acquired_at_utc=owner.acquired_at_utc,
            released_at_utc=None,
            stale_owner_recovered=stale_owner_recovered,
        )
        self._owned = True

    @classmethod
    def acquire(cls, lease_key: str) -> Self:
        """Acquire *lease_key* or fail closed without waiting for another runner."""
        _require_windows()
        if not _KEY_PATTERN.fullmatch(lease_key):
            raise AutoCADLeaseError("lease key must be a canonical trusted-fact digest")

        user_sid = _current_user_sid()
        bindings = _OwnerBindings(user_sid, _computer_name(), _current_windows_session_id())
        root = _lease_root()
        _create_private_directory(root.parent, user_sid)
        _create_private_directory(root, user_sid)
        lease_dir = root / lease_key
        directory_was_new = _create_private_directory(lease_dir, user_sid)
        lock_path = lease_dir / _LOCK_NAME
        _create_private_file(lock_path, user_sid)
        metadata_path = lease_dir / _METADATA_NAME
        metadata_existed = metadata_path.exists()
        if metadata_existed:
            _assert_not_reparse(metadata_path)

        lock_file = lock_path.open("a+b")
        try:
            _lock_nonblocking(lock_file)
        except ImportError as error:
            lock_file.close()
            raise AutoCADLeaseUnavailableError(
                "Windows non-blocking file locking is unavailable"
            ) from error
        except OSError as error:
            lock_file.close()
            owner = _read_contended_owner(metadata_path, bindings)
            raise AutoCADLeaseContendedError(
                "AutoCAD verification lease is already held", owner
            ) from error

        try:
            stale_owner = _recoverable_prior_owner(
                metadata_path,
                bindings,
                expected_lease_key=lease_key,
                missing_metadata_allowed=directory_was_new and not metadata_existed,
            )
            owner = _current_owner(lease_key, bindings)
            _write_metadata(metadata_path, owner, None, user_sid)
            return cls(
                owner=owner,
                lock_file=lock_file,
                lock_path=lock_path,
                metadata_path=metadata_path,
                stale_owner_recovered=stale_owner,
            )
        except BaseException:
            _unlock_and_close(lock_file)
            raise

    @property
    def evidence(self) -> LeaseEvidence:
        """The latest acquisition/release evidence for this lease."""
        return self._evidence

    def assert_owned(self) -> None:
        """Fail closed unless this process still owns the protected live lease."""
        _require_windows()
        if not self._owned:
            raise AutoCADLeaseError("AutoCAD verification lease is not owned")
        assert_current_user_system_only_acl(self._metadata_path)
        bindings = _OwnerBindings(
            _current_user_sid(), _computer_name(), _current_windows_session_id()
        )
        if bindings != _OwnerBindings(
            self._owner.user_sid, self._owner.computer_name, self._owner.windows_session_id
        ):
            raise AutoCADLeaseError("AutoCAD verification lease controller identity changed")
        owner, released_at = _read_metadata(
            self._metadata_path,
            expected_lease_key=self._owner.lease_key,
            expected_bindings=bindings,
        )
        if released_at is not None or owner != self._owner:
            raise AutoCADLeaseError("AutoCAD verification lease ownership cannot be proven")

    def release(self) -> LeaseEvidence:
        """Record release evidence before relinquishing the operating-system lock."""
        _require_windows()
        if not self._owned:
            raise AutoCADLeaseError("cannot release an AutoCAD verification lease not owned")
        try:
            self.assert_owned()
            released_at = _utc_now()
            _write_metadata(self._metadata_path, self._owner, released_at, self._owner.user_sid)
            self._evidence = LeaseEvidence(
                owner=self._owner,
                metadata_path=str(self._metadata_path),
                acquired_at_utc=self._acquired_at_utc,
                released_at_utc=released_at,
                stale_owner_recovered=self._stale_owner_recovered,
            )
        except BaseException:
            self._owned = False
            try:
                _unlock_and_close(self._lock_file)
            except BaseException:  # noqa: S110 - preserve the original release failure
                pass
            raise
        self._owned = False
        _unlock_and_close(self._lock_file)
        return self._evidence

    def __enter__(self) -> Self:
        try:
            self.assert_owned()
        except BaseException:
            if self._owned:
                self._owned = False
                try:
                    _unlock_and_close(self._lock_file)
                except BaseException:  # noqa: S110 - retain the ownership assertion failure
                    pass
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is not None:
            try:
                self.release()
            except BaseException:  # noqa: S110 - preserve the context-body failure
                pass
            return None
        self.release()
        return None


def _require_windows() -> None:
    if sys.platform != "win32":
        raise AutoCADLeaseUnavailableError("AutoCAD verification leases require Windows")


def _lease_root() -> Path:
    return _known_local_app_data() / "AutoCADMCP" / "verification-leases"


def _known_local_app_data() -> Path:
    shell32 = _shell32()
    result = ctypes.c_wchar_p()
    status = shell32.SHGetKnownFolderPath(
        ctypes.byref(_FOLDERID_LOCAL_APP_DATA), 0, None, ctypes.byref(result)
    )
    if status != 0 or not result.value:
        if result.value:
            _ole32().CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))
        raise AutoCADLeaseUnavailableError("trusted Windows local-app-data path is unavailable")
    try:
        return Path(result.value)
    finally:
        _ole32().CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))


def _windows_temp_directory() -> Path:
    kernel32 = _kernel32()
    size = 32768
    while size <= 262144:
        buffer = ctypes.create_unicode_buffer(size)
        length = kernel32.GetTempPathW(size, buffer)
        if not length:
            break
        if length < size:
            return Path(buffer.value)
        size = int(length) + 1
    raise AutoCADLeaseUnavailableError("Windows temporary directory is unavailable")


def _trusted_key_facts(installation_path: Path) -> _TrustedLeaseFacts:
    executable = Path(installation_path).resolve(strict=True)
    if executable.name.casefold() != "acad.exe" or not executable.is_file():
        raise AutoCADLeaseError("installation_path must identify a regular acad.exe file")
    file_stat = executable.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise AutoCADLeaseError("installation_path must identify a regular acad.exe file")
    return _TrustedLeaseFacts(
        machine_identity=_machine_identity(),
        user_sid=_current_user_sid(),
        windows_session_id=_current_windows_session_id(),
        normalized_installation_path=os.path.normcase(str(executable)),
        file_identity=(
            f"device={file_stat.st_dev};inode={file_stat.st_ino};"
            f"size={file_stat.st_size};mtime_ns={file_stat.st_mtime_ns}"
        ),
        version_build=_verified_file_version(executable),
    )


def _machine_identity() -> str:
    try:
        winreg = importlib.import_module("winreg")
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
    except (ImportError, OSError, AttributeError) as error:
        raise AutoCADLeaseUnavailableError(
            "trusted Windows machine identity is unavailable"
        ) from error
    if not isinstance(value, str) or not value.strip():
        raise AutoCADLeaseError("trusted Windows machine identity is invalid")
    return value.strip()


def _current_user_sid() -> str:
    try:
        win32api = importlib.import_module("win32api")
        win32con = importlib.import_module("win32con")
        win32security = importlib.import_module("win32security")
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            value = win32security.ConvertSidToStringSid(user_sid)
        finally:
            token.Close()
    except (ImportError, OSError, AttributeError) as error:
        raise AutoCADLeaseUnavailableError("current Windows user SID is unavailable") from error
    if not isinstance(value, str) or not value.startswith("S-"):
        raise AutoCADLeaseError("current Windows user SID is invalid")
    return value


def _current_windows_session_id() -> int:
    session_id = ctypes.c_uint32()
    kernel32 = _kernel32()
    if not kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session_id)):
        raise AutoCADLeaseUnavailableError("current Windows interactive session is unavailable")
    return int(session_id.value)


def _computer_name() -> str:
    kernel32 = _kernel32()
    size = ctypes.c_uint32(256)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not kernel32.GetComputerNameW(buffer, ctypes.byref(size)):
        raise AutoCADLeaseUnavailableError("current Windows computer name is unavailable")
    if not buffer.value:
        raise AutoCADLeaseError("current Windows computer name is invalid")
    return buffer.value


def _verified_file_version(executable: Path) -> str:
    version = _version_api()
    handle = ctypes.c_uint32()
    size = version.GetFileVersionInfoSizeW(str(executable), ctypes.byref(handle))
    if not size:
        raise AutoCADLeaseError("verified acad.exe version metadata is unavailable")
    buffer = ctypes.create_string_buffer(size)
    buffer_pointer = ctypes.cast(buffer, ctypes.c_void_p)
    if not version.GetFileVersionInfoW(str(executable), 0, size, buffer_pointer):
        raise AutoCADLeaseError("verified acad.exe version metadata is unavailable")

    class _FixedFileInfo(ctypes.Structure):
        _fields_ = [
            ("signature", ctypes.c_uint32),
            ("struct_version", ctypes.c_uint32),
            ("file_version_ms", ctypes.c_uint32),
            ("file_version_ls", ctypes.c_uint32),
            ("product_version_ms", ctypes.c_uint32),
            ("product_version_ls", ctypes.c_uint32),
            ("file_flags_mask", ctypes.c_uint32),
            ("file_flags", ctypes.c_uint32),
            ("file_os", ctypes.c_uint32),
            ("file_type", ctypes.c_uint32),
            ("file_subtype", ctypes.c_uint32),
            ("file_date_ms", ctypes.c_uint32),
            ("file_date_ls", ctypes.c_uint32),
        ]

    value = ctypes.c_void_p()
    value_size = ctypes.c_uint32()
    if not version.VerQueryValueW(
        buffer_pointer, "\\", ctypes.byref(value), ctypes.byref(value_size)
    ):
        raise AutoCADLeaseError("verified acad.exe version metadata is unavailable")
    if value_size.value < ctypes.sizeof(_FixedFileInfo):
        raise AutoCADLeaseError("verified acad.exe version metadata is invalid")
    info = ctypes.cast(value, ctypes.POINTER(_FixedFileInfo)).contents
    if info.signature != 0xFEEF04BD:
        raise AutoCADLeaseError("verified acad.exe version metadata is invalid")
    return ".".join(
        str(component)
        for component in (
            info.file_version_ms >> 16,
            info.file_version_ms & 0xFFFF,
            info.file_version_ls >> 16,
            info.file_version_ls & 0xFFFF,
        )
    )


def _create_private_directory(path: Path, user_sid: str) -> bool:
    """Create a path exclusively, or verify a safe existing directory without repair."""
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        _assert_not_reparse(path)
        if not path.is_dir():
            raise AutoCADLeaseError("Windows lease directory is not a directory") from None
        _verify_lease_acl(path, user_sid)
        return False
    except OSError as error:
        raise AutoCADLeaseError("unable to create Windows lease directory") from error
    _assert_not_reparse(path)
    _set_private_acl(path, user_sid)
    _verify_lease_acl(path, user_sid)
    return True


def _create_private_file(path: Path, user_sid: str) -> bool:
    """Create a path exclusively, or verify a safe existing file without repair."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _assert_not_reparse(path)
        if not path.is_file():
            raise AutoCADLeaseError("Windows lease path is not a regular file") from None
        _verify_lease_acl(path, user_sid)
        return False
    except OSError as error:
        raise AutoCADLeaseError("unable to create Windows lease file") from error
    else:
        os.close(descriptor)
    _assert_not_reparse(path)
    _set_private_acl(path, user_sid)
    _verify_lease_acl(path, user_sid)
    return True


def _create_guard_temp_root(path: Path, user_sid: str) -> bool:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        return False
    except OSError as error:
        raise AutoCADLeaseError("unable to create Windows guard temporary root") from error
    _assert_not_reparse(path)
    _set_private_acl(path, user_sid, inheritable=True)
    _verify_guard_run_acl(path, user_sid)
    return True


def _assert_not_reparse(path: Path) -> None:
    try:
        details = path.lstat()
    except OSError as error:
        raise AutoCADLeaseError("unable to inspect Windows lease path") from error
    attributes = getattr(details, "st_file_attributes", 0)
    if stat.S_ISLNK(details.st_mode) or attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise AutoCADLeaseError("Windows lease path must not be a reparse point")


def _set_private_acl(path: Path, user_sid: str, *, inheritable: bool = False) -> None:
    try:
        ntsecuritycon = importlib.import_module("ntsecuritycon")
        security = importlib.import_module("win32security")
        ace_flags = 0
        if inheritable:
            ace_flags = security.OBJECT_INHERIT_ACE | security.CONTAINER_INHERIT_ACE
        dacl = security.ACL()
        dacl.AddAccessAllowedAceEx(
            security.ACL_REVISION,
            ace_flags,
            ntsecuritycon.FILE_ALL_ACCESS,
            security.ConvertStringSidToSid(user_sid),
        )
        dacl.AddAccessAllowedAceEx(
            security.ACL_REVISION,
            ace_flags,
            ntsecuritycon.FILE_ALL_ACCESS,
            security.ConvertStringSidToSid(_SYSTEM_SID),
        )
        descriptor = security.SECURITY_DESCRIPTOR()
        descriptor.SetSecurityDescriptorOwner(security.ConvertStringSidToSid(user_sid), False)
        descriptor.SetSecurityDescriptorDacl(True, dacl, False)
        security.SetFileSecurity(
            str(path),
            security.OWNER_SECURITY_INFORMATION
            | security.DACL_SECURITY_INFORMATION
            | security.PROTECTED_DACL_SECURITY_INFORMATION,
            descriptor,
        )
    except (ImportError, OSError, AttributeError) as error:
        raise AutoCADLeaseUnavailableError("Windows lease ACL cannot be established") from error


def _verify_lease_acl(  # noqa: C901 - explicit ACL fail-closed checks
    path: Path, user_sid: str
) -> None:
    try:
        ntsecuritycon = importlib.import_module("ntsecuritycon")
        security = importlib.import_module("win32security")
        descriptor = security.GetFileSecurity(
            str(path), security.DACL_SECURITY_INFORMATION | security.OWNER_SECURITY_INFORMATION
        )
        _require_current_owner(descriptor, security, user_sid)
        control, _ = descriptor.GetSecurityDescriptorControl()
        if not control & security.SE_DACL_PROTECTED:
            raise AutoCADLeaseError("Windows lease ACL is not protected")
        dacl = descriptor.GetSecurityDescriptorDacl()
        if dacl is None:
            raise AutoCADLeaseError("Windows lease ACL is absent")
        expected_sids = {user_sid, _SYSTEM_SID}
        seen_sids: set[str] = set()
        if dacl.GetAceCount() != len(expected_sids):
            raise AutoCADLeaseError("Windows lease ACL contains unexpected entries")
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            if ace[0][0] != security.ACCESS_ALLOWED_ACE_TYPE:
                raise AutoCADLeaseError("Windows lease ACL contains a non-allow entry")
            ace_flags = ace[0][1]
            if ace_flags & ntsecuritycon.INHERIT_ONLY_ACE or ace_flags != 0:
                raise AutoCADLeaseError("Windows lease ACL contains an ineffective inherited entry")
            if ace[1] != ntsecuritycon.FILE_ALL_ACCESS:
                raise AutoCADLeaseError("Windows lease ACL does not grant full controller access")
            sid = security.ConvertSidToStringSid(ace[2])
            if sid not in expected_sids or sid in seen_sids:
                raise AutoCADLeaseError("Windows lease ACL contains a foreign owner entry")
            seen_sids.add(sid)
    except AutoCADLeaseError:
        raise
    except (ImportError, OSError, AttributeError, IndexError, TypeError) as error:
        raise AutoCADLeaseUnavailableError("Windows lease ACL cannot be verified") from error
    if seen_sids != expected_sids:
        raise AutoCADLeaseError("Windows lease ACL is not current-user/SYSTEM-only")


def _verify_guard_run_acl(
    path: Path, user_sid: str
) -> None:  # noqa: C901 - explicit effective inherited-ACL checks
    try:
        ntsecuritycon = importlib.import_module("ntsecuritycon")
        security = importlib.import_module("win32security")
        descriptor = security.GetFileSecurity(
            str(path), security.DACL_SECURITY_INFORMATION | security.OWNER_SECURITY_INFORMATION
        )
        _require_current_owner(descriptor, security, user_sid)
        dacl = descriptor.GetSecurityDescriptorDacl()
        if dacl is None:
            raise AutoCADLeaseError("Windows guard ACL is absent")
        expected_sids = {user_sid, _SYSTEM_SID}
        seen_sids: set[str] = set()
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            if ace[0][0] != security.ACCESS_ALLOWED_ACE_TYPE:
                raise AutoCADLeaseError("Windows guard ACL contains a non-allow entry")
            if not _guard_ace_is_effective(
                ace[0][1], inherit_only_flag=security.INHERIT_ONLY_ACE
            ):
                raise AutoCADLeaseError("Windows guard ACL contains an ineffective inherited entry")
            if ace[1] != ntsecuritycon.FILE_ALL_ACCESS:
                raise AutoCADLeaseError("Windows guard ACL does not grant full controller access")
            sid = security.ConvertSidToStringSid(ace[2])
            if sid not in expected_sids or sid in seen_sids:
                raise AutoCADLeaseError("Windows guard ACL contains a foreign owner entry")
            seen_sids.add(sid)
    except AutoCADLeaseError:
        raise
    except (ImportError, OSError, AttributeError, IndexError, TypeError) as error:
        raise AutoCADLeaseUnavailableError("Windows guard ACL cannot be verified") from error
    if seen_sids != expected_sids:
        raise AutoCADLeaseError("Windows guard ACL is not current-user/SYSTEM-only")


def _require_current_owner(descriptor: object, security: object, user_sid: str) -> None:
    owner = descriptor.GetSecurityDescriptorOwner()  # type: ignore[attr-defined]
    if isinstance(owner, tuple):
        owner = owner[0]
    if security.ConvertSidToStringSid(owner) != user_sid:  # type: ignore[attr-defined]
        raise AutoCADLeaseError("Windows lease path owner is not the current user")


def _guard_ace_is_effective(ace_flags: int, *, inherit_only_flag: int) -> bool:
    return not bool(ace_flags & inherit_only_flag)


def _lock_nonblocking(lock_file: BinaryIO) -> None:
    msvcrt = importlib.import_module("msvcrt")
    lock_file.seek(0)
    if not lock_file.read(1):
        lock_file.seek(0)
        lock_file.write(b"\0")
        lock_file.flush()
    lock_file.seek(0)
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)


def _unlock_and_close(lock_file: BinaryIO) -> None:
    try:
        msvcrt = importlib.import_module("msvcrt")
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    except (ImportError, OSError):
        pass
    finally:
        lock_file.close()


def _read_contended_owner(
    metadata_path: Path, bindings: _OwnerBindings
) -> LeaseOwner | None:
    if not metadata_path.exists():
        return None
    try:
        _verify_lease_acl(metadata_path, bindings.user_sid)
        owner, _ = _read_metadata(
            metadata_path,
            expected_lease_key=metadata_path.parent.name,
            expected_bindings=bindings,
        )
        return owner
    except AutoCADLeaseError:
        return None


def _recoverable_prior_owner(
    metadata_path: Path,
    bindings: _OwnerBindings,
    *,
    expected_lease_key: str,
    missing_metadata_allowed: bool,
) -> LeaseOwner | None:
    if not metadata_path.exists():
        if missing_metadata_allowed:
            return None
        raise AutoCADLeaseError("lease metadata is unexpectedly missing")
    _verify_lease_acl(metadata_path, bindings.user_sid)
    prior_owner, released_at = _read_metadata(
        metadata_path, expected_lease_key=expected_lease_key, expected_bindings=bindings
    )
    if released_at is not None:
        return None
    liveness = _owner_liveness(prior_owner)
    if liveness == "dead":
        return prior_owner
    if liveness == "live":
        raise AutoCADLeaseContendedError(
            "a live AutoCAD verification lease owner cannot be stolen", prior_owner
        )
    raise AutoCADLeaseError("prior AutoCAD verification lease owner liveness is indeterminate")


def _read_metadata(  # noqa: C901 - explicit fail-closed owner shape validation
    metadata_path: Path, *, expected_lease_key: str, expected_bindings: _OwnerBindings
) -> tuple[LeaseOwner, str | None]:
    try:
        _assert_not_reparse(metadata_path)
        if (
            metadata_path.name != _METADATA_NAME
            or metadata_path.parent.name != expected_lease_key
            or not _KEY_PATTERN.fullmatch(expected_lease_key)
        ):
            raise ValueError("metadata location is invalid")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"owner", "released_at_utc"}:
            raise ValueError("unexpected metadata shape")
        owner_payload = payload["owner"]
        owner_keys = {
            "lease_key",
            "pid",
            "process_created_at_100ns",
            "user_sid",
            "computer_name",
            "windows_session_id",
            "acquired_at_utc",
            "command",
        }
        if not isinstance(owner_payload, dict) or set(owner_payload) != owner_keys:
            raise ValueError("owner is not an object")
        if owner_payload["lease_key"] != expected_lease_key or not _KEY_PATTERN.fullmatch(
            expected_lease_key
        ):
            raise ValueError("owner lease key is invalid")
        if not _positive_int(owner_payload["pid"]):
            raise ValueError("owner pid is invalid")
        if not _positive_int(owner_payload["process_created_at_100ns"]):
            raise ValueError("owner creation time is invalid")
        if not _valid_sid(owner_payload["user_sid"]):
            raise ValueError("owner SID is invalid")
        if not _valid_computer_name(owner_payload["computer_name"]):
            raise ValueError("owner computer name is invalid")
        if not _nonnegative_int(owner_payload["windows_session_id"]):
            raise ValueError("owner session is invalid")
        if (
            owner_payload["user_sid"] != expected_bindings.user_sid
            or owner_payload["computer_name"] != expected_bindings.computer_name
            or owner_payload["windows_session_id"] != expected_bindings.windows_session_id
        ):
            raise ValueError("owner is not from this controller identity")
        _parse_utc_timestamp(owner_payload["acquired_at_utc"])
        command = owner_payload["command"]
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("owner command is invalid")
        owner = LeaseOwner(
            lease_key=owner_payload["lease_key"],
            pid=owner_payload["pid"],
            process_created_at_100ns=owner_payload["process_created_at_100ns"],
            user_sid=owner_payload["user_sid"],
            computer_name=owner_payload["computer_name"],
            windows_session_id=owner_payload["windows_session_id"],
            acquired_at_utc=owner_payload["acquired_at_utc"],
            command=tuple(command),
        )
        released_at = payload["released_at_utc"]
        if released_at is not None:
            _parse_utc_timestamp(released_at)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise AutoCADLeaseError("lease metadata is corrupt") from error
    return owner, released_at


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _valid_sid(value: object) -> bool:
    return isinstance(value, str) and bool(_SID_PATTERN.fullmatch(value))


def _valid_computer_name(value: object) -> bool:
    return isinstance(value, str) and bool(value) and "\0" not in value and len(value) <= 255


def _parse_utc_timestamp(value: object) -> None:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError("timestamp is invalid")
    parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp is not UTC")


def _write_metadata(
    metadata_path: Path, owner: LeaseOwner, released_at_utc: str | None, user_sid: str
) -> None:
    _create_private_file(metadata_path, user_sid)
    payload = json.dumps(
        {"owner": asdict(owner), "released_at_utc": released_at_utc},
        sort_keys=True,
        separators=(",", ":"),
    )
    try:
        with metadata_path.open("w", encoding="utf-8", newline="\n") as metadata:
            metadata.write(payload)
            metadata.flush()
            os.fsync(metadata.fileno())
    except OSError as error:
        raise AutoCADLeaseError("unable to write protected lease metadata") from error
    _verify_lease_acl(metadata_path, user_sid)


def _current_owner(lease_key: str, bindings: _OwnerBindings) -> LeaseOwner:
    return LeaseOwner(
        lease_key=lease_key,
        pid=os.getpid(),
        process_created_at_100ns=_process_created_at_100ns(os.getpid()),
        user_sid=bindings.user_sid,
        computer_name=bindings.computer_name,
        windows_session_id=bindings.windows_session_id,
        acquired_at_utc=_utc_now(),
        command=tuple(sys.argv),
    )


def _process_created_at_100ns(pid: int) -> int:
    kernel32 = _kernel32()
    process = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not process:
        raise AutoCADLeaseUnavailableError("Windows process creation time is unavailable")
    try:
        created = _FileTime()
        exited = _FileTime()
        kernel = _FileTime()
        user = _FileTime()
        if not kernel32.GetProcessTimes(
            process,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            raise AutoCADLeaseUnavailableError("Windows process creation time is unavailable")
        return (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
    finally:
        kernel32.CloseHandle(process)


def _owner_liveness(owner: LeaseOwner) -> Literal["live", "dead", "indeterminate"]:
    kernel32 = _kernel32()
    process = kernel32.OpenProcess(0x1000, False, owner.pid)
    if not process:
        return "dead" if ctypes.get_last_error() == 87 else "indeterminate"
    try:
        created = _FileTime()
        exited = _FileTime()
        kernel = _FileTime()
        user = _FileTime()
        if not kernel32.GetProcessTimes(
            process,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return "indeterminate"
        observed = (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
        return "live" if observed == owner.process_created_at_100ns else "dead"
    finally:
        kernel32.CloseHandle(process)


def _kernel32() -> ctypes.WinDLL:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.ProcessIdToSessionId.argtypes = (ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))
    kernel32.ProcessIdToSessionId.restype = ctypes.c_int
    kernel32.GetComputerNameW.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32))
    kernel32.GetComputerNameW.restype = ctypes.c_int
    kernel32.GetTempPathW.argtypes = (ctypes.c_uint32, ctypes.c_wchar_p)
    kernel32.GetTempPathW.restype = ctypes.c_uint32
    kernel32.GetProcessTimes.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
    )
    kernel32.GetProcessTimes.restype = ctypes.c_int
    return kernel32


def _shell32() -> ctypes.WinDLL:
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = (
        ctypes.POINTER(_Guid),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    )
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    return shell32


def _ole32() -> ctypes.WinDLL:
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    ole32.CoTaskMemFree.restype = None
    return ole32


def _version_api() -> ctypes.WinDLL:
    version = ctypes.WinDLL("version", use_last_error=True)
    version.GetFileVersionInfoSizeW.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32))
    version.GetFileVersionInfoSizeW.restype = ctypes.c_uint32
    version.GetFileVersionInfoW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    version.GetFileVersionInfoW.restype = ctypes.c_int
    version.VerQueryValueW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_uint32),
    )
    version.VerQueryValueW.restype = ctypes.c_int
    return version


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
