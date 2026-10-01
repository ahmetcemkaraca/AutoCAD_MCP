"""Complete snapshot admission, exact storage bounds, expiry and worker concurrency."""

import copy
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from threading import Barrier
from typing import Any, cast

import pytest
from autocad_mcp.context.models import (
    CapabilityIssue,
    DrawingSnapshot,
    EntityContext,
    RelationshipFact,
)
from autocad_mcp.context.pagination import Clock
from autocad_mcp.context.repository import (
    InMemorySnapshotRepository,
    SnapshotRepository,
    SnapshotRepositoryError,
)
from autocad_mcp.context.serialization import record_to_json, record_to_payload

from tests.unit.context.fixtures import snapshot

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
MIB = 1024 * 1024


class TestClock:
    __test__ = False

    def __init__(self) -> None:
        self.value = NOW

    def now(self) -> datetime:
        return self.value


def unchecked(record: Any, **changes: Any) -> Any:
    """Model a forged incomplete record at the repository admission boundary."""
    result = copy.copy(record)
    for name, value in changes.items():
        object.__setattr__(result, name, value)
    return result


def seal(value: DrawingSnapshot) -> DrawingSnapshot:
    """Independent fixture counts use the contract's JSON form with the count omitted."""
    count = len(value.entities)
    value = replace(
        value,
        fingerprint=replace(value.fingerprint, entity_count=count),
        materialization=replace(
            value.materialization,
            entity_count=count,
            relationship_count=sum(len(entity.relationships) for entity in value.entities),
        ),
    )
    payload = record_to_payload(value)
    del payload["materialization"]["canonical_byte_count"]
    measured = len(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    )
    return replace(
        value, materialization=replace(value.materialization, canonical_byte_count=measured)
    )


def complete(index: int = 1, entities: tuple[EntityContext, ...] | None = None) -> DrawingSnapshot:
    value = cast(DrawingSnapshot, snapshot())
    identifier = f"ds1_{index:032x}"
    return seal(
        replace(
            value,
            snapshot_id=identifier,
            reference=replace(value.reference, snapshot_id=identifier),
            entities=value.entities if entities is None else entities,
        )
    )


def session_snapshot(
    value: DrawingSnapshot, session_id: str, object_id: int = 999
) -> DrawingSnapshot:
    return seal(
        replace(
            value,
            document=replace(value.document, session_document_id=session_id),
            reference=replace(value.reference, session_id=session_id),
            entities=tuple(
                replace(entity, identity=replace(entity.identity, object_id=object_id))
                for entity in value.entities
            ),
        )
    )


def sized_snapshot(target: int, index: int = 1) -> DrawingSnapshot:
    """Fill bounded observed block attributes to reach an actual full JSON byte size."""
    source = complete(index)
    entity = source.entities[0]
    assert entity.block is not None
    count = (target + 196607) // 196608
    values = tuple(
        replace(
            entity,
            identity=replace(entity.identity, handle=f"{i+1:X}"),
            block=replace(entity.block, attribute_values={"A": "", "B": "", "C": ""}),
        )
        for i in range(count)
    )
    value = complete(index, values)
    padding = target - len(record_to_json(value).encode())
    filled = []
    last = (0, "A")
    chunk = "x" * 65536
    for i, current in enumerate(value.entities):
        assert current.block is not None
        attributes = {}
        for key in ("A", "B", "C"):
            amount = min(padding, 65536)
            attributes[key] = chunk[:amount]
            padding -= amount
            if amount:
                last = (i, key)
        filled.append(replace(current, block=replace(current.block, attribute_values=attributes)))
    assert padding == 0
    value = complete(index, tuple(filled))
    correction = len(record_to_json(value).encode()) - target
    position, key = last
    current = filled[position]
    assert current.block is not None
    attributes = dict(current.block.attribute_values)
    attributes[key] = attributes[key][:-correction] if correction else attributes[key]
    filled[position] = replace(current, block=replace(current.block, attribute_values=attributes))
    result = complete(index, tuple(filled))
    assert len(record_to_json(result).encode()) == target
    return result


def error(code: str, action: Callable[[], object]) -> None:
    with pytest.raises(SnapshotRepositoryError) as caught:
        action()
    assert caught.value.code == code


