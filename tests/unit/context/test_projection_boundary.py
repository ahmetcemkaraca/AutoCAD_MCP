"""Projected response facts cannot masquerade as complete entity/drawing state."""

from dataclasses import replace

import pytest
from autocad_mcp.context.fingerprint import build_drawing_fingerprint, entity_state_digest
from autocad_mcp.context.models import CapabilityIssue, EntityContext
from autocad_mcp.context.pagination import SystemClock
from autocad_mcp.context.repository import InMemorySnapshotRepository, SnapshotRepositoryError
from autocad_mcp.context.serialization import record_to_json, record_to_payload
from autocad_mcp.context.validation import ContextValidationError, record_from_payload

from tests.unit.context.fixtures import snapshot
from tests.unit.context.test_repository import complete, unchecked


def projected(entity: EntityContext, group: str) -> EntityContext:
    issue = CapabilityIssue("NOT_REQUESTED", group, entity.identity.handle, None, "Omitted", False)
    return replace(
        entity,
        capability_issues=(issue,),
        geometry=None if group == "geometry" else entity.geometry,
        text=None if group == "text" else entity.text,
    )


def test_marked_geometry_projection_roundtrips_without_changing_source_state() -> None:
    original = snapshot().entities[0]
    original = replace(original, state_digest=entity_state_digest(original))
    partial = projected(original, "geometry")
    payload = record_to_payload(partial)
    assert payload["geometry"] is None
    assert partial.state_digest == original.state_digest
    assert record_from_payload(EntityContext, payload) == partial
    assert original.geometry is not None and original.capability_issues == ()


def test_null_geometry_needs_its_explicit_projection_marker() -> None:
    original = snapshot().entities[0]
    for issues in ((), (CapabilityIssue("NOT_REQUESTED", "text", "A1", None, "Omitted", False),)):
        with pytest.raises(ContextValidationError):
            replace(original, geometry=None, capability_issues=issues)


@pytest.mark.parametrize("group", ["geometry", "text", "visual_style"])
def test_projection_is_refused_by_complete_model_and_digest_boundaries(group: str) -> None:
    whole = snapshot()
    partial = projected(whole.entities[0], group)
    for operation in (
        lambda: replace(whole, entities=(partial,)),
        lambda: entity_state_digest(partial),
        lambda: build_drawing_fingerprint(
            whole.document, whole.units, whole.tolerance, whole.active_context, (partial,), ()
        ),
    ):
        with pytest.raises(ContextValidationError) as error:
            operation()
        assert error.value.code == "SNAPSHOT_INCOMPLETE"


def test_repository_rejects_forged_complete_projection_even_with_correct_counts_and_bytes() -> None:
    original = complete()
    partial = projected(original.entities[0], "text")
    forged = unchecked(original, entities=(partial,))
    payload = record_to_payload(forged)
    del payload["materialization"]["canonical_byte_count"]
    measured = len(record_to_json(payload).encode("utf-8"))
    forged = unchecked(
        forged, materialization=replace(forged.materialization, canonical_byte_count=measured)
    )
    repository = InMemorySnapshotRepository(clock=SystemClock())
    with pytest.raises(SnapshotRepositoryError) as error:
        repository.put_complete(forged)
    assert error.value.code == "SNAPSHOT_INCOMPLETE"
    repository.put_complete(original)
    assert repository.get_complete(original.snapshot_id) == original


def test_complete_snapshot_refuses_top_level_projection_markers() -> None:
    with pytest.raises(ContextValidationError) as error:
        replace(
            snapshot(),
            capability_issues=(
                CapabilityIssue("NOT_REQUESTED", "text", None, None, "Omitted", False),
            ),
        )
    assert error.value.code == "SNAPSHOT_INCOMPLETE"


def test_drawing_fingerprint_refuses_top_level_projection_markers() -> None:
    whole = snapshot()
    issue = CapabilityIssue("NOT_REQUESTED", "text", None, None, "Omitted", False)
    with pytest.raises(ContextValidationError) as error:
        build_drawing_fingerprint(
            whole.document, whole.units, whole.tolerance, whole.active_context,
            whole.entities, (issue,),
        )
    assert error.value.code == "SNAPSHOT_INCOMPLETE"
