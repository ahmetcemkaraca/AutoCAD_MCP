# EPIC-04: Structured Drawing Context

## Status

**Planned.** This epic describes target behavior for roadmap stage 3. It is not evidence that structured context exists. Implementation starts only after the stable MCP core entry gate below is satisfied, and the stage closes only with automated evidence plus the disposable-DWG AutoCAD 2026 evidence defined here.

## Outcome

An explicitly requested analysis produces a versioned, bounded, reproducible `DrawingSnapshot`. The snapshot identifies the active document, separates persistent handles from session-local `ObjectID` values, records active layout/space/UCS/view state, exposes supported entity facts and relationship facts, and reports every unsupported requested capability. `query_entities`, `get_entity_context`, and `analyze_drawing` share the same data contracts, filters, ordering, pagination, and structured errors. Eligible complete snapshots enter one bounded immutable `SnapshotRepository` for downstream capture, edits, and semantics; partial pages never do.

## User value

Users and model clients can reason from CAD facts instead of screen appearance or guessed semantics. They can retrieve a useful page from a large drawing, resume the same ordered query safely, correlate later work with the exact document state, and see when AutoCAD could not supply a property. Future edit plans and architectural semantics receive a stable source snapshot without treating incomplete data as certainty.

## Scope

- Version 1 of `DrawingSnapshot`, `EntityContext`, their supporting value types, and JSON serialization.
- Privacy-preserving document identity for saved and unsaved drawings.
- Separate content and presentation fingerprints with documented coverage and completeness.
- Active model/paper/model-through-paper-viewport state, active layout, UCS, and view metadata.
- Handle-based entity identity with explicitly session-local `ObjectID` metadata.
- Geometry, bounding box, layer, visual style, block, text, dimension, and deterministic relationship facts.
- A separate semantic interpretation envelope that cites fact evidence and never changes CAD facts.
- Exact filters, deterministic ordering, opaque cursors, page limits, per-entity limits, and total payload limits.
- Revision-token-checked `SnapshotBuilder` materialization over 500-entity adapter pages, bounded to 10,000 entities and 32 MiB before response filtering/pagination.
- Structured tool-level and per-property capability failures.
- A bounded process-local `SnapshotRepository` with complete-only insertion, immutable reads, TTL/count/byte limits, and distinct expiry/not-found errors.
- Pure Python models and services, a focused fake adapter, MCP contract tests, and a Windows COM implementation behind the adapter boundary.
- A versioned additive `ContextAutoCADAdapter` protocol, focused fake, and Windows implementation without changing EPIC-03's four-method read-only/status base.
- Read-only AutoCAD 2026 verification against a disposable DWG.

## Out of scope

- Drawing mutation, edit-plan approval, Undo grouping, and deletion.
- Automatic capture or any raster image generation; that belongs to [EPIC-05](EPIC-05-on-demand-visual-capture.md).
- Vision inference, a vision provider, a provider API key, or server-side image interpretation.
- Architectural labels such as wall, room, door, or window. Version 1 may carry client-confirmed or later-stage interpretations, but does not generate domain semantics.
- Complete support for every AutoCAD entity class or every custom object. Unsupported members remain visible as capability issues.
- A full in-memory replica of the AutoCAD object model, database-event subscriptions, or a long-lived snapshot cache.
- Adding context members directly to EPIC-03's four-method read-only/status `AutoCADAdapter` or importing Windows adapter classes from context domain/service code.
- A cryptographic guarantee that every possible DWG database object is unchanged. Fingerprints cover the facts enumerated by this version and publish their completeness.
- AutoCAD LT, Linux-hosted AutoCAD, macOS, or real-installation claims for AutoCAD 2021-2025.

## Prerequisites and entry gate

Roadmap stage 2 must be accepted before implementation lanes fork. The entry-gate review records fresh evidence that:

1. EPIC-02's installable-package migration is accepted: `src/autocad_mcp/server.py` is the sole active MCP server and `mcp.json` starts `uv run python -m autocad_mcp.server`.
2. EPIC-03's `src/autocad_mcp/adapter/protocol.py` is reviewer-accepted and frozen with exactly the four read-only/status `AutoCADAdapter` methods listed under consumed interfaces. It does **not** provide drawing-context records or methods. `src/autocad_mcp/adapter/provider.py` exposes `AdapterProvider.get() -> AutoCADAdapter`.
3. `src/autocad_mcp/core/models.py` exposes `ErrorCode`, `ToolError`, `ToolSuccess`, `ToolFailure`, `ToolResponse`, `response_payload`, and `response_json`; normal logs cannot enter stdio.
4. `src/autocad_mcp/adapter/capabilities.py` exposes the accepted read-only/status `AdapterCapability`, `AdapterCapabilityIssue`, and `AdapterCapabilityReport`. EPIC-04 adds context-specific capability values in its own additive protocol rather than changing the meaning or four-method contract of `AutoCADAdapter`.
5. EPIC-03's adapter-internal `WindowsSessionManager.session(require_document: bool) -> Iterator[AutoCADSession]`, `AutoCADSession`, and delayed `load_com_modules()` behavior are documented and covered by lifecycle tests. Among EPIC-04 files, only `adapter/windows_context.py` may consume that manager.
6. `uv run pytest`, `uv run ruff check src tests`, and the stable-core AutoCAD 2026 smoke command have recorded results.
7. The EPIC-03 exclusive AutoCAD verification lease is available to Windows feature runners; its scope is one interactive AutoCAD session and it releases on normal exit, assertion failure, timeout, and process termination.

These EPIC-03 names are the base integration boundary. CTX-C then adds and freezes the separate `ContextAutoCADAdapter` extension, pure records, fake, and Windows implementation before CTX-D, CTX-E, or CTX-F integrate them. If the base names differ, a small prerequisite change must reconcile them before parallel work begins. No other lane may edit an adapter-extension file or add context methods directly to the four-method `AutoCADAdapter`.

## Design invariants

- Analysis happens only in response to `query_entities`, `get_entity_context`, or `analyze_drawing`; it is not a startup or connection side effect.
- Pure model, validation, fingerprint, pagination, and relationship modules do not import Windows COM packages.
- `adapter/context_protocol.py` and `adapter/fake_context.py` are pure Python. Among EPIC-04 files, only `adapter/windows_context.py` may use COM-facing `AutoCADSession` objects, and it does so exclusively through an injected EPIC-03 `WindowsSessionManager`.
- All coordinates are WCS unless a field name explicitly says `ucs` or `image`.
- Handles are uppercase hexadecimal strings without `0x`; they are persistent only within the lifetime of that entity in that drawing.
- `ObjectID` is diagnostic session data. It is excluded from document identity, content fingerprints, cursors, durable references, and semantic subject references.
- Missing optional values are accompanied by `CapabilityIssue`; the serializer does not silently drop a requested property.
- CAD facts and semantic interpretations remain separate collections. An inference cannot overwrite an observed fact.
- Input order, COM enumeration order, timestamps, page boundaries, and session-local IDs cannot change a version 1 digest.
- Every list and string has a bound. Non-finite coordinates and unbounded entity payloads fail explicitly.
- An `analyze_drawing` cursor is bound to one retained complete snapshot ID plus normalized filters/order/page size. A live `query_entities` cursor is instead bound to an adapter revision-token digest; it never claims a page-derived drawing fingerprint.

## Schemas and bounds

### Versioning rule

`SNAPSHOT_SCHEMA_VERSION` is the string `"1.0"`. Additive optional fields require a documented minor version and golden-fixture update. Removing a field, changing its meaning, changing canonicalization, or changing ordering requires a new major version and new type names or explicit migration. A serializer never emits an unknown version, and a parser rejects an unsupported major version with `UNSUPPORTED_SCHEMA_VERSION`.

### Exact Python data contract

The implementation uses frozen, slotted dataclasses and tuples at the domain boundary. JSON serializers convert datetimes to UTC RFC 3339 strings with millisecond precision and enums/literals to their wire strings.

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

SNAPSHOT_SCHEMA_VERSION = "1.0"
SchemaVersion = Literal["1.0"]
JsonScalar: TypeAlias = str | int | float | bool | None

@dataclass(frozen=True, slots=True)
class Point2D:
    x: float
    y: float

@dataclass(frozen=True, slots=True)
class Point3D:
    x: float
    y: float
    z: float

@dataclass(frozen=True, slots=True)
class Bounds3D:
    minimum: Point3D
    maximum: Point3D

DocumentIdentityScope = Literal["drawing", "session"]

@dataclass(frozen=True, slots=True)
class DocumentIdentity:
    document_id: str
    scope: DocumentIdentityScope
    display_name: str
    database_fingerprint_guid: str | None
    path_hash: str | None
    session_document_id: str
    is_saved: bool
    is_read_only: bool

@dataclass(frozen=True, slots=True)
class DrawingFingerprint:
    algorithm: Literal["sha256-cad-facts-v1"]
    content_digest: str
    presentation_digest: str
    coverage: Literal["enumerated-entity-facts-v1"]
    complete: Literal[True]
    incomplete_reasons: tuple[str, ...]
    entity_count: int

@dataclass(frozen=True, slots=True)
class SnapshotRef:
    snapshot_id: str
    document_id: str
    session_id: str
    fingerprint: str

