"""Hand-computable rigid triangle charts, independent of solver arithmetic."""

import math

import pytest
from autocad_mcp.advanced.bounds import BoundedExecutionFailure, BoundedExecutionPolicy, WorkBudget
from autocad_mcp.advanced.unfolding.metrics import verify_layout
from autocad_mcp.advanced.unfolding.models import (
    MeshFace,
    MeshVertex,
    UnfoldingLayout,
    UnfoldingRequest,
)
from autocad_mcp.advanced.unfolding.solver import SOLVER_VERSION, solve_layout
from autocad_mcp.advanced.unfolding.validation import ValidatedMesh, validate_mesh

POLICY = BoundedExecutionPolicy(200000, 1000000, 30.0, 1024, 9041)


def mesh_from(
    points: tuple[tuple[float, float, float], ...],
    faces: tuple[tuple[int, tuple[int, int, int]], ...] = ((10, (0, 1, 2)),),
    *,
    seams: tuple[tuple[int, int], ...] = (),
    root: int = 10,
) -> ValidatedMesh:
    result = validate_mesh(
        UnfoldingRequest(
            "solver-check",
            "unit",
            tuple(MeshVertex(i, point) for i, point in enumerate(points)),
            tuple(MeshFace(i, ids) for i, ids in faces),
            seams,
            root,
            POLICY,
        )
    )
    assert isinstance(result, ValidatedMesh)
    return result


def solve(mesh: ValidatedMesh) -> UnfoldingLayout:
    result = solve_layout(mesh, budget=WorkBudget(mesh.request.policy))
    assert isinstance(result, UnfoldingLayout)
    return result


def accepted(mesh: ValidatedMesh, layout: UnfoldingLayout) -> None:
    result = verify_layout(mesh, layout, budget=WorkBudget(mesh.request.policy))
    assert not isinstance(result, BoundedExecutionFailure)
    assert result.accepted, result.issues
    assert result.metrics is not None and result.metrics.overlap_pair_count == 0
    assert not hasattr(layout, "metrics") and not hasattr(layout, "input_digest")


def square_mesh(*, root: int = 10, cut: bool = False, scale: float = 1.0) -> ValidatedMesh:
    return mesh_from(
        ((0.0, 0.0, 0.0), (scale, 0.0, 0.0), (scale, scale, 0.0), (0.0, scale, 0.0)),
        ((20, (0, 2, 3)), (10, (0, 1, 2))),
        seams=((0, 2),) if cut else (),
        root=root,
    )


def test_oriented_three_four_five_root_has_exact_anchor_and_golden_coordinates() -> None:
    mesh = mesh_from(((2.0, -3.0, 4.0), (5.0, -3.0, 4.0), (2.0, 1.0, 4.0)))
    layout = solve(mesh)
    assert tuple(vertex.point_2d for vertex in layout.vertices_2d) == (
        (0.0, 0.0),
        (3.0, 0.0),
        (0.0, 4.0),
    )
    assert layout.faces_2d == ((0, 1, 2),)
    assert layout.solver_version == SOLVER_VERSION == "rigid-triangle-unfolding-v1"
    accepted(mesh, layout)


def test_folded_neighbor_is_rigid_and_uses_only_shared_edge_indices() -> None:
    mesh = mesh_from(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((10, (0, 1, 2)), (20, (1, 0, 3))),
    )
    layout = solve(mesh)
    assert layout.faces_2d == ((0, 1, 2), (1, 0, 3))
    assert layout.vertices_2d[3].point_2d == (0.0, -1.0)
    accepted(mesh, layout)


def test_nonminimum_root_preserves_global_face_order_and_oriented_anchor() -> None:
    mesh = square_mesh(root=20)
    layout = solve(mesh)
    assert layout.faces_2d == ((0, 3, 1), (0, 1, 2))
    r = math.sqrt(0.5)
    expected = ((0.0, 0.0), (2 * r, 0.0), (r, r), (r, -r))
    for vertex, point in zip(layout.vertices_2d, expected, strict=True):
        assert vertex.point_2d == pytest.approx(point)
    accepted(mesh, layout)