def test_complete_storage_reconstructs_read_only_nested_facts() -> None:
    repository: SnapshotRepository = InMemorySnapshotRepository(clock=TestClock())
    original = complete()
    repository.put_complete(original)
    first = repository.get_complete(original.snapshot_id)
    second = repository.get_complete(original.snapshot_id)
    assert first == second == original
    assert first is not original and first is not second
    assert first.entities[0].block is not None
    with pytest.raises(TypeError):
        first.entities[0].block.attribute_values["KEY"] = "mutation"  # type: ignore[index]
    assert repository.get_complete(original.snapshot_id) == original
    assert repository.expires_at(original.snapshot_id) == NOW + timedelta(seconds=600)
    clock: Clock = TestClock()
    assert clock.now() == NOW


@pytest.mark.parametrize(
    "defect",
    [
        "schema",
        "fingerprint-complete",
        "materialization-complete",
        "fingerprint-count",
        "materialization-count",
        "relationship-count",
        "byte-count",
        "duplicate-handle",
        "required-top-issue",
        "required-entity-issue",
        "reference-id",
        "reference-document",
        "reference-session",
        "reference-fingerprint",
        "unknown-field-shape",
    ],
)
def test_incomplete_and_inconsistent_objects_never_enter_repository(defect: str) -> None:
    value = complete()
    if defect == "schema":
        value = unchecked(value, schema_version="2.0")
    elif defect.startswith("fingerprint-"):
        name = "complete" if defect.endswith("complete") else "entity_count"
        value = unchecked(
            value,
            fingerprint=unchecked(value.fingerprint, **{name: False if name == "complete" else 2}),
        )
    elif defect.startswith("materialization-"):
        name = "complete" if defect.endswith("complete") else "entity_count"
        value = unchecked(
            value,
            materialization=unchecked(
                value.materialization, **{name: False if name == "complete" else 2}
            ),
        )
    elif defect in ("relationship-count", "byte-count"):
        name = "relationship_count" if defect == "relationship-count" else "canonical_byte_count"
        value = unchecked(value, materialization=unchecked(value.materialization, **{name: 99}))
    elif defect == "duplicate-handle":
        value = complete(entities=value.entities * 2)
    elif defect.startswith("required-"):
        issue = CapabilityIssue("MISSING", "geometry", "A1", "StartPoint", "private fact", True)
        value = (
            seal(replace(value, capability_issues=(issue,)))
            if defect == "required-top-issue"
            else seal(
                replace(value, entities=(replace(value.entities[0], capability_issues=(issue,)),))
            )
        )
    elif defect.startswith("reference-"):
        name = {
            "reference-id": "snapshot_id",
            "reference-document": "document_id",
            "reference-session": "session_id",
            "reference-fingerprint": "fingerprint",
        }[defect]
        value = seal(replace(value, reference=replace(value.reference, **{name: "different"})))
    else:
        value = unchecked(value, units={"unknown": "private fact"})
    repository = InMemorySnapshotRepository(clock=TestClock())
    error("SNAPSHOT_INCOMPLETE", lambda: repository.put_complete(value))
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(value.snapshot_id))


def test_pages_and_arbitrary_inputs_are_not_complete_snapshots() -> None:
    repository = InMemorySnapshotRepository(clock=TestClock())
    invalid_values: tuple[object, ...] = (None, {}, record_to_payload(complete()))
    for value in invalid_values:
        error("SNAPSHOT_INCOMPLETE", partial(repository.put_complete, cast(DrawingSnapshot, value)))


def test_same_session_idempotency_keeps_first_payload_expiry_and_diagnostics() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(clock=clock)
    original = complete()
    repository.put_complete(original)
    clock.value += timedelta(seconds=500)
    changed = seal(
        replace(
            original,
            captured_at=NOW + timedelta(seconds=500),
            materialization=replace(
                original.materialization, revision_token_digest="sha256:" + "0" * 64
            ),
            entities=(
                replace(
                    original.entities[0],
                    identity=replace(original.entities[0].identity, object_id=999),
                ),
            ),
        )
    )
    repository.put_complete(changed)
    assert repository.get_complete(original.snapshot_id) == original
    assert repository.expires_at(original.snapshot_id) == NOW + timedelta(seconds=600)
    clock.value = NOW + timedelta(seconds=600)
    error("SNAPSHOT_EXPIRED", lambda: repository.get_complete(original.snapshot_id))
    error("SNAPSHOT_EXPIRED", lambda: repository.expires_at(original.snapshot_id))