@dataclass(frozen=True, slots=True)
class DrawingUnits:
    insunits_code: int
    name: str
    meters_per_unit: float | None

@dataclass(frozen=True, slots=True)
class GeometryTolerance:
    linear: float
    angular_radians: float
    source: Literal["drawing_units_default", "request_override"]

@dataclass(frozen=True, slots=True)
class CapabilityIssue:
    code: str
    capability: str
    entity_handle: str | None
    member: str | None
    message: str
    required: bool

UnsupportedCapability: TypeAlias = CapabilityIssue

DisplaySpace = Literal["model", "paper", "model_in_paper_viewport"]

@dataclass(frozen=True, slots=True)
class SpaceContext:
    display_space: DisplaySpace
    active_layout_name: str
    viewport_object_id: int | None
    viewport_object_id_scope: Literal["session"] | None

@dataclass(frozen=True, slots=True)
class UcsContext:
    name: str | None
    origin_wcs: Point3D
    x_axis_wcs: Point3D
    y_axis_wcs: Point3D
    is_orthonormal: bool

ProjectionKind = Literal["parallel", "perspective", "unknown"]

@dataclass(frozen=True, slots=True)
class ViewContext:
    center_ucs: Point2D
    target_wcs: Point3D
    direction_wcs: Point3D
    width: float
    height: float
    twist_radians: float
    projection: ProjectionKind
    visual_style: str | None

@dataclass(frozen=True, slots=True)
class ActiveDrawingContext:
    space: SpaceContext
    ucs: UcsContext
    view: ViewContext

@dataclass(frozen=True, slots=True)
class EntityIdentity:
    handle: str
    object_id: int | None
    object_id_scope: Literal["session"] | None
    object_name: str
    dxf_name: str | None

@dataclass(frozen=True, slots=True)
class EntitySpace:
    kind: Literal["model", "paper", "block_definition"]
    layout_name: str | None
    owner_block_handle: str | None

@dataclass(frozen=True, slots=True)
class LayerFacts:
    name: str
    is_off: bool
    is_frozen: bool
    is_locked: bool

@dataclass(frozen=True, slots=True)
class StyleFacts:
    color_index: int | None
    true_color_rgb: tuple[int, int, int] | None
    linetype: str | None
    linetype_scale: float | None
    lineweight: int | None
    transparency: str | None
    visible: bool | None

@dataclass(frozen=True, slots=True)
class LineGeometry:
    kind: Literal["line"]
    start_wcs: Point3D
    end_wcs: Point3D

@dataclass(frozen=True, slots=True)
class CircleGeometry:
    kind: Literal["circle"]
    center_wcs: Point3D
    normal_wcs: Point3D
    radius: float

@dataclass(frozen=True, slots=True)
class ArcGeometry:
    kind: Literal["arc"]
    center_wcs: Point3D
    normal_wcs: Point3D
    radius: float
    start_angle_radians: float
    end_angle_radians: float

@dataclass(frozen=True, slots=True)
class PolylineGeometry:
    kind: Literal["lwpolyline", "polyline"]
    vertices_wcs: tuple[Point3D, ...]
    bulges: tuple[float, ...]
    closed: bool

@dataclass(frozen=True, slots=True)
class PointGeometry:
    kind: Literal["point"]
    position_wcs: Point3D

@dataclass(frozen=True, slots=True)
class BlockReferenceGeometry:
    kind: Literal["block_reference"]
    insertion_wcs: Point3D
    normal_wcs: Point3D
    rotation_radians: float
    scale_xyz: Point3D

@dataclass(frozen=True, slots=True)
class UnsupportedGeometry:
    kind: Literal["unsupported"]
    object_name: str

GeometryFacts: TypeAlias = (
    LineGeometry | CircleGeometry | ArcGeometry | PolylineGeometry |
    PointGeometry | BlockReferenceGeometry | UnsupportedGeometry
)

@dataclass(frozen=True, slots=True)
class BlockFacts:
    effective_name: str
    definition_handle: str | None
    attribute_values: Mapping[str, str]
    is_dynamic: bool | None

@dataclass(frozen=True, slots=True)
class TextFacts:
    plain_text: str
    raw_text: str | None
    style_name: str | None
    height: float | None
    rotation_radians: float | None
    insertion_wcs: Point3D | None

@dataclass(frozen=True, slots=True)
class DimensionFacts:
    measurement: float | None
    dimension_text: str | None
    style_name: str | None
    text_position_wcs: Point3D | None

RelationshipKind = Literal[
    "same_owner", "bbox_intersects", "bbox_contains", "bbox_within",
    "endpoint_touches", "parallel"
]

@dataclass(frozen=True, slots=True)
class RelationshipFact:
    kind: RelationshipKind
    source_handle: str
    target_handle: str
    tolerance: float | None
    measured_value: float | None

@dataclass(frozen=True, slots=True)
class CadFactEvidence:
    fact_path: str
    source: Literal["autocad_com"]
    member: str
    status: Literal["observed", "unavailable"]

@dataclass(frozen=True, slots=True)
class EntityContext:
    identity: EntityIdentity
    space: EntitySpace
    layer: LayerFacts
    style: StyleFacts
    geometry: GeometryFacts
    bounding_box_wcs: Bounds3D | None
    block: BlockFacts | None
    text: TextFacts | None
    dimension: DimensionFacts | None
    relationships: tuple[RelationshipFact, ...]
    fact_evidence: tuple[CadFactEvidence, ...]
    capability_issues: tuple[CapabilityIssue, ...]
    state_digest: str

InterpretationState = Literal["confirmed", "inferred", "unknown"]

@dataclass(frozen=True, slots=True)
class SemanticEvidenceRef:
    evidence_id: str
    kind: Literal["cad_fact", "client_visual_observation", "user_confirmation"]
    fact_path: str | None
    observation: str | None

@dataclass(frozen=True, slots=True)
class SemanticInterpretation:
    interpretation_id: str
    subject_handles: tuple[str, ...]
    label: str
    state: InterpretationState
    confidence: float | None
    evidence: tuple[SemanticEvidenceRef, ...]

@dataclass(frozen=True, slots=True)
class EntityQueryFilters:
    spaces: tuple[Literal["model", "paper", "block_definition"], ...]
    layout_names: tuple[str, ...]
    entity_types: tuple[str, ...]
    layer_names: tuple[str, ...]
    layer_globs: tuple[str, ...]
    handles: tuple[str, ...]
    intersects_wcs: Bounds3D | None

@dataclass(frozen=True, slots=True)
class PageInfo:
    page_size: int
    returned: int
    has_more: bool
    next_cursor: str | None

@dataclass(frozen=True, slots=True)
class SnapshotMaterialization:
    builder_version: Literal["snapshot-builder-v1"]
    complete: Literal[True]
    entity_count: int
    relationship_count: int
    canonical_byte_count: int
    revision_token_digest: str

@dataclass(frozen=True, slots=True)
class DrawingSnapshot:
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
class AnalyzeDrawingResult:
    schema_version: SchemaVersion
    source: SnapshotRef
    document: DocumentIdentity
    fingerprint: DrawingFingerprint
    filters: EntityQueryFilters
    entities: tuple[EntityContext, ...]
    interpretations: tuple[SemanticInterpretation, ...]
    page: PageInfo
    snapshot_repository_state: Literal["stored"]
