"""Fixed complete relation policy, owner frames and deterministic resource admission."""

import math
from dataclasses import replace

import pytest
from autocad_mcp.context.models import (
    ArcGeometry,
    Bounds3D,
    EntitySpace,
    GeometryTolerance,
    LineGeometry,
    Point3D,
    PointGeometry,
    PolylineGeometry,
)
from autocad_mcp.context.relationships import RelationshipOptions, extract_relationships
from autocad_mcp.context.validation import ContextValidationError

from tests.unit.context.fixtures import snapshot


def fact(handle="1", *, geometry=None, bounds=None, owner=None, kind="model", layout=None):
    original = snapshot().entities[0]
    return replace(
        original,
        identity=replace(original.identity, handle=handle, object_id=1),
        space=EntitySpace(kind, layout, owner),
        geometry=geometry or PointGeometry("point", Point3D(0, 0, 0)),
        bounds=bounds,
        block=None,
        relationships=(),
    )


def box(a, b):
    return Bounds3D(Point3D(*a), Point3D(*b))


def triples(facts):
    return {(item.kind, item.source_handle, item.target_handle) for item in facts}


def test_options_exact_defaults_and_explicit_tolerance_no_hidden_policy():
    assert RelationshipOptions().tolerance == GeometryTolerance(1e-6, 1e-6, "drawing_units_default")
    value = GeometryTolerance(0.1, 0.2, "request_override")
    assert RelationshipOptions(value).tolerance is value
    with pytest.raises((ContextValidationError, TypeError)):
        RelationshipOptions(tolerance={"linear": 1})


def test_bbox_inclusive_containment_reciprocal_equal_boxes_and_orientation():
    a = fact("10", bounds=box((0, 0, 0), (2, 2, 2)))
    b = fact("2", bounds=box((1, 1, 1), (2, 2, 2)))
    result = extract_relationships((a, b), RelationshipOptions())
    assert triples(result) == {
        ("bbox_intersects", "2", "10"),
        ("bbox_contains", "10", "2"),
        ("bbox_within", "2", "10"),
    }
    equal = extract_relationships((a, replace(b, bounds=a.bounds)), RelationshipOptions())
    assert len(equal) == 5
    assert all(item.tolerance is None and item.measured_value is None for item in equal)
    touching = replace(b, bounds=box((2, 2, 2), (3, 3, 3)))
    assert ("bbox_intersects", "2", "10") in triples(
        extract_relationships((a, touching), RelationshipOptions())
    )


def test_frame_isolation_and_same_owner_unknown_metadata():
    same = box((0, 0, 0), (1, 1, 1))
    papers = (
        fact("1", bounds=same, kind="paper", layout="A"),
        fact("2", bounds=same, kind="paper", layout="B"),
    )
    assert not extract_relationships(papers, RelationshipOptions())
    definitions = (
        fact("1", bounds=same, kind="block_definition", owner="A"),
        fact("2", bounds=same, kind="block_definition", owner="B"),
    )
    assert not extract_relationships(definitions, RelationshipOptions())
    assert not extract_relationships((fact("1"), fact("2")), RelationshipOptions())
    distant = (
        fact("1", owner="A", bounds=same),
        fact("2", owner="A", bounds=box((1e9, 0, 0), (1e9 + 1, 1, 1))),
    )
    assert triples(extract_relationships(distant, RelationshipOptions())) == {
        ("same_owner", "1", "2")
    }
    normalized = (papers[0], replace(papers[1], space=EntitySpace("paper", "a", None)))
    assert len(extract_relationships(normalized, RelationshipOptions())) == 5


def test_endpoint_distance_and_distant_unoriented_parallel_with_zero_line_exclusion():
    a = fact("1", geometry=LineGeometry("line", Point3D(0, 0, 0), Point3D(1, 0, 0)))
    b = fact("2", geometry=LineGeometry("line", Point3D(1.001, 0, 0), Point3D(2, 1, 0)))
    opts = RelationshipOptions(GeometryTolerance(0.002, 1e-6, "request_override"))
    result = extract_relationships((a, b), opts)
    touch = next(item for item in result if item.kind == "endpoint_touches")
    assert touch.tolerance == 0.002 and touch.measured_value == pytest.approx(0.001)
    far = fact("3", geometry=LineGeometry("line", Point3D(1e9, 0, 0), Point3D(1e9 - 2, 0, 0)))
    parallel = extract_relationships((a, far), opts)
    assert triples(parallel) == {("parallel", "1", "3")} and parallel[0].measured_value == 0
    zero = replace(far, geometry=LineGeometry("line", Point3D(3, 3, 3), Point3D(3, 3, 3)))
    assert not extract_relationships((a, zero), opts)


