"""Independent rigid-triangle verification in one global frame; no solver imports."""

import json
import math
from bisect import bisect_left
from collections import defaultdict
from fractions import Fraction
from heapq import heappop, heappush
from typing import Any, TypeAlias, cast

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_RESULT_BYTES,
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding.models import (
    MAX_FACES,
    MAX_ISLAND_ID_CHARACTERS,
    MAX_RESULT_ISSUES,
    MAX_SEAMS,
    MAX_VERSION_CHARACTERS,
    LayoutVerification,
    MeshValidationError,
    UnfoldedVertex,
    UnfoldingIssue,
    UnfoldingLayout,
    UnfoldingMetrics,
    _integer,
    _text,
)
from autocad_mcp.advanced.unfolding.validation import ValidatedMesh

VERIFIER_VERSION = "rigid-triangle-verifier-v1"
ERROR_LIMIT = 1e-9
Point2: TypeAlias = tuple[Fraction, Fraction]  # noqa: UP040
Vector: TypeAlias = tuple[Fraction, ...]  # noqa: UP040


class _LayoutRejectedError(Exception):
    def __init__(self, code: str, message: str, face_ids: tuple[int, ...] = ()) -> None:
        self.issue = UnfoldingIssue(code, face_ids, message)


def _require(
    condition: bool, message: str, *, code: str = "INVALID_LAYOUT", face_ids: tuple[int, ...] = ()
) -> None:
    if not condition:
        raise _LayoutRejectedError(code, message, face_ids)


def _shape(mesh: ValidatedMesh, layout: UnfoldingLayout, budget: WorkBudget) -> None:
    _require(type(layout) is UnfoldingLayout, "Expected an unfolding candidate")
    _text(layout.solver_version, MAX_VERSION_CHARACTERS, "solver version")
    _require(
        type(layout.vertices_2d) is tuple and 3 <= len(layout.vertices_2d) <= 3 * MAX_FACES,
        "Candidate vertex bound exceeded",
        code="RESOURCE_LIMIT",
    )
    _require(
        type(layout.faces_2d) is tuple and len(layout.faces_2d) == len(mesh.request.faces),
        "Candidate faces are incomplete",
    )
    _require(
        type(layout.cut_edges) is tuple and len(layout.cut_edges) <= MAX_SEAMS,
        "Candidate cut-edge bound exceeded",
        code="RESOURCE_LIMIT",
    )
    _require(
        len(layout.vertices_2d) + len(layout.faces_2d) + len(layout.cut_edges)
        <= budget.policy.max_items,
        "Candidate item limit exceeded",
        code="RESOURCE_LIMIT",
    )
    for vertex in layout.vertices_2d:
        budget.checkpoint()
        _require(type(vertex) is UnfoldedVertex, "Invalid candidate vertex")
        _integer(vertex.source_vertex_id, "source vertex ID")
        _text(vertex.island_id, MAX_ISLAND_ID_CHARACTERS, "island ID")
        _require(
            type(vertex.point_2d) is tuple and len(vertex.point_2d) == 2, "Invalid candidate point"
        )
        for value in vertex.point_2d:
            try:
                finite = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                finite = False
            _require(finite, "Candidate points must be finite non-Boolean numbers")
    cuts = []
    for edge in layout.cut_edges:
        budget.checkpoint()
        _require(type(edge) is tuple and len(edge) == 2, "Invalid cut edge")
        cuts.append(tuple(sorted(_integer(value, "cut vertex ID") for value in edge)))
    _require(
        len(set(cuts)) == len(cuts) and set(cuts) == set(mesh.request.seam_edges),
        "Candidate cuts do not match source seams",
    )
    used: set[int] = set()
    for indices in layout.faces_2d:
        budget.checkpoint()
        _require(
            type(indices) is tuple
            and len(indices) == 3
            and all(
                type(index) is int and 0 <= index < len(layout.vertices_2d) for index in indices
            ),
            "Invalid output face indices",
        )
        used.update(indices)
    _require(used == set(range(len(layout.vertices_2d))), "Candidate has unused vertices")