```

`DrawingSnapshot` is never an MCP page. It is the complete bounded server-side/downstream fact object produced by `SnapshotBuilder` and retained by `SnapshotRepository`. `AnalyzeDrawingResult` is the MCP-facing filtered page plus `SnapshotRef`; subsequent pages load the same immutable retained snapshot and never rebuild a fingerprint from page contents.

`SnapshotMaterialization.canonical_byte_count` is the UTF-8 canonical serialized size with that single count field omitted, avoiding a self-referential length. `SnapshotBuilder` and `SnapshotRepository` also enforce the 32 MiB limit against the actual full stored bytes including the count field.

`EntitySummary`, used by `query_entities`, is the exact subset `identity`, `space`, `layer.name`, `geometry.kind`, `bounding_box_wcs`, `state_digest`, and `capability_issues`. `EntityContextBatch` contains `schema_version`, the current adapter revision-token digest, `document`, ordered `entities`, and top-level `capability_issues`; it is a bounded live read, not a `DrawingSnapshot`.

### Document identity semantics

- Prefer a normalized AutoCAD database fingerprint GUID when the connected capability exposes one. `document_id` is `dwg_` plus the first 32 lowercase hexadecimal characters of `sha256("drawing-v1\0" + normalized_guid)`.
- If no database GUID is available and the document is saved, hash the Windows path after absolute normalization, slash normalization, Unicode NFC normalization, and case folding. The path itself is not returned or logged. `path_hash` is the full SHA-256 hex digest, `scope` remains `drawing`, and a capability issue records that identity changes if the file moves.
- For an unsaved document, use an adapter-generated UUID held only for that open document. `document_id` is `session_` plus the UUID hex and `scope` is `session`. Reopening an unsaved drawing intentionally creates a different identity.
- `display_name` is the AutoCAD document `Name`, bounded to 255 Unicode code points. `session_document_id` distinguishes two simultaneously open instances even when their persistent drawing identity matches.
- Neither an entity `ObjectID` nor a Python COM proxy identity may enter document identity.

### Complete materialization and revision-token semantics

`AdapterDocumentRevisionToken` is an opaque, session-local read-consistency value, not drawing identity and not a durable fingerprint. The Windows context adapter must produce a new unequal token whenever its documented covered document/entity facts change; if the connected installation cannot provide a trustworthy token for that coverage, complete snapshot building fails `REVISION_TOKEN_UNAVAILABLE`. Raw token values are never logged or exposed through MCP. `SnapshotMaterialization.revision_token_digest` stores only SHA-256 of the accepted token for diagnostic correlation.

`SnapshotBuilder.build(CompleteSnapshotRequest) -> DrawingSnapshot` executes this exact sequence:

1. Acquire one `ContextAutoCADAdapter` and read `revision_before` plus `document_context_before` for the same active document.
2. Call `read_entity_page` repeatedly with the fixed full version-1 include set, empty filters, `page_size=500`, and initially `cursor=None`. Require every page's revision token to equal `revision_before`, `partial` to be false, each non-final page to contain 1-500 records, and cursors to be non-repeating.
3. Normalize and map records as pages arrive, reject duplicate handles, and stop with `COMPLETE_SNAPSHOT_LIMIT` before retaining entity 10,001 or exceeding 32 MiB of canonical complete-snapshot bytes. A 500-entity response limit never truncates this internal loop.
4. Require the final page to have `next_cursor=None`, then read `revision_after` and `document_context_after`. Reject `SNAPSHOT_CHANGED_DURING_READ` unless `revision_before`, every page token, and `revision_after` are exactly equal, both contexts have the same document/session identity, and their active space/layout/UCS/view/units fields are equal.
5. Sort the full 0-10,000 entity set canonically, calculate bounded deterministic relationships, calculate every entity state digest, then build the content/presentation fingerprints from the full set only.
6. Serialize the complete object, recheck the 32 MiB bound, set `SnapshotMaterialization(complete=True, entity_count=len(entities), relationship_count=..., canonical_byte_count=..., revision_token_digest=...)`, and return one immutable `DrawingSnapshot`.

Any adapter partial-read issue, missing required fact, repeated cursor, empty non-final page, document switch, token mismatch, entity overflow, relationship overflow, or byte overflow prevents construction and repository insertion. No `DrawingSnapshot` instance represents a partial build.

### Fingerprint semantics

`build_drawing_fingerprint(document, units, tolerance, active_context, entities, issues) -> DrawingFingerprint` performs canonical JSON encoding with sorted keys, UTF-8, no insignificant whitespace, NFC strings, normalized uppercase handles, booleans as JSON booleans, and finite floats formatted from their IEEE-754 value with `format(value, ".17g")`; negative zero becomes `0`.

The content digest includes schema major version, `DocumentIdentity.document_id`, drawing units, tolerance, every entity in the successfully revision-checked complete materialization sorted by `(space kind, casefold(layout name), integer handle value, handle)`, and all observed entity facts except `ObjectID`, fact-evidence source names, capability messages, and response pagination. It includes full-set relationship facts sorted by `(kind, source_handle, target_handle)`. It excludes `session_document_id`, timestamp, active view, active UCS, active layout, adapter/public cursor, page size, request filters, semantic interpretations, revision token, viewport `ObjectID`, and all other session-local IDs. Unsaved drawings remain session-scoped because their `document_id` itself is session-generated; a saved drawing's content digest remains stable across reopen when facts do not change.

The presentation digest includes `document_id`, content digest, active space/layout, UCS, and view. Changing only a zoom, view twist, active layout, or UCS changes `presentation_digest` but not `content_digest`. Changing any covered geometry, layer, style, block attribute, text, dimension, space owner, or supported relationship changes `content_digest`. Changing only `ObjectID` does not.

Every constructed `DrawingSnapshot` has `fingerprint.complete=True` and an empty `incomplete_reasons`. Enumeration failure, limit overflow, missing required property, duplicate handle, revision mismatch, or adapter partial read aborts `SnapshotBuilder` before a `DrawingSnapshot` exists. A later edit implementation may use the content digest as one stale-state signal, but must also revalidate target handles and expected prior values.

`snapshot_id` is `ds1_` plus the first 32 hex characters of SHA-256 over schema major version, fixed version-1 fact coverage, `document_id`, content digest, and presentation digest. It excludes filters, include options, cursors, page size, page boundary, revision token, and `captured_at`. Every `AnalyzeDrawingResult` page for the retained object therefore has the same `SnapshotRef`.

No filtered subset or response page is ever passed to `build_drawing_fingerprint`. `analyze_drawing` filters and paginates the already retained `DrawingSnapshot`. `query_entities` is a separate live paginated read: its result carries a revision-token digest and its cursor binds that digest plus normalized filters/order/page size, but it does not emit a `DrawingFingerprint` or `snapshot_id`. This distinction prevents a page digest from being mistaken for whole-drawing stale-state evidence.

Each `EntityContext.state_digest` is `sha256:<64 lowercase hex>` over the canonical version, handle, entity type, owner space, layer, style, geometry, bounding box, block, text, and dimension facts for that entity. It excludes `ObjectID`, relationships to other entities, evidence messages, and semantics. `SnapshotRef` copies the snapshot ID, `DocumentIdentity.document_id`, `DocumentIdentity.session_document_id`, and `DrawingFingerprint.content_digest`; downstream edit and semantic epics consume this compact reference instead of inventing a second snapshot identity.

### Fact and semantic evidence separation

- `EntityContext` contains only observed or explicitly unavailable CAD properties and deterministic relationships derived from those facts.
- `SemanticInterpretation` is a sibling collection on `AnalyzeDrawingResult`, never a field stored inside fact-only `DrawingSnapshot`. Its `subject_handles` are persistent handles, never `ObjectID` values.
- Pure stage-3 extraction emits no domain labels. It may round-trip client-provided interpretations after validation.
- `confirmed` requires at least one `user_confirmation` evidence item. `inferred` requires at least one evidence item and a finite confidence in `[0.0, 1.0]`. `unknown` uses `confidence=None` and may explain ambiguity in an observation.
- A CAD fact evidence reference uses a JSON Pointer rooted under `/entities/{handle}`. A missing pointer makes the interpretation invalid.
- Client visual evidence remains labelled `client_visual_observation`; it cannot be serialized as `autocad_com` evidence.

### Filters, ordering, pagination, and payload limits

| Constraint | Version 1 bound |
| --- | ---: |
| Default / maximum MCP response page | 100 / 500 entities |
| SnapshotBuilder adapter page size | 500 entities |
| Complete `DrawingSnapshot` entities | 10,000 |
| Downstream semantic handle scope | 2,000 within one retained snapshot |
| Handles in one request | 256 |
| Entity types, layer names, layer globs, layouts | 64 each |
| Filter string or glob length | 128 code points |
| Cursor length / live-query lifetime | 2,048 bytes / 15 minutes |
| Analyze cursor lifetime | no later than retained snapshot's 10-minute expiry |
| Adapter revision token / adapter cursor | 512 / 2,048 bytes |
| Vertices in one entity | 10,000 |
| Block attributes in one entity | 512 |
| Characters in one text entity | 65,536 |
| Relationships per entity / MCP page / complete snapshot | 100 / 10,000 / 100,000 |
| Serialized `EntityContext` | 256 KiB |
| Serialized MCP result | 4 MiB |
| Absolute coordinate or scalar magnitude | `1e15` drawing units |
| Complete `DrawingSnapshot` / repository total | 32 MiB / 128 MiB |
| Live repository snapshots / TTL | 4 / 10 minutes |
| Expired-ID tombstones / tombstone TTL | 8 / 15 minutes |

All numbers must be finite. A `Bounds3D` requires minimum coordinates no greater than maximum coordinates. Handle filters are unique after normalization. Layer globs support only `*`, `?`, and literal characters; no regular expressions. Exact names and globs are ORed within their field and fields are ANDed. `intersects_wcs` uses inclusive WCS axis-aligned bounds.

Entities sort by `(space rank: model, paper, block_definition; casefold(layout); numeric handle; handle)`. `SnapshotBuilder` materializes and relates the full bounded entity set before `analyze_drawing` applies filters and response pagination. Downstream semantic analysis may select at most 2,000 handles, all of which must exist inside that retained complete snapshot. Live `query_entities` applies filters before its adapter/public pages. Relationship extraction uses a deterministic spatial grid and emits sorted, deduplicated pairs. If adding the next response entity would exceed 4 MiB, the MCP page stops before that entity and returns a cursor even when fewer than 500 were returned. An individual entity over 256 KiB returns `PAYLOAD_LIMIT` with its handle and measured size; it is never silently truncated.

`CursorCodec.encode(PageCursor) -> str` and `CursorCodec.decode(str) -> PageCursor` use versioned canonical JSON, base64url, and HMAC-SHA256 with a per-process secret. An analyze cursor contains kind `snapshot`, snapshot ID, normalized filter digest, page size, last sort key, issued-at, and an expiry no later than the retained snapshot's expiry; page continuation reads only `SnapshotRepository`. A query cursor contains kind `live_query`, document/session identity, adapter revision-token digest, normalized filter/include digest, page size, adapter/public continuation keys, issued-at, and expiry; it contains no `DrawingFingerprint`. Invalid signatures return `INVALID_CURSOR`, expiry returns `CURSOR_EXPIRED`, a missing retained snapshot returns its repository error, and a changed live revision token returns `STALE_CURSOR`.

### Complete snapshot repository

`SnapshotRepository` is the single process-local handoff used by EPIC-05 through EPIC-08. `put_complete(snapshot)` accepts only a `DrawingSnapshot` with `fingerprint.complete=True`, `materialization.complete=True`, matching `len(entities)`, `DrawingFingerprint.entity_count`, `SnapshotMaterialization.entity_count`, and counted/recorded relationships, no required capability issue, no duplicate handle, at most 10,000 entities, at most 100,000 relationships, and canonical serialized size at most 32 MiB. It rejects an invalid/partial object with `SNAPSHOT_INCOMPLETE` and a valid complete object beyond entity/relationship/byte bounds with `COMPLETE_SNAPSHOT_LIMIT`; response-page fields are not part of `DrawingSnapshot` and cannot satisfy this interface.

The repository stores canonical bytes and reconstructs frozen tuples/read-only mappings on read, so callers cannot mutate a retained snapshot through a nested `Mapping`. It also calculates identity bytes that exclude `captured_at`, revision token, and response metadata, matching the documented `snapshot_id` inputs. [Decision 0003](../decisions/0003-session-qualified-snapshot-retention.md) qualifies retention by `(snapshot_id, session_id)`: identical facts in the same pair preserve the first payload/expiry; a new session retains its own payload/expiry and counts separately toward all limits. The same ID with different normalized facts in any live session is `SNAPSHOT_ID_COLLISION`. Both `get_complete` and `expires_at` accept optional keyword `session_id`; qualified lookup never falls back to another session, and unqualified lookup succeeds only for one live match (multiple live sessions fail `SNAPSHOT_ID_COLLISION`). Tombstones are pair-qualified; no live match is expired only when a matching tombstone exists. Consumers with a reference/cursor must pass its session. Future ID-only request boundaries add optional `source_session_id` for disambiguation; omission never chooses an arbitrary session. It retains at most 4 live snapshots, 128 MiB total, and 32 MiB per snapshot for 10 minutes from insertion. It purges expired content before each operation; a per-snapshot overflow returns `COMPLETE_SNAPSHOT_LIMIT`, while a fifth live record or total-capacity overflow returns `SNAPSHOT_REPOSITORY_LIMIT` instead of silently evicting a live snapshot. It retains at most 8 content-free expired-ID tombstones for 15 minutes so `get_complete` can distinguish `SNAPSHOT_EXPIRED` from `SNAPSHOT_NOT_FOUND` without retaining drawing facts.

`analyze_drawing` first asks `SnapshotBuilder` for the complete object, inserts it, and only then returns an `AnalyzeDrawingResult` page/reference. A changing, partial, greater-than-10,000-entity, greater-than-100,000-relationship, or greater-than-32-MiB drawing returns a structured failure rather than a partial snapshot reference. Drawings with 501-10,000 entities are read over multiple adapter pages, retained completely, and exposed through multiple maximum-500 response pages. `query_entities` and `get_entity_context` never populate the repository. The singleton repository is composed in `autocad_mcp.runtime` and shared with downstream services; it is not a disk cache and is empty after process restart.

### Capability and error contract

Optional unavailable entity members produce a `CapabilityIssue` with stable `code`, `capability`, `entity_handle`, COM `member`, and actionable `message`. Required failures stop the tool with `ToolFailure`. Version 1 uses these exact `ErrorCode` members:

```python
AUTOCAD_UNAVAILABLE
COM_BUSY
NO_ACTIVE_DOCUMENT
ENTITY_NOT_FOUND
INVALID_ARGUMENT
UNSUPPORTED_SCHEMA_VERSION
UNSUPPORTED_CAPABILITY
INVALID_CURSOR
CURSOR_EXPIRED
STALE_CURSOR
STALE_SNAPSHOT
PAYLOAD_LIMIT
PARTIAL_READ
REVISION_TOKEN_UNAVAILABLE
SNAPSHOT_CHANGED_DURING_READ
COMPLETE_SNAPSHOT_LIMIT
SNAPSHOT_INCOMPLETE
SNAPSHOT_NOT_FOUND
SNAPSHOT_EXPIRED
SNAPSHOT_ID_COLLISION
SNAPSHOT_REPOSITORY_LIMIT
INTERNAL_ERROR
```

EPIC-04 is the sole owner of the serialized core-model `STALE_SNAPSHOT` member and all `SNAPSHOT_*` members above. `STALE_SNAPSHOT` means a caller-supplied complete `SnapshotRef` no longer matches the current document/content precondition; it is distinct from `STALE_CURSOR`, `SNAPSHOT_EXPIRED`, and `SNAPSHOT_CHANGED_DURING_READ`. Later capture, edit, and semantic epics import this exact `ErrorCode.STALE_SNAPSHOT` value and must not add an alias or redefine its wire string.

Retries are limited to the stable-core transient COM-busy policy. Validation, payload, missing-handle, cursor, and unsupported-capability failures are not retried. Exception strings, absolute paths, proprietary text, and COM representations are not written to normal logs.

## Consumed and produced interfaces

### Consumed from stable MCP core

```python
class AdapterProvider:
    def get(self) -> AutoCADAdapter: ...

