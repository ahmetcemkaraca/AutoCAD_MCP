"""Pure bounded metadata protocol; host authentication and transport live elsewhere."""

import json
import re
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import BinaryIO, Protocol, cast
from uuid import UUID

MAX_REQUEST_BYTES = 4096
MAX_RESPONSE_BYTES = 8192
_ERROR_CODES = frozenset({"UNAVAILABLE", "BUSY", "INVALID_REQUEST", "TIMEOUT", "UNTRUSTED_PEER"})


class NativeRevisionError(RuntimeError):
    """Private fixed-code failure, translated later by the context adapter."""

    def __init__(self, code: str = "INVALID_REQUEST") -> None:
        self.code = code if code in _ERROR_CODES else "INVALID_REQUEST"
        super().__init__(self.code)


def _require(condition: bool) -> None:
    if not condition:
        raise NativeRevisionError()


def _uuid(value: object) -> str:
    _require(type(value) is str)
    assert isinstance(value, str)
    try:
        _require(str(UUID(value)) == value)
    except ValueError:
        raise NativeRevisionError() from None
    return value


def _nonce(value: object) -> str:
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)
    assert isinstance(value, str)
    return value


@dataclass(frozen=True)
class RevisionWitness:
    bridge_id: str
    session_id: str
    epoch: int
    database_guid: str | None

    def __post_init__(self) -> None:
        _uuid(self.bridge_id)
        _uuid(self.session_id)
        _require(type(self.epoch) is int and 1 <= self.epoch <= 2**64 - 1)
        if self.database_guid is not None:
            _uuid(self.database_guid)

    @property
    def opaque_token(self) -> str:
        return f"native-context-epochs-v1:{self.bridge_id}:{self.session_id}:{self.epoch}"


class NativeRevisionSource(Protocol):
    """Read one authenticated host witness; never fabricate fallback epochs."""

    def witness(self, document_hwnd: int) -> RevisionWitness: ...


@dataclass(frozen=True)
class StateRequest:
    nonce: str
    client_pid: int
    document_hwnd: int

    def __post_init__(self) -> None:
        _nonce(self.nonce)
        _require(type(self.client_pid) is int and 1 <= self.client_pid <= 2**32 - 1)
        _require(type(self.document_hwnd) is int and 1 <= self.document_hwnd <= 2**64 - 1)


def _frame(payload: bytes, limit: int) -> bytes:
    _require(0 < len(payload) <= limit)
    return struct.pack("<I", len(payload)) + payload


def _json_frame(value: Mapping[str, object], limit: int) -> bytes:
    return _frame(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        ),
        limit,
    )


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise NativeRevisionError()


def _payload(frame: bytes, limit: int) -> dict[str, object]:
    try:
        _require(type(frame) is bytes and len(frame) >= 4)
        length = struct.unpack("<I", frame[:4])[0]
        _require(0 < length <= limit and len(frame) == length + 4)
        value = json.loads(
            frame[4:].decode("utf-8"), object_pairs_hook=_unique, parse_constant=_reject_constant
        )
        _require(type(value) is dict)
        return cast(dict[str, object], value)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise NativeRevisionError() from None


def encode_request(*, nonce: str, client_pid: int, document_hwnd: int) -> bytes:
    request = StateRequest(nonce, client_pid, document_hwnd)
    return _json_frame(
        {
            "version": 1,
            "operation": "read_state",
            "nonce": request.nonce,
            "client_pid": request.client_pid,
            "document_hwnd": f"{request.document_hwnd:016x}",
        },
        MAX_REQUEST_BYTES,
    )


def decode_request(frame: bytes) -> StateRequest:
    value = _payload(frame, MAX_REQUEST_BYTES)
    _require(value.keys() == {"version", "operation", "nonce", "client_pid", "document_hwnd"})
    _require(type(value["version"]) is int and value["version"] == 1)
    _require(value["operation"] == "read_state")
    hwnd = value["document_hwnd"]
    _require(type(hwnd) is str and re.fullmatch(r"[0-9a-f]{16}", hwnd) is not None)
    assert isinstance(hwnd, str)
    return StateRequest(_nonce(value["nonce"]), value["client_pid"], int(hwnd, 16))  # type: ignore[arg-type]


def encode_response(
    *, nonce: str, witness: RevisionWitness | None = None, error: str | None = None
) -> bytes:
    _nonce(nonce)
    _require((witness is None) != (error is None))
    value: dict[str, object] = {"version": 1, "nonce": nonce}
    if error is not None:
        _require(error in _ERROR_CODES)
        value["error"] = error
    else:
        _require(type(witness) is RevisionWitness)
        assert witness is not None
        value["state"] = {
            "bridge_id": witness.bridge_id,
            "session_id": witness.session_id,
            "epoch": str(witness.epoch),
            "database_guid": witness.database_guid,
            "ready": True,
            "coverage": "context-facts-v1",
        }
    return _json_frame(value, MAX_RESPONSE_BYTES)


def decode_response(frame: bytes, *, expected_nonce: str) -> RevisionWitness:
    _nonce(expected_nonce)
    value = _payload(frame, MAX_RESPONSE_BYTES)
    _require(value.keys() in ({"version", "nonce", "error"}, {"version", "nonce", "state"}))
    _require(type(value["version"]) is int and value["version"] == 1)
    _nonce(value["nonce"])
    if value["nonce"] != expected_nonce:
        raise NativeRevisionError("UNTRUSTED_PEER")
    if "error" in value:
        _require(type(value["error"]) is str and value["error"] in _ERROR_CODES)
        raise NativeRevisionError(cast(str, value["error"]))
    state = value["state"]
    _require(type(state) is dict)
    assert isinstance(state, dict)
    _require(
        state.keys() == {"bridge_id", "session_id", "epoch", "database_guid", "ready", "coverage"}
    )
    _require(state["ready"] is True and state["coverage"] == "context-facts-v1")
    epoch = state["epoch"]
    _require(type(epoch) is str and re.fullmatch(r"[1-9][0-9]{0,19}", epoch) is not None)
    return RevisionWitness(
        state["bridge_id"], state["session_id"], int(epoch), state["database_guid"]
    )


def read_frame(stream: BinaryIO, *, limit: int) -> bytes:
    """Read one bounded frame; transport owns timeout and single-request closure."""
    _require(limit in (MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES))

    def exact(length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            chunk = stream.read(length - len(chunks))
            _require(type(chunk) is bytes and 0 < len(chunk) <= length - len(chunks))
            chunks.extend(chunk)
        return bytes(chunks)

    header = exact(4)
    length = struct.unpack("<I", header)[0]
    _require(0 < length <= limit)
    return header + exact(length)
