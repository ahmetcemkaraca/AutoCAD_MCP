"""Immutable mesh and result contracts; strict canonical request decoding."""

import json
import math
import unicodedata
from dataclasses import dataclass
from typing import Final, TypeAlias, cast

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_REQUEST_BYTES,
    MAX_JSON_INTEGER,
    BoundedExecutionFailure,
    BoundedExecutionPolicy,
    WorkBudget,
)

MAX_VERTICES: Final = 2_000
MAX_FACES: Final = 4_000
MAX_SEAMS: Final = 6_000
MAX_RESULT_ISSUES: Final = 1_000
MAX_ISSUE_FACE_IDS: Final = 2
MAX_ISSUE_CODE_CHARACTERS: Final = 64
MAX_ISSUE_MESSAGE_CHARACTERS: Final = 256
MAX_RESULT_WARNINGS: Final = 16
MAX_WARNING_CHARACTERS: Final = 256
MAX_VERSION_CHARACTERS: Final = 64
# Island labels are ASCII 'island-{root_face_id}', at most 23 bytes.
MAX_ISLAND_ID_CHARACTERS: Final = 23


@dataclass(frozen=True)
class MeshVertex:
    vertex_id: int
    point: tuple[float, float, float]


@dataclass(frozen=True)
class MeshFace:
    face_id: int
    vertex_ids: tuple[int, int, int]


@dataclass(frozen=True)
class UnfoldingRequest:
    request_id: str
    units_label: str
    vertices: tuple[MeshVertex, ...]
    faces: tuple[MeshFace, ...]
    seam_edges: tuple[tuple[int, int], ...]
    root_face_id: int
    policy: BoundedExecutionPolicy


@dataclass(frozen=True)
class UnfoldedVertex:
    source_vertex_id: int
    island_id: str
    point_2d: tuple[float, float]


@dataclass(frozen=True)
class UnfoldingMetrics:
    max_relative_edge_error: float
    max_relative_area_error: float
    max_angle_error_radians: float
    overlap_pair_count: int
    island_count: int


@dataclass(frozen=True)
class UnfoldingIssue:
    code: str
    face_ids: tuple[int, ...]
    message: str


@dataclass(frozen=True)
class UnfoldingLayout:
    solver_version: str
    vertices_2d: tuple[UnfoldedVertex, ...]
    faces_2d: tuple[tuple[int, int, int], ...]
    cut_edges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class LayoutVerification:
    accepted: bool
    metrics: UnfoldingMetrics | None
    issues: tuple[UnfoldingIssue, ...]


@dataclass(frozen=True)
class UnfoldingResult:
    request_id: str
    input_digest: str
    units_label: str
    solver_version: str
    verifier_version: str
    vertices_2d: tuple[UnfoldedVertex, ...]
    faces_2d: tuple[tuple[int, int, int], ...]
    cut_edges: tuple[tuple[int, int], ...]
    metrics: UnfoldingMetrics
    warnings: tuple[str, ...]
    issues: tuple[UnfoldingIssue, ...]


UnfoldingResponse: TypeAlias = UnfoldingResult | BoundedExecutionFailure  # noqa: UP040


class MeshValidationError(ValueError):
    """A redacted, structured strict-schema/topology/resource rejection."""

    def __init__(
        self, code: str, message: str, *, issues: tuple[UnfoldingIssue, ...] = ()
    ) -> None:
        if type(issues) is not tuple or len(issues) > MAX_RESULT_ISSUES:
            raise MeshValidationError("RESOURCE_LIMIT", "Diagnostic count bound exceeded")
        self.code = code
        self.issues = issues
        super().__init__(message)


def _object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or len(value) != len(fields) or set(value) != fields:
        raise MeshValidationError("INVALID_ARGUMENT", f"{label} has invalid fields")
    return cast(dict[str, object], value)


def _integer(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_JSON_INTEGER:
        raise MeshValidationError("INVALID_ARGUMENT", f"{label} must be a bounded integer")
    return value


def _text(value: object, maximum: int, label: str) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= maximum
        or any(unicodedata.category(char) in ("Cc", "Cs") for char in value)
    ):
        raise MeshValidationError("INVALID_ARGUMENT", f"{label} has invalid text")
    return value


def _array(value: object, minimum: int, maximum: int, label: str) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise MeshValidationError("RESOURCE_LIMIT", f"{label} exceeds its item limit")
    return cast(list[object], value)


def _point(value: object) -> tuple[float, float, float]:
    values = _array(value, 3, 3, "point")
    point = []
    for coordinate in values:
        try:
            if type(coordinate) not in (int, float) or not math.isfinite(cast(float, coordinate)):
                raise ValueError
            number = float(cast(float, coordinate))
        except (ValueError, OverflowError) as error:
            raise MeshValidationError("INVALID_ARGUMENT", "point must be finite numbers") from error
        point.append(number if number else 0.0)
    return cast(tuple[float, float, float], tuple(point))


def _checkpoint(budget: WorkBudget | None) -> None:
    if budget is not None:
        try:
            budget.checkpoint()
        except ValueError as error:
            raise MeshValidationError("RESOURCE_LIMIT", "Fixed iteration limit exceeded") from error


