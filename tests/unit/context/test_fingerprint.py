"""Canonical independent vectors and full-set drawing identity invariants."""

import json
from dataclasses import replace

import pytest
from autocad_mcp.context.fingerprint import (
    build_drawing_fingerprint,
    canonical_bytes,
    entity_state_digest,
    snapshot_id,
    snapshot_identity_bytes,
)
from autocad_mcp.context.models import (
    CadFactEvidence,
    CapabilityIssue,
    EntitySpace,
    RelationshipFact,
)
from autocad_mcp.context.validation import ContextValidationError

from tests.unit.context.fixtures import snapshot


def fingerprint(complete, entities=None, issues=()):
    return build_drawing_fingerprint(
        complete.document,
        complete.units,
        complete.tolerance,
        complete.active_context,
        complete.entities if entities is None else entities,
        issues,
    )


def test_canonical_float_numeric_tokens_nfc_booleans_and_sorting():
    assert canonical_bytes({"z": True, "a": [0.1, -0.0, 1.0, "cafe\u0301"]}) == (
        b'{"a":[0.10000000000000001,0,1,"caf\xc3\xa9"],"z":true}'
    )
    assert canonical_bytes(1e-7) == format(1e-7, ".17g").encode()
    assert canonical_bytes(1e15) == b"1000000000000000"
    assert json.loads(canonical_bytes({"float": 0.1}))["float"] == 0.1


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), {"é": 1, "e\u0301": 2}, {1: "bad-key"}, object()],
)
def test_canonical_rejects_nonfinite_collision_and_non_json(value):
    with pytest.raises(ContextValidationError):
        canonical_bytes(value)


def test_complete_set_order_and_reopen_object_ids_do_not_change_identity():
    complete = snapshot()
    first = complete.entities[0]
    second = replace(first, identity=replace(first.identity, handle="10"))
    before = fingerprint(complete, (first, second))
    reopened = replace(first, identity=replace(first.identity, object_id=987))
    after = fingerprint(
        replace(
            complete, document=replace(complete.document, session_document_id="different-session")
        ),
        (second, reopened),
    )
    assert before == after
    assert before.entity_count == 2 and before.complete is True and not before.incomplete_reasons
    assert snapshot_id(complete.document, before) == snapshot_id(complete.document, after)
    assert entity_state_digest(first) == entity_state_digest(reopened)
    assert fingerprint(complete, (first,)) != before


def test_content_vs_presentation_and_viewport_object_id_exclusion():
    complete = snapshot()
    base = fingerprint(complete)
    for context in (
        replace(complete.active_context, view=replace(complete.active_context.view, width=200)),
        replace(complete.active_context, ucs=replace(complete.active_context.ucs, name="other")),
        replace(
            complete.active_context,
            space=replace(complete.active_context.space, active_layout_name="Layout2"),
        ),
    ):
        changed = fingerprint(replace(complete, active_context=context))
        assert changed.content_digest == base.content_digest
        assert changed.presentation_digest != base.presentation_digest
    viewport = replace(
        complete.active_context.space, viewport_object_id=999, viewport_object_id_scope="session"
    )
    assert (
        fingerprint(
            replace(complete, active_context=replace(complete.active_context, space=viewport))
        )
        == base
    )


def test_nested_facts_change_content_and_entity_state_but_metadata_does_not():
    complete = snapshot()
    entity = complete.entities[0]
    base = fingerprint(complete)
    for changed in (
        replace(
            entity,
            geometry=replace(entity.geometry, end=replace(entity.geometry.end, x=99)),
        ),
        replace(entity, block=replace(entity.block, attribute_values={"KEY": "changed"})),
        replace(entity, layer=replace(entity.layer, is_locked=True)),
        replace(entity, style=replace(entity.style, color_index=1)),
    ):
        assert fingerprint(complete, (changed,)).content_digest != base.content_digest
        assert entity_state_digest(changed) != entity_state_digest(entity)
    derived = replace(entity, state_digest="sha256:" + "0" * 64)
    assert fingerprint(complete, (derived,)) == base
    issue = CapabilityIssue("UNAVAILABLE", "text", "A1", "TextString", "message", False)
    assert fingerprint(complete, issues=(issue,)) == fingerprint(
        complete, issues=(replace(issue, message="different localized message"),)
    )


def test_relationship_order_affects_content_not_entity_state():
    complete = snapshot()
    entity = complete.entities[0]
    first = RelationshipFact("parallel", "A1", "A2", 0.01, None)
    second = RelationshipFact("same_owner", "A1", "A3", None, None)
    changed = replace(entity, relationships=(first, second))
    reverse = replace(entity, relationships=(second, first))
    assert fingerprint(complete, (changed,)) == fingerprint(complete, (reverse,))
    assert fingerprint(complete, (changed,)) != fingerprint(complete)
    assert entity_state_digest(entity) == entity_state_digest(changed)
    changed_evidence = replace(
        entity,
        fact_evidence=(
            CadFactEvidence("/geometry/start", "autocad_com", "StartPoint", "unavailable"),
        ),
    )
    assert fingerprint(complete, (changed_evidence,)) != fingerprint(complete)


