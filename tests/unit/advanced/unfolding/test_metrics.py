"""Hand-built numerical expectations frozen independently before a solver exists."""

import math
from dataclasses import replace
from fractions import Fraction

import pytest
from autocad_mcp.advanced.bounds import BoundedExecutionFailure, BoundedExecutionPolicy, WorkBudget
from autocad_mcp.advanced.unfolding.metrics import VERIFIER_VERSION, verify_layout
from autocad_mcp.advanced.unfolding.models import (
    MeshFace,
    MeshVertex,
    UnfoldedVertex,
    UnfoldingLayout,
    UnfoldingRequest,
)
from autocad_mcp.advanced.unfolding.validation import validate_mesh

POLICY = BoundedExecutionPolicy(200000, 1000000, 30.0, 1024, 9041)


def source(points, faces, *, seams=(), root=10):
    request = UnfoldingRequest(
        "hand-built",
        "unit",
        tuple(MeshVertex(index, point) for index, point in enumerate(points)),
        tuple(MeshFace(face_id, ids) for face_id, ids in faces),
        seams,
        root,
        POLICY,
    )
    mesh = validate_mesh(request)
    assert not isinstance(mesh, BoundedExecutionFailure)
    return mesh


def triangle(scale=1.0, height=None):
    height = scale if height is None else height
    mesh = source(((0.0, 0.0, 0.0), (scale, 0.0, 0.0), (0.0, height, 0.0)), ((10, (0, 1, 2)),))
    layout = UnfoldingLayout(
        "hand-built-v1",
        tuple(
            UnfoldedVertex(index, "island-10", point)
            for index, point in enumerate(((0.0, 0.0), (scale, 0.0), (0.0, height)))
        ),
        ((0, 1, 2),),
        (),
    )
    return mesh, layout


def square(*, cut=False, root=10):
    mesh = source(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        ((20, (0, 2, 3)), (10, (0, 1, 2))),
        seams=((0, 2),) if cut else (),
        root=root,
    )
    if cut:
        vertices = (
            UnfoldedVertex(0, "island-10", (0.0, 0.0)),
            UnfoldedVertex(1, "island-10", (1.0, 0.0)),
            UnfoldedVertex(2, "island-10", (1.0, 1.0)),
            UnfoldedVertex(0, "island-20", (3.0, 0.0)),
            UnfoldedVertex(2, "island-20", (4.0, 1.0)),
            UnfoldedVertex(3, "island-20", (3.0, 1.0)),
        )
        return mesh, UnfoldingLayout("hand-built-v1", vertices, ((0, 1, 2), (3, 4, 5)), ((0, 2),))
    points = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    if root == 20:
        r = math.sqrt(0.5)
        points = ((0.0, 0.0), (r, -r), (2 * r, 0.0), (r, r))
    vertices = tuple(
        UnfoldedVertex(index, f"island-{root}", point) for index, point in enumerate(points)
    )
    return mesh, UnfoldingLayout("hand-built-v1", vertices, ((0, 1, 2), (0, 2, 3)), ())


def verify(mesh, layout, *, budget=None):
    return verify_layout(mesh, layout, budget=budget if budget is not None else WorkBudget(POLICY))


@pytest.mark.parametrize("scale", [1.0, 1e-300, 1e300, float.fromhex("0x0.0000000000001p-1022")])
def test_exact_triangles_stable_at_extreme_scales(scale):
    mesh, layout = triangle(scale)
    result = verify(mesh, layout)
    assert result.accepted and result.metrics is not None and not result.issues
    assert result.metrics.max_relative_edge_error == 0
    assert result.metrics.max_relative_area_error == 0
    assert result.metrics.max_angle_error_radians == 0
    assert result.metrics.overlap_pair_count == 0 and result.metrics.island_count == 1
    assert VERIFIER_VERSION == "rigid-triangle-verifier-v1"


@pytest.mark.parametrize("root", [10, 20])
def test_face_order_is_source_id_order_independent_of_requested_root(root):
    mesh, layout = square(root=root)
    result = verify(mesh, layout)
    assert result.accepted
    assert result.metrics.max_relative_edge_error <= 1e-9
    assert result.metrics.max_relative_area_error <= 1e-9
    assert result.metrics.max_angle_error_radians <= 1e-9


def test_global_disjoint_islands_and_zero_area_cut_boundary_contact():
    mesh, layout = square(cut=True)
    assert verify(mesh, layout).accepted
    touching = replace(
        layout,
        vertices_2d=layout.vertices_2d[:3]
        + tuple(
            replace(vertex, point_2d=(vertex.point_2d[0] - 3, vertex.point_2d[1]))
            for vertex in layout.vertices_2d[3:]
        ),
    )
    result = verify(mesh, touching)
    assert result.accepted and result.metrics.overlap_pair_count == 0
    assert result.metrics.island_count == 2


