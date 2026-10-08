"""Deterministic rigid charts from an accepted seam forest; no self-approval."""

import json
import math
from bisect import bisect_left
from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from heapq import heappop, heappush

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_RESULT_BYTES,
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding.models import (
    MeshValidationError,
    UnfoldedVertex,
    UnfoldingLayout,
)
from autocad_mcp.advanced.unfolding.validation import ValidatedMesh

SOLVER_VERSION = "rigid-triangle-unfolding-v1"
type SourcePoint = tuple[Fraction, ...]
type Point2 = tuple[float, float]
type Chart = tuple[int, int, tuple[float, float, float, float]]


def _checkpoint(budget: WorkBudget) -> None:
    try:
        budget.checkpoint()
    except ValueError:
        raise MeshValidationError("RESOURCE_LIMIT", "Fixed solver work limit exceeded") from None


def _require(condition: bool) -> None:
    if not condition:
        raise MeshValidationError("NUMERICAL_FAILURE", "Rigid chart cannot be represented")


def _decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _frame(a: SourcePoint, b: SourcePoint, c: SourcePoint) -> tuple[Decimal, Decimal, Decimal]:
    """Intrinsic projection and altitude, with an exact Gram residual before square roots."""
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    uu = sum((component**2 for component in u), Fraction())
    uv = sum((u[i] * v[i] for i in range(3)), Fraction())
    vv = sum((component**2 for component in v), Fraction())
    altitude_squared = vv - uv**2 / uu
    _require(uu > 0 and altitude_squared > 0)
    base = _decimal(uu).sqrt()
    return base, _decimal(uv) / base, _decimal(altitude_squared).sqrt()


def _point(x: Decimal, y: Decimal) -> Point2:
    result = float(x), float(y)
    _require(all(math.isfinite(value) for value in result))
    return result


def _third(a: Point2, b: Point2, frame: tuple[Decimal, Decimal, Decimal]) -> Point2:
    base, along, height = frame
    ax, ay, bx, by = (Decimal.from_float(value) for value in (*a, *b))
    dx, dy = bx - ax, by - ay
    return _point(ax + (dx * along - dy * height) / base, ay + (dy * along + dx * height) / base)


def _positive(a: Point2, b: Point2, c: Point2) -> None:
    # Exact output determinant detects collapse even at subnormal coordinates.
    ax, ay, bx, by, cx, cy = (Fraction(value) for value in (*a, *b, *c))
    _require((bx - ax) * (cy - ay) > (by - ay) * (cx - ax))


def _charts(  # noqa: C901 - explicit bounded forest traversal and oriented corner attachment
    mesh: ValidatedMesh, budget: WorkBudget
) -> tuple[list[UnfoldedVertex], dict[int, tuple[int, int, int]], list[Chart]]:
    source = {}
    for vertex in mesh.request.vertices:
        _checkpoint(budget)
        source[vertex.vertex_id] = tuple(Fraction(value) for value in vertex.point)
    faces = {}
    for face in mesh.request.faces:
        _checkpoint(budget)
        faces[face.face_id] = face.vertex_ids
    adjacency = {}
    for face_id, neighbors in mesh.adjacency:
        _checkpoint(budget)
        adjacency[face_id] = neighbors
    shared = {}
    seams = set(mesh.request.seam_edges)
    for edge in mesh.edges:
        _checkpoint(budget)
        if len(edge.face_ids) == 2 and edge.vertex_ids not in seams:
            shared[edge.face_ids] = edge.vertex_ids
    roots = []
    for island in mesh.islands:
        _checkpoint(budget)
        position = bisect_left(island, mesh.request.root_face_id)
        roots.append(
            mesh.request.root_face_id
            if position < len(island) and island[position] == mesh.request.root_face_id
            else island[0]
        )
    roots.sort(key=lambda root: (root != mesh.request.root_face_id, root))
    vertices: list[UnfoldedVertex] = []
    output_faces: dict[int, tuple[int, int, int]] = {}
    charts: list[Chart] = []
    for root in roots:
        _checkpoint(budget)
        start = len(vertices)
        label = f"island-{root}"
        root_ids = faces[root]
        base, along, height = _frame(*(source[source_id] for source_id in root_ids))
        points = ((0.0, 0.0), _point(base, Decimal(0)), _point(along, height))
        _positive(*points)
        for source_id, point in zip(root_ids, points, strict=True):
            _checkpoint(budget)
            vertices.append(UnfoldedVertex(source_id, label, point))
        output_faces[root] = (start, start + 1, start + 2)
        low_x = min(point[0] for point in points)
        high_x = max(point[0] for point in points)
        low_y = min(point[1] for point in points)
        high_y = max(point[1] for point in points)
        pending: list[tuple[int, int]] = []
        for child in adjacency[root]:
            _checkpoint(budget)
            heappush(pending, (child, root))
        while pending:
            _checkpoint(budget)
            child, parent = heappop(pending)
            child_ids = faces[child]
            pair = min(child, parent), max(child, parent)
            endpoints = shared[pair]
            first = next(
                i
                for i in range(3)
                if child_ids[i] in endpoints and child_ids[(i + 1) % 3] in endpoints
            )
            second, third = (first + 1) % 3, (first + 2) % 3
            parent_indices = dict(zip(faces[parent], output_faces[parent], strict=True))
            a_index, b_index = parent_indices[child_ids[first]], parent_indices[child_ids[second]]
            frame = _frame(
                source[child_ids[first]], source[child_ids[second]], source[child_ids[third]]
            )
            point = _third(vertices[a_index].point_2d, vertices[b_index].point_2d, frame)
            _positive(vertices[a_index].point_2d, vertices[b_index].point_2d, point)
            indices = [0, 0, 0]
            indices[first], indices[second], indices[third] = a_index, b_index, len(vertices)
            vertices.append(UnfoldedVertex(child_ids[third], label, point))
            output_faces[child] = (indices[0], indices[1], indices[2])
            low_x, high_x = min(low_x, point[0]), max(high_x, point[0])
            low_y, high_y = min(low_y, point[1]), max(high_y, point[1])
            for neighbor in adjacency[child]:
                _checkpoint(budget)
                if neighbor != parent:
                    heappush(pending, (neighbor, child))
        charts.append((start, len(vertices), (low_x, high_x, low_y, high_y)))
    return vertices, output_faces, charts


