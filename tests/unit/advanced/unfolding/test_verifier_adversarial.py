"""Corrupt candidates cannot self-certify geometry, topology, or bounded completion."""

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest
from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedFailureCode,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding import metrics
from autocad_mcp.advanced.unfolding.models import UnfoldingLayout

from tests.unit.advanced.unfolding.test_metrics import POLICY, seam_fan, square, triangle, verify


@pytest.mark.parametrize(
    "change",
    [
        "stretch",
        "flip",
        "incomplete",
        "bad-index",
        "bool-index",
        "foreign-source",
        "bad-island",
        "unused",
        "wrong-order",
        "split-uncut",
        "bad-cuts",
        "duplicate-cuts",
        "translated-anchor",
        "wrong-axis",
        "bad-version",
    ],
)
def test_corrupt_candidates_are_redacted_rejections_without_fake_metrics(change):  # noqa: C901
    mesh, layout = square()
    if change == "stretch":
        layout = replace(
            layout,
            vertices_2d=tuple(
                replace(vertex, point_2d=(vertex.point_2d[0] * 1.01, vertex.point_2d[1]))
                for vertex in layout.vertices_2d
            ),
        )
    elif change == "flip":
        layout = replace(
            layout,
            vertices_2d=tuple(
                replace(vertex, point_2d=(vertex.point_2d[0], -vertex.point_2d[1]))
                for vertex in layout.vertices_2d
            ),
        )
    elif change == "incomplete":
        layout = replace(layout, faces_2d=layout.faces_2d[:1])
    elif change in ("bad-index", "bool-index"):
        layout = replace(
            layout, faces_2d=((0, 1, True if change == "bool-index" else 99), (0, 2, 3))
        )
    elif change in ("foreign-source", "bad-island"):
        vertex = replace(
            layout.vertices_2d[0],
            **(
                {"source_vertex_id": 99}
                if change == "foreign-source"
                else {"island_id": "island-999"}
            ),
        )
        layout = replace(layout, vertices_2d=(vertex,) + layout.vertices_2d[1:])
    elif change == "unused":
        layout = replace(layout, vertices_2d=layout.vertices_2d + (layout.vertices_2d[0],))
    elif change == "wrong-order":
        layout = replace(layout, faces_2d=layout.faces_2d[::-1])
    elif change == "split-uncut":
        layout = replace(
            layout,
            vertices_2d=layout.vertices_2d + (layout.vertices_2d[0],),
            faces_2d=((0, 1, 2), (4, 2, 3)),
        )
    elif change == "bad-cuts":
        layout = replace(layout, cut_edges=((0, 2),))
    elif change == "duplicate-cuts":
        mesh, layout = square(cut=True)
        layout = replace(layout, cut_edges=layout.cut_edges * 2)
    elif change in ("translated-anchor", "wrong-axis"):
        layout = replace(
            layout,
            vertices_2d=tuple(
                replace(
                    vertex,
                    point_2d=(
                        vertex.point_2d[0] + (1 if change == "translated-anchor" else 0),
                        vertex.point_2d[1] + (1 if change == "wrong-axis" else 0),
                    ),
                )
                for vertex in layout.vertices_2d
            ),
        )
    else:
        layout = replace(layout, solver_version="private-invalid\x00solver")
    result = verify(mesh, layout)
    assert not isinstance(result, BoundedExecutionFailure)
    assert not result.accepted and result.metrics is None and result.issues
    assert "private" not in repr(result)
    assert len(result.issues) <= 1000
    assert all(
        len(issue.face_ids) <= 2 and len(issue.code) <= 64 and len(issue.message) <= 256
        for issue in result.issues
    )


@pytest.mark.parametrize(
    "point",
    [
        (True, 0.0),
        (math.nan, 0.0),
        (math.inf, 0.0),
        (0.0, -math.inf),
        (1.0,),
        (None, 0.0),
        (10**400, 0.0),
    ],
)
def test_invalid_output_points_never_reach_numeric_work(point):
    mesh, layout = triangle()
    candidate = replace(
        layout,
        vertices_2d=(replace(layout.vertices_2d[0], point_2d=point),) + layout.vertices_2d[1:],
    )
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None


def test_global_cross_island_overlap_is_rejected_with_explicit_pair():
    mesh, layout = square(cut=True)
    points = ((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))
    layout = replace(
        layout,
        vertices_2d=layout.vertices_2d[:3]
        + tuple(
            replace(vertex, point_2d=point)
            for vertex, point in zip(layout.vertices_2d[3:], points, strict=True)
        ),
    )
    result = verify(mesh, layout)
    assert not result.accepted and result.metrics is None
    assert any(
        issue.code == "OVERLAP" and set(issue.face_ids) == {10, 20} for issue in result.issues
    )