def test_nfc_collision_comparison_preserves_exact_original_unicode_values() -> None:
    value = complete()
    original = seal(
        replace(
            value,
            entities=(
                replace(
                    value.entities[0], layer=replace(value.entities[0].layer, name="cafe\u0301")
                ),
            ),
        )
    )
    equivalent = seal(
        replace(
            original,
            entities=(
                replace(
                    original.entities[0], layer=replace(original.entities[0].layer, name="café")
                ),
            ),
        )
    )
    repository = InMemorySnapshotRepository(clock=TestClock())
    repository.put_complete(original)
    repository.put_complete(equivalent)
    assert repository.get_complete(original.snapshot_id).entities[0].layer.name == "cafe\u0301"
    forged = seal(
        replace(
            original,
            entities=(
                replace(
                    original.entities[0],
                    layer=replace(original.entities[0].layer, name="changed fact"),
                ),
            ),
        )
    )
    error("SNAPSHOT_ID_COLLISION", lambda: repository.put_complete(forged))
    assert repository.get_complete(original.snapshot_id) == original


def test_expiry_boundary_accessor_and_long_idle_tombstone_age() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(clock=clock)
    value = complete()
    repository.put_complete(value)
    clock.value = NOW + timedelta(seconds=600, microseconds=-1)
    assert repository.get_complete(value.snapshot_id) == value
    clock.value = NOW + timedelta(seconds=1499, microseconds=999999)
    error("SNAPSHOT_EXPIRED", lambda: repository.expires_at(value.snapshot_id))
    clock.value = NOW + timedelta(seconds=1500)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(value.snapshot_id))
    repository.put_complete(complete(2))
    clock.value = NOW + timedelta(seconds=10000)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(complete(2).snapshot_id))
    error("SNAPSHOT_NOT_FOUND", lambda: repository.expires_at("unknown-id"))


def test_eight_latest_tombstones_and_expired_capacity_reuse() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(clock=clock, ttl_seconds=1)
    for index in range(1, 10):
        repository.put_complete(complete(index))
        clock.value += timedelta(seconds=1)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(complete(1).snapshot_id))
    for index in range(2, 10):
        error(
            "SNAPSHOT_EXPIRED",
            partial(repository.get_complete, complete(index).snapshot_id),
        )
    repository.put_complete(complete(9))
    assert repository.get_complete(complete(9).snapshot_id) == complete(9)
    assert repository.expires_at(complete(9).snapshot_id) == clock.value + timedelta(seconds=1)


@pytest.mark.parametrize(
    "name,ceiling",
    [
        ("ttl_seconds", 600),
        ("max_snapshots", 4),
        ("max_snapshot_bytes", 32 * MIB),
        ("max_total_bytes", 128 * MIB),
        ("max_expired_tombstones", 8),
        ("tombstone_ttl_seconds", 900),
    ],
)
@pytest.mark.parametrize("kind", ["zero", "negative", "bool", "float", "above"])
def test_configuration_can_only_lower_integer_positive_server_limits(
    name: str, ceiling: int, kind: str
) -> None:
    invalid = {"zero": 0, "negative": -1, "bool": True, "float": 1.0, "above": ceiling + 1}[kind]
    with pytest.raises(ValueError):
        InMemorySnapshotRepository(clock=TestClock(), **{name: invalid})  # type: ignore[arg-type]


def test_four_live_records_never_evict_and_failed_insert_preserves_capacity() -> None:
    repository = InMemorySnapshotRepository(clock=TestClock())
    for index in range(1, 5):
        repository.put_complete(complete(index))
    error("SNAPSHOT_REPOSITORY_LIMIT", lambda: repository.put_complete(complete(5)))
    repository.put_complete(complete(1))
    for index in range(1, 5):
        assert repository.get_complete(complete(index).snapshot_id) == complete(index)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(complete(5).snapshot_id))


def test_lowered_byte_caps_check_actual_stored_bytes_and_no_refresh() -> None:
    value = complete()
    size = len(record_to_json(value).encode())
    repository = InMemorySnapshotRepository(
        clock=TestClock(), max_snapshot_bytes=size, max_total_bytes=2 * size
    )
    repository.put_complete(value)
    repository.put_complete(complete(2))
    error("SNAPSHOT_REPOSITORY_LIMIT", lambda: repository.put_complete(complete(3)))
    small = InMemorySnapshotRepository(clock=TestClock(), max_snapshot_bytes=size - 1)
    error("COMPLETE_SNAPSHOT_LIMIT", lambda: small.put_complete(value))