@pytest.mark.parametrize("root", [10, 20])
def test_islands_use_requested_root_first_and_declared_strip_gap(root: int) -> None:
    mesh = square_mesh(root=root, cut=True)
    layout = solve(mesh)
    assert tuple(v.island_id for v in layout.vertices_2d[:3]) == (f"island-{root}",) * 3
    charts = [layout.vertices_2d[:3], layout.vertices_2d[3:]]
    span = 1.0 if root == 10 else math.sqrt(2)
    maximum = max(v.point_2d[0] for v in charts[0])
    assert min(v.point_2d[0] for v in charts[1]) == pytest.approx(maximum + 1e-6 * span)
    assert min(v.point_2d[0] for v in charts[1]) > maximum
    assert min(v.point_2d[1] for v in charts[1]) == 0.0
    assert layout.cut_edges == ((0, 2),)
    accepted(mesh, layout)


def test_cut_fan_duplicates_a_source_corner_within_the_same_island() -> None:
    mesh = mesh_from(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
        ((10, (0, 1, 2)), (20, (0, 2, 3)), (30, (0, 3, 4)), (40, (0, 4, 1))),
        seams=((0, 1),),
    )
    layout = solve(mesh)
    duplicate = [v for v in layout.vertices_2d if v.source_vertex_id == 1]
    assert len(duplicate) == 2 and all(v.island_id == "island-10" for v in duplicate)
    assert len(layout.vertices_2d) == 6
    assert layout.faces_2d[0][1] != layout.faces_2d[-1][2]
    accepted(mesh, layout)


@pytest.mark.parametrize("scale", [1e-300, 1e300, math.ulp(0.0)])
def test_single_chart_root_stays_rigid_at_extreme_scales(scale: float) -> None:
    mesh = mesh_from(((0.0, 0.0, 0.0), (scale, 0.0, 0.0), (0.0, scale, 0.0)))
    layout = solve(mesh)
    assert layout.vertices_2d[1].point_2d == (scale, 0.0)
    assert layout.vertices_2d[2].point_2d == (0.0, scale)
    accepted(mesh, layout)


def test_thin_root_does_not_lose_height_to_gram_cancellation() -> None:
    mesh = mesh_from(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1e-300, 0.0)))
    layout = solve(mesh)
    assert layout.vertices_2d[2].point_2d == (1.0, 1e-300)
    accepted(mesh, layout)


def test_intrinsic_overlap_is_left_for_verifier_without_retry() -> None:
    mesh = mesh_from(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 1.0, -1.0), (-1.0, 0.0, 1.0), (0.0, -1.0, -1.0)),
        ((10, (0, 1, 2)), (20, (0, 2, 3)), (30, (0, 3, 4)), (40, (0, 4, 1))),
        seams=((0, 1),),
    )
    layout = solve(mesh)
    result = verify_layout(mesh, layout, budget=WorkBudget(POLICY))
    assert not isinstance(result, BoundedExecutionFailure)
    assert not result.accepted and result.metrics is None
    assert any(issue.code == "OVERLAP" for issue in result.issues)
    assert solve(mesh) == layout


def test_many_islands_order_root_then_remaining_minimum_faces() -> None:
    mesh = mesh_from(
        (
            (0.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
            (1.0, 2.0, 0.0),
            (1.0, -1.0, 0.0),
            (3.0, 2.0, 0.0),
            (-1.0, 2.0, 0.0),
        ),
        ((10, (0, 1, 2)), (20, (1, 0, 3)), (30, (2, 1, 4)), (40, (0, 2, 5))),
        seams=((0, 1), (0, 2), (1, 2)),
        root=30,
    )
    layout = solve(mesh)
    assert [v.island_id for v in layout.vertices_2d[::3]] == [
        "island-30",
        "island-10",
        "island-20",
        "island-40",
    ]
    accepted(mesh, layout)
