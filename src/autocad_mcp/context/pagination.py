"""Pure entity ordering, normalized request bindings, and stateless signed cursors."""

import base64
import binascii
import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol
from unicodedata import normalize

from .models import EntityContext, EntityQueryFilters
from .serialization import _reject_constant, _unique_object, record_to_json, record_to_payload
from .validation import MAX_CURSOR_BYTES, ContextValidationError, normalize_handle, require

_SPACE_RANK = {"model": 0, "paper": 1, "block_definition": 2}


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def entity_sort_key(entity: EntityContext) -> tuple[int, str, int, str]:
    return (
        _SPACE_RANK[entity.space.kind],
        normalize("NFC", normalize("NFC", entity.space.layout_name or "").casefold()),
        int(entity.identity.handle, 16),
        entity.identity.handle,
    )


def normalize_filters(filters: EntityQueryFilters) -> EntityQueryFilters:
    changes: dict[str, Any] = {
        name: tuple(sorted({normalize("NFC", value) for value in getattr(filters, name)}))
        for name in ("spaces", "layout_names", "entity_types", "layer_names", "layer_globs")
    }
    changes["handles"] = tuple(
        sorted(
            {normalize_handle(handle) for handle in filters.handles},
            key=lambda handle: (int(handle, 16), handle),
        )
    )
    return replace(filters, **changes)


def filter_digest(filters: EntityQueryFilters, include: Mapping[str, bool]) -> str:
    from .fingerprint import canonical_bytes

    require(
        isinstance(include, Mapping)
        and all(isinstance(key, str) and type(value) is bool for key, value in include.items()),
        "Include flags must be a boolean mapping",
    )
    payload = {"filters": record_to_payload(normalize_filters(filters)), "include": dict(include)}
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _valid(condition: bool) -> None:
    require(condition, "Invalid cursor", code="INVALID_CURSOR")


def _text(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and "\0" not in value
        and len(value.encode("utf-8")) <= limit
    )


def _utc(value: datetime) -> bool:
    return isinstance(value, datetime) and value.utcoffset() == timedelta(0)


@dataclass(frozen=True, slots=True)
class PageCursor:
    kind: Literal["snapshot", "live_query"]
    document_id: str
    session_id: str
    filter_digest: str
    page_size: int
    last_handle: str | None
    issued_at: datetime
    expires_at: datetime
    snapshot_id: str | None = None
    revision_token_digest: str | None = None
    adapter_cursor: str | None = None

    def __post_init__(self) -> None:
        try:
            _valid(self.kind in ("snapshot", "live_query"))
            _valid(
                isinstance(self.document_id, str)
                and re.fullmatch(r"(?:dwg_|session_)[0-9a-f]{32}", self.document_id) is not None
            )
            _valid(_text(self.session_id, MAX_CURSOR_BYTES))
            _valid(
                isinstance(self.filter_digest, str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", self.filter_digest) is not None
            )
            _valid(type(self.page_size) is int and 1 <= self.page_size <= 500)
            _valid(_utc(self.issued_at) and _utc(self.expires_at))
            lifetime = self.expires_at - self.issued_at
            _valid(
                timedelta(0)
                < lifetime
                <= timedelta(seconds=600 if self.kind == "snapshot" else 900)
            )
            if self.kind == "snapshot":
                _valid(
                    isinstance(self.snapshot_id, str)
                    and re.fullmatch(r"ds1_[0-9a-f]{32}", self.snapshot_id) is not None
                )
                _valid(self.revision_token_digest is None and self.adapter_cursor is None)
            else:
                _valid(
                    self.snapshot_id is None
                    and isinstance(self.revision_token_digest, str)
                    and re.fullmatch(r"sha256:[0-9a-f]{64}", self.revision_token_digest) is not None
                )
                _valid(self.adapter_cursor is None or _text(self.adapter_cursor, MAX_CURSOR_BYTES))
            if self.last_handle is not None:
                _valid(normalize_handle(self.last_handle) == self.last_handle)
        except (ContextValidationError, ValueError, TypeError, OverflowError, UnicodeError):
            raise ContextValidationError("Invalid cursor", code="INVALID_CURSOR") from None


def _base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unbase64(value: str) -> bytes:
    _valid(re.fullmatch(r"[A-Za-z0-9_-]+", value) is not None)
    result = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    _valid(_base64(result) == value)
    return result


class CursorCodec:
    def __init__(self, *, clock: Clock, secret: bytes) -> None:
        require(
            type(secret) is bytes and len(secret) >= 32, "Cursor secret requires at least 32 bytes"
        )
        self._clock = clock
        self._secret = secret

    def _check_time(self, cursor: PageCursor) -> None:
        now = self._clock.now()
        _valid(_utc(now) and cursor.issued_at <= now)
        require(now < cursor.expires_at, "Cursor expired", code="CURSOR_EXPIRED")

    def encode(self, cursor: PageCursor) -> str:
        _valid(type(cursor) is PageCursor)
        self._check_time(cursor)
        payload = {field.name: getattr(cursor, field.name) for field in fields(cursor)}
        for name in ("issued_at", "expires_at"):
            payload[name] = payload[name].isoformat(timespec="microseconds").replace("+00:00", "Z")
        # Opaque adapter/session bindings must retain their original Unicode bytes.
        raw = record_to_json({"version": 1, **payload}).encode("utf-8")
        result = _base64(raw) + "." + _base64(hmac.digest(self._secret, raw, "sha256"))
        _valid(len(result.encode("utf-8")) <= MAX_CURSOR_BYTES)
        return result

    def decode(self, value: str) -> PageCursor:
        try:
            _valid(isinstance(value, str) and 0 < len(value.encode("utf-8")) <= MAX_CURSOR_BYTES)
            parts = value.split(".")
            _valid(len(parts) == 2)
            raw, signature = (_unbase64(part) for part in parts)
            _valid(hmac.compare_digest(signature, hmac.digest(self._secret, raw, "sha256")))
            payload: Any = json.loads(
                raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant
            )
            _valid(
                isinstance(payload, dict)
                and payload.keys() == {field.name for field in fields(PageCursor)} | {"version"}
            )
            version = payload.pop("version")
            _valid(type(version) is int and version == 1)
            for name in ("issued_at", "expires_at"):
                _valid(isinstance(payload[name], str))
                payload[name] = datetime.fromisoformat(payload[name])
            cursor = PageCursor(**payload)
            self._check_time(cursor)
            return cursor
        except ContextValidationError as error:
            if error.code in ("INVALID_CURSOR", "CURSOR_EXPIRED"):
                raise
            raise ContextValidationError("Invalid cursor", code="INVALID_CURSOR") from None
        except (ValueError, TypeError, UnicodeError, RecursionError, binascii.Error):
            raise ContextValidationError("Invalid cursor", code="INVALID_CURSOR") from None
