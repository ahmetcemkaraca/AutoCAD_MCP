"""Windows-only authenticated local witness transport with delayed API binding."""

import ctypes
import importlib
import os
import secrets
import struct
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from autocad_mcp.adapter.native_revision import (
    MAX_RESPONSE_BYTES,
    NativeRevisionError,
    RevisionWitness,
    decode_response,
    encode_request,
)


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    created_filetime: int
    sid: str
    session_id: int


class _Bindings(Protocol):
    def current(self) -> ProcessIdentity: ...
    def window_process(self, hwnd: int) -> ProcessIdentity: ...
    def process(self, pid: int) -> ProcessIdentity: ...
    def open_pipe(self, name: str, deadline: float) -> object: ...
    def server_pid(self, handle: object) -> int: ...
    def write(self, handle: object, data: bytes) -> int: ...
    def read(self, handle: object, size: int) -> bytes: ...
    def pause(self, remaining: float) -> None: ...
    def close(self, handle: object) -> None: ...


def _remaining(deadline: float, clock: Callable[[], float]) -> float:
    remaining = deadline - clock()
    if remaining <= 0:
        raise NativeRevisionError("TIMEOUT")
    return remaining


class WindowsNativeRevisionSource:
    """Consume a trusted COM HWND; callers cannot choose a pipe name or peer PID."""

    def __init__(
        self, *, bindings: _Bindings | None = None, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._bindings = bindings
        self._clock = clock

    def witness(self, document_hwnd: int) -> RevisionWitness:
        if type(document_hwnd) is not int or not 1 <= document_hwnd <= 2**64 - 1:
            raise NativeRevisionError("INVALID_REQUEST")
        deadline = self._clock() + 2.0
        handle: object | None = None
        bindings: _Bindings | None = None
        try:
            bindings = self._bindings or _Win32()
            expected = bindings.window_process(document_hwnd)
            client = bindings.current()
            if expected.session_id == 0 or (expected.sid, expected.session_id) != (
                client.sid,
                client.session_id,
            ):
                raise NativeRevisionError("UNTRUSTED_PEER")
            _remaining(deadline, self._clock)
            name = f"autocad-mcp-context-v1-{expected.pid}-{expected.created_filetime:016x}"
            nonce = secrets.token_hex(32)
            handle = bindings.open_pipe(name, deadline)
            _remaining(deadline, self._clock)
            if (
                bindings.server_pid(handle) != expected.pid
                or bindings.process(expected.pid) != expected
            ):
                raise NativeRevisionError("UNTRUSTED_PEER")
            request = encode_request(
                nonce=nonce, client_pid=client.pid, document_hwnd=document_hwnd
            )
            result = self._exchange(bindings, handle, deadline, request, nonce)
            if (
                bindings.process(expected.pid) != expected
                or bindings.window_process(document_hwnd) != expected
                or bindings.server_pid(handle) != expected.pid
            ):
                raise NativeRevisionError("UNTRUSTED_PEER")
            _remaining(deadline, self._clock)
            return result
        except NativeRevisionError:
            raise
        except Exception:
            raise NativeRevisionError("UNAVAILABLE") from None
        finally:
            if handle is not None and bindings is not None:
                try:
                    bindings.close(handle)
                except Exception:
                    raise NativeRevisionError("UNAVAILABLE") from None

    def _exchange(
        self, bindings: _Bindings, handle: object, deadline: float, request: bytes, nonce: str
    ) -> RevisionWitness:
        offset = 0
        while offset < len(request):
            _remaining(deadline, self._clock)
            count = bindings.write(handle, request[offset:])
            if type(count) is not int or not 0 <= count <= len(request) - offset:
                raise NativeRevisionError("INVALID_REQUEST")
            offset += count
            if count == 0:
                bindings.pause(_remaining(deadline, self._clock))

        def exact(size: int) -> bytes:
            data = bytearray()
            while len(data) < size:
                _remaining(deadline, self._clock)
                chunk = bindings.read(handle, size - len(data))
                if type(chunk) is not bytes or len(chunk) > size - len(data):
                    raise NativeRevisionError("INVALID_REQUEST")
                data.extend(chunk)
                if not chunk:
                    bindings.pause(_remaining(deadline, self._clock))
            return bytes(data)

        header = exact(4)
        size = struct.unpack("<I", header)[0]
        if not 0 < size <= MAX_RESPONSE_BYTES:
            raise NativeRevisionError("INVALID_REQUEST")
        return decode_response(header + exact(size), expected_nonce=nonce)


class _Win32:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise NativeRevisionError("UNAVAILABLE")
        self.api: Any = importlib.import_module("win32api")
        self.process_api: Any = importlib.import_module("win32process")
        self.security: Any = importlib.import_module("win32security")
        self.file: Any = importlib.import_module("win32file")
        self.pipe: Any = importlib.import_module("win32pipe")
        self.event: Any = importlib.import_module("win32event")
        self.sessions: Any = importlib.import_module("win32ts")
        from ctypes import wintypes

        self.kernel: Any = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        self.kernel.GetProcessTimes.restype = wintypes.BOOL
        self.kernel.GetNamedPipeServerProcessId.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel.GetNamedPipeServerProcessId.restype = wintypes.BOOL

    def current(self) -> ProcessIdentity:
        return self.process(os.getpid())

    def window_process(self, hwnd: int) -> ProcessIdentity:
        _, pid = self.process_api.GetWindowThreadProcessId(hwnd)
        return self.process(pid)

    def process(self, pid: int) -> ProcessIdentity:
        from ctypes import wintypes

        process = self.api.OpenProcess(0x1000 | 0x100000, False, pid)
        try:
            if self.event.WaitForSingleObject(process, 0) != 258:
                raise NativeRevisionError("UNAVAILABLE")
            created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
            if not self.kernel.GetProcessTimes(
                int(process),
                ctypes.byref(created),
                ctypes.byref(exited),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                raise NativeRevisionError("UNAVAILABLE")
            token = self.security.OpenProcessToken(process, 8)
            try:
                sid = self.security.ConvertSidToStringSid(
                    self.security.GetTokenInformation(token, self.security.TokenUser)[0]
                )
            finally:
                token.Close()
            return ProcessIdentity(
                pid,
                (created.dwHighDateTime << 32) | created.dwLowDateTime,
                str(sid),
                int(self.sessions.ProcessIdToSessionId(pid)),
            )
        finally:
            process.Close()

    def open_pipe(self, name: str, deadline: float) -> object:
        while True:
            remaining = _remaining(deadline, time.monotonic)
            try:
                # Identification-only SQOS prevents the server from impersonating this client.
                handle = self.file.CreateFile(
                    "\\\\.\\pipe\\" + name, 0xC0000000, 0, None, 3, 0x00110000, None
                )
                try:
                    self.pipe.SetNamedPipeHandleState(handle, 1, None, None)  # PIPE_NOWAIT
                    return handle
                except Exception:
                    handle.Close()
                    raise
            except Exception as error:
                if getattr(error, "winerror", None) != 231:  # ERROR_PIPE_BUSY
                    raise NativeRevisionError("UNAVAILABLE") from None
                try:
                    self.pipe.WaitNamedPipe("\\\\.\\pipe\\" + name, max(1, int(remaining * 1000)))
                except Exception:
                    raise NativeRevisionError("TIMEOUT") from None

    def server_pid(self, handle: object) -> int:
        from ctypes import wintypes

        pid = wintypes.DWORD()
        if not self.kernel.GetNamedPipeServerProcessId(int(handle), ctypes.byref(pid)):  # type: ignore[call-overload]
            raise NativeRevisionError("UNAVAILABLE")
        return int(pid.value)

    def write(self, handle: object, data: bytes) -> int:
        _, count = self.file.WriteFile(handle, data)
        return int(count)

    def read(self, handle: object, size: int) -> bytes:
        try:
            _, data = self.file.ReadFile(handle, size)
            return bytes(data)
        except Exception as error:
            if getattr(error, "winerror", None) == 232:  # ERROR_NO_DATA: nonblocking empty pipe
                return b""
            raise NativeRevisionError("UNAVAILABLE") from None

    def pause(self, remaining: float) -> None:
        # ponytail: bounded metadata polling; overlapped I/O if idle syscall cost matters.
        time.sleep(min(remaining, 0.005))

    def close(self, handle: object) -> None:
        self.file.CloseHandle(handle)