class AutoCADAdapter(Protocol):
    def status(self) -> ConnectionInfo: ...
    def reconnect(self) -> ConnectionInfo: ...
    def list_entities(self) -> tuple[EntitySummary, ...]: ...
    def get_entity_info(self, object_id: int) -> EntityDetails: ...

class BasicToolService(Protocol):
    async def invoke(self, request: BasicToolInput) -> ToolResponse: ...

@dataclass(frozen=True)
class ToolSuccess:
    data: Mapping[str, JsonValue]

@dataclass(frozen=True)
class ToolFailure:
    error: ToolError

def response_payload(response: ToolResponse) -> dict[str, JsonValue]: ...
def response_json(response: ToolResponse) -> str: ...
```

The existing three-tool read-only `BasicToolService` API remains intact. Context handlers return the same `ToolResponse` envelope and do not import MCP transport internals outside `src/autocad_mcp/server.py` and `src/autocad_mcp/tools/context_tools.py`.

The four read-only/status methods above are the complete consumed EPIC-03 base protocol. `AdapterDocumentContext`, `AdapterEntityFacts`, revision tokens, or capture methods are not attributed to EPIC-03.

### Produced by this epic

```python
CONTEXT_ADAPTER_SCHEMA_VERSION = "1.0"

@dataclass(frozen=True, slots=True)
class AdapterContextIssue:
    code: str
    capability: str
    member: str | None
    entity_handle: str | None
    message: str

@dataclass(frozen=True, slots=True)
class AdapterDocumentIdentity:
    display_name: str
    full_path: str | None
    database_fingerprint_guid: str | None
    session_document_id: str
    is_saved: bool
    is_read_only: bool

@dataclass(frozen=True, slots=True)
class AdapterDocumentContext:
    schema_version: Literal["1.0"]
    identity: AdapterDocumentIdentity
    display_space: Literal["model", "paper", "model_in_paper_viewport"]
    active_layout_name: str
    viewport_object_id: int | None
    ucs: Mapping[str, JsonValue]
    view: Mapping[str, JsonValue]
    units: Mapping[str, JsonValue]
    issues: tuple[AdapterContextIssue, ...]

@dataclass(frozen=True, slots=True)
class ContextInclude:
    geometry: bool
    bounding_box: bool
    visual_style: bool
    block: bool
    text: bool
    dimension: bool

@dataclass(frozen=True, slots=True)
class AdapterDocumentRevisionToken:
    schema_version: Literal["1.0"]
    session_document_id: str
    source: str
    opaque_value: str

@dataclass(frozen=True, slots=True)
class AdapterEntityReadRequest:
    spaces: tuple[str, ...]
    layout_names: tuple[str, ...]
    entity_types: tuple[str, ...]
    layer_names: tuple[str, ...]
    handles: tuple[str, ...]
    intersects_wcs: tuple[float, float, float, float, float, float] | None
    include: ContextInclude
    page_size: int
    cursor: str | None

@dataclass(frozen=True, slots=True)
class AdapterEntityFacts:
    schema_version: Literal["1.0"]
    handle: str
    object_id: int | None
    object_name: str
    dxf_name: str | None
    space_kind: Literal["model", "paper", "block_definition"]
    layout_name: str | None
    owner_block_handle: str | None
    layer: Mapping[str, JsonValue]
    style: Mapping[str, JsonValue]
    geometry: Mapping[str, JsonValue]
    bounding_box_wcs: tuple[float, float, float, float, float, float] | None
    block: Mapping[str, JsonValue] | None
    text: Mapping[str, JsonValue] | None
    dimension: Mapping[str, JsonValue] | None
    issues: tuple[AdapterContextIssue, ...]

@dataclass(frozen=True, slots=True)
class AdapterEntityPage:
    schema_version: Literal["1.0"]
    revision_token: AdapterDocumentRevisionToken
    entities: tuple[AdapterEntityFacts, ...]
    next_cursor: str | None
    partial: bool
    issues: tuple[AdapterContextIssue, ...]