def test_actual_32_mib_snapshot_and_four_actual_128_mib_records() -> None:
    maximum = sized_snapshot(32 * MIB)
    repository = InMemorySnapshotRepository(clock=TestClock())
    for index in range(1, 5):
        value = seal(
            replace(
                maximum,
                snapshot_id=f"ds1_{index:032x}",
                reference=replace(maximum.reference, snapshot_id=f"ds1_{index:032x}"),
            )
        )
        assert len(record_to_json(value).encode()) == 32 * MIB
        repository.put_complete(value)
    assert repository.get_complete(maximum.snapshot_id) == maximum
    error("SNAPSHOT_REPOSITORY_LIMIT", lambda: repository.put_complete(complete(5)))
    overflow = sized_snapshot(32 * MIB + 1, 6)
    error("COMPLETE_SNAPSHOT_LIMIT", lambda: repository.put_complete(overflow))


def test_full_stored_count_field_is_included_in_byte_limit() -> None:
    value = complete()
    omitted_size = value.materialization.canonical_byte_count
    assert len(record_to_json(value).encode()) > omitted_size
    repository = InMemorySnapshotRepository(clock=TestClock(), max_snapshot_bytes=omitted_size)
    error("COMPLETE_SNAPSHOT_LIMIT", lambda: repository.put_complete(value))


def test_exact_10000_entities_and_one_over_preflight() -> None:
    source = complete().entities[0]
    entities = tuple(
        replace(source, identity=replace(source.identity, handle=f"{i+1:X}")) for i in range(10000)
    )
    value = complete(entities=entities)
    repository = InMemorySnapshotRepository(clock=TestClock())
    repository.put_complete(value)
    assert len(repository.get_complete(value.snapshot_id).entities) == 10000
    overflow = unchecked(
        value,
        entities=entities + (replace(source, identity=replace(source.identity, handle="FFFF")),),
    )
    error("COMPLETE_SNAPSHOT_LIMIT", lambda: repository.put_complete(overflow))


def test_exact_100000_relationships_and_one_over_preflight() -> None:
    source = complete().entities[0]
    entities = tuple(
        replace(
            source,
            identity=replace(source.identity, handle=f"{i+1:X}"),
            relationships=tuple(
                RelationshipFact("same_owner", f"{i+1:X}", f"{(i+j+1)%1000+1:X}", None, None)
                for j in range(100)
            ),
        )
        for i in range(1000)
    )
    value = complete(entities=entities)
    repository = InMemorySnapshotRepository(clock=TestClock())
    repository.put_complete(value)
    assert (
        sum(
            len(entity.relationships)
            for entity in repository.get_complete(value.snapshot_id).entities
        )
        == 100000
    )
    extra = unchecked(
        entities[0], relationships=entities[0].relationships + (entities[0].relationships[0],)
    )
    error(
        "COMPLETE_SNAPSHOT_LIMIT",
        lambda: repository.put_complete(unchecked(value, entities=(extra,) + entities[1:])),
    )


@pytest.mark.parametrize("capacity", ["count", "bytes"])
def test_competing_workers_cannot_claim_the_same_final_capacity(capacity: str) -> None:
    size = len(record_to_json(complete()).encode())
    retained_count = 3 if capacity == "count" else 2
    repository = InMemorySnapshotRepository(
        clock=TestClock(),
        max_total_bytes=(retained_count + 1) * size if capacity == "bytes" else 128 * MIB,
    )
    for index in range(1, retained_count + 1):
        repository.put_complete(complete(index))
    barrier = Barrier(2)

    def insert(index: int) -> str:
        value = complete(index)
        barrier.wait(timeout=5)
        try:
            repository.put_complete(value)
            return "stored"
        except SnapshotRepositoryError as failure:
            return failure.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(insert, (4, 5)))
    assert sorted(results) == ["SNAPSHOT_REPOSITORY_LIMIT", "stored"]
    for index in range(1, retained_count + 1):
        assert repository.get_complete(complete(index).snapshot_id) == complete(index)


def test_idempotency_keeps_original_diagnostic_messages_and_detached_reads() -> None:
    value = complete()
    issue = CapabilityIssue("OPTIONAL", "text", "A1", "TextString", "original diagnostic", False)
    original = seal(replace(value, capability_issues=(issue,)))
    changed = seal(
        replace(original, capability_issues=(replace(issue, message="changed diagnostic"),))
    )
    repository = InMemorySnapshotRepository(clock=TestClock())
    repository.put_complete(original)
    repository.put_complete(changed)
    first = repository.get_complete(original.snapshot_id)
    assert first == original
    object.__setattr__(first.entities[0].layer, "name", "forced read mutation")
    assert repository.get_complete(original.snapshot_id) == original