def _connectivity(  # noqa: C901 - explicit corner equivalence and identity checks
    mesh: ValidatedMesh, layout: UnfoldingLayout, budget: WorkBudget
) -> int:
    parent = list(range(3 * len(mesh.request.faces)))
    corners = {}
    labels = {}
    for island in mesh.islands:
        budget.checkpoint()
        # ValidatedMesh publishes sorted island IDs; avoid a whole-island membership/min scan.
        position = bisect_left(island, mesh.request.root_face_id)
        root = (
            mesh.request.root_face_id
            if position < len(island) and island[position] == mesh.request.root_face_id
            else island[0]
        )
        for face_id in island:
            budget.checkpoint()
            labels[face_id] = f"island-{root}"
    root_index = -1
    for index, face in enumerate(mesh.request.faces):
        budget.checkpoint()
        if face.face_id == mesh.request.root_face_id:
            root_index = index
        corners[face.face_id] = {
            source_id: 3 * index + corner for corner, source_id in enumerate(face.vertex_ids)
        }

    def find(index: int) -> int:
        while parent[index] != index:
            budget.checkpoint()
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    seams = set(mesh.request.seam_edges)
    for edge in mesh.edges:
        budget.checkpoint()
        if len(edge.face_ids) != 2 or edge.vertex_ids in seams:
            continue
        left, right = edge.face_ids
        for source_id in edge.vertex_ids:
            a, b = find(corners[left][source_id]), find(corners[right][source_id])
            parent[max(a, b)] = min(a, b)
    classes: dict[int, int] = {}
    indices: dict[int, int] = {}
    for index, face in enumerate(mesh.request.faces):
        budget.checkpoint()
        for corner, (source_id, output_index) in enumerate(
            zip(face.vertex_ids, layout.faces_2d[index], strict=True)
        ):
            budget.checkpoint()
            vertex = layout.vertices_2d[output_index]
            _require(
                vertex.source_vertex_id == source_id and vertex.island_id == labels[face.face_id],
                "Source corner or island identity mismatch",
                face_ids=(face.face_id,),
            )
            equivalence = find(3 * index + corner)
            _require(
                classes.setdefault(equivalence, output_index) == output_index,
                "Uncut corners must share an output index",
                face_ids=(face.face_id,),
            )
            _require(
                indices.setdefault(output_index, equivalence) == equivalence,
                "Separate seam corners cannot be welded",
                face_ids=(face.face_id,),
            )
    _require(root_index >= 0, "Requested root face is missing")
    return root_index


def _serialized_bound(
    mesh: ValidatedMesh,
    layout: UnfoldingLayout,
    budget: WorkBudget,
    metrics: UnfoldingMetrics | None = None,
    issues: tuple[UnfoldingIssue, ...] = (),
) -> None:
    vertices = []
    for vertex in layout.vertices_2d:
        budget.checkpoint()
        vertices.append(
            {
                "source_vertex_id": vertex.source_vertex_id,
                "island_id": vertex.island_id,
                "point_2d": vertex.point_2d,
            }
        )
    # Reserve the fixed digest/version/envelope fields before numerical work.
    payload: dict[str, Any] = {
        "request_id": mesh.request.request_id,
        "input_digest": "0" * 64,
        "units_label": mesh.request.units_label,
        "solver_version": layout.solver_version,
        "verifier_version": VERIFIER_VERSION,
        "vertices_2d": vertices,
        "faces_2d": layout.faces_2d,
        "cut_edges": layout.cut_edges,
        "metrics": None if metrics is None else vars(metrics),
        "warnings": (),
        "issues": [vars(issue) for issue in issues],
    }
    size = 0
    for chunk in json.JSONEncoder(
        ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).iterencode(payload):
        budget.checkpoint()
        size += len(chunk.encode("utf-8"))
        _require(
            size <= MAX_ADVANCED_RESULT_BYTES, "Result byte bound exceeded", code="RESOURCE_LIMIT"
        )


def _subtract(a: Vector, b: Vector) -> Vector:
    return tuple(x - y for x, y in zip(a, b, strict=True))


def _squared(vector: Vector) -> Fraction:
    return sum((value * value for value in vector), Fraction())


def _cross(a: Vector, b: Vector) -> Vector:
    if len(a) == 2:
        return (a[0] * b[1] - a[1] * b[0],)
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _relative_norm(source_squared: Fraction, output_squared: Fraction) -> float:
    # Rational Gram quantities avoid underflow and cancellation before the dimensionless ratio.
    delta = float((output_squared - source_squared) / source_squared)
    ratio = float(output_squared / source_squared)
    return abs(delta) / (math.sqrt(ratio) + 1)


def _angle(a: Vector, b: Vector) -> float:
    dot = sum((x * y for x, y in zip(a, b, strict=True)), Fraction())
    cross = _cross(a, b)
    scale = max(abs(dot), *(abs(value) for value in cross))
    _require(scale > 0, "Cannot measure a collapsed edge", code="NUMERICAL_FAILURE")
    return math.atan2(math.hypot(*(float(value / scale) for value in cross)), float(dot / scale))