class ContextAutoCADAdapter(AutoCADAdapter, Protocol):
    def context_capabilities(self) -> tuple[str, ...]: ...
    def read_document_context(self) -> AdapterDocumentContext: ...
    def read_document_revision(self) -> AdapterDocumentRevisionToken: ...
    def read_entity_page(
        self, request: AdapterEntityReadRequest
    ) -> AdapterEntityPage: ...
    def entity_facts_by_handles(
        self, handles: tuple[str, ...], include: ContextInclude
    ) -> tuple[AdapterEntityFacts, ...]: ...

class ContextAdapterProvider(Protocol):
    def get(self) -> ContextAutoCADAdapter: ...

class StaticContextAdapterProvider:
    def __init__(self, adapter: ContextAutoCADAdapter) -> None: ...
    def get(self) -> ContextAutoCADAdapter: ...

class WindowsContextAdapterProvider:
    def get(self) -> ContextAutoCADAdapter: ...

class FakeContextAutoCADAdapter(FakeAutoCADAdapter): ...
class WindowsContextAutoCADAdapter(WindowsAutoCADAdapter): ...

class Clock(Protocol):
    def now(self) -> datetime: ...

@dataclass(frozen=True, slots=True)
class CompleteSnapshotRequest:
    schema_version: Literal["1.0"]
    relationship_options: RelationshipOptions

class SnapshotBuildError(Exception):
    code: Literal[
        "REVISION_TOKEN_UNAVAILABLE", "SNAPSHOT_CHANGED_DURING_READ",
        "PARTIAL_READ", "UNSUPPORTED_CAPABILITY", "COMPLETE_SNAPSHOT_LIMIT"
    ]

class SnapshotBuilder:
    def __init__(
        self,
        provider: ContextAdapterProvider,
        *,
        clock: Clock,
        max_entities: int = 10_000,
        max_relationships: int = 100_000,
        max_snapshot_bytes: int = 32 * 1024 * 1024,
        adapter_page_size: int = 500,
    ) -> None: ...
    def build(self, request: CompleteSnapshotRequest) -> DrawingSnapshot: ...

class SnapshotRepositoryError(Exception):
    code: Literal[
        "SNAPSHOT_INCOMPLETE", "SNAPSHOT_NOT_FOUND", "SNAPSHOT_EXPIRED",
        "SNAPSHOT_ID_COLLISION", "SNAPSHOT_REPOSITORY_LIMIT",
        "COMPLETE_SNAPSHOT_LIMIT"
    ]

class SnapshotRepository(Protocol):
    def put_complete(self, snapshot: DrawingSnapshot) -> None: ...
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...
    def expires_at(self, snapshot_id: str, *, session_id: str | None = None) -> datetime: ...

class InMemorySnapshotRepository:
    def __init__(
        self,
        *,
        clock: Clock,
        ttl_seconds: int = 600,
        max_snapshots: int = 4,
        max_snapshot_bytes: int = 32 * 1024 * 1024,
        max_total_bytes: int = 128 * 1024 * 1024,
        max_expired_tombstones: int = 8,
        tombstone_ttl_seconds: int = 900,
    ) -> None: ...
    def put_complete(self, snapshot: DrawingSnapshot) -> None: ...
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...
    def expires_at(self, snapshot_id: str, *, session_id: str | None = None) -> datetime: ...

class DrawingContextService:
    def __init__(
        self,
        provider: ContextAdapterProvider,
        snapshot_builder: SnapshotBuilder,
        repository: SnapshotRepository,
    ) -> None: ...
    def query_entities(self, request: QueryEntitiesRequest) -> EntityPage: ...
    def get_entity_context(self, request: GetEntityContextRequest) -> EntityContextBatch: ...
    def analyze_drawing(self, request: AnalyzeDrawingRequest) -> AnalyzeDrawingResult: ...

class ContextToolService(Protocol):
    async def invoke_context(self, request: ContextToolInput) -> ToolResponse: ...

