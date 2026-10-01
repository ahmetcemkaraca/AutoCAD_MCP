"""Version 1 immutable AutoCAD-independent drawing context records."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from .validation import validate_record


class _Validated:
    __slots__ = ()

    def __post_init__(self) -> None:
        validate_record(self)


SNAPSHOT_SCHEMA_VERSION = "1.0"
SchemaVersion = Literal["1.0"]
JsonScalar: TypeAlias = str | int | float | bool | None  # noqa: UP040


@dataclass(frozen=True, slots=True)
class Point2D(_Validated):
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Point3D(_Validated):
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class Bounds3D(_Validated):
    minimum: Point3D
    maximum: Point3D


DocumentIdentityScope = Literal["drawing", "session"]


@dataclass(frozen=True, slots=True)
class DocumentIdentity(_Validated):
    document_id: str
    scope: DocumentIdentityScope
    display_name: str
    database_fingerprint_guid: str | None
    path_hash: str | None
    session_document_id: str
    is_saved: bool
    is_read_only: bool


@dataclass(frozen=True, slots=True)
class DrawingFingerprint(_Validated):
    algorithm: Literal["sha256-cad-facts-v1"]
    content_digest: str
    presentation_digest: str
    coverage: Literal["enumerated-entity-facts-v1"]
    complete: Literal[True]
    incomplete_reasons: tuple[str, ...]
    entity_count: int


@dataclass(frozen=True, slots=True)
class SnapshotRef(_Validated):
    snapshot_id: str
    document_id: str
    session_id: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class DrawingUnits(_Validated):
    insunits_code: int
    name: str
    meters_per_unit: float | None


@dataclass(frozen=True, slots=True)
class GeometryTolerance(_Validated):
    linear: float
    angular_radians: float
    source: Literal["drawing_units_default", "request_override"]


@dataclass(frozen=True, slots=True)
class CapabilityIssue(_Validated):
    code: str
    capability: str
    entity_handle: str | None
    member: str | None
    message: str
    required: bool


UnsupportedCapability: TypeAlias = CapabilityIssue  # noqa: UP040

DisplaySpace = Literal["model", "paper", "model_in_paper_viewport"]


@dataclass(frozen=True, slots=True)
class SpaceContext(_Validated):
    display_space: DisplaySpace
    active_layout_name: str
    viewport_object_id: int | None
    viewport_object_id_scope: Literal["session"] | None


@dataclass(frozen=True, slots=True)
class UcsContext(_Validated):
    name: str | None
    origin_wcs: Point3D
    x_axis_wcs: Point3D
    y_axis_wcs: Point3D
    is_orthonormal: bool


ProjectionKind = Literal["parallel", "perspective", "unknown"]


@dataclass(frozen=True, slots=True)
class ViewContext(_Validated):
    center_ucs: Point2D
    target_wcs: Point3D
    direction_wcs: Point3D
    width: float
    height: float
    twist_radians: float
    projection: ProjectionKind
    visual_style: str | None


@dataclass(frozen=True, slots=True)
class ActiveDrawingContext(_Validated):
    space: SpaceContext
    ucs: UcsContext
    view: ViewContext


@dataclass(frozen=True, slots=True)
class EntityIdentity(_Validated):
    handle: str
    object_id: int | None
    object_id_scope: Literal["session"] | None
    object_name: str
    dxf_name: str | None


@dataclass(frozen=True, slots=True)
class EntitySpace(_Validated):
    """Entity frame: model WCS, named paper-layout WCS, or owner-block local coordinates."""

    kind: Literal["model", "paper", "block_definition"]
    layout_name: str | None
    owner_block_handle: str | None


@dataclass(frozen=True, slots=True)
class LayerFacts(_Validated):
    name: str
    is_off: bool
    is_frozen: bool
    is_locked: bool


@dataclass(frozen=True, slots=True)
class StyleFacts(_Validated):
    color_index: int | None
    true_color_rgb: tuple[int, int, int] | None
    linetype: str | None
    linetype_scale: float | None
    lineweight: int | None
    transparency: str | None
    visible: bool | None


@dataclass(frozen=True, slots=True)
class LineGeometry(_Validated):
    kind: Literal["line"]
    start: Point3D
    end: Point3D


@dataclass(frozen=True, slots=True)
class CircleGeometry(_Validated):
    kind: Literal["circle"]
    center: Point3D
    normal: Point3D
    radius: float


@dataclass(frozen=True, slots=True)
class ArcGeometry(_Validated):
    kind: Literal["arc"]
    center: Point3D
    normal: Point3D
    radius: float
    start_angle_radians: float
    end_angle_radians: float


@dataclass(frozen=True, slots=True)
class PolylineGeometry(_Validated):
    kind: Literal["lwpolyline", "polyline"]
    vertices: tuple[Point3D, ...]
    bulges: tuple[float, ...]
    closed: bool


@dataclass(frozen=True, slots=True)
class PointGeometry(_Validated):
    kind: Literal["point"]
    position: Point3D


@dataclass(frozen=True, slots=True)
class BlockReferenceGeometry(_Validated):
    kind: Literal["block_reference"]
    insertion: Point3D
    normal: Point3D
    rotation_radians: float
    scale_xyz: Point3D


@dataclass(frozen=True, slots=True)
class UnsupportedGeometry(_Validated):
    kind: Literal["unsupported"]
    object_name: str


GeometryFacts: TypeAlias = (  # noqa: UP040
    LineGeometry
    | CircleGeometry
    | ArcGeometry
    | PolylineGeometry
    | PointGeometry
    | BlockReferenceGeometry
    | UnsupportedGeometry
)


@dataclass(frozen=True, slots=True)
class BlockFacts(_Validated):
    effective_name: str
    definition_handle: str | None
    attribute_values: Mapping[str, str]
    is_dynamic: bool | None


@dataclass(frozen=True, slots=True)
class TextFacts(_Validated):
    plain_text: str
    raw_text: str | None
    style_name: str | None
    height: float | None
    rotation_radians: float | None
    insertion: Point3D | None


@dataclass(frozen=True, slots=True)
class DimensionFacts(_Validated):
    measurement: float | None
    dimension_text: str | None
    style_name: str | None
    text_position: Point3D | None


RelationshipKind = Literal[
    "same_owner", "bbox_intersects", "bbox_contains", "bbox_within", "endpoint_touches", "parallel"
]


@dataclass(frozen=True, slots=True)
class RelationshipFact(_Validated):
    kind: RelationshipKind
    source_handle: str
    target_handle: str
    tolerance: float | None
    measured_value: float | None


@dataclass(frozen=True, slots=True)
class CadFactEvidence(_Validated):
    fact_path: str
    source: Literal["autocad_com"]
    member: str
    status: Literal["observed", "unavailable"]


@dataclass(frozen=True, slots=True)
class EntityContext(_Validated):
    identity: EntityIdentity
    space: EntitySpace
    layer: LayerFacts
    style: StyleFacts
    geometry: GeometryFacts
    bounds: Bounds3D | None
    block: BlockFacts | None
    text: TextFacts | None
    dimension: DimensionFacts | None
    relationships: tuple[RelationshipFact, ...]
    fact_evidence: tuple[CadFactEvidence, ...]
    capability_issues: tuple[CapabilityIssue, ...]
    state_digest: str


InterpretationState = Literal["confirmed", "inferred", "unknown"]


@dataclass(frozen=True, slots=True)
class SemanticEvidenceRef(_Validated):
    evidence_id: str
    kind: Literal["cad_fact", "client_visual_observation", "user_confirmation"]
    fact_path: str | None
    observation: str | None


@dataclass(frozen=True, slots=True)
class SemanticInterpretation(_Validated):
    interpretation_id: str
    subject_handles: tuple[str, ...]
    label: str
    state: InterpretationState
    confidence: float | None
    evidence: tuple[SemanticEvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class EntityQueryFilters(_Validated):
    spaces: tuple[Literal["model", "paper", "block_definition"], ...]
    layout_names: tuple[str, ...]
    entity_types: tuple[str, ...]
    layer_names: tuple[str, ...]
    layer_globs: tuple[str, ...]
    handles: tuple[str, ...]
    intersects_wcs: Bounds3D | None


@dataclass(frozen=True, slots=True)
class PageInfo(_Validated):
    page_size: int
    returned: int
    has_more: bool
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SnapshotMaterialization(_Validated):
    builder_version: Literal["snapshot-builder-v1"]
    complete: Literal[True]
    entity_count: int
    relationship_count: int
    canonical_byte_count: int
    revision_token_digest: str


@dataclass(frozen=True, slots=True)
class DrawingSnapshot(_Validated):
    schema_version: SchemaVersion
    snapshot_id: str
    reference: SnapshotRef
    captured_at: datetime
    document: DocumentIdentity
    fingerprint: DrawingFingerprint
    units: DrawingUnits
    tolerance: GeometryTolerance
    active_context: ActiveDrawingContext
    entities: tuple[EntityContext, ...]
    capability_issues: tuple[CapabilityIssue, ...]
    materialization: SnapshotMaterialization


@dataclass(frozen=True, slots=True)
class AnalyzeDrawingResult(_Validated):
    schema_version: SchemaVersion
    source: SnapshotRef
    document: DocumentIdentity
    fingerprint: DrawingFingerprint
    filters: EntityQueryFilters
    entities: tuple[EntityContext, ...]
    interpretations: tuple[SemanticInterpretation, ...]
    page: PageInfo
    snapshot_repository_state: Literal["stored"]


GeometryKind = Literal[
    "line", "circle", "arc", "lwpolyline", "polyline", "point", "block_reference", "unsupported"
]


@dataclass(frozen=True, slots=True)
class LayerSummary(_Validated):
    name: str


@dataclass(frozen=True, slots=True)
class GeometrySummary(_Validated):
    kind: GeometryKind


@dataclass(frozen=True, slots=True)
class EntitySummary(_Validated):
    identity: EntityIdentity
    space: EntitySpace
    layer: LayerSummary
    geometry: GeometrySummary
    bounds: Bounds3D | None
    state_digest: str
    capability_issues: tuple[CapabilityIssue, ...]


@dataclass(frozen=True, slots=True)
class EntityContextBatch(_Validated):
    schema_version: SchemaVersion
    revision_token_digest: str
    document: DocumentIdentity
    entities: tuple[EntityContext, ...]
    capability_issues: tuple[CapabilityIssue, ...]
