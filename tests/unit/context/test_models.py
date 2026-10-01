"""Strict constructor, immutability, evidence, and field-limit tests."""

from dataclasses import FrozenInstanceError, replace

import pytest
from autocad_mcp.context.models import (
    BlockFacts,
    Bounds3D,
    EntityIdentity,
    EntityQueryFilters,
    EntitySpace,
    GeometrySummary,
    LayerSummary,
    PageInfo,
    Point3D,
    PolylineGeometry,
    SemanticEvidenceRef,
    SemanticInterpretation,
    TextFacts,
)
from autocad_mcp.context.validation import ContextValidationError

from tests.unit.context.fixtures import snapshot


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -float("inf"), 1e15 + 1])
def test_coordinates_reject_bool_non_numeric_non_finite_and_over_bound(value):
    with pytest.raises(ContextValidationError):
        Point3D(value, 0, 0)


def test_coordinate_boundary_and_inverted_bounds():
    point = Point3D(1e15, -1e15, 0)
    assert point.x == 1e15
    with pytest.raises(ContextValidationError):
        Bounds3D(point, Point3D(0, 0, 0))


def test_handle_normalization_and_session_scoping():
    assert EntityIdentity("aF", 42, "session", "AcDbLine", "LINE").handle == "AF"
    for handle in ("0xAF", "", "-1", "GG", " AF ", 42):
        with pytest.raises(ContextValidationError):
            EntityIdentity(handle, None, None, "AcDbLine", None)
    with pytest.raises(ContextValidationError):
        EntityIdentity("A", 42, None, "AcDbLine", None)


def test_nested_input_is_copied_and_frozen():
    values = {"TAG": "original"}
    block = BlockFacts("fixture", "b", values, False)
    values["TAG"] = "changed"
    assert block.attribute_values["TAG"] == "original"
    with pytest.raises(TypeError):
        block.attribute_values["TAG"] = "mutated"
    vertices = [Point3D(0, 0, 0)]
    geometry = PolylineGeometry("polyline", vertices, [0.0], False)
    vertices.clear()
    assert geometry.vertices == (Point3D(0, 0, 0),)
    with pytest.raises(FrozenInstanceError):
        geometry.closed = True
    assert not hasattr(geometry, "__dict__")


@pytest.mark.parametrize("count", [10000, 10001])
def test_vertex_limit_is_inclusive(count):
    if count == 10000:
        assert (
            len(PolylineGeometry("polyline", (Point3D(0, 0, 0),) * count, (), False).vertices)
            == count
        )
    else:
        with pytest.raises(ContextValidationError) as error:
            PolylineGeometry("polyline", (Point3D(0, 0, 0),) * count, (), False)
        assert error.value.code == "PAYLOAD_LIMIT"


def test_filters_reject_duplicates_and_enforce_cardinality_and_length():
    filters = EntityQueryFilters((), (), (), (), (), ("a",), None)
    assert filters.handles == ("A",)
    for handles in (("a", "A"), tuple(format(i, "X") for i in range(257))):
        with pytest.raises(ContextValidationError):
            replace(filters, handles=handles)
    for changes in ({"layer_names": ("x" * 129,)}, {"layout_names": ("x",) * 65}):
        with pytest.raises(ContextValidationError):
            replace(filters, **changes)


def test_confirmation_inference_unknown_and_fact_pointer_rules():
    confirmation = SemanticEvidenceRef("user-1", "user_confirmation", None, "confirmed")
    fact = SemanticEvidenceRef("cad-1", "cad_fact", "/entities/A1/geometry/start", None)
    accepted = SemanticInterpretation(
        "i-1", ("a1",), "candidate", "confirmed", None, (confirmation,)
    )
    assert accepted.subject_handles == ("A1",)
    assert (
        SemanticInterpretation("i-2", ("A1",), "candidate", "inferred", 1.0, (fact,)).confidence
        == 1
    )
    for changes in (
        {"evidence": ()},
        {"state": "inferred", "confidence": None},
        {"state": "inferred", "confidence": 1.01},
        {"state": "unknown", "confidence": 0.5},
    ):
        with pytest.raises(ContextValidationError):
            replace(accepted, **changes)
    for pointer in (None, "/geometry", "/entities/A1"):
        with pytest.raises(ContextValidationError):
            SemanticEvidenceRef("cad", "cad_fact", pointer, None)


