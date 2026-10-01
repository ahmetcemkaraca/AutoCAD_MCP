"""Complete mapping preserves owner facts and refuses partial source digests."""

from dataclasses import replace

import pytest
from autocad_mcp.adapter.context_protocol import AdapterContextIssue, ContextInclude
from autocad_mcp.context.adapter_reader import map_document_context, map_entity_context
from autocad_mcp.context.fingerprint import entity_state_digest
from autocad_mcp.context.identity import build_document_identity
from autocad_mcp.context.serialization import record_to_payload
from autocad_mcp.context.validation import ContextValidationError

from tests.adapter.test_context_protocol import fixture_records, request
from tests.adapter.test_fake_context import fake


def test_fixture_maps_all_complete_groups_document_and_two_session_identity():
    document, entities = fixture_records()
    later, records = fixture_records(1)
    assert (
        build_document_identity(document.identity).document_id
        == build_document_identity(later.identity).document_id
    )
    assert "full_path" not in record_to_payload(build_document_identity(document.identity))
    active = map_document_context(document)
    assert active.space.active_layout_name == "Model" and active.ucs.origin_wcs.x == 0
    mapped = {entity.handle: map_entity_context(entity) for entity in entities}
    assert mapped["10"].geometry.kind == "line" and mapped["20"].geometry.kind == "circle"
    assert (
        mapped["30"].geometry.kind == "lwpolyline"
        and mapped["40"].block.attribute_values["KEY"] == "VALUE"
    )
    assert (
        mapped["50"].text.plain_text == "Synthetic label"
        and mapped["60"].dimension.measurement == 5
    )
    assert mapped["20"].style.visible is None and mapped["20"].capability_issues
    assert not mapped["20"].capability_issues[0].required
    for raw in records:
        entity = map_entity_context(raw)
        assert entity.state_digest == mapped[raw.handle].state_digest == entity_state_digest(entity)
        assert entity.fact_evidence and all(
            item.source == "autocad_com" for item in entity.fact_evidence
        )
    assert any(
        item.status == "unavailable" and item.fact_path == "/style/visible"
        for item in mapped["20"].fact_evidence
    )


@pytest.mark.parametrize(
    "geometry",
    [
        {
            "kind": "arc",
            "center": {"x": 0, "y": 0, "z": 0},
            "normal": {"x": 0, "y": 0, "z": 1},
            "radius": 2,
            "start_angle_radians": 0,
            "end_angle_radians": 1,
        },
        {"kind": "point", "position": {"x": 0, "y": 0, "z": 0}},
        {
            "kind": "polyline",
            "vertices": [{"x": 0, "y": 0, "z": 0}, {"x": 1, "y": 1, "z": 1}],
            "bulges": [],
            "closed": False,
        },
    ],
)
def test_other_supported_geometry_families(geometry):
    _, entities = fixture_records()
    entity = map_entity_context(replace(entities[0], geometry=geometry, issues=()))
    assert entity.geometry.kind == geometry["kind"]


def test_missing_required_supported_geometry_and_projection_refuse_mapping():
    _, entities = fixture_records()
    raw = entities[0]
    broken = replace(raw, geometry={"kind": "line", "start": {"x": 0, "y": 0, "z": 0}}, issues=())
    with pytest.raises(ContextValidationError):
        map_entity_context(broken)
    for group in ("geometry", "bounding_box", "visual_style", "block", "text", "dimension"):
        issue = AdapterContextIssue("NOT_REQUESTED", group, None, raw.handle, "Omitted")
        with pytest.raises(ContextValidationError) as error:
            map_entity_context(replace(raw, issues=(issue,)))
        assert error.value.code == "SNAPSHOT_INCOMPLETE"
    partial = fake().read_entity_page(
        request(include=ContextInclude(False, False, False, False, False, False))
    )
    assert all(map_entity_context(item).geometry is not None for item in partial.entities)


def test_optional_unavailable_member_missing_key_is_explicit_and_bounds_owner_preserved():
    _, entities = fixture_records()
    raw = next(x for x in entities if x.handle == "20")
    style = dict(raw.style)
    del style["visible"]
    mapped = map_entity_context(replace(raw, style=style))
    assert mapped.style.visible is None and mapped.capability_issues
    with pytest.raises(ContextValidationError):
        map_entity_context(replace(raw, style=style, issues=()))
    definition = replace(
        raw, space_kind="block_definition", layout_name=None, owner_block_handle="B1"
    )
    mapped = map_entity_context(definition)
    assert mapped.space.owner_block_handle == "B1" and mapped.bounds.minimum.x == 0


