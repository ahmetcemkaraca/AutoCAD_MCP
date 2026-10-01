"""Bounded process-local complete snapshots with immutable reads and anchored expiry."""

import json
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Literal, Protocol, TypeAlias

from .fingerprint import snapshot_identity_bytes
from .models import DrawingSnapshot
from .pagination import Clock
from .serialization import record_to_json, record_to_payload, snapshot_from_json
from .validation import (
    MAX_COMPLETE_RELATIONSHIPS,
    MAX_SNAPSHOT_BYTES,
    MAX_SNAPSHOT_ENTITIES,
    ContextValidationError,
)

__all__ = ["Clock", "SnapshotRepository", "SnapshotRepositoryError", "InMemorySnapshotRepository"]

SnapshotRepositoryCode: TypeAlias = Literal[  # noqa: UP040
    "SNAPSHOT_INCOMPLETE",
    "SNAPSHOT_NOT_FOUND",
    "SNAPSHOT_EXPIRED",
    "SNAPSHOT_ID_COLLISION",
    "SNAPSHOT_REPOSITORY_LIMIT",
    "COMPLETE_SNAPSHOT_LIMIT",
]


class SnapshotRepositoryError(Exception):
    """A structured, input-free repository admission or lookup failure."""

    code: SnapshotRepositoryCode

    def __init__(self, code: SnapshotRepositoryCode) -> None:
        self.code = code
        super().__init__(code.replace("_", " ").capitalize())


class SnapshotRepository(Protocol):
    def put_complete(self, snapshot: DrawingSnapshot) -> None: ...
    def get_complete(self, snapshot_id: str) -> DrawingSnapshot: ...
    def expires_at(self, snapshot_id: str) -> datetime: ...


def _check_metadata(snapshot: DrawingSnapshot) -> None:
    if type(snapshot) is not DrawingSnapshot:
        raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE")
    if (
        snapshot.schema_version != "1.0"
        or snapshot.fingerprint.complete is not True
        or snapshot.materialization.complete is not True
    ):
        raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE")
    entity_count = len(snapshot.entities)
    relationship_count = sum(len(entity.relationships) for entity in snapshot.entities)
    if entity_count > MAX_SNAPSHOT_ENTITIES or relationship_count > MAX_COMPLETE_RELATIONSHIPS:
        raise SnapshotRepositoryError("COMPLETE_SNAPSHOT_LIMIT")
    if (
        snapshot.fingerprint.entity_count != entity_count
        or snapshot.materialization.entity_count != entity_count
        or snapshot.materialization.relationship_count != relationship_count
        or len({entity.identity.handle for entity in snapshot.entities}) != entity_count
        or any(issue.required for issue in snapshot.capability_issues)
        or any(issue.required for entity in snapshot.entities for issue in entity.capability_issues)
    ):
        raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE")
    reference = snapshot.reference
    if (
        reference.snapshot_id != snapshot.snapshot_id
        or reference.document_id != snapshot.document.document_id
        or reference.session_id != snapshot.document.session_document_id
        or reference.fingerprint != snapshot.fingerprint.content_digest
    ):
        raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE")


def _encode_complete(snapshot: DrawingSnapshot, maximum: int) -> tuple[bytes, DrawingSnapshot]:
    try:
        _check_metadata(snapshot)
        payload = record_to_payload(snapshot)
        encoded = record_to_json(payload).encode("utf-8")
        if len(encoded) > maximum:
            raise SnapshotRepositoryError("COMPLETE_SNAPSHOT_LIMIT")
        declared = payload["materialization"].pop("canonical_byte_count")
        measured = len(record_to_json(payload).encode("utf-8"))
        payload["materialization"]["canonical_byte_count"] = declared
        if declared != measured:
            raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE")
        validated = snapshot_from_json(payload)
        _check_metadata(validated)
        # Reject invalid normalized identity facts, including NFC key collisions.
        snapshot_identity_bytes(validated)
        return encoded, validated
    except SnapshotRepositoryError:
        raise
    except ContextValidationError as error:
        code: SnapshotRepositoryCode = (
            "COMPLETE_SNAPSHOT_LIMIT"
            if error.code == "COMPLETE_SNAPSHOT_LIMIT"
            else "SNAPSHOT_INCOMPLETE"
        )
        raise SnapshotRepositoryError(code) from None
    except (ValueError, TypeError, AttributeError, KeyError, RecursionError, OverflowError):
        raise SnapshotRepositoryError("SNAPSHOT_INCOMPLETE") from None