def test_open_polyline_and_arc_ocs_endpoints_not_closed_shapes_or_insertions():
    arc = fact(
        "1", geometry=ArcGeometry("arc", Point3D(0, 0, 0), Point3D(0, 1, 0), 2, 0, math.pi / 2)
    )
    line = fact("2", geometry=LineGeometry("line", Point3D(-2, 0, 0), Point3D(-3, 0, 0)))
    assert ("endpoint_touches", "1", "2") in triples(
        extract_relationships((arc, line), RelationshipOptions())
    )
    poly = fact(
        "3",
        geometry=PolylineGeometry("polyline", (Point3D(-3, 0, 0), Point3D(-4, 0, 0)), (), False),
    )
    assert ("endpoint_touches", "2", "3") in triples(
        extract_relationships((line, poly), RelationshipOptions())
    )
    closed = replace(poly, geometry=replace(poly.geometry, closed=True))
    assert not extract_relationships((line, closed), RelationshipOptions())


def test_shuffle_invariance_no_duplicate_pair_emission_with_multiple_indexes():
    values = tuple(
        fact(
            f"{i+1:X}",
            owner="A",
            bounds=box((0, 0, 0), (1, 1, 1)),
            geometry=LineGeometry("line", Point3D(0, 0, 0), Point3D(1, 0, 0)),
        )
        for i in range(4)
    )
    first = extract_relationships(values, RelationshipOptions())
    assert first == extract_relationships(tuple(reversed(values)), RelationshipOptions())
    assert len(first) == len(triples(first))
    assert list(first) == sorted(
        first, key=lambda item: (item.kind, item.source_handle, item.target_handle)
    )


def test_exact_outgoing_limit_and_overflow_without_truncated_graph():
    values = tuple(fact(f"{i+1:X}", owner="A") for i in range(101))
    assert len(extract_relationships(values, RelationshipOptions())) == 5050
    with pytest.raises(ContextValidationError) as error:
        extract_relationships(values + (fact("100", owner="A"),), RelationshipOptions())
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"


def test_grid_and_candidate_boundaries_and_large_box_fallback(monkeypatch):
    import autocad_mcp.context.relationships as module

    values = (
        fact("1", bounds=box((0, 0, 0), (1, 1, 1))),
        fact("2", bounds=box((0, 0, 0), (1e12, 1, 1))),
    )
    assert ("bbox_intersects", "1", "2") in triples(
        extract_relationships(values, RelationshipOptions())
    )
    monkeypatch.setattr(module, "MAX_GRID_ENTRIES", 1)
    with pytest.raises(ContextValidationError) as error:
        extract_relationships(values, RelationshipOptions())
    assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"
    monkeypatch.setattr(module, "MAX_GRID_ENTRIES", 200000)
    monkeypatch.setattr(module, "MAX_CANDIDATE_PAIRS", 1)
    with pytest.raises(ContextValidationError):
        extract_relationships(
            (fact("1", owner="A"), fact("2", owner="A"), fact("3", owner="A")),
            RelationshipOptions(),
        )


def test_tiny_tolerance_finite_cell_indices_and_sparse_true_maximum():
    options = RelationshipOptions(GeometryTolerance(5e-324, 5e-324, "request_override"))
    a = fact("1", geometry=LineGeometry("line", Point3D(1e15, 0, 0), Point3D(1e15, 1, 0)))
    b = fact("2", geometry=LineGeometry("line", Point3D(1e15, 1, 0), Point3D(1e15, 2, 0)))
    assert {"parallel", "endpoint_touches"} == {
        item.kind for item in extract_relationships((a, b), options)
    }
    base = fact()
    maximum = tuple(
        replace(
            base,
            identity=replace(base.identity, handle=f"{i+1:X}"),
            bounds=box((i * 10, 0, 0), (i * 10 + 1, 1, 1)),
        )
        for i in range(10000)
    )
    assert extract_relationships(maximum, RelationshipOptions()) == ()