def test_intrinsic_saddle_fan_overlap_is_rejected_without_a_solver():
    mesh, layout = seam_fan(saddle=True)
    result = verify(mesh, layout)
    assert not result.accepted and result.metrics is None
    assert any(issue.code == "OVERLAP" for issue in result.issues)


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_interruption_during_verification_returns_only_exact_bounded_failure(cause):
    mesh, layout = square()
    state = SimpleNamespace(calls=0, time=0.0)

    def cancelled():
        state.calls += 1
        return cause == "cancelled" and state.calls >= 8

    def now():
        state.time += 0.01 if cause == "deadline" else 0.0
        return state.time

    policy = replace(POLICY, cancellation_check_interval=1, deadline_seconds=0.07)
    budget = WorkBudget(
        policy, clock=SimpleNamespace(now=now), cancellation=SimpleNamespace(is_cancelled=cancelled)
    )
    budget.checkpoint(2)
    result = verify(mesh, layout, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
    assert result.completed_iterations > 2
    assert not hasattr(result, "metrics") and not hasattr(result, "vertices_2d")


def test_fixed_iteration_and_item_limits_fail_structurally():
    mesh, layout = triangle()
    for policy in (replace(POLICY, max_iterations=2), replace(POLICY, max_items=2)):
        result = verify(mesh, layout, budget=WorkBudget(policy))
        assert not result.accepted and result.metrics is None
        assert result.issues[0].code == "RESOURCE_LIMIT"


def test_candidate_byte_ceiling_is_enforced(monkeypatch):
    mesh, layout = triangle()
    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", 128)
    result = verify(mesh, layout)
    assert not result.accepted and result.metrics is None
    assert result.issues[0].code == "RESOURCE_LIMIT"


def test_extreme_distortion_is_not_an_overflow_or_fake_success():
    mesh, layout = triangle(1e-300)
    candidate = replace(
        layout,
        vertices_2d=tuple(
            replace(vertex, point_2d=(vertex.point_2d[0] * 1e300, vertex.point_2d[1] * 1e300))
            for vertex in layout.vertices_2d
        ),
    )
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None


def test_no_solver_or_com_module_is_required():
    import ast
    import inspect

    imports = [
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(metrics)))
        if isinstance(node, ast.ImportFrom)
    ]
    assert all("solver" not in module for module in imports if module)
    assert all(
        not any(name in module for name in ("pythoncom", "win32com", "pyautocad"))
        for module in imports
        if module
    )
    assert UnfoldingLayout.__dataclass_params__.frozen


def test_positive_area_sliver_is_rejected_even_below_float_area_range():
    mesh, layout = square(cut=True)
    points = ((0.0, -float.fromhex("0x0.0000000000001p-1022")), (1.0, 1.0), (0.0, 1.0))
    layout = replace(
        layout,
        vertices_2d=layout.vertices_2d[:3]
        + tuple(
            replace(vertex, point_2d=point)
            for vertex, point in zip(layout.vertices_2d[3:], points, strict=True)
        ),
    )
    result = verify(mesh, layout)
    assert not result.accepted and result.metrics is None
    assert any(issue.code == "OVERLAP" for issue in result.issues)


def test_non_string_island_identity_is_a_redacted_shape_rejection():
    mesh, layout = triangle()

    class PretendIdentity:
        def __eq__(self, other):
            return True

    vertex = replace(layout.vertices_2d[0], island_id=PretendIdentity())
    candidate = replace(layout, vertices_2d=(vertex,) + layout.vertices_2d[1:])
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None