class InMemorySnapshotRepository:
    def __init__(
        self,
        *,
        clock: Clock,
        ttl_seconds: int = 600,
        max_snapshots: int = 4,
        max_snapshot_bytes: int = 32 * 1024 * 1024,
        max_total_bytes: int = 128 * 1024 * 1024,
        max_expired_tombstones: int = 8,
        tombstone_ttl_seconds: int = 900,
    ) -> None:
        for value, ceiling in (
            (ttl_seconds, 600),
            (max_snapshots, 4),
            (max_snapshot_bytes, MAX_SNAPSHOT_BYTES),
            (max_total_bytes, 128 * 1024 * 1024),
            (max_expired_tombstones, 8),
            (tombstone_ttl_seconds, 900),
        ):
            if type(value) is not int or not 0 < value <= ceiling:
                raise ValueError(
                    "Repository limits require positive integers within server ceilings"
                )
        self._clock = clock
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_snapshots = max_snapshots
        self._max_snapshot_bytes = max_snapshot_bytes
        self._max_total_bytes = max_total_bytes
        self._max_expired_tombstones = max_expired_tombstones
        self._tombstone_ttl = timedelta(seconds=tombstone_ttl_seconds)
        self._records: dict[str, tuple[bytes, datetime]] = {}
        self._tombstones: dict[str, datetime] = {}
        # ponytail: one repository lock; finer locks if measured worker contention matters.
        self._lock = Lock()

    def _purge(self) -> datetime:
        now = self._clock.now()
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("Repository clock must return an aware datetime")
        now = now.astimezone(UTC)
        for identifier, (_, expires) in tuple(self._records.items()):
            if now >= expires:
                del self._records[identifier]
                self._tombstones[identifier] = expires + self._tombstone_ttl
        self._tombstones = {
            identifier: expires
            for identifier, expires in sorted(
                self._tombstones.items(), key=lambda pair: (pair[1], pair[0]), reverse=True
            )
            if expires > now
        }
        self._tombstones = dict(list(self._tombstones.items())[: self._max_expired_tombstones])
        return now

    def _entry(self, identifier: str) -> tuple[bytes, datetime]:
        if not isinstance(identifier, str):
            raise SnapshotRepositoryError("SNAPSHOT_NOT_FOUND")
        record = self._records.get(identifier)
        if record is None:
            raise SnapshotRepositoryError(
                "SNAPSHOT_EXPIRED" if identifier in self._tombstones else "SNAPSHOT_NOT_FOUND"
            )
        return record

    def put_complete(self, snapshot: DrawingSnapshot) -> None:
        with self._lock:
            now = self._purge()
            encoded, validated = _encode_complete(snapshot, self._max_snapshot_bytes)
            identifier = validated.snapshot_id
            existing = self._records.get(identifier)
            if existing is not None:
                retained = snapshot_from_json(json.loads(existing[0]))
                if snapshot_identity_bytes(retained) != snapshot_identity_bytes(validated):
                    raise SnapshotRepositoryError("SNAPSHOT_ID_COLLISION")
                return
            if (
                len(self._records) >= self._max_snapshots
                or sum(len(record[0]) for record in self._records.values()) + len(encoded)
                > self._max_total_bytes
            ):
                raise SnapshotRepositoryError("SNAPSHOT_REPOSITORY_LIMIT")
            self._records[identifier] = encoded, now + self._ttl
            self._tombstones.pop(identifier, None)

    def get_complete(self, snapshot_id: str) -> DrawingSnapshot:
        with self._lock:
            self._purge()
            encoded, _ = self._entry(snapshot_id)
            return snapshot_from_json(json.loads(encoded))

    def expires_at(self, snapshot_id: str) -> datetime:
        with self._lock:
            self._purge()
            return self._entry(snapshot_id)[1]
