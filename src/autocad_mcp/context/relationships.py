"""Complete fixed relation facts, with bounded spatial and nonlocal candidate discovery."""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from statistics import median
from typing import TypeAlias, cast
from unicodedata import normalize

from .models import (
    ArcGeometry,
    Bounds3D,
    EntityContext,
    GeometryTolerance,
    LineGeometry,
    Point3D,
    PolylineGeometry,
    RelationshipFact,
    RelationshipKind,
)
from .validation import (
    MAX_COMPLETE_RELATIONSHIPS,
    MAX_ENTITY_RELATIONSHIPS,
    MAX_SNAPSHOT_ENTITIES,
    require,
    require_complete_entity,
    validate_record,
)

MAX_GRID_ENTRIES = 200000
MAX_CANDIDATE_PAIRS = 1000000
_MAX_BOX_CELLS = 64
_Point: TypeAlias = tuple[float, float, float]  # noqa: UP040
_Frame: TypeAlias = tuple[str, str]  # noqa: UP040
_Cell: TypeAlias = tuple[int, int, int]  # noqa: UP040


@dataclass(frozen=True, slots=True)
class RelationshipOptions:
    tolerance: GeometryTolerance = GeometryTolerance(1e-6, 1e-6, "drawing_units_default")

    def __post_init__(self) -> None:
        validate_record(self)


@dataclass
class _Work:
    entries: int = 0
    pairs: int = 0

    def insert(self) -> None:
        require(
            self.entries < MAX_GRID_ENTRIES,
            "Relationship index bound exceeded",
            code="COMPLETE_SNAPSHOT_LIMIT",
        )
        self.entries += 1

    def pair(self) -> None:
        require(
            self.pairs < MAX_CANDIDATE_PAIRS,
            "Relationship candidate bound exceeded",
            code="COMPLETE_SNAPSHOT_LIMIT",
        )
        self.pairs += 1


def _xyz(point: Point3D) -> _Point:
    return (float(point.x), float(point.y), float(point.z))


def _frame(entity: EntityContext) -> _Frame:
    space = entity.space
    discriminator = (
        normalize("NFC", normalize("NFC", space.layout_name or "").casefold())
        if space.kind == "paper"
        else (space.owner_block_handle or "" if space.kind == "block_definition" else "")
    )
    return space.kind, discriminator


def _unit(vector: _Point) -> _Point | None:
    scale = max(abs(value) for value in vector)
    if scale == 0:
        return None
    reduced = tuple(value / scale for value in vector)
    length = math.hypot(*reduced)
    return cast(_Point, tuple(value / length for value in reduced))


def _cross(a: _Point, b: _Point) -> _Point:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _endpoints(entity: EntityContext) -> tuple[_Point, ...]:
    geometry = entity.geometry
    if isinstance(geometry, LineGeometry):
        return (_xyz(geometry.start), _xyz(geometry.end))
    if isinstance(geometry, PolylineGeometry) and not geometry.closed and geometry.vertices:
        return (_xyz(geometry.vertices[0]), _xyz(geometry.vertices[-1]))
    if isinstance(geometry, ArcGeometry):
        normal = _unit(_xyz(geometry.normal))
        require(normal is not None, "Arc normal is unavailable", code="SNAPSHOT_INCOMPLETE")
        normal = cast(_Point, normal)
        axis = (
            (0.0, 1.0, 0.0)
            if abs(normal[0]) < 1 / 64 and abs(normal[1]) < 1 / 64
            else (0.0, 0.0, 1.0)
        )
        x = cast(_Point, _unit(_cross(axis, normal)))
        y = cast(_Point, _unit(_cross(normal, x)))
        center = _xyz(geometry.center)
        return tuple(
            cast(
                _Point,
                tuple(
                    center[i] + geometry.radius * (math.cos(angle) * x[i] + math.sin(angle) * y[i])
                    for i in range(3)
                ),
            )
            for angle in (geometry.start_angle_radians, geometry.end_angle_radians)
        )
    return ()