def build_document_identity(raw: AdapterDocumentIdentity) -> DocumentIdentity: ...
def map_document_context(raw: AdapterDocumentContext) -> ActiveDrawingContext: ...
def map_entity_context(raw: AdapterEntityFacts) -> EntityContext: ...
def build_drawing_fingerprint(
    document: DocumentIdentity,
    units: DrawingUnits,
    tolerance: GeometryTolerance,
    active_context: ActiveDrawingContext,
    entities: Sequence[EntityContext],
    issues: Sequence[CapabilityIssue],
) -> DrawingFingerprint: ...
def extract_relationships(
    entities: Sequence[EntityContext], options: RelationshipOptions
) -> tuple[RelationshipFact, ...]: ...
def snapshot_to_json(snapshot: DrawingSnapshot) -> dict[str, object]: ...
def snapshot_from_json(value: Mapping[str, object]) -> DrawingSnapshot: ...
def analyze_result_to_json(result: AnalyzeDrawingResult) -> dict[str, object]: ...
```

MCP requests use `schema_version="1.0"`. `query_entities` accepts `filters`, `include`, `page_size`, and a live-query cursor. `get_entity_context` accepts one to 256 `handles` plus `include`. An initial `analyze_drawing` request accepts response filters/include projection, page size, `relationship_options`, and optional validated interpretations; `SnapshotBuilder` still extracts the fixed complete version-1 fact coverage before those response choices apply. A continuation request uses its snapshot cursor to load/page the retained object without touching AutoCAD. `AnalyzeDrawingResult.snapshot_repository_state` is always `stored`; builder/repository failures return a structured `ToolFailure` and never a partial reference.

`adapter/context_protocol.py` is additive: it imports and extends the accepted four-method `AutoCADAdapter` without modifying that protocol. `adapter/fake_context.py` extends the focused EPIC-03 fake and provides the static provider. `adapter/windows_context.py` extends `WindowsAutoCADAdapter`, receives the documented `WindowsSessionManager`, and uses only `session(require_document=True)` and `AutoCADSession`; it must not reimplement COM initialization, cache proxies, or expose them through a record. Runtime imports the Windows provider only inside its factory.

EPIC-05 may import `ContextAutoCADAdapter`, `ActiveDrawingContext`, `Bounds3D`, `CapabilityIssue`, `DocumentIdentity`, `DrawingFingerprint`, `DrawingSnapshot`, `EntityContext`, `Point2D`, `Point3D`, `SnapshotRepository`, `ViewContext`, `DrawingContextService.get_entity_context`, and `build_drawing_fingerprint`. It may not change their version 1 meaning.

## Exact proposed files and ownership

Each path has one owning lane. Other lanes may read it, but concurrent workers must not edit it.

| Owner | File | Responsibility |
| --- | --- | --- |
| CTX-A contracts | `src/autocad_mcp/context/__init__.py` | Public context exports only |
| CTX-A contracts | `src/autocad_mcp/context/models.py` | Frozen version 1 domain types and constants |
| CTX-A contracts | `src/autocad_mcp/context/serialization.py` | Strict JSON parsing and emission |
| CTX-A contracts | `src/autocad_mcp/context/validation.py` | Bounds and cross-field validation |
| CTX-A contracts | `tests/unit/context/test_models.py` | Model/version/validation tests |
| CTX-A contracts | `tests/unit/context/test_serialization.py` | Round-trip and rejection tests |
| CTX-B identity | `src/autocad_mcp/context/identity.py` | Document/handle normalization and identity |
| CTX-B identity | `src/autocad_mcp/context/fingerprint.py` | Canonicalization and both digests |
| CTX-B identity | `src/autocad_mcp/context/pagination.py` | Ordering and signed cursor codec |
| CTX-B identity | `src/autocad_mcp/context/repository.py` | Bounded complete-snapshot store and expiry errors |
| CTX-B identity | `tests/unit/context/test_identity.py` | Saved/unsaved identity tests |
| CTX-B identity | `tests/unit/context/test_fingerprint.py` | Deterministic digest tests |
| CTX-B identity | `tests/unit/context/test_pagination.py` | Cursor and ordering tests |
| CTX-B identity | `tests/unit/context/test_repository.py` | Completeness, immutability, TTL, count, and byte-limit tests |
| CTX-C adapter integration | `src/autocad_mcp/adapter/__init__.py` | Export accepted additive context interfaces without importing Windows modules |
| CTX-C adapter integration | `src/autocad_mcp/adapter/context_protocol.py` | Versioned pure records, `ContextAutoCADAdapter`, and provider protocol |
| CTX-C adapter integration | `src/autocad_mcp/adapter/fake_context.py` | Focused additive fake over `FakeAutoCADAdapter` |
| CTX-C adapter integration | `src/autocad_mcp/adapter/windows_context.py` | Context COM mapping through an injected EPIC-03 `WindowsSessionManager` only |
| CTX-C adapter integration | `src/autocad_mcp/context/adapter_reader.py` | Map pure adapter records and capability issues into context facts |
| CTX-C adapter integration | `tests/adapter/test_context_protocol.py` | Pure record, version, protocol, and provider contracts |
| CTX-C adapter integration | `tests/adapter/test_fake_context.py` | Additive fake ordering, failures, and session variation |
| CTX-C adapter integration | `tests/adapter/test_windows_context_imports.py` | Delayed COM/import isolation for the extension |
| CTX-C adapter integration | `tests/adapter/test_windows_context.py` | Injected-session COM member and cleanup mapping tests |
| CTX-C adapter integration | `tests/unit/context/test_adapter_reader.py` | Raw-record-to-domain mapping and failure tests |
| CTX-C adapter integration | `tests/fixtures/context/raw_entities_v1.json` | Fixed unordered adapter inputs for fake and mapper tests |
| CTX-D service | `src/autocad_mcp/context/relationships.py` | Bounded deterministic fact relationships |
| CTX-D service | `src/autocad_mcp/context/builder.py` | Revision-checked complete snapshot materialization |
| CTX-D service | `src/autocad_mcp/context/service.py` | Query/context/analysis orchestration |
| CTX-D service | `tests/unit/context/test_relationships.py` | Geometry relationship tests |
| CTX-D service | `tests/unit/context/test_builder.py` | Multi-page, revision, partial-read, and complete-limit tests |
| CTX-D service | `tests/unit/context/test_service.py` | Filter/page/capability service tests |
| CTX-E fake/contract | `tests/fixtures/context/snapshot_v1.json` | Golden serialized snapshot |
| CTX-E fake/contract | `tests/fixtures/context/analyze_page_v1.json` | Golden MCP page referencing the snapshot |
| CTX-E fake/contract | `tests/fixtures/context/context_fixture_v1.dxf` | Deterministic text fixture for AutoCAD |
| CTX-E fake/contract | `tests/contract/test_context_tools.py` | MCP schema/success/error/stdio tests |
| CTX-F server | `src/autocad_mcp/tools/context_tools.py` | Request parsing and domain-result shaping |
| CTX-F server | `src/autocad_mcp/core/models.py` | Sole integration owner for `STALE_SNAPSHOT` and all snapshot/context error wire values |
| CTX-F server | `tests/unit/test_mcp_models.py` | Exact enum and deterministic serialized error-envelope regression tests |
| CTX-F server | `src/autocad_mcp/runtime.py` | Compose the accepted adapter and `ContextToolService` |
| CTX-F server | `src/autocad_mcp/server.py` | Register exactly three context tools alongside the three active read-only/status tools |
| CTX-F server | `mcp.json` | Advertise schemas matching registration |
| CTX-F server | `tests/contract/test_server_tool_catalog.py` | Catalog and metadata agreement |
| CTX-G Windows/docs | `tests/integration/windows/test_context_autocad.py` | Full AutoCAD read-only assertions |
| CTX-G Windows/docs | `tests/windows/run_context_autocad_2026.ps1` | Disposable-DWG runner and evidence capture |
| CTX-G Windows/docs | `docs/contracts/drawing-snapshot-v1.md` | Published wire contract and examples |
| CTX-G Windows/docs | `docs/verification/context-autocad-2026.md` | Recorded environment and results |
| CTX-G Windows/docs | `docs/architecture.md` | Move context from target to adopted only after evidence |
| CTX-G Windows/docs | `docs/roadmap.md` | Stage-3 evidence gate/status update |
| CTX-G Windows/docs | `docs/testing.md` | Context test commands and evidence labels |
| CTX-G Windows/docs | `docs/compatibility.md` | Feature-specific AutoCAD 2026 result |

No imported module under `src/mcp_integration/`, `src/enhanced_autocad/`, or `src/testing/mock_autocad.py` is promoted by reference. Useful behavior must be re-expressed through the contracts above and tested.

## Work packages

### CTX-01 — Freeze models, serialization, and bounds

**Owner:** CTX-A contracts. **Depends on:** entry gate only.

1. Write failing tests for schema version rejection, finite numeric validation, handle normalization, tuple immutability, cross-field interpretation evidence, 10,000-vertex acceptance, 10,001-vertex rejection, 256 KiB entity rejection, and exact JSON round-trip.
2. Run `uv run pytest tests/unit/context/test_models.py tests/unit/context/test_serialization.py -v`; expected initial result is import/collection failure because `autocad_mcp.context` does not exist.
3. Implement only the data types, validators, and serializer needed for those tests. Reject unknown input fields so a misspelled property cannot vanish silently.
4. Re-run the same command; expected result is all tests passing.
5. Run `uv run mypy src/autocad_mcp/context/models.py src/autocad_mcp/context/serialization.py src/autocad_mcp/context/validation.py`; expected result is exit code 0.

### CTX-02 — Make identity, fingerprints, and cursors deterministic

**Owner:** CTX-B identity. **Depends on:** CTX-01 public types.

1. Write failing tests proving shuffled complete input has the same digests; changed geometry changes content; changed view changes presentation only; changed `ObjectID`, `session_document_id`, timestamp, filter, page size, or response page does not change the complete digest/snapshot ID; unsaved `document_id` remains session-scoped; snapshot and live-query cursors carry distinct kinds; and HMAC tampering, expiry, stale retained snapshots, and changed live revision tokens produce distinct errors.
2. Run `uv run pytest tests/unit/context/test_identity.py tests/unit/context/test_fingerprint.py tests/unit/context/test_pagination.py -v`; expected initial failures identify missing functions, not environment-dependent COM failures.
3. Implement the exact canonicalization, snapshot-ID, ordering, and cursor rules in this epic with an injected `Clock` and injected cursor secret.
4. Re-run the three files; expected result is all tests passing on Linux and Windows.
5. Run `uv run pytest tests/unit/context/test_fingerprint.py -k "shuffle or object_id or view" --count=50 -v` if the stable-core test dependencies include `pytest-repeat`; otherwise run `for i in 1 2 3 4 5; do uv run pytest tests/unit/context/test_fingerprint.py -q || exit 1; done`. Every run must produce the committed golden digest.

### CTX-02R — Add the bounded complete-snapshot repository

**Owner:** CTX-B identity. **Depends on:** CTX-01 serialization and CTX-02 snapshot identity.

1. Write failing tests for idempotent insert with different `captured_at` but identical identity bytes, same-ID/different-identity collision, immutable nested mappings on read, 600-second expiry, distinct expired/not-found errors, eight expired tombstones, fifth-live-record refusal, 32 MiB per-record refusal, 128 MiB total refusal, and rejection of false/missing materialization completeness, count/byte mismatches, more than 10,000 entities, more than 100,000 relationships, or a required capability issue.
2. Run `uv run pytest tests/unit/context/test_repository.py -v`; expected initial failure is a missing `SnapshotRepository` implementation.
3. Implement `SnapshotRepository`, `SnapshotRepositoryError`, and `InMemorySnapshotRepository` with an injected clock, canonical-byte storage, strict completeness validation, and no background task or disk persistence.
4. Re-run the focused test; expected result is all repository tests passing, including exact accepted boundaries at 32 MiB, 4 records, 128 MiB total, 10,000 entities, and 600 seconds.
5. Run `uv run mypy src/autocad_mcp/context/repository.py tests/unit/context/test_repository.py`; expected result is exit code 0.

### CTX-03 — Add the context adapter extension and Windows implementation

**Owner:** CTX-C adapter integration. **Depends on:** the accepted EPIC-03 protocol/session helper and CTX-01 value rules; can run in parallel with CTX-02/CTX-02R after the additive protocol names are reviewed.

1. Write failing pure tests for schema version `1.0`, immutable revision/page/fact records, 512-byte token and 2,048-byte adapter-cursor limits, additive protocol conformance, provider typing, 1/500/501-record fake paging, non-repeating cursors, stable/changeable revision tokens, two-session `ObjectID` variation, failure/partial injection, and raw-to-domain mapping for active layout/UCS/view, all supported geometry families, WCS bounds, blocks, text, dimensions, duplicate handles, and capability issues.
2. Write failing injected-session tests for revision-token acquisition, each page read, every COM member read, missing optional members, partial enumeration, document switch, COM busy, balanced `WindowsSessionManager.session()` entry/exit, no proxy escape, and no direct `CoInitialize`/`CoUninitialize` call in `windows_context.py`.
3. Run `uv run pytest tests/adapter/test_context_protocol.py tests/adapter/test_fake_context.py tests/adapter/test_windows_context_imports.py tests/adapter/test_windows_context.py tests/unit/context/test_adapter_reader.py -v`; expected initial failures identify the absent extension files.
4. Implement `context_protocol.py` and `fake_context.py` without Windows imports, then implement `windows_context.py` as an additive `WindowsAutoCADAdapter` subclass that receives `WindowsSessionManager`, uses only `session(require_document=True)`, and returns pure records. Implement `adapter_reader.py` without importing `adapter.windows_context`.
5. Re-run the focused command; every page is bounded to 500, every unavailable requested member produces an issue, partial enumeration is explicit, revision tokens are present, and every success/failure exits the injected session-manager context.
6. Run `uv run python -c "import autocad_mcp.adapter.context_protocol, autocad_mcp.adapter.fake_context, autocad_mcp.context.models, autocad_mcp.context.service"` on Linux; expected result is exit code 0 with neither `adapter.windows_context` nor COM modules loaded.
7. Freeze all CTX-C paths before CTX-D/E/F integrate them. Subsequent adapter defect reports return to CTX-C; no other lane edits an adapter-extension file.

### CTX-04 — Implement bounded filtering and relationships

**Owner:** CTX-D service. **Depends on:** CTX-01, CTX-02, CTX-02R, and the frozen CTX-03 extension.

1. Write failing `SnapshotBuilder` tests for 0, 1, 500, 501, and 10,000 entities; exact multi-page order; 10,001-entity rejection; exact 32 MiB acceptance and one-byte-over rejection; 100,001-relationship rejection; repeated/empty-nonfinal cursors; partial page; missing revision token; unequal before/page/after tokens; document/session or active space/layout/UCS/view/units change; duplicate handles; and no fingerprint/repository call after any failure.
2. Write failing service tests for complete build before filtering, complete repository insertion before page response, 501 entities exposed as two pages referencing one snapshot, exact/glob/space/layout/handle/bounds filters over the retained object, maximum-500 pages, deterministic snapshot cursors, 4 MiB response-size early stop, overlarge single response entity, unsupported property propagation, and live-query cursor invalidation by revision-token change without a page-derived fingerprint.
3. Write failing geometry tests for same owner, inclusive bbox intersection/containment, endpoint touch at the supplied tolerance, parallel lines, non-parallel lines, duplicate suppression, stable ordering from shuffled input, and the complete relationship bound.
4. Run `uv run pytest tests/unit/context/test_builder.py tests/unit/context/test_service.py tests/unit/context/test_relationships.py -v`; expected initial result is missing builder/service/relationship behavior.
5. Implement `SnapshotBuildError`, an injected clock, the revision-checked page loop, and complete-set fingerprint in `SnapshotBuilder`, then deterministic spatial-grid relationships and page-only filtering in the service. Do not compute a fingerprint from filtered/page entities or an unbounded all-pairs graph.
6. Re-run the focused tests, then run `uv run pytest tests/unit/context -v`; expected result is all context unit tests passing.

### CTX-05 — Add deterministic fixtures and the focused fake

**Owner:** CTX-E fake/contract. **Depends on:** CTX-01 and the frozen CTX-03 fake/raw fixture; can prepare only the golden snapshot and DXF while CTX-02/CTX-04 run.

1. Consume the CTX-C-owned raw fixture with fixed handles `10`, `20`, `30`, `40`, `50`, and `60`; verify its two fake sessions use different `ObjectID` values and include model/paper line, circle, polyline, block, text, dimension, one unavailable property, and shuffled raw ordering. Do not edit the raw fixture in this lane.
2. Write a failing golden test inside `tests/contract/test_context_tools.py` that uses a fixed UTC clock, fixed cursor secret, and `FakeContextAutoCADAdapter` to compare the retained complete object to `snapshot_v1.json` and the first `AnalyzeDrawingResult` page/reference to `analyze_page_v1.json`.
3. Run `uv run pytest tests/contract/test_context_tools.py -k golden -v`; expected initial result is failure until service integration and the golden output agree.
4. Configure `FakeContextAutoCADAdapter` through its public constructor/failure hooks without editing CTX-C files. Generate the golden once through the real serializer, review it field by field, then keep it static.
5. Re-run the golden test twice with reversed fake enumeration; both runs must match the same fixture bytes.

### CTX-06 — Register and contract-test the MCP tools

**Owner:** CTX-F server. **Depends on:** CTX-02R, CTX-04, and CTX-05.

1. Write failing core-model tests asserting `ErrorCode.STALE_SNAPSHOT.value == "STALE_SNAPSHOT"`, every owned snapshot code is unique, and `response_json(ToolFailure(ToolError(code=ErrorCode.STALE_SNAPSHOT, ...)))` emits the existing deterministic envelope. Write contract tests for tool catalog/schema agreement, valid calls, all validation codes, cursor resumption, missing handle, unsupported property, 4 MiB bound, stderr-only logging, and zero drawing mutations.
2. Run `uv run pytest tests/unit/test_mcp_models.py tests/contract/test_context_tools.py tests/contract/test_server_tool_catalog.py -v`; expected initial failures show the snapshot codes and three tools are absent.
3. Compose one `InMemorySnapshotRepository`, inject it into `DrawingContextService`, and share its `SnapshotRepository` interface with downstream service factories. Implement handlers that validate first, call the service, and shape structured results. Register exactly `query_entities`, `get_entity_context`, and `analyze_drawing`, then make `mcp.json` agree.
4. Re-run the focused command; expected result is all tests passing, one canonical `STALE_SNAPSHOT` enum/wire value, and no non-protocol bytes on stdout.
5. Run `uv run pytest tests/contract -v`; expected result is all stable-core and context contract tests passing.

### CTX-07 — Verify a disposable DWG in full AutoCAD 2026

**Owner:** CTX-G Windows/docs. **Depends on:** CTX-01 through CTX-06.

1. Write the Windows integration/runner test before completing adapter support. Assert the runner acquires the EPIC-03 exclusive verification lease with owner `EPIC-04/context-autocad-2026/<pid>` before connecting/opening a fixture, refuses to run while a base/context/capture runner holds it, and releases it in `finally` on success, assertion failure, timeout, and cleanup failure. After acquisition it opens `context_fixture_v1.dxf`, saves it as a uniquely named temporary DWG, closes the seed, reopens the DWG, and records disk SHA-256, `DBMOD`, active context, and entity handles.
2. Run the exact command below. The first run may fail only on explicit unmet assertions or a structured capability result; a modal prompt, source-fixture modification, or unstructured exception is a test-harness defect.
3. Verify `WindowsContextAutoCADAdapter` produces expected facts, stable repeated content digest, changed presentation digest after zoom with unchanged content digest, session-local `ObjectID` exclusion, filters/pages, and capability reporting. If a mapping/lifecycle defect appears, return it to CTX-C for correction and rerun CTX-C focused tests before this gate; CTX-G does not edit adapter-extension files.
4. The runner closes the disposable copy without saving, verifies its on-disk hash is unchanged after the read-only phase, deletes the temporary directory, preserves only redacted JSON evidence under the requested artifact directory, and then releases the lease. Lease release occurs after AutoCAD/temp cleanup but cannot be skipped when either cleanup step fails.
5. Update canonical documentation only from the recorded result. AutoCAD 2021-2025 remain `Targeted, not verified`.

Exact Windows command from a PowerShell prompt with full AutoCAD 2026 installed:

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_context_autocad_2026.ps1 -AutoCADProgId AutoCAD.Application.25.1 -Fixture tests/fixtures/context/context_fixture_v1.dxf -Artifacts .artifacts/context-autocad-2026
```