def test_snapshot_identity_excludes_session_time_revision_but_retains_underlying_facts():
    complete = snapshot()
    base = snapshot_identity_bytes(complete)
    changed = replace(
        complete,
        captured_at=complete.captured_at.replace(year=2025),
        reference=replace(complete.reference, session_id="other-session"),
        document=replace(complete.document, session_document_id="other-session"),
        materialization=replace(
            complete.materialization, revision_token_digest="sha256:" + "0" * 64
        ),
        entities=(
            replace(
                complete.entities[0], identity=replace(complete.entities[0].identity, object_id=999)
            ),
        ),
    )
    assert snapshot_identity_bytes(changed) == base
    forged = replace(
        complete,
        entities=(
            replace(
                complete.entities[0], layer=replace(complete.entities[0].layer, name="altered")
            ),
        ),
    )
    assert forged.snapshot_id == complete.snapshot_id and forged.fingerprint == complete.fingerprint
    assert snapshot_identity_bytes(forged) != base
    assert snapshot_id(complete.document, complete.fingerprint).startswith("ds1_")


def test_fingerprinting_refuses_duplicate_handles_required_issues_and_incomplete_count():
    complete = snapshot()
    for entities, issues in (
        (complete.entities * 2, ()),
        (complete.entities, (CapabilityIssue("MISSING", "geometry", None, None, "missing", True),)),
    ):
        with pytest.raises(ContextValidationError):
            fingerprint(complete, entities, issues)


def test_shuffled_full_sets_issues_and_nfc_facts_have_stable_digests():
    import random

    complete = snapshot()
    entity = complete.entities[0]
    entities = [
        replace(entity, identity=replace(entity.identity, handle=f"{index:X}"))
        for index in range(1, 101)
    ]
    issues = (
        CapabilityIssue("A", "text", None, "TextString", "first", False),
        CapabilityIssue("B", "block", None, "Name", "second", False),
    )
    expected = fingerprint(complete, entities, issues)
    random.Random(42).shuffle(entities)  # noqa: S311 - deterministic test permutation
    assert fingerprint(complete, entities, issues[::-1]) == expected
    nfc = replace(entity, layer=replace(entity.layer, name="café"))
    decomposed = replace(entity, layer=replace(entity.layer, name="cafe\u0301"))
    assert entity_state_digest(nfc) == entity_state_digest(decomposed)
    assert fingerprint(complete, (nfc,)) == fingerprint(complete, (decomposed,))
    with pytest.raises(ContextValidationError) as error:
        fingerprint(complete, complete.entities * 10001)
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"


def test_all_nested_covered_entity_facts_and_units_tolerance_change_content():
    from autocad_mcp.context.models import DimensionFacts, TextFacts

    complete = snapshot()
    entity = complete.entities[0]
    before = fingerprint(complete)
    for changed in (
        replace(entity, space=replace(entity.space, owner_block_handle="B2")),
        replace(entity, text=TextFacts("observed text", None, None, None, None, None)),
        replace(entity, dimension=DimensionFacts(5.0, None, None, None)),
        replace(
            entity,
            bounds=replace(
                entity.bounds, maximum=replace(entity.bounds.maximum, z=1)
            ),
        ),
        replace(
            entity,
            capability_issues=(
                CapabilityIssue("OPTIONAL", "text", "A1", "TextString", "unavailable", False),
            ),
        ),
    ):
        assert fingerprint(complete, (changed,)).content_digest != before.content_digest
        assert snapshot_identity_bytes(replace(complete, entities=(changed,))) != (
            snapshot_identity_bytes(complete)
        )
    assert fingerprint(replace(complete, units=replace(complete.units, insunits_code=5))) != before
    assert (
        fingerprint(replace(complete, tolerance=replace(complete.tolerance, linear=0.02))) != before
    )
    shifted_context = replace(
        complete.active_context, view=replace(complete.active_context.view, twist_radians=0.2)
    )
    assert snapshot_identity_bytes(replace(complete, active_context=shifted_context)) != (
        snapshot_identity_bytes(complete)
    )


def test_equal_coordinates_in_distinct_owner_frames_have_distinct_fact_identities():
    complete = snapshot()
    entity = complete.entities[0]
    frames = (
        EntitySpace("model", None, None),
        EntitySpace("paper", "Layout A", None),
        EntitySpace("paper", "Layout B", None),
        EntitySpace("block_definition", None, "B1"),
        EntitySpace("block_definition", None, "B2"),
    )
    values = tuple(replace(entity, space=space) for space in frames)
    assert all(value.geometry == entity.geometry for value in values)
    assert len({entity_state_digest(value) for value in values}) == len(frames)
    assert len({fingerprint(complete, (value,)).content_digest for value in values}) == len(frames)
    assert len(
        {snapshot_identity_bytes(replace(complete, entities=(value,))) for value in values}
    ) == len(frames)