def test_admission_failure_message_never_retains_private_facts() -> None:
    value = complete()
    invalid = seal(
        replace(value, reference=replace(value.reference, session_id="private session value"))
    )
    repository = InMemorySnapshotRepository(clock=TestClock())
    with pytest.raises(SnapshotRepositoryError) as caught:
        repository.put_complete(invalid)
    assert caught.value.code == "SNAPSHOT_INCOMPLETE"
    assert "private session value" not in str(caught.value)


def test_lower_count_ttl_and_tombstone_configuration_are_enforced() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(
        clock=clock,
        ttl_seconds=2,
        max_snapshots=1,
        max_expired_tombstones=1,
        tombstone_ttl_seconds=3,
    )
    first, second = complete(1), complete(2)
    repository.put_complete(first)
    assert repository.expires_at(first.snapshot_id) == NOW + timedelta(seconds=2)
    error("SNAPSHOT_REPOSITORY_LIMIT", lambda: repository.put_complete(second))
    clock.value = NOW + timedelta(seconds=2)
    repository.put_complete(second)
    clock.value = NOW + timedelta(seconds=4)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(first.snapshot_id))
    error("SNAPSHOT_EXPIRED", lambda: repository.get_complete(second.snapshot_id))
    clock.value = NOW + timedelta(seconds=7)
    error("SNAPSHOT_NOT_FOUND", lambda: repository.get_complete(second.snapshot_id))


def test_empty_complete_drawing_is_admitted_with_zero_fact_counts() -> None:
    repository = InMemorySnapshotRepository(clock=TestClock())
    value = complete(entities=())
    repository.put_complete(value)
    retained = repository.get_complete(value.snapshot_id)
    assert retained == value
    assert retained.entities == ()
    assert retained.fingerprint.entity_count == retained.materialization.entity_count == 0
    assert retained.materialization.relationship_count == 0


def test_reopened_session_retains_fresh_ids_and_original_scoped_payload() -> None:
    repository: SnapshotRepository = InMemorySnapshotRepository(clock=TestClock())
    original = complete()
    reopened = session_snapshot(original, "reopened-session")
    assert reopened.snapshot_id == original.snapshot_id
    repository.put_complete(original)
    repository.put_complete(reopened)

    old = repository.get_complete(original.snapshot_id, session_id=original.reference.session_id)
    new = repository.get_complete(reopened.snapshot_id, session_id=reopened.reference.session_id)
    assert old == original and new == reopened
    assert old.entities[0].identity.object_id == 42
    assert new.entities[0].identity.object_id == 999
    error("SNAPSHOT_ID_COLLISION", partial(repository.get_complete, original.snapshot_id))
    error("SNAPSHOT_ID_COLLISION", partial(repository.expires_at, original.snapshot_id))


def test_session_expiry_is_independent_and_qualified_lookup_never_falls_back() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(clock=clock)
    original = complete()
    repository.put_complete(original)
    clock.value += timedelta(seconds=100)
    reopened = session_snapshot(original, "reopened-session")
    repository.put_complete(reopened)
    repository.put_complete(original)
    assert repository.expires_at(
        original.snapshot_id, session_id=original.reference.session_id
    ) == NOW + timedelta(seconds=600)
    assert repository.expires_at(
        reopened.snapshot_id, session_id=reopened.reference.session_id
    ) == NOW + timedelta(seconds=700)
    clock.value = NOW + timedelta(seconds=600)
    for lookup in (repository.get_complete, repository.expires_at):
        error(
            "SNAPSHOT_EXPIRED",
            partial(lookup, original.snapshot_id, session_id=original.reference.session_id),
        )
    assert repository.get_complete(original.snapshot_id) == reopened
    assert repository.expires_at(original.snapshot_id) == NOW + timedelta(seconds=700)
    clock.value = NOW + timedelta(seconds=1500)
    error(
        "SNAPSHOT_NOT_FOUND",
        partial(
            repository.get_complete, original.snapshot_id, session_id=original.reference.session_id
        ),
    )
    error(
        "SNAPSHOT_EXPIRED",
        partial(
            repository.get_complete, original.snapshot_id, session_id=reopened.reference.session_id
        ),
    )
    error("SNAPSHOT_EXPIRED", partial(repository.get_complete, original.snapshot_id))
    clock.value = NOW + timedelta(seconds=1600)
    error("SNAPSHOT_NOT_FOUND", partial(repository.get_complete, original.snapshot_id))