### CTX-08 — Run the completion gate

**Owner:** integration lead. **Depends on:** CTX-07.

Run, in order:

```bash
uv run pytest tests/unit/context tests/adapter/test_context_protocol.py tests/adapter/test_fake_context.py tests/adapter/test_windows_context_imports.py tests/adapter/test_windows_context.py -v
uv run pytest tests/contract -v
uv run pytest -v
uv run ruff check src tests
uv run mypy src/autocad_mcp
python -m compileall -q src tests
git diff --check
```

Record exact exit codes and test counts. Linux results are labelled `unit tested` or `MCP contract tested`; only CTX-07 can produce the feature-specific label `structured context extraction verified on full AutoCAD 2026`.

## Independent subagent lanes

After CTX-01 freezes the public model names, the integration lead may dispatch these non-overlapping lanes:

```text
CTX-01 contracts
   |-- CTX-02 identity/fingerprint/cursor --> CTX-02R repository --|
   |-- CTX-03 additive adapter extension --------------------------|--> CTX-04 service/relationships
   |                    |                          |          |
   |                    `--> CTX-05 fake/fixtures -|----------|--> CTX-06 MCP
   `----------------------------------------------------------|        |
                                                                       v
                                                              CTX-07 Windows/docs
                                                                       |
                                                                       v
                                                              CTX-08 completion
```

- CTX-02 and CTX-03 are independent after model freeze; CTX-02R follows CTX-02.
- CTX-C exclusively owns `adapter/__init__.py`, `context_protocol.py`, `fake_context.py`, `windows_context.py`, adapter-extension tests, `adapter_reader.py`, and the raw adapter fixture. It consumes but does not edit EPIC-03's `windows_session.py`; all other lanes treat CTX-C paths as read-only.
- CTX-05 consumes the CTX-C raw fixture and authors only the golden snapshot/DXF/contract test; the golden snapshot waits for CTX-04.
- CTX-B exclusively owns `SnapshotRepository`, its in-memory implementation, and repository tests. CTX-D/F consume that frozen interface.
- CTX-04 is the only owner of `SnapshotBuilder`, service orchestration, and relationships.
- CTX-06 is the only owner of server registration and `mcp.json`.
- CTX-07 is the only owner of canonical documentation and real-AutoCAD evidence.
- Every lane hands back a diff and fresh focused-test output. The integration lead reviews contracts before merging a lane and resolves no shared-file edits by blind overwrite.

## Acceptance criteria