def test_field_bounds_for_text_block_and_page():
    assert len(TextFacts("x" * 65536, None, None, None, None, None).plain_text) == 65536
    with pytest.raises(ContextValidationError):
        TextFacts("x" * 65537, None, None, None, None, None)
    with pytest.raises(ContextValidationError):
        BlockFacts("fixture", None, {str(i): "x" for i in range(513)}, None)
    assert PageInfo(500, 500, False, None).returned == 500
    for args in (
        (501, 0, False, None),
        (1, 2, False, None),
        (1, 1, True, None),
        (1, 1, False, "cursor"),
        (True, 0, False, None),
    ):
        with pytest.raises(ContextValidationError):
            PageInfo(*args)


def test_entity_limit_counts_utf8_bytes_and_reports_handle():
    entity = snapshot().entities[0]
    assert replace(entity, text=TextFacts("x" * 65536, None, None, None, None, None))
    with pytest.raises(ContextValidationError) as error:
        replace(entity, text=TextFacts("😀" * 65536, None, None, None, None, None))
    assert error.value.code == "PAYLOAD_LIMIT"
    assert error.value.details["entity_handle"] == "A1"
    assert error.value.details["measured_bytes"] > 256 * 1024


def test_summary_value_types_preserve_nested_projection():
    assert LayerSummary("0").name == "0"
    assert GeometrySummary("line").kind == "line"
    with pytest.raises(ContextValidationError):
        GeometrySummary("made_up")


def test_entity_byte_limit_accepts_exact_boundary_and_rejects_one_byte_over():
    from autocad_mcp.context.serialization import record_to_json

    entity = snapshot().entities[0]
    # ASCII attribute values make byte accounting exact without changing text limits.
    blank = replace(entity, block=BlockFacts("fixture", None, {str(i): "" for i in range(4)}, None))
    baseline = len(record_to_json(blank).encode("utf-8"))
    remaining = 256 * 1024 - baseline
    attrs = {str(i): "x" * min(65536, max(0, remaining - 65536 * i)) for i in range(4)}
    exact = replace(entity, block=BlockFacts("fixture", None, attrs, None))
    assert len(record_to_json(exact).encode("utf-8")) == 256 * 1024
    attrs["3"] += "x"
    with pytest.raises(ContextValidationError) as error:
        replace(entity, block=BlockFacts("fixture", None, attrs, None))
    assert error.value.details["measured_bytes"] == 256 * 1024 + 1


def test_optional_payload_limit_preserves_structured_error():
    from autocad_mcp.context.models import EntityContext
    from autocad_mcp.context.serialization import record_to_payload
    from autocad_mcp.context.validation import record_from_payload

    payload = record_to_payload(snapshot().entities[0])
    payload["text"] = {
        "plain_text": "x" * 65537,
        "raw_text": None,
        "style_name": None,
        "height": None,
        "rotation_radians": None,
        "insertion": None,
    }
    with pytest.raises(ContextValidationError) as error:
        record_from_payload(EntityContext, payload)
    assert error.value.code == "PAYLOAD_LIMIT"


def test_optional_scalar_rejects_boolean_and_nonfinite():
    for value in (True, float("nan"), float("inf"), 1e15 + 1):
        with pytest.raises(ContextValidationError):
            TextFacts("fixture", None, None, value, None, None)


def test_cad_fact_pointer_requires_valid_json_pointer_escaping():
    for pointer in ("/entities/A1/geometry/~2x", "/entities/A1/geometry/~", "/entities/A1/"):
        with pytest.raises(ContextValidationError):
            SemanticEvidenceRef("cad", "cad_fact", pointer, None)
    ref = SemanticEvidenceRef("cad", "cad_fact", "/entities/A1/block/attribute_values/A~1B", None)
    assert ref.kind == "cad_fact"


