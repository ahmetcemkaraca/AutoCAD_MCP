"""Strict embedded two-manifold and seam-forest validation, without solving."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from heapq import heappop, heappush
from typing import TypeAlias, cast

from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding.models import (
    MeshFace,
    MeshValidationError,
    UnfoldingRequest,
    normalize_request,
)

Point: TypeAlias = tuple[Fraction, Fraction, Fraction]  # noqa: UP040
Point2: TypeAlias = tuple[Fraction, Fraction]  # noqa: UP040


@dataclass(frozen=True)
class MeshEdge:
    vertex_ids: tuple[int, int]
    face_ids: tuple[int, ...]


@dataclass(frozen=True)
class ValidatedMesh:
    request: UnfoldingRequest
    edges: tuple[MeshEdge, ...]
    adjacency: tuple[tuple[int, tuple[int, ...]], ...]
    islands: tuple[tuple[int, ...], ...]


def _subtract(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _cross(a: Point, b: Point) -> Point:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def _dot(a: Point, b: Point) -> Fraction:
    return sum((a[i] * b[i] for i in range(3)), Fraction())


def _orient2(a: Point2, b: Point2, c: Point2) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(point: Point2, a: Point2, b: Point2) -> bool:
    return _orient2(a, b, point) == 0 and all(
        min(a[i], b[i]) <= point[i] <= max(a[i], b[i]) for i in range(2)
    )


def _segment_points(a: Point2, b: Point2, c: Point2, d: Point2) -> set[Point2]:
    """Exact closed segment intersections, including collinear endpoints."""
    ab_c, ab_d = _orient2(a, b, c), _orient2(a, b, d)
    cd_a, cd_b = _orient2(c, d, a), _orient2(c, d, b)
    if ab_c * ab_d < 0 and cd_a * cd_b < 0:
        t = cd_a / (cd_a - cd_b)
        return {(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))}
    return {
        point
        for point, start, end in ((a, c, d), (b, c, d), (c, a, b), (d, a, b))
        if _on_segment(point, start, end)
    }


def _inside(point: Point2, triangle: tuple[Point2, ...]) -> bool:
    signs = [_orient2(triangle[i], triangle[(i + 1) % 3], point) for i in range(3)]
    return all(value >= 0 for value in signs) or all(value <= 0 for value in signs)


def _coplanar_excess(
    a: tuple[Point, ...], b: tuple[Point, ...], shared: tuple[Point, ...], normal: Point
) -> bool:
    drop = next(i for i, value in enumerate(normal) if value)

    def project(point: Point) -> Point2:
        coordinates = tuple(point[i] for i in range(3) if i != drop)
        return coordinates[0], coordinates[1]

    left, right = tuple(map(project, a)), tuple(map(project, b))
    permitted = tuple(map(project, shared))
    intersection = {p for p in left if _inside(p, right)}
    intersection.update(p for p in right if _inside(p, left))
    for i in range(3):
        for j in range(3):
            intersection.update(
                _segment_points(left[i], left[(i + 1) % 3], right[j], right[(j + 1) % 3])
            )
    if not permitted:
        return bool(intersection)
    if len(permitted) == 1:
        return any(p != permitted[0] for p in intersection)
    return any(not _on_segment(p, permitted[0], permitted[1]) for p in intersection)


def _plane_cut(triangle: tuple[Point, ...], distances: tuple[Fraction, ...]) -> tuple[Point, ...]:
    points = {point for point, distance in zip(triangle, distances, strict=True) if distance == 0}
    for i in range(3):
        j = (i + 1) % 3
        if distances[i] * distances[j] < 0:
            t = distances[i] / (distances[i] - distances[j])
            points.add(
                cast(
                    Point,
                    tuple(triangle[i][k] + t * (triangle[j][k] - triangle[i][k]) for k in range(3)),
                )
            )
    return tuple(points)


def _intersects_excess(
    a: tuple[Point, ...],
    b: tuple[Point, ...],
    shared: tuple[Point, ...],
    normal_a: Point,
    normal_b: Point,
) -> bool:
    distance_b = tuple(_dot(normal_a, _subtract(point, a[0])) for point in b)
    if all(d > 0 for d in distance_b) or all(d < 0 for d in distance_b):
        return False
    if all(d == 0 for d in distance_b):
        return _coplanar_excess(a, b, shared, normal_a)
    # Distinct planes intersect along a line. A legitimate common mesh edge is that line.
    if len(shared) == 2:
        return False
    distance_a = tuple(_dot(normal_b, _subtract(point, b[0])) for point in a)
    if all(d > 0 for d in distance_a) or all(d < 0 for d in distance_a):
        return False
    cut_a, cut_b = _plane_cut(a, distance_a), _plane_cut(b, distance_b)
    if not cut_a or not cut_b:
        return False
    direction = _cross(normal_a, normal_b)
    axis = next(i for i, value in enumerate(direction) if value)
    low = max(min(p[axis] for p in cut_a), min(p[axis] for p in cut_b))
    high = min(max(p[axis] for p in cut_a), max(p[axis] for p in cut_b))
    if low > high:
        return False
    return not (shared and low == high == shared[0][axis])


def _validate_vertex_links(faces: tuple[MeshFace, ...], budget: WorkBudget) -> None:
    links: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for face in faces:
        budget.checkpoint()
        for i, vertex in enumerate(face.vertex_ids):
            links[vertex].append((face.vertex_ids[(i + 1) % 3], face.vertex_ids[(i + 2) % 3]))
    for edges in links.values():
        neighbors: dict[int, set[int]] = defaultdict(set)
        for a, b in edges:
            budget.checkpoint()
            neighbors[a].add(b)
            neighbors[b].add(a)
        if any(len(adjacent) > 2 for adjacent in neighbors.values()):
            raise MeshValidationError("NON_MANIFOLD_VERTEX", "Vertex link branches")
        visited: set[int] = set()
        pending = [next(iter(neighbors))]
        while pending:
            budget.checkpoint()
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(neighbors[node] - visited)
        degree_one = sum(len(adjacent) == 1 for adjacent in neighbors.values())
        if len(visited) != len(neighbors) or degree_one not in (0, 2):
            raise MeshValidationError("NON_MANIFOLD_VERTEX", "Vertex link is not a path or cycle")


def _components(
    adjacency: dict[int, set[int]], budget: WorkBudget, *, require_forest: bool
) -> tuple[tuple[int, ...], ...]:
    unseen = set(adjacency)
    components = []
    while unseen:
        pending = [min(unseen)]
        component: set[int] = set()
        while pending:
            budget.checkpoint()
            face = pending.pop()
            if face in component:
                continue
            component.add(face)
            unseen.discard(face)
            pending.extend(sorted(adjacency[face] - component, reverse=True))
        if require_forest and sum(len(adjacency[f]) for f in component) != 2 * (len(component) - 1):
            raise MeshValidationError("CYCLIC_ISLAND", "Seams must cut the adjacency into a forest")
        components.append(tuple(sorted(component)))
    return tuple(components)


def _triangle_boxes(
    request: UnfoldingRequest, budget: WorkBudget
) -> dict[int, tuple[tuple[float, float], ...]]:
    coordinates = {v.vertex_id: v.point for v in request.vertices}
    boxes = {}
    for face in request.faces:
        budget.checkpoint()
        triangle = [coordinates[v] for v in face.vertex_ids]
        boxes[face.face_id] = tuple(
            (min(p[i] for p in triangle), max(p[i] for p in triangle)) for i in range(3)
        )
    return boxes


def _check_intersections(
    request: UnfoldingRequest,
    points: dict[int, Point],
    normals: dict[int, Point],
    budget: WorkBudget,
) -> None:
    boxes = _triangle_boxes(request, budget)
    ordered = sorted(request.faces, key=lambda f: (boxes[f.face_id][0][0], f.face_id))
    faces = {face.face_id: face for face in request.faces}
    y_min = Fraction(min(box[1][0] for box in boxes.values()))
    y_span = (Fraction(max(box[1][1] for box in boxes.values())) - y_min) or Fraction(1)

    # ponytail: 64 bounded y buckets; use a spatial tree if measured large-mesh needs grow.
    def y_bins(face_id: int) -> range:
        low, high = boxes[face_id][1]
        return range(
            int((Fraction(low) - y_min) * 63 // y_span),
            int((Fraction(high) - y_min) * 63 // y_span) + 1,
        )

    buckets: dict[int, set[int]] = defaultdict(set)
    expiry: list[tuple[float, int]] = []
    for face in ordered:
        budget.checkpoint()
        box = boxes[face.face_id]
        while expiry and expiry[0][0] < box[0][0]:
            _, expired = heappop(expiry)
            for index in y_bins(expired):
                budget.checkpoint()
                buckets[index].remove(expired)
        candidates: set[int] = set()
        indices = y_bins(face.face_id)
        for index in indices:
            budget.checkpoint()
            candidates.update(buckets[index])
        for other_id in sorted(candidates):
            budget.checkpoint()
            other = faces[other_id]
            other_box = boxes[other_id]
            if any(box[i][1] < other_box[i][0] or other_box[i][1] < box[i][0] for i in (1, 2)):
                continue
            shared_ids = sorted(set(face.vertex_ids) & set(other.vertex_ids))
            if _intersects_excess(
                tuple(points[v] for v in face.vertex_ids),
                tuple(points[v] for v in other.vertex_ids),
                tuple(points[v] for v in shared_ids),
                normals[face.face_id],
                normals[other.face_id],
            ):
                raise MeshValidationError(
                    "SELF_INTERSECTION", "Input triangles intersect excessively"
                )
        for index in indices:
            budget.checkpoint()
            buckets[index].add(face.face_id)
        heappush(expiry, (box[0][1], face.face_id))


def _incidences(
    request: UnfoldingRequest, points: dict[int, Point], budget: WorkBudget
) -> tuple[dict[tuple[int, int], list[tuple[int, int, int]]], dict[int, Point]]:
    if request.root_face_id not in {face.face_id for face in request.faces}:
        raise MeshValidationError("INVALID_ARGUMENT", "Root face does not exist")
    incidences: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    duplicate_keys = set()
    used: set[int] = set()
    normals = {}
    for face in request.faces:
        budget.checkpoint()
        key = tuple(sorted(face.vertex_ids))
        if len(set(key)) != 3 or key in duplicate_keys:
            raise MeshValidationError("INVALID_FACE", "Repeated corners or duplicate triangle")
        duplicate_keys.add(key)
        if any(vertex not in points for vertex in face.vertex_ids):
            raise MeshValidationError("INVALID_ARGUMENT", "Face refers to an unknown vertex")
        used.update(key)
        a, b, c = (points[vertex] for vertex in face.vertex_ids)
        normal = _cross(_subtract(b, a), _subtract(c, a))
        if not any(normal):
            raise MeshValidationError("DEGENERATE_FACE", "Triangle has zero area")
        normals[face.face_id] = normal
        for a_id, b_id in ((key[0], key[1]), (key[1], key[2]), (key[0], key[2])):
            # Recover orientation from the caller's original cyclic order.
            forward = any(
                face.vertex_ids[i] == a_id and face.vertex_ids[(i + 1) % 3] == b_id
                for i in range(3)
            )
            incidences[(a_id, b_id)].append(
                (face.face_id, a_id if forward else b_id, b_id if forward else a_id)
            )
    if used != set(points):
        raise MeshValidationError("INVALID_ARGUMENT", "Mesh contains unused vertices")
    return incidences, normals


def _validate(request: UnfoldingRequest, budget: WorkBudget) -> ValidatedMesh:
    request = normalize_request(request, budget=budget)
    points: dict[int, Point] = {}
    for vertex in request.vertices:
        budget.checkpoint()
        points[vertex.vertex_id] = cast(Point, tuple(Fraction(value) for value in vertex.point))
    incidences, normals = _incidences(request, points, budget)
    adjacency: dict[int, set[int]] = {face.face_id: set() for face in request.faces}
    edges = []
    for edge, incidence in sorted(incidences.items()):
        budget.checkpoint()
        if len(incidence) > 2:
            raise MeshValidationError("NON_MANIFOLD_EDGE", "More than two faces share an edge")
        if len(incidence) == 2:
            left, right = incidence
            if left[1:] == right[1:]:
                raise MeshValidationError("INCONSISTENT_WINDING", "Faces have inconsistent winding")
            adjacency[left[0]].add(right[0])
            adjacency[right[0]].add(left[0])
        edges.append(MeshEdge(edge, tuple(sorted(item[0] for item in incidence))))
    _validate_vertex_links(request.faces, budget)
    if len(_components(adjacency, budget, require_forest=False)) != 1:
        raise MeshValidationError("DISCONNECTED_MESH", "Mesh must be connected")
    for seam in request.seam_edges:
        budget.checkpoint()
        if seam not in incidences:
            raise MeshValidationError("INVALID_SEAM", "Seam must be an existing mesh edge")
        incidence = incidences[seam]
        if len(incidence) == 2:
            left, right = incidence
            adjacency[left[0]].remove(right[0])
            adjacency[right[0]].remove(left[0])
    islands = _components(adjacency, budget, require_forest=True)
    _check_intersections(request, points, normals, budget)
    return ValidatedMesh(
        request,
        tuple(edges),
        tuple((f, tuple(sorted(neighbors))) for f, neighbors in sorted(adjacency.items())),
        islands,
    )


def validate_mesh(
    request: UnfoldingRequest, *, budget: WorkBudget | None = None
) -> ValidatedMesh | BoundedExecutionFailure:
    """Return canonical immutable topology or an interruption; reject unsupported inputs."""
    try:
        return _validate(request, budget if budget is not None else WorkBudget(request.policy))
    except BoundedExecutionInterrupted as error:
        return error.failure
    except MeshValidationError:
        raise
    except ValueError as error:
        raise MeshValidationError("RESOURCE_LIMIT", "Fixed iteration limit exceeded") from error