def _numeric(
    mesh: ValidatedMesh, layout: UnfoldingLayout, budget: WorkBudget, root_index: int
) -> tuple[tuple[float, float, float], tuple[UnfoldingIssue, ...], list[tuple[Point2, ...]]]:
    source = {}
    for vertex in mesh.request.vertices:
        budget.checkpoint()
        source[vertex.vertex_id] = tuple(Fraction(value) for value in vertex.point)
    output = []
    for flat_vertex in layout.vertices_2d:
        budget.checkpoint()
        output.append(cast(Point2, tuple(Fraction(value) for value in flat_vertex.point_2d)))
    root = [output[index] for index in layout.faces_2d[root_index]]
    _require(
        root[0] == (0, 0) and root[1][1] == 0 and root[1][0] > 0 and root[2][1] > 0,
        "Requested root anchor or orientation changed",
        face_ids=(mesh.request.root_face_id,),
    )
    maxima = [0.0, 0.0, 0.0]
    issues = []
    triangles = []
    for face, indices in zip(mesh.request.faces, layout.faces_2d, strict=True):
        budget.checkpoint()
        original = tuple(source[vertex_id] for vertex_id in face.vertex_ids)
        flat = tuple(output[index] for index in indices)
        triangles.append(flat)
        area_2d = _cross(_subtract(flat[1], flat[0]), _subtract(flat[2], flat[0]))[0]
        if area_2d <= 0:
            issues.append(
                UnfoldingIssue(
                    "FLIPPED_FACE", (face.face_id,), "Triangle orientation is flipped or collapsed"
                )
            )
        else:
            try:
                edge_error = 0.0
                angle_error = 0.0
                for index in range(3):
                    budget.checkpoint()
                    before = _subtract(original[(index + 1) % 3], original[index])
                    after = _subtract(flat[(index + 1) % 3], flat[index])
                    edge_error = max(edge_error, _relative_norm(_squared(before), _squared(after)))
                    angle_error = max(
                        angle_error,
                        abs(
                            _angle(before, _subtract(original[(index + 2) % 3], original[index]))
                            - _angle(after, _subtract(flat[(index + 2) % 3], flat[index]))
                        ),
                    )
                area_error = _relative_norm(
                    _squared(
                        _cross(
                            _subtract(original[1], original[0]), _subtract(original[2], original[0])
                        )
                    ),
                    area_2d * area_2d,
                )
                measured = (edge_error, area_error, angle_error)
                _require(
                    all(math.isfinite(value) for value in measured),
                    "Non-finite numerical verification",
                    code="NUMERICAL_FAILURE",
                )
                maxima = [max(old, new) for old, new in zip(maxima, measured, strict=True)]
                if any(value > ERROR_LIMIT for value in measured):
                    issues.append(
                        UnfoldingIssue(
                            "DISTORTION", (face.face_id,), "Rigid triangle error exceeds 1e-9"
                        )
                    )
            except (OverflowError, ZeroDivisionError):
                issues.append(
                    UnfoldingIssue(
                        "NUMERICAL_FAILURE", (face.face_id,), "Numerical evaluation is not finite"
                    )
                )
        _require(
            len(issues) <= MAX_RESULT_ISSUES, "Diagnostic bound exceeded", code="RESOURCE_LIMIT"
        )
    return (
        (maxima[0], maxima[1], maxima[2]),
        tuple(issues),
        triangles,
    )


def _orient(a: Point2, b: Point2, c: Point2) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _positive_intersection(
    left: tuple[Point2, ...], right: tuple[Point2, ...], budget: WorkBudget
) -> bool:
    """Exact convex half-plane clipping distinguishes boundary contact from positive area."""
    polygon = list(left)
    for index in range(3):
        budget.checkpoint()
        a, b = right[index], right[(index + 1) % 3]
        clipped = []
        if not polygon:
            return False
        previous = polygon[-1]
        before = _orient(a, b, previous)
        for current in polygon:
            budget.checkpoint()
            after = _orient(a, b, current)
            if (before >= 0) != (after >= 0):
                ratio = before / (before - after)
                clipped.append(
                    (
                        previous[0] + ratio * (current[0] - previous[0]),
                        previous[1] + ratio * (current[1] - previous[1]),
                    )
                )
            if after >= 0:
                clipped.append(current)
            previous, before = current, after
        polygon = clipped
    return (
        bool(polygon)
        and abs(
            sum(
                (
                    polygon[index - 1][0] * point[1] - polygon[index - 1][1] * point[0]
                    for index, point in enumerate(polygon)
                ),
                Fraction(),
            )
        )
        > 0
    )