@pytest.mark.parametrize("invalid_session", ["unknown-session", False, 1, []])
@pytest.mark.parametrize("method", ["get_complete", "expires_at"])
def test_unknown_or_invalid_session_never_returns_another_live_session(
    invalid_session: object, method: str
) -> None:
    repository = InMemorySnapshotRepository(clock=TestClock())
    original = complete()
    repository.put_complete(original)
    error(
        "SNAPSHOT_NOT_FOUND",
        partial(getattr(repository, method), original.snapshot_id, session_id=invalid_session),
    )


def test_session_tombstones_share_the_eight_entry_limit() -> None:
    clock = TestClock()
    repository = InMemorySnapshotRepository(clock=clock, ttl_seconds=1)
    original = complete()
    for index in range(9):
        repository.put_complete(session_snapshot(original, f"session-{index}"))
        clock.value += timedelta(seconds=1)
    error(
        "SNAPSHOT_NOT_FOUND",
        partial(repository.get_complete, original.snapshot_id, session_id="session-0"),
    )
    for index in range(1, 9):
        error(
            "SNAPSHOT_EXPIRED",
            partial(repository.get_complete, original.snapshot_id, session_id=f"session-{index}"),
        )
    live = session_snapshot(original, "current-session")
    repository.put_complete(live)
    assert repository.get_complete(original.snapshot_id) == live
    error(
        "SNAPSHOT_EXPIRED",
        partial(repository.get_complete, original.snapshot_id, session_id="session-8"),
    )


def test_cross_session_fact_collisions_reject_without_changing_retained_payloads() -> None:
    repository = InMemorySnapshotRepository(clock=TestClock())
    original = complete()
    reopened = session_snapshot(original, "reopened-session")
    repository.put_complete(original)
    repository.put_complete(reopened)
    forged = session_snapshot(original, "third-session")
    forged = seal(
        replace(
            forged,
            entities=(
                replace(
                    forged.entities[0], layer=replace(forged.entities[0].layer, name="changed")
                ),
            ),
        )
    )
    error("SNAPSHOT_ID_COLLISION", partial(repository.put_complete, forged))
    for value in (original, reopened):
        assert repository.get_complete(
            value.snapshot_id, session_id=value.reference.session_id
        ) == value
    error(
        "SNAPSHOT_NOT_FOUND",
        partial(repository.get_complete, original.snapshot_id, session_id="third-session"),
    )


@pytest.mark.parametrize("capacity", ["count", "bytes"])
def test_same_id_sessions_share_count_and_byte_capacity(capacity: str) -> None:
    original = complete()
    size = len(record_to_json(original).encode())
    count = 4 if capacity == "count" else 2
    repository = InMemorySnapshotRepository(
        clock=TestClock(), max_total_bytes=count * size if capacity == "bytes" else 128 * MIB
    )
    values = tuple(session_snapshot(original, f"session-{i}", 42) for i in range(1, count + 1))
    for value in values:
        assert len(record_to_json(value).encode()) == size
        repository.put_complete(value)
    error(
        "SNAPSHOT_REPOSITORY_LIMIT",
        partial(repository.put_complete, session_snapshot(original, "session-5", 42)),
    )
    repository.put_complete(values[0])
    for value in values:
        assert repository.get_complete(
            value.snapshot_id, session_id=value.reference.session_id
        ) == value


@pytest.mark.parametrize("capacity", ["count", "bytes"])
def test_competing_sessions_cannot_claim_the_same_final_capacity(capacity: str) -> None:
    original = complete()
    size = len(record_to_json(original).encode())
    retained_count = 3 if capacity == "count" else 2
    repository = InMemorySnapshotRepository(
        clock=TestClock(),
        max_total_bytes=(retained_count + 1) * size if capacity == "bytes" else 128 * MIB,
    )
    for index in range(1, retained_count + 1):
        repository.put_complete(session_snapshot(original, f"session-{index}", 42))
    barrier = Barrier(2)

    def insert(index: int) -> str:
        value = session_snapshot(original, f"session-{index}", 42)
        barrier.wait(timeout=5)
        try:
            repository.put_complete(value)
            return "stored"
        except SnapshotRepositoryError as failure:
            return failure.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(insert, (4, 5)))
    assert sorted(results) == ["SNAPSHOT_REPOSITORY_LIMIT", "stored"]