def test_near_degenerate_nonzero_planar_triangle_is_not_falsely_collapsed():
    mesh, layout = triangle(1.0, 1e-300)
    assert verify(mesh, layout).accepted
    collapsed = replace(
        layout,
        vertices_2d=layout.vertices_2d[:2] + (replace(layout.vertices_2d[2], point_2d=(0.0, 0.0)),),
    )
    result = verify(mesh, collapsed)
    assert not result.accepted and result.metrics is None


def test_nonzero_measured_distortion_and_exact_area_threshold_bracketing():
    mesh, layout = triangle()
    at = math.sqrt(1 + 1e-9)
    low, high = math.nextafter(at, 1.0), math.nextafter(at, math.inf)
    assert float(Fraction(low) ** 2 - 1) <= 1e-9
    assert float(Fraction(high) ** 2 - 1) > 1e-9

    def scaled(factor):
        return replace(
            layout,
            vertices_2d=tuple(
                replace(vertex, point_2d=(vertex.point_2d[0] * factor, vertex.point_2d[1] * factor))
                for vertex in layout.vertices_2d
            ),
        )

    accepted = verify(mesh, scaled(low))
    assert accepted.accepted and accepted.metrics.max_relative_area_error > 0
    assert accepted.metrics.max_relative_edge_error > 0
    rejected = verify(mesh, scaled(high))
    assert not rejected.accepted and rejected.metrics is None


def test_angle_distortion_is_independently_measured():
    mesh, layout = triangle()
    slight = replace(
        layout,
        vertices_2d=layout.vertices_2d[:2]
        + (replace(layout.vertices_2d[2], point_2d=(0.9e-9, 1.0)),),
    )
    result = verify(mesh, slight)
    assert result.accepted and 0 < result.metrics.max_angle_error_radians <= 1e-9
    severe = replace(
        slight,
        vertices_2d=slight.vertices_2d[:2]
        + (replace(slight.vertices_2d[2], point_2d=(2e-9, 1.0)),),
    )
    assert not verify(mesh, severe).accepted


def seam_fan(*, saddle=False):
    points = (
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 1.0 if saddle else 0.0),
        (0.0, 1.0, -1.0 if saddle else 0.0),
        (-1.0, 0.0, 1.0 if saddle else 0.0),
        (0.0, -1.0, -1.0 if saddle else 0.0),
    )
    mesh = source(
        points,
        ((10, (0, 1, 2)), (20, (0, 2, 3)), (30, (0, 3, 4)), (40, (0, 4, 1))),
        seams=((0, 1),),
    )
    coords = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (1.0, 0.0))
    if saddle:
        a, b = math.sqrt(0.5), math.sqrt(1.5)
        coords = ((0.0, 0.0), (2 * a, 0.0), (-a, b), (-a, -b), (2 * a, 0.0), (-a, b))
    vertices = tuple(
        UnfoldedVertex(source_id, "island-10", point)
        for source_id, point in zip((0, 1, 2, 3, 4, 1), coords, strict=True)
    )
    return mesh, UnfoldingLayout(
        "hand-built-v1", vertices, ((0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)), ((0, 1),)
    )


def test_seam_corner_duplicates_within_one_island_are_not_welded():
    mesh, layout = seam_fan()
    assert verify(mesh, layout).accepted
    welded = replace(
        layout, vertices_2d=layout.vertices_2d[:-1], faces_2d=layout.faces_2d[:-1] + ((0, 4, 1),)
    )
    result = verify(mesh, welded)
    assert not result.accepted and result.metrics is None


def test_requested_root_island_can_follow_other_faces_in_canonical_output_order():
    mesh, _ = square(cut=True, root=20)
    r = math.sqrt(0.5)
    vertices = (
        UnfoldedVertex(0, "island-10", (3.0, r)),
        UnfoldedVertex(1, "island-10", (3.0 + r, 0.0)),
        UnfoldedVertex(2, "island-10", (3.0 + 2 * r, r)),
        UnfoldedVertex(0, "island-20", (0.0, 0.0)),
        UnfoldedVertex(2, "island-20", (2 * r, 0.0)),
        UnfoldedVertex(3, "island-20", (r, r)),
    )
    layout = UnfoldingLayout("hand-built-v1", vertices, ((0, 1, 2), (3, 4, 5)), ((0, 2),))
    assert verify(mesh, layout).accepted