def _strip(vertices: list[UnfoldedVertex], charts: list[Chart], budget: WorkBudget) -> None:
    if len(charts) == 1:
        return
    span = 0.0
    for _, _, (low_x, high_x, low_y, high_y) in charts:
        _checkpoint(budget)
        span = max(span, high_x - low_x, high_y - low_y)
    gap = 1e-6 * span
    _require(math.isfinite(gap) and gap > 0)
    previous_max = charts[0][2][1]
    for start, end, (low_x, _, low_y, _) in charts[1:]:
        _checkpoint(budget)
        target = previous_max + gap
        shift = target - low_x
        _require(math.isfinite(shift) and math.isfinite(target) and target > previous_max)
        minimum = math.inf
        maximum = -math.inf
        for index in range(start, end):
            _checkpoint(budget)
            vertex = vertices[index]
            x, y = vertex.point_2d[0] + shift, vertex.point_2d[1] - low_y
            _require(math.isfinite(x) and math.isfinite(y))
            vertices[index] = replace(vertex, point_2d=(x, y))
            minimum, maximum = min(minimum, x), max(maximum, x)
        _require(minimum > previous_max)
        previous_max = maximum


def _bytes(layout: UnfoldingLayout, budget: WorkBudget) -> None:
    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"), default=vars
    )
    empty = {
        "solver_version": layout.solver_version,
        "vertices_2d": (),
        "faces_2d": (),
        "cut_edges": (),
    }
    size = len(encoder.encode(empty).encode("utf-8"))
    # Each bounded record is encoded natively; no duplicate candidate staging list.
    for records in (layout.vertices_2d, layout.faces_2d, layout.cut_edges):
        for index, record in enumerate(records):
            _checkpoint(budget)
            size += len(encoder.encode(record).encode("utf-8")) + (index > 0)
            if size > MAX_ADVANCED_RESULT_BYTES:
                raise MeshValidationError("RESOURCE_LIMIT", "Solver candidate byte limit exceeded")


def solve_layout(
    mesh: ValidatedMesh, *, budget: WorkBudget
) -> UnfoldingLayout | BoundedExecutionFailure:
    """Build one rigid layout; the caller must obtain separate numerical verification."""
    try:
        budget.checkpoint(0)
        count = len(mesh.request.faces) + 2 * len(mesh.islands)
        if count + len(mesh.request.faces) + len(mesh.request.seam_edges) > budget.policy.max_items:
            raise MeshValidationError("RESOURCE_LIMIT", "Solver candidate item limit exceeded")
        # ponytail: 50-digit transforms; raise precision if measured verifier failures justify it.
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)):
            vertices, indices, charts = _charts(mesh, budget)
        _strip(vertices, charts, budget)
        faces = []
        for face in mesh.request.faces:
            _checkpoint(budget)
            output = indices[face.face_id]
            _positive(*(vertices[index].point_2d for index in output))
            faces.append(output)
        layout = UnfoldingLayout(
            SOLVER_VERSION, tuple(vertices), tuple(faces), mesh.request.seam_edges
        )
        _bytes(layout, budget)
        budget.checkpoint(0)
        return layout
    except BoundedExecutionInterrupted as error:
        return error.failure
    except (MeshValidationError, ArithmeticError, ValueError) as failure:
        try:
            budget.checkpoint(0)
        except BoundedExecutionInterrupted as error:
            return error.failure
        if isinstance(failure, MeshValidationError):
            raise
        raise MeshValidationError(
            "NUMERICAL_FAILURE", "Rigid chart cannot be represented"
        ) from None