def test_cursor_limit_counts_bytes():
    assert PageInfo(1, 1, True, "é" * 1024).has_more
    with pytest.raises(ContextValidationError):
        PageInfo(1, 1, True, "é" * 1025)


def test_literal_glob_brackets_are_not_interpreted_as_character_classes():
    filters = EntityQueryFilters((), (), (), (), ("layer[1]",), (), None)
    assert filters.layer_globs == ("layer[1]",)


def test_complete_relationship_bound_is_enforced():
    from autocad_mcp.context.models import RelationshipFact

    complete = snapshot()
    entity = replace(
        complete.entities[0],
        relationships=(RelationshipFact("parallel", "A1", "B1", None, 0),) * 100,
    )
    assert len(replace(complete, entities=(entity,) * 1000).entities) == 1000
    with pytest.raises(ContextValidationError) as error:
        replace(complete, entities=(entity,) * 1001)
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"


def test_relationship_and_filter_limits_accept_exact_boundaries():
    from autocad_mcp.context.models import RelationshipFact

    entity = snapshot().entities[0]
    relationship = RelationshipFact("endpoint_touches", "a1", "b1", 0.01, 0)
    assert relationship.source_handle == "A1"
    assert len(replace(entity, relationships=(relationship,) * 100).relationships) == 100
    with pytest.raises(ContextValidationError):
        replace(entity, relationships=(relationship,) * 101)
    handles = tuple(format(i, "X") for i in range(256))
    filters = EntityQueryFilters(
        ("model", "paper", "block_definition"),
        ("x" * 128,) * 64,
        ("LINE",) * 64,
        ("0",) * 64,
        ("*",) * 64,
        handles,
        None,
    )
    assert len(filters.handles) == 256
    assert (
        len(BlockFacts("fixture", None, {str(i): "x" for i in range(512)}, None).attribute_values)
        == 512
    )


def test_boolean_cannot_impersonate_complete_marker():
    complete = snapshot()
    for invalid in (1, False, None):
        with pytest.raises(ContextValidationError):
            replace(complete.fingerprint, complete=invalid)
        with pytest.raises(ContextValidationError):
            replace(complete.materialization, complete=invalid)


def test_model_does_not_retain_nested_json_containers():
    from autocad_mcp.context.models import DrawingSnapshot
    from autocad_mcp.context.validation import record_from_payload

    from tests.unit.context.fixtures import snapshot_payload

    payload = snapshot_payload()
    result = record_from_payload(DrawingSnapshot, payload)
    payload["entities"][0]["block"]["attribute_values"]["KEY"] = "changed"
    payload["entities"].clear()
    assert len(result.entities) == 1
    assert result.entities[0].block.attribute_values["KEY"] == "VALUE"
    assert result.entities[0].style.true_color_rgb == (12, 34, 56)


@pytest.mark.parametrize(
    "kind, layout, owner",
    [
        ("model", None, None),
        ("model", "Modèle", "a1"),
        ("paper", "Layout A", None),
        ("paper", "Layout A", "a1"),
        ("block_definition", None, "a1"),
    ],
)
def test_owner_space_accepts_observed_layouts_and_normalized_ownership(kind, layout, owner):
    space = EntitySpace(kind, layout, owner)
    assert space.layout_name == layout
    assert space.owner_block_handle == (owner.upper() if owner else None)


@pytest.mark.parametrize(
    "kind, layout, owner",
    [
        ("paper", None, None),
        ("paper", "", "A1"),
        ("block_definition", None, None),
        ("block_definition", "Layout A", "A1"),
        ("block_definition", "", "A1"),
    ],
)
@pytest.mark.parametrize("decode", [False, True])
def test_owner_space_rejects_missing_or_conflicting_frame_identity(kind, layout, owner, decode):
    from autocad_mcp.context.validation import record_from_payload

    with pytest.raises(ContextValidationError) as error:
        if decode:
            record_from_payload(
                EntitySpace, {"kind": kind, "layout_name": layout, "owner_block_handle": owner}
            )
        else:
            EntitySpace(kind, layout, owner)
    assert error.value.code == "INVALID_ARGUMENT"