1. All three tools emit schema version `1.0` and share exact identity, filter, error, and entity contracts; only complete analysis emits a whole-drawing `SnapshotRef`/`DrawingFingerprint`, while live query pages expose revision-token correlation instead.
2. Complete `DrawingSnapshot` objects contain document identity, active display space/layout, UCS, view, both digests, all bounded entity/relationship facts, capability issues, and complete materialization evidence—but no response-page fields. `AnalyzeDrawingResult` contains only a filtered maximum-500 page plus the retained reference.
3. Handles are the only durable entity reference; every returned `ObjectID` is marked session-local and excluded from identity, fingerprints, cursors, and semantic subjects.
4. Golden complete-snapshot and page fixtures prove deterministic output across adapter enumeration/page boundaries, timestamps, response pages, and fake-session `ObjectID` changes.
5. Content/presentation fingerprints are computed from the complete revision-checked fact set only, include `document_id`, exclude `session_document_id` and every pagination/filter/revision field, and are never synthesized from a query or analysis page.
6. Geometry, layer, style, block, text, dimension, WCS bounding-box, and supported relationship extraction have focused passing tests.
7. CAD facts and semantic interpretations are structurally separate, and evidence/state/confidence validation prevents invented confirmation.
8. Analyze filters apply after complete materialization and before response pagination; live-query filters apply before live pages. Snapshot/live-query cursor kinds and stale checks remain distinct and deterministic.
9. Unsupported requested properties produce per-entity capability issues or structured tool failures, never silent omission.
10. `ContextAutoCADAdapter` is an additive versioned extension; the EPIC-03 `AutoCADAdapter` remains exactly four read-only/status methods. Its pure protocol/fake import without COM, and only `windows_context.py` consumes the injected `WindowsSessionManager`/`AutoCADSession` boundary.
11. `SnapshotBuilder` reads adapter pages of at most 500 with equal before/page/after revision tokens; 501 entities succeed across multiple pages, exactly 10,000/32 MiB succeed, and 10,001 entities, one byte over 32 MiB, partial reads, repeated cursors, document changes, or missing trustworthy tokens fail without repository insertion.
12. `SnapshotRepository.put_complete`/`get_complete` store only complete objects, preserve immutable reads and expiry/not-found distinction, enforce 4 live snapshots/32 MiB each/128 MiB total/10-minute TTL, and return a structured complete-limit failure for drawings beyond bounds.
13. Downstream semantic scopes are limited to 2,000 handles that must belong to one retained complete snapshot; a scope never compensates for an unmaterializable larger drawing.
14. Platform-independent imports and tests pass without Windows COM installed.
15. EPIC-04's core-model integration owns the one serialized `STALE_SNAPSHOT` value and all snapshot codes; deterministic unit/contract tests prevent later redefinition.
16. MCP metadata, registration, schemas, docs, and contract tests agree, and stdio remains protocol-clean.
17. The AutoCAD 2026 runner acquires/releases the EPIC-03 exclusive verification lease around its entire interactive-session use, refuses concurrent base/CTX/CAP verification against that session, completes against a disposable DWG, records the environment, observes no modal UI, leaves source/disposable content unchanged, and cleans temporary files.
18. No result is claimed for AutoCAD 2021-2025, LT, Linux-hosted AutoCAD, or macOS.

## Windows / AutoCAD 2026 disposable-DWG verification

The runner must first acquire the EPIC-03 exclusive AutoCAD verification lease for the entire interactive-session interval, then require `AutoCAD.Application.25.1`, confirm the product is full AutoCAD 2026, and fail if another release or LT answers. CTX and CAP runners may not overlap against one interactive AutoCAD session; lease contention fails closed before connection or fixture access. After acquisition it creates a unique directory below the system temporary directory, opens the committed DXF seed, saves a generated DWG copy there, and performs all assertions against that copy. It never opens a user drawing supplied by a broad directory scan. A `finally` path releases the lease only after AutoCAD/disposable cleanup has been attempted.

The evidence JSON records Windows version, AutoCAD product/version, ProgID, Python version, lockfile SHA-256, fixture SHA-256, generated-DWG initial/final SHA-256, command, start/end UTC times, test counts, capability issues, modal-interaction flag, cleanup result, lease owner, acquisition result/time, and release result/time. It does not record absolute user paths, drawing text beyond fixed fixture values, or raw COM exceptions.

The test performs two complete reads, changes only the view with a documented zoom call, performs a third read, then restores the original view. It asserts stable content digests, a presentation change only during the zoom, deterministic handle order, known geometry/text/dimension facts, page continuation, and identical covered facts across repeated reads. It records `DBMOD` before and after and closes without saving. Any changed on-disk DWG hash, unexpected `DBMOD` change, modal dialog, leftover selection set, or temporary-directory cleanup failure fails the gate.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| COM exposes different members for a release or custom entity | Probe capabilities, request members explicitly, and return `CapabilityIssue`; do not branch speculatively by version. |
| A fingerprint is mistaken for a complete DWG database hash | Publish coverage and `complete`; require target precondition checks in later edit plans. |
| Enumeration order makes pages or digests unstable | Canonical handle-based ordering and shuffled deterministic fixtures. |
| Huge polylines, text, blocks, or relationship graphs exhaust memory | Enforce per-field, per-entity, relationship, page, and total byte bounds before serialization. |
| A stale or tampered cursor leaks or skips data | HMAC-bind it to document, digests, filters, include set, page size, version, and expiry. |
| Path identity exposes proprietary locations | Return only display name and SHA-256 path hash; redact absolute paths from logs/evidence. |
| Custom objects disappear from results | Return identity plus `UnsupportedGeometry` and issues when identity enumeration succeeds; fail `PARTIAL_READ` when it does not. |
| Semantic evidence is confused with fact | Separate dataclasses/JSON collections and validate every evidence reference and state transition. |
| Relationship computation becomes quadratic | Bound candidates and use deterministic spatial buckets; include performance fixtures at maximum page size. |
| A partial adapter/MCP page is treated as a complete source snapshot | Only revision-checked `SnapshotBuilder` can construct `DrawingSnapshot`; the repository validates its complete marker/counts/bytes, while MCP pages carry only `SnapshotRef`. |
| The in-memory repository retains too much proprietary drawing content | Enforce 10-minute TTL, 4-record/128 MiB totals, 32 MiB per snapshot, eight content-free expiry tombstones, no disk persistence, and explicit refusal instead of live eviction. |
| CTX/CAP/base runners race through one interactive AutoCAD session | Acquire the EPIC-03 exclusive verification lease before connection, fail closed on contention, hold it through cleanup, and release in `finally`. |
| Linux tests are overreported as product evidence | Preserve the project’s explicit evidence labels and require the named Windows runner for AutoCAD claims. |

## Rollback

Before the roadmap stage is declared complete, rollback is a normal code/documentation revert of the focused epic commits; no drawing migration or persisted server state exists. Remove the three tool registrations and their matching `mcp.json` entries together, then remove the unused context package and tests. Do not leave schemas advertised without handlers.

After version `1.0` is released, do not redefine it. Disable the tools as a unit if a safety defect requires emergency rollback, retain parsers/fixtures for previously emitted snapshots, and fix behavior under a new compatible minor or breaking major version. Cursors are process-local and expire within 15 minutes, so rollback requires no cursor database cleanup.

## Completion evidence

The pull request must attach or link:

- focused unit command output and test counts for CTX-01 through CTX-05;
- builder evidence for 501-entity multi-page success, exact 10,000-entity/32-MiB success, over-bound rejection, stable revision tokens, and change/partial-read refusal before fingerprint/storage;
- repository evidence for complete-only insertion, immutable reads, exact 4-record/32-MiB-each/128-MiB-total/600-second limits, and distinct expired/not-found errors;
- additive adapter evidence showing the base protocol remains four read-only/status methods, pure protocol/fake imports without COM, and Windows context sessions are balanced;
- core-model evidence showing EPIC-04 owns one `ErrorCode.STALE_SNAPSHOT` wire value, deterministic serialization, and unique snapshot error members;
- MCP contract command output proving catalog/schema/error/pagination and clean stdout;
- full `pytest`, Ruff, mypy, compileall, and `git diff --check` output;
- the reviewed complete `snapshot_v1.json` and paged `analyze_page_v1.json` fixtures plus content/presentation digests;
- redacted AutoCAD 2026 runner evidence with environment, disposable-DWG hashes, `DBMOD`, modal flag, and cleanup result;
- verification-lease evidence covering contention refusal and release on success, assertion failure, timeout, and cleanup failure;
- a file-ownership summary showing no legacy server or unrestricted execution path was promoted;
- canonical documentation changes that label only the evidence actually obtained.

The roadmap stage may move to complete only in the pull request containing all acceptance evidence. Code presence alone leaves it in progress.

## Handoff

The integration lead gives each worker this epic, the approved modernization design, repository `AGENTS.md`, and only the files owned by its lane. Each worker starts with the stated failing tests, returns exact commands/results, and calls out any contract mismatch rather than creating an alias.

At completion, hand EPIC-05 the released schema version, public import paths, maximum context payload, `ContextAutoCADAdapter`, the singleton `SnapshotRepository`, `DrawingContextService` factory, the canonical core-model `ErrorCode.STALE_SNAPSHOT`, EPIC-03 verification-lease usage/evidence, verified capture-relevant capabilities, golden fixture handles, and the AutoCAD 2026 evidence artifact. EPIC-05 through EPIC-08 import the exact `autocad_mcp.context.repository.SnapshotRepository` interface, call `get_complete(snapshot_id, session_id=reference.session_id)` when holding a reference (ID-only requests follow decision 0003), and consume EPIC-04's serialized `STALE_SNAPSHOT`; they do not create a repository/error alias, accept a partial page, or change version `1.0` fingerprint semantics. EPIC-05 keeps image generation explicitly invoked and cannot overlap its real-AutoCAD runner with CTX/base verification on the same interactive session.