def _enforce_request_bytes(payload: object, budget: WorkBudget | None) -> None:
    size = 0
    try:
        encoder = json.JSONEncoder(
            ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        )
        for chunk in encoder.iterencode(payload):
            _checkpoint(budget)
            size += len(chunk.encode("utf-8"))
            if size > MAX_ADVANCED_REQUEST_BYTES:
                raise MeshValidationError("RESOURCE_LIMIT", "Request byte limit exceeded")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        if isinstance(error, MeshValidationError):
            raise
        raise MeshValidationError("INVALID_ARGUMENT", "Request must be finite JSON data") from error


def decode_policy(value: object) -> BoundedExecutionPolicy:
    """Decode only the fixed small policy before starting one shared work budget."""
    policy_data = _object(
        value,
        {
            "max_items",
            "max_iterations",
            "deadline_seconds",
            "cancellation_check_interval",
            "deterministic_seed",
        },
        "policy",
    )
    try:
        return BoundedExecutionPolicy(**policy_data)  # type: ignore[arg-type]
    except ValueError as error:
        raise MeshValidationError("RESOURCE_LIMIT", "Invalid bounded execution policy") from error


def decode_request(payload: object, *, budget: WorkBudget | None = None) -> UnfoldingRequest:
    """Reject unknown/over-limit JSON fields, then normalize order and edge direction."""
    if budget is not None:
        budget.checkpoint(0)
    data = _object(
        payload,
        {"request_id", "units_label", "vertices", "faces", "seam_edges", "root_face_id", "policy"},
        "request",
    )
    vertices_data = _array(data["vertices"], 3, MAX_VERTICES, "vertices")
    faces_data = _array(data["faces"], 1, MAX_FACES, "faces")
    seams_data = _array(data["seam_edges"], 0, MAX_SEAMS, "seam_edges")
    policy = decode_policy(data["policy"])
    if len(vertices_data) + len(faces_data) + len(seams_data) > policy.max_items:
        raise MeshValidationError("RESOURCE_LIMIT", "Request exceeds policy item limit")
    _enforce_request_bytes(payload, budget)
    vertices = []
    faces = []
    seams = []
    for value in vertices_data:
        _checkpoint(budget)
        item = _object(value, {"vertex_id", "point"}, "vertex")
        vertices.append(MeshVertex(_integer(item["vertex_id"], "vertex_id"), _point(item["point"])))
    for value in faces_data:
        _checkpoint(budget)
        item = _object(value, {"face_id", "vertex_ids"}, "face")
        ids = tuple(_integer(i, "vertex_ids") for i in _array(item["vertex_ids"], 3, 3, "face"))
        faces.append(
            MeshFace(_integer(item["face_id"], "face_id"), cast(tuple[int, int, int], ids))
        )
    for value in seams_data:
        _checkpoint(budget)
        seam_ids = sorted(_integer(i, "seam edge") for i in _array(value, 2, 2, "seam edge"))
        seams.append((seam_ids[0], seam_ids[1]))
    if (
        len({v.vertex_id for v in vertices}) != len(vertices)
        or len({f.face_id for f in faces}) != len(faces)
        or len(set(seams)) != len(seams)
    ):
        raise MeshValidationError("INVALID_ARGUMENT", "Duplicate IDs or seam edges")
    return UnfoldingRequest(
        _text(data["request_id"], 128, "request_id"),
        _text(data["units_label"], 64, "units_label"),
        tuple(sorted(vertices, key=lambda v: v.vertex_id)),
        tuple(sorted(faces, key=lambda f: f.face_id)),
        tuple(sorted(seams)),
        _integer(data["root_face_id"], "root_face_id"),
        policy,
    )


def _payload(request: UnfoldingRequest, budget: WorkBudget | None = None) -> dict[str, object]:
    vertices: list[dict[str, object]] = []
    faces: list[dict[str, object]] = []
    seams = []
    for vertex in request.vertices:
        _checkpoint(budget)
        vertices.append({"vertex_id": vertex.vertex_id, "point": list(vertex.point)})
    for face in request.faces:
        _checkpoint(budget)
        faces.append({"face_id": face.face_id, "vertex_ids": list(face.vertex_ids)})
    for edge in request.seam_edges:
        _checkpoint(budget)
        seams.append(list(edge))
    return {
        "request_id": request.request_id,
        "units_label": request.units_label,
        "vertices": vertices,
        "faces": faces,
        "seam_edges": seams,
        "root_face_id": request.root_face_id,
        "policy": {
            name: getattr(request.policy, name)
            for name in (
                "max_items",
                "max_iterations",
                "deadline_seconds",
                "cancellation_check_interval",
                "deterministic_seed",
            )
        },
    }


def normalize_request(
    request: UnfoldingRequest, *, budget: WorkBudget | None = None
) -> UnfoldingRequest:
    """Apply identical schema checks to direct dataclass callers; never trust annotations."""
    try:
        if (
            len(request.vertices) > MAX_VERTICES
            or len(request.faces) > MAX_FACES
            or len(request.seam_edges) > MAX_SEAMS
        ):
            raise MeshValidationError("RESOURCE_LIMIT", "Mesh item limit exceeded")
        return decode_request(_payload(request, budget), budget=budget)
    except (AttributeError, TypeError) as error:
        raise MeshValidationError("INVALID_ARGUMENT", "Invalid request model") from error


def request_json(request: UnfoldingRequest) -> str:
    """Canonical finite UTF-8 JSON; elapsed time and host evidence never enter it."""
    return json.dumps(
        _payload(normalize_request(request)),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