def _direction(entity: EntityContext) -> _Point | None:
    if not isinstance(entity.geometry, LineGeometry):
        return None
    start, end = _xyz(entity.geometry.start), _xyz(entity.geometry.end)
    return _unit(cast(_Point, tuple(b - a for a, b in zip(start, end, strict=True))))


class _Grid:
    """Three concrete indexes share finite cell arithmetic and one entry admission counter."""

    def __init__(self, width: float, work: _Work) -> None:
        self.width = width.as_integer_ratio()
        self.work = work
        self.cells: dict[tuple[_Frame, _Cell], list[int]] = defaultdict(list)

    def cell(self, point: _Point) -> _Cell:
        numerator, denominator = self.width
        return cast(
            _Cell,
            tuple(
                (coordinate.as_integer_ratio()[0] * denominator)
                // (coordinate.as_integer_ratio()[1] * numerator)
                for coordinate in point
            ),
        )

    def insert(self, frame: _Frame, cell: _Cell, index: int) -> None:
        self.work.insert()
        self.cells[frame, cell].append(index)

    def nearby(self, frame: _Frame, point: _Point) -> set[int]:
        cell = self.cell(point)
        return {
            index
            for shift in product((-1, 0, 1), repeat=3)
            for index in self.cells.get(
                (frame, cast(_Cell, tuple(cell[i] + shift[i] for i in range(3)))), ()
            )
        }


def _box_cells(bounds: Bounds3D, grid: _Grid) -> tuple[_Cell, ...] | None:
    low, high = grid.cell(_xyz(bounds.minimum)), grid.cell(_xyz(bounds.maximum))
    spans = tuple(high[i] - low[i] + 1 for i in range(3))
    if math.prod(spans) > _MAX_BOX_CELLS:
        return None
    return tuple(
        cast(_Cell, cell) for cell in product(*(range(low[i], high[i] + 1) for i in range(3)))
    )


def _bbox(a: Bounds3D, b: Bounds3D) -> tuple[bool, bool, bool]:
    amin, amax, bmin, bmax = map(_xyz, (a.minimum, a.maximum, b.minimum, b.maximum))
    intersects = all(amin[i] <= bmax[i] and bmin[i] <= amax[i] for i in range(3))
    contains = all(amin[i] <= bmin[i] and bmax[i] <= amax[i] for i in range(3))
    within = all(bmin[i] <= amin[i] and amax[i] <= bmax[i] for i in range(3))
    return intersects, contains, within


def extract_relationships(
    entities: Sequence[EntityContext], options: RelationshipOptions
) -> tuple[RelationshipFact, ...]:
    require(type(options) is RelationshipOptions, "Invalid relationship options")
    require(
        len(entities) <= MAX_SNAPSHOT_ENTITIES,
        "Entity count exceeds relation bound",
        code="COMPLETE_SNAPSHOT_LIMIT",
    )
    ordered = tuple(
        sorted(
            entities, key=lambda entity: (int(entity.identity.handle, 16), entity.identity.handle)
        )
    )
    require(
        len({entity.identity.handle for entity in ordered}) == len(ordered),
        "Duplicate relationship handle",
        code="SNAPSHOT_INCOMPLETE",
    )
    for entity in ordered:
        require_complete_entity(entity)
    return _extract(ordered, options)