def test_missing_optional_fact_issue_must_bind_entity_and_capability_member():
    _, entities = fixture_records()
    raw = next(item for item in entities if item.handle == "20")
    style = dict(raw.style)
    del style["visible"]
    wrong = replace(raw.issues[0], entity_handle="A1")
    with pytest.raises(ContextValidationError):
        map_entity_context(replace(raw, style=style, issues=(wrong,)))
    whole_operation = replace(raw.issues[0], entity_handle=None)
    assert (
        map_entity_context(replace(raw, style=style, issues=(whole_operation,))).style.visible
        is None
    )


def test_unavailable_evidence_is_scoped_to_capability_and_entity_not_global_member_name():
    _, entities = fixture_records()
    raw = next(item for item in entities if item.handle == "50")
    issue = AdapterContextIssue(
        "MEMBER_UNAVAILABLE", "text", "StyleName", raw.handle, "Unavailable"
    )
    text = dict(raw.text, style_name=None)
    dimension = {
        "measurement": 5,
        "dimension_text": None,
        "style_name": "SyntheticDim",
        "text_position": None,
    }
    mapped = map_entity_context(
        replace(raw, text=text, dimension=dimension, issues=raw.issues + (issue,))
    )
    evidence = {item.fact_path: item for item in mapped.fact_evidence}
    assert evidence["/text/style_name"].status == "unavailable"
    assert evidence["/dimension/style_name"].status == "observed"
    foreign = replace(issue, entity_handle="A1")
    mapped = map_entity_context(replace(raw, text=text, issues=raw.issues + (foreign,)))
    assert (
        next(item for item in mapped.fact_evidence if item.fact_path == "/text/style_name").status
        == "observed"
    )


def test_bad_geometry_kind_and_known_family_demotion_fail_structured():
    _, entities = fixture_records()
    raw = next(item for item in entities if item.handle == "10")
    for geometry in ({"kind": []}, {"kind": "unsupported", "object_name": raw.object_name}):
        issue = AdapterContextIssue(
            "UNSUPPORTED_CAPABILITY", "geometry", None, raw.handle, "Unavailable"
        )
        with pytest.raises(ContextValidationError):
            map_entity_context(replace(raw, geometry=geometry, issues=(issue,)))


def test_block_scale_and_definition_provenance_names_actual_planned_activex_members():
    _, entities = fixture_records()
    raw = next(item for item in entities if item.handle == "40")
    evidence = {item.fact_path: item.member for item in map_entity_context(raw).fact_evidence}
    assert evidence["/geometry/scale_xyz/x"] == "XScaleFactor"
    assert evidence["/geometry/scale_xyz/y"] == "YScaleFactor"
    assert evidence["/geometry/scale_xyz/z"] == "ZScaleFactor"
    assert evidence["/block/definition_handle"] == "Blocks.Item(Name).Handle"


@pytest.mark.parametrize("issue_handle", ["A1", "50", None])
def test_unknown_proxy_geometry_issue_requires_same_entity_or_whole_operation(issue_handle):
    _, entities = fixture_records()
    raw = next(item for item in entities if item.handle == "50")
    issue = AdapterContextIssue(
        "UNSUPPORTED_CAPABILITY", "geometry", None, issue_handle, "Synthetic proxy geometry"
    )
    raw = replace(
        raw,
        object_name="AcDbProxyEntity",
        geometry={"kind": "unsupported", "object_name": "AcDbProxyEntity"},
        issues=(issue,),
    )
    if issue_handle == "A1":
        with pytest.raises(ContextValidationError) as error:
            map_entity_context(raw)
        assert error.value.code == "UNSUPPORTED_CAPABILITY"
    else:
        mapped = map_entity_context(raw)
        assert mapped.geometry.kind == "unsupported"
        assert mapped.geometry.object_name == "AcDbProxyEntity"
        assert mapped.state_digest == entity_state_digest(mapped)