@pytest.mark.parametrize("cells", [500, 501])
def test_diagnostic_overflow_is_structured_failure_not_truncated_measurements(cells):
    from autocad_mcp.advanced.unfolding.models import UnfoldedVertex

    from tests.unit.advanced.unfolding.test_metrics import source

    points = tuple(
        (float(column), float(row), 0.0) for column in range(cells + 1) for row in (0, 1)
    )
    faces = tuple(
        (2 * column + offset, ids)
        for column in range(cells)
        for offset, ids in enumerate(
            (
                (2 * column, 2 * column + 2, 2 * column + 3),
                (2 * column, 2 * column + 3, 2 * column + 1),
            )
        )
    )
    edges = tuple(
        sorted(
            {
                tuple(sorted((ids[index], ids[(index + 1) % 3])))
                for _, ids in faces
                for index in range(3)
            }
        )
    )
    mesh = source(points, faces, seams=edges, root=0)
    vertices = []
    for face_id, ids in faces:
        column = face_id // 2
        for source_id in ids:
            vertices.append(
                UnfoldedVertex(
                    source_id,
                    f"island-{face_id}",
                    (3.0 * face_id + 2 * (points[source_id][0] - column), points[source_id][1]),
                )
            )
    candidate = UnfoldingLayout(
        "hand-built-v1",
        tuple(vertices),
        tuple((3 * index, 3 * index + 1, 3 * index + 2) for index in range(len(faces))),
        edges,
    )
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None
    if cells == 500:
        assert len(result.issues) == 1000
        assert all(issue.code == "DISTORTION" for issue in result.issues)
    else:
        assert len(result.issues) == 1 and result.issues[0].code == "RESOURCE_LIMIT"
        assert "Diagnostic" in result.issues[0].message


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_pending_interruption_wins_over_a_resource_rejection(monkeypatch, cause):
    mesh, layout = triangle()
    state = SimpleNamespace(cancelled=False, time=0.0)
    budget = WorkBudget(
        POLICY,
        clock=SimpleNamespace(now=lambda: state.time),
        cancellation=SimpleNamespace(is_cancelled=lambda: state.cancelled),
    )
    original = metrics._serialized_bound

    def interrupted_size_check(*args, **kwargs):
        state.cancelled = cause == "cancelled"
        state.time = 31.0 if cause == "deadline" else 0.0
        return original(*args, **kwargs)

    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", 128)
    monkeypatch.setattr(metrics, "_serialized_bound", interrupted_size_check)
    result = verify(mesh, layout, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )


def test_reflected_non_root_triangle_is_rejected_even_with_correct_edge_lengths():
    mesh, layout = square(cut=True)
    candidate = replace(
        layout,
        vertices_2d=layout.vertices_2d[:3]
        + tuple(
            replace(vertex, point_2d=(vertex.point_2d[0], -vertex.point_2d[1]))
            for vertex in layout.vertices_2d[3:]
        ),
    )
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None
    assert any(issue.code == "FLIPPED_FACE" and issue.face_ids == (20,) for issue in result.issues)


def test_actual_four_mib_candidate_overflow_rejects_before_numeric_work():
    import json
    from dataclasses import asdict

    from autocad_mcp.advanced.unfolding.models import (
        MeshFace,
        MeshVertex,
        UnfoldedVertex,
        UnfoldingRequest,
        normalize_request,
    )
    from autocad_mcp.advanced.unfolding.validation import MeshEdge, ValidatedMesh

    width, height = 39, 49
    points = tuple((float(x), float(y), 0.0) for x in range(width + 1) for y in range(height + 1))
    faces = []
    for x in range(width):
        for y in range(height):
            a = x * (height + 1) + y
            b = a + height + 1
            faces.extend(((len(faces), (a, b, b + 1)), (len(faces) + 1, (a, b + 1, a + 1))))
    edges = tuple(
        sorted(
            {
                tuple(sorted((ids[index], ids[(index + 1) % 3])))
                for _, ids in faces
                for index in range(3)
            }
        )
    )
    # A planar unit-cell triangulation is embedded/manifold by construction. All cuts
    # give singleton islands; this byte test consumes the public immutable topology
    # directly rather than rerunning unrelated 3D intersection validation for 3,822 faces.
    request = normalize_request(
        UnfoldingRequest(
            "hand-built-byte-bound",
            "unit",
            tuple(MeshVertex(i, p) for i, p in enumerate(points)),
            tuple(MeshFace(face_id, ids) for face_id, ids in faces),
            edges,
            0,
            POLICY,
        )
    )
    incidences = {edge: [] for edge in edges}
    for face_id, ids in faces:
        for index in range(3):
            incidences[tuple(sorted((ids[index], ids[(index + 1) % 3])))].append(face_id)
    mesh = ValidatedMesh(
        request,
        tuple(MeshEdge(edge, tuple(sorted(owners))) for edge, owners in incidences.items()),
        tuple((face_id, ()) for face_id, _ in faces),
        tuple((face_id,) for face_id, _ in faces),
    )
    vertices = tuple(
        UnfoldedVertex(source_id, f"island-{face_id}", (10**300, 10**300))
        for face_id, ids in faces
        for source_id in ids
    )
    candidate = UnfoldingLayout(
        "hand-built-v1",
        vertices,
        tuple((3 * index, 3 * index + 1, 3 * index + 2) for index in range(len(faces))),
        edges,
    )
    assert (
        len(
            json.dumps(
                asdict(candidate), separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode()
        )
        > 4 * 1024**2
    )
    result = verify(mesh, candidate)
    assert not result.accepted and result.metrics is None
    assert result.issues[0].code == "RESOURCE_LIMIT"
    assert "byte" in result.issues[0].message