def _extract(
    entities: tuple[EntityContext, ...], options: RelationshipOptions
) -> tuple[RelationshipFact, ...]:
    tolerance = options.tolerance
    work = _Work()
    frames = tuple(_frame(entity) for entity in entities)
    endpoints = tuple(_endpoints(entity) for entity in entities)
    directions = tuple(_direction(entity) for entity in entities)
    extents = [
        max(
            b - a
            for a, b in zip(_xyz(entity.bounds.minimum), _xyz(entity.bounds.maximum), strict=True)
        )
        for entity in entities
        if entity.bounds is not None
    ]
    positive = [extent for extent in extents if extent > 0]
    box_grid = _Grid(float(max(median(positive) if positive else 1.0, tolerance.linear)), work)
    endpoint_grid = _Grid(float(tolerance.linear), work)
    # Conservative roundoff padding is index-only; the actual angle predicate is never relaxed.
    direction_grid = _Grid(float(max(min(tolerance.angular_radians, 2.0), 8 * math.ulp(1.0))), work)
    owners: dict[str, list[int]] = defaultdict(list)
    boxes: dict[_Frame, list[int]] = defaultdict(list)
    large: dict[_Frame, list[int]] = defaultdict(list)
    box_keys: list[tuple[_Cell, ...] | None] = []
    for index, entity in enumerate(entities):
        frame = frames[index]
        owner = entity.space.owner_block_handle
        if owner is not None:
            work.insert()
            owners[owner].append(index)
        cells = _box_cells(entity.bounds, box_grid) if entity.bounds is not None else ()
        box_keys.append(cells)
        if entity.bounds is not None:
            boxes[frame].append(index)
            if cells is None:
                work.insert()
                large[frame].append(index)
            else:
                for cell in cells:
                    box_grid.insert(frame, cell, index)
        for point in endpoints[index]:
            endpoint_grid.insert(frame, endpoint_grid.cell(point), index)
        direction = directions[index]
        if direction is not None:
            direction_grid.insert(frame, direction_grid.cell(direction), index)
    result = []
    outgoing = [0] * len(entities)

    def add(
        kind: RelationshipKind,
        source: int,
        target: int,
        threshold: float | None = None,
        measured: float | None = None,
    ) -> None:
        require(
            outgoing[source] < MAX_ENTITY_RELATIONSHIPS
            and len(result) < MAX_COMPLETE_RELATIONSHIPS,
            "Complete relationship count exceeds bound",
            code="COMPLETE_SNAPSHOT_LIMIT",
        )
        outgoing[source] += 1
        result.append(
            RelationshipFact(
                kind,
                entities[source].identity.handle,
                entities[target].identity.handle,
                threshold,
                measured,
            )
        )

    for source, entity in enumerate(entities):
        frame = frames[source]
        candidates = set(owners.get(entity.space.owner_block_handle or "", ()))
        cells = box_keys[source]
        if entity.bounds is not None:
            candidates.update(large.get(frame, ()))
            if cells is None:
                candidates.update(boxes.get(frame, ()))
            else:
                for cell in cells:
                    candidates.update(box_grid.cells.get((frame, cell), ()))
        for point in endpoints[source]:
            candidates.update(endpoint_grid.nearby(frame, point))
        direction = directions[source]
        if direction is not None:
            candidates.update(direction_grid.nearby(frame, direction))
            candidates.update(
                direction_grid.nearby(frame, cast(_Point, tuple(-value for value in direction)))
            )
        for target in sorted(index for index in candidates if index > source):
            work.pair()
            other = entities[target]
            if (
                entity.space.owner_block_handle is not None
                and entity.space.owner_block_handle == other.space.owner_block_handle
            ):
                add("same_owner", source, target)
            if frame != frames[target]:
                continue
            if entity.bounds is not None and other.bounds is not None:
                intersects, contains, within = _bbox(entity.bounds, other.bounds)
                if intersects:
                    add("bbox_intersects", source, target)
                if contains:
                    add("bbox_contains", source, target)
                    add("bbox_within", target, source)
                if within:
                    add("bbox_contains", target, source)
                    add("bbox_within", source, target)
            if endpoints[source] and endpoints[target]:
                distance = min(
                    math.dist(a, b) for a in endpoints[source] for b in endpoints[target]
                )
                if distance <= tolerance.linear:
                    add("endpoint_touches", source, target, tolerance.linear, distance)
            if direction is not None and directions[target] is not None:
                other_direction = cast(_Point, directions[target])
                angle = math.atan2(
                    math.hypot(*_cross(direction, other_direction)),
                    abs(sum(a * b for a, b in zip(direction, other_direction, strict=True))),
                )
                if angle <= tolerance.angular_radians:
                    add("parallel", source, target, tolerance.angular_radians, angle)
    return tuple(
        sorted(result, key=lambda fact: (fact.kind, fact.source_handle, fact.target_handle))
    )