def _overlaps(  # noqa: C901 - bounded sweep and exact candidate predicates
    mesh: ValidatedMesh, triangles: list[tuple[Point2, ...]], budget: WorkBudget
) -> None:
    boxes: list[tuple[tuple[Fraction, Fraction], ...]] = []
    minimums: list[Fraction] = []
    maximums: list[Fraction] = []
    extents: list[Fraction] = []
    for triangle in triangles:
        budget.checkpoint()
        box = tuple(
            (min(point[axis] for point in triangle), max(point[axis] for point in triangle))
            for axis in range(2)
        )
        if not boxes:
            minimums = [bounds[0] for bounds in box]
            maximums = [bounds[1] for bounds in box]
            extents = [high - low for low, high in box]
        else:
            for axis in range(2):
                minimums[axis] = min(minimums[axis], box[axis][0])
                maximums[axis] = max(maximums[axis], box[axis][1])
                extents[axis] = max(extents[axis], box[axis][1] - box[axis][0])
        boxes.append(box)
    spans = [maximums[axis] - minimums[axis] for axis in range(2)]
    sweep, secondary = (0, 1) if spans[0] >= spans[1] else (1, 0)
    low = minimums[secondary]
    span = spans[secondary]
    extent = extents[secondary]
    # ponytail: at most 64 adaptive sweep buckets; spatial trees if measured scale needs grow.
    count = min(64, max(1, int(span / extent)))

    def bins(index: int) -> range:
        return range(
            min(count - 1, int((boxes[index][secondary][0] - low) * count // span)),
            min(count - 1, int((boxes[index][secondary][1] - low) * count // span)) + 1,
        )

    buckets: dict[int, set[int]] = defaultdict(set)
    expiry: list[tuple[Fraction, int]] = []
    for index in sorted(range(len(boxes)), key=lambda item: (boxes[item][sweep][0], item)):
        budget.checkpoint()
        while expiry and expiry[0][0] < boxes[index][sweep][0]:
            _, expired = heappop(expiry)
            for bucket in bins(expired):
                budget.checkpoint()
                buckets[bucket].remove(expired)
        candidates = set()
        for bucket in bins(index):
            budget.checkpoint()
            for candidate in buckets[bucket]:
                budget.checkpoint()
                candidates.add(candidate)
        for other in sorted(candidates):
            budget.checkpoint()
            if (
                boxes[index][secondary][1] < boxes[other][secondary][0]
                or boxes[other][secondary][1] < boxes[index][secondary][0]
            ):
                continue
            if _positive_intersection(triangles[index], triangles[other], budget):
                pair = tuple(
                    sorted((mesh.request.faces[index].face_id, mesh.request.faces[other].face_id))
                )
                raise _LayoutRejectedError(
                    "OVERLAP", "Output triangles overlap with positive area", pair
                )
        for bucket in bins(index):
            budget.checkpoint()
            buckets[bucket].add(index)
        heappush(expiry, (boxes[index][sweep][1], index))


def verify_layout(
    mesh: ValidatedMesh, layout: UnfoldingLayout, *, budget: WorkBudget
) -> LayoutVerification | BoundedExecutionFailure:
    """Release metrics only after topology, reversible edge geometry, and global overlap pass."""
    try:
        budget.checkpoint(0)
        _shape(mesh, layout, budget)
        root_index = _connectivity(mesh, layout, budget)
        _serialized_bound(mesh, layout, budget)
        errors, issues, triangles = _numeric(mesh, layout, budget, root_index)
        if issues:
            _serialized_bound(mesh, layout, budget, issues=issues)
            budget.checkpoint(0)
            return LayoutVerification(False, None, issues)
        _overlaps(mesh, triangles, budget)
        measured = UnfoldingMetrics(errors[0], errors[1], errors[2], 0, len(mesh.islands))
        _serialized_bound(mesh, layout, budget, measured)
        budget.checkpoint(0)
        return LayoutVerification(True, measured, ())
    except BoundedExecutionInterrupted as error:
        return error.failure
    except _LayoutRejectedError as error:
        return _finish_rejection((error.issue,), budget)
    except MeshValidationError:
        return _finish_rejection(
            (UnfoldingIssue("INVALID_LAYOUT", (), "Candidate fields are invalid"),), budget
        )
    except ValueError:
        return _finish_rejection(
            (UnfoldingIssue("RESOURCE_LIMIT", (), "Fixed work or serialization limit exceeded"),),
            budget,
        )


def _finish_rejection(
    issues: tuple[UnfoldingIssue, ...], budget: WorkBudget
) -> LayoutVerification | BoundedExecutionFailure:
    """A pending interruption still wins when an early validation/resource check rejects."""
    try:
        budget.checkpoint(0)
    except BoundedExecutionInterrupted as error:
        return error.failure
    return LayoutVerification(False, None, issues)
