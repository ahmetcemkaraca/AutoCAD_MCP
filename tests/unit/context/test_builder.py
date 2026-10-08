"""Complete acquisition sequencing, strict source admission and canonical byte accounting."""

import hashlib
from dataclasses import replace

import pytest
from autocad_mcp.adapter.fake_context import FakeContextAutoCADAdapter, StaticContextAdapterProvider
from autocad_mcp.context.builder import CompleteSnapshotRequest, SnapshotBuilder, SnapshotBuildError
from autocad_mcp.context.relationships import RelationshipOptions
from autocad_mcp.context.repository import InMemorySnapshotRepository
from autocad_mcp.context.serialization import record_to_json, record_to_payload
from autocad_mcp.context.validation import ContextValidationError

from tests.adapter.test_context_protocol import ALL, fixture_records
from tests.adapter.test_fake_context import CLOCK, SECRET

REQUEST = CompleteSnapshotRequest("1.0", RelationshipOptions())


def sparse_raw(count):
    document, records = fixture_records()
    base = next(item for item in records if item.handle == "10")
    values = tuple(
        replace(
            base,
            handle=f"{i+1:X}",
            object_id=i + 1,
            geometry={"kind": "point", "position": {"x": i * 10, "y": 0, "z": 0}},
            object_name="AcDbPoint",
            dxf_name="POINT",
            bounds=(i * 10, 0, 0, i * 10 + 1, 1, 1),
            block=None,
            issues=(),
        )
        for i in range(count)
    )
    return document, values


def build_fake(count=1, **bounds):
    document, values = sparse_raw(count)
    adapter = FakeContextAutoCADAdapter(
        document=document, entities=values, clock=CLOCK, cursor_secret=SECRET
    )
    builder = SnapshotBuilder(StaticContextAdapterProvider(adapter), clock=CLOCK, **bounds)
    return builder, adapter


@pytest.mark.parametrize("count", [0, 1, 500, 501, 10000])
def test_true_complete_counts_exact_sequence_all_coverage_and_repository_admission(count):
    builder, adapter = build_fake(count)
    result = builder.build(REQUEST)
    assert (
        len(result.entities)
        == result.materialization.entity_count
        == result.fingerprint.entity_count
        == count
    )
    calls = [name for name, _ in adapter.calls]
    assert calls[:2] == ["read_document_revision", "read_document_context"]
    assert calls[-2:] == ["read_document_context", "read_document_revision"]
    for name, current in adapter.calls:
        if name == "read_entity_page":
            assert current.include == ALL and not current.spaces and not current.handles
    payload = record_to_payload(result)
    declared = payload["materialization"].pop("canonical_byte_count")
    assert declared == len(record_to_json(payload).encode())
    token = adapter.read_document_revision()
    assert (
        result.materialization.revision_token_digest
        == "sha256:" + hashlib.sha256(record_to_json(token).encode()).hexdigest()
    )
    repository = InMemorySnapshotRepository(clock=CLOCK)
    repository.put_complete(result)
    assert (
        repository.get_complete(result.snapshot_id, session_id=result.document.session_document_id)
        == result
    )


@pytest.mark.parametrize(
    "limits",
    [
        {"max_entities": 0},
        {"max_entities": True},
        {"max_entities": 10001},
        {"max_relationships": 100001},
        {"max_snapshot_bytes": 33554433},
        {"adapter_page_size": 501},
    ],
)
def test_constructor_cannot_raise_or_disable_published_ceilings(limits):
    with pytest.raises((ContextValidationError, ValueError)):
        build_fake(**limits)


@pytest.mark.parametrize(
    "defect",
    [
        "partial",
        "token",
        "duplicate",
        "repeated",
        "empty-nonfinal",
        "session",
        "context-final",
        "token-final",
        "missing-token",
    ],
)
def test_invalid_source_never_fingerprints_or_returns_partial_snapshot(monkeypatch, defect):
    import autocad_mcp.context.builder as module

    builder, adapter = build_fake(501)
    original_page = adapter.read_entity_page
    original_context = adapter.read_document_context
    seen = {"pages": 0, "contexts": 0, "tokens": 0}

    def page(request):
        value = original_page(request)
        seen["pages"] += 1
        if defect == "partial":
            return replace(value, partial=True)
        if defect == "token":
            return replace(
                value, revision_token=replace(value.revision_token, opaque_value="changed")
            )
        if defect == "duplicate":
            return replace(value, entities=(value.entities[0],) * len(value.entities))
        if defect == "repeated":
            return replace(value, next_cursor="fixed-repeated")
        if defect == "empty-nonfinal":
            return replace(value, entities=(), next_cursor="nonfinal")
        return value

    def context():
        value = original_context()
        seen["contexts"] += 1
        if defect == "session":
            return replace(value, identity=replace(value.identity, session_document_id="different"))
        if defect == "context-final" and seen["contexts"] == 2:
            return replace(value, active_layout_name="changed")
        return value

    original_token = adapter.read_document_revision

    def token():
        seen["tokens"] += 1
        if defect == "missing-token":
            return None
        value = original_token()
        return (
            replace(value, opaque_value="changed")
            if defect == "token-final" and seen["tokens"] == 2
            else value
        )

    monkeypatch.setattr(adapter, "read_entity_page", page)
    monkeypatch.setattr(adapter, "read_document_context", context)
    monkeypatch.setattr(adapter, "read_document_revision", token)
    monkeypatch.setattr(
        module,
        "build_drawing_fingerprint",
        lambda *args: pytest.fail("Refused materialization reached fingerprint"),
    )
    with pytest.raises(SnapshotBuildError):
        builder.build(REQUEST)


def test_10001_entity_and_lower_byte_ceiling_fail_before_snapshot(monkeypatch):
    import autocad_mcp.context.builder as module

    builder, _ = build_fake(10001)
    monkeypatch.setattr(
        module,
        "build_drawing_fingerprint",
        lambda *args: pytest.fail("Overflow reached fingerprint"),
    )
    with pytest.raises(SnapshotBuildError) as error:
        builder.build(REQUEST)
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"
    builder, _ = build_fake(1, max_snapshot_bytes=1)
    with pytest.raises(SnapshotBuildError) as error:
        builder.build(REQUEST)
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"


def test_exact_full_byte_boundary_one_over_and_complete_graph_placement():
    builder, _ = build_fake(2)
    value = builder.build(REQUEST)
    exact = len(record_to_json(value).encode())
    builder, _ = build_fake(2, max_snapshot_bytes=exact)
    assert builder.build(REQUEST) == value
    builder, _ = build_fake(2, max_snapshot_bytes=exact - 1)
    with pytest.raises(SnapshotBuildError) as error:
        builder.build(REQUEST)
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"
