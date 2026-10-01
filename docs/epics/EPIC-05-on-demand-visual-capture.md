# EPIC-05: On-Demand Visual Capture

## Pre-release context amendments

[Decision 0003](../decisions/0003-session-qualified-snapshot-retention.md)
requires every lookup holding a `SnapshotRef`/cursor to pass its session ID.
ID-only inputs use an optional `source_session_id`; omission succeeds only for
one live matching session and never silently selects the active document.
For optional snapshot inputs, a session without a snapshot ID is invalid.
Approval/source agreement still uses the complete exact reference.

[Decision 0005](../decisions/0005-owner-scoped-entity-coordinates.md)
uses `EntitySpace` to distinguish model WCS, named paper-layout WCS and local
block-definition frames. Entity geometry/positions/`bounds` have frame-neutral
field names. Establish equal supported owner frames before spatial comparisons,
WCS capture projection, topology or edit compilation. Version-1 consumers must
report unsupported instance projection rather than interpret definition-local
coordinates as drawing WCS. Document UCS/view and topology-plane WCS fields
retain their explicit meaning.

## Status

**Planned.** This epic describes target behavior for roadmap stage 4. It is not evidence that drawing capture exists. The implementation may start only after the stable MCP core and [EPIC-04](EPIC-04-structured-drawing-context.md) entry gates pass. The stage remains in progress until all automated gates and the disposable-DWG AutoCAD 2026 capture gate below pass.

## Outcome

The canonical MCP server exposes one explicitly invoked tool, `capture_drawing_view`. A caller chooses `current`, `extents`, or `selection` mode and receives exactly one bounded image plus versioned correlation metadata tied to structured drawing context. The default result is a clean PNG. An opt-in handle-labelled result is rendered outside AutoCAD and never adds annotation entities, layers, blocks, selection markers, or other content to the DWG.

## User value

A user or vision-capable MCP client can request a visual only when it helps, understand which document/view/bounds produced it, correlate visible locations with persistent entity handles, and distinguish a capture limitation from a drawing error. Normal connection, status, analysis, planning, editing, and model turns do not incur capture latency or expose drawing pixels.

## Scope

- The version 1 `capture_drawing_view` request, image, correlation, capability, and error contracts.
- Explicit `current`, `extents`, and `selection` capture modes.
- A clean PNG result by default.
- An optional outside-DWG handle overlay, returned as a safe SVG image that embeds the clean PNG and deterministic labels.
- Correlation to EPIC-04 document identity, snapshot ID, content/presentation fingerprints, active space/layout/UCS/view, plotted WCS bounds, pixel content rectangle, and handle anchors.
- Complete pre/post correlation through EPIC-04 `SnapshotBuilder`/`SnapshotRepository`; version 1 fails structurally when the drawing exceeds 10,000 entities or 32 MiB of complete snapshot facts.
- A state-neutral Windows capture adapter that probes installed plot/export capabilities and fails structurally when it cannot honor a mode without leaving drawing state changed.
- A versioned additive `CaptureAutoCADAdapter` protocol, focused fake, and Windows implementation layered after EPIC-04 without changing EPIC-03's four-method read-only/status base.
- Bounded dimensions, pixel count, file bytes, MCP payload bytes, handles, labels, timeout, temporary files, and metadata.
- Focused fake-adapter unit and MCP contract tests plus full AutoCAD 2026 tests for success, cleanup after failure, and unchanged drawing content/state.

## Out of scope

- Automatic capture on startup, connection, `server_status`, context analysis, edit preview/application, or every model turn.
- Background capture, periodic thumbnails, prefetching, caching across tool invocations, or file watchers.
- Vision inference, OCR, object detection, semantic labelling, a vision SDK, a provider-specific client, or any provider/API key.
- Desktop/window screenshots, mouse/keyboard automation, focus stealing, clipboard capture, or capture of other applications.
- Arbitrary output paths supplied by the MCP caller.
- Arbitrary `SendCommand`, AutoLISP, VBA, Python, shell, or user-provided plot commands.
- Adding capture members directly to EPIC-03's `AutoCADAdapter` or importing a Windows adapter from capture domain/service code.
- Hiding non-selected entities in `selection` mode. Version 1 frames the selected handles' bounds; other visible entities inside that rectangle may appear.
- Raster editing inside the DWG, temporary label entities, temporary layers, plot stamps, watermarks, or saved layout changes.
- JPEG, WebP, TIFF, PDF, DWF, GIF, animated output, tiled pyramids, or multi-image responses in version 1.
- Perspective-accurate WCS-to-pixel inversion. Perspective views return bounds-only correlation with an explicit capability issue.
- Visual capture of drawings that cannot satisfy EPIC-04's complete-snapshot revision or 10,000-entity/32-MiB bounds; version 1 does not downgrade those captures to page-derived fingerprints.
- AutoCAD LT, macOS, Linux-hosted AutoCAD, or real-installation claims for AutoCAD 2021-2025.

## Prerequisites and entry gate

Before parallel lanes fork, the integration lead records that:

1. EPIC-02's installable-package migration is accepted: `src/autocad_mcp/server.py` is canonical, and `mcp.json` starts `uv run python -m autocad_mcp.server` with protocol-clean stdio.
2. EPIC-03's `AutoCADAdapter` remains frozen at exactly four read-only/status methods; it does **not** contain capture records or methods. Its adapter-internal `WindowsSessionManager.session(require_document: bool) -> Iterator[AutoCADSession]` contract and delayed COM lifecycle are documented and tested.
3. EPIC-04 schema `1.0`, additive `ContextAutoCADAdapter`, `FakeContextAutoCADAdapter`, `WindowsContextAutoCADAdapter`, revision-checked `SnapshotBuilder`, and `SnapshotRepository` are released and their unit, MCP, and AutoCAD 2026 read-only gates pass.
4. These imports are stable: `DrawingSnapshot`, `DocumentIdentity`, `DrawingFingerprint`, `EntityContext`, `Bounds3D`, `Point2D`, `Point3D`, `ViewContext`, `DrawingContextService`, `CompleteSnapshotRequest`, and `SnapshotBuilder` from `autocad_mcp.context`; `SnapshotRepository` from `autocad_mcp.context.repository`; and `ContextAutoCADAdapter` from `autocad_mcp.adapter.context_protocol`.
5. `SnapshotBuilder.build(CompleteSnapshotRequest) -> DrawingSnapshot`, `DrawingContextService.analyze_drawing(AnalyzeDrawingRequest) -> AnalyzeDrawingResult`, `get_entity_context(GetEntityContextRequest) -> EntityContextBatch`, and `SnapshotRepository.get_complete(snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot` are available read-only.
6. `src/autocad_mcp/core/models.py` provides `ErrorCode`, `ToolError`, `ToolSuccess`, `ToolFailure`, `ToolResponse`, `response_payload`, and `response_json`; EPIC-04 provides `CapabilityIssue` and the adapter provides `AdapterCapabilityReport`.
7. The AutoCAD 2026 context fixture has known persistent handles and a reproducible disposable-DWG preparation path.
8. The EPIC-03 exclusive AutoCAD verification lease is available; CAP must not overlap the EPIC-03 base smoke runner, CTX runner, or another CAP runner against the same interactive AutoCAD session.

CAP-C adds the separate versioned `CaptureAutoCADAdapter` protocol, pure records, fake, and Windows implementation after these prerequisites pass, then freezes all adapter-extension paths before CAP-B/E/F integrate them. If prerequisites use different names, reconcile them in one prerequisite change before dispatch. No other lane may edit an adapter-extension file, add capture methods to EPIC-03's four-method protocol, copy EPIC-04 types, or create a second server/error stack.

## Design invariants

- Only the registered `capture_drawing_view` handler may construct or call `CaptureService.capture_drawing_view`.
- The service and Windows adapter perform no work until that tool handler receives a valid invocation.
- Every successful invocation returns exactly one image content block and one bounded JSON metadata content block; image bytes are not duplicated in JSON.
- The clean output contains only AutoCAD's rendered drawing/view. The default request has no handle overlay.
- Handle annotation is rendered after AutoCAD returns the clean image. It never calls an AutoCAD mutation method.
- A capture never saves the DWG, changes the active document, zooms the UI, or leaves changed layout/view/UCS/system-variable/selection state.
- Temporary output lives in a random per-request directory below the OS temporary directory. The caller cannot choose it. Cleanup runs in `finally` after success, validation failure, COM failure, timeout, cancellation, image validation failure, overlay failure, or MCP shaping failure.
- Capture and context use the same active document identity. A document switch or content change during capture invalidates the result.
- The server produces pixels and correlation facts only. It does not interpret those pixels.
- Platform-independent request validation, PNG inspection, SVG generation, projection, and MCP shaping remain importable without Windows COM.
- `adapter/capture_protocol.py` and `adapter/fake_capture.py` are pure Python. Among new EPIC-05 files, only `adapter/windows_capture.py` may use COM-facing `AutoCADSession` objects, exclusively through an injected EPIC-03 `WindowsSessionManager`.

## Capture mode semantics

### `current`

Capture the active display of the active model or paper-space context using AutoCAD's display plot/export scope. Use the EPIC-04 active layout, UCS, view direction, target, center, height, width, twist, and projection read immediately before capture. Do not invoke Zoom, change the current view, activate another document, or switch layouts. If the installed state-neutral backend cannot represent the current display, return `UNSUPPORTED_CAPTURE_MODE`.

### `extents`

Capture the extents of visible, plottable entities in the active space and active layout. Model space means model-space extents. Paper space means that layout's paper-space extents. Model-through-paper-viewport captures the active paper layout, not an unbounded model-space `ZoomExtents`. Apply `padding_ratio` to the computed rectangle without changing the active view. Empty or non-finite extents return `EMPTY_CAPTURE_SCOPE`.

### `selection`

Require one to 256 normalized persistent handles. Resolve every handle in the same active document and active space/layout through EPIC-04, union their WCS bounding boxes, and apply `padding_ratio`. A missing handle returns `ENTITY_NOT_FOUND`; a handle in another space/layout returns `SELECTION_SCOPE_MISMATCH`; an entity without a usable bounding box returns `UNSUPPORTED_CAPABILITY`. The image frames the resulting rectangle and may include other visible entities inside it. It never hides, isolates, highlights, erases, or recolors drawing entities.

## Schemas and bounds

### Versioning and exact Python data contract

`CAPTURE_SCHEMA_VERSION` is `"1.0"`. The request parser rejects unknown fields and unsupported major versions. Changing a mode's meaning, clean/annotated image behavior, projection math, or byte accounting requires a new major version. Additive optional metadata requires a documented minor version and contract-fixture update.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

CAPTURE_SCHEMA_VERSION = "1.0"
CaptureSchemaVersion = Literal["1.0"]
CaptureMode = Literal["current", "extents", "selection"]
CaptureFormat = Literal["png"]
CaptureVariant = Literal["clean", "handle_overlay"]

@dataclass(frozen=True, slots=True)
class CaptureOutputSpec:
    format: CaptureFormat = "png"
    max_width_px: int = 1920
    max_height_px: int = 1080
    background: Literal["drawing"] = "drawing"

@dataclass(frozen=True, slots=True)
class HandleOverlayOptions:
    enabled: bool = False
    handles: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class CaptureRequest:
    schema_version: CaptureSchemaVersion
    mode: CaptureMode
    source_snapshot_id: str | None
    selection_handles: tuple[str, ...]
    padding_ratio: float
    output: CaptureOutputSpec
    overlay: HandleOverlayOptions
    timeout_seconds: int
    source_session_id: str | None = None

@dataclass(frozen=True, slots=True)
class PixelSize:
    width: int
    height: int

@dataclass(frozen=True, slots=True)
class PixelPoint:
    x: float
    y: float

@dataclass(frozen=True, slots=True)
class PixelRect:
    left: int
    top: int
    right: int
    bottom: int

CorrelationQuality = Literal["affine", "bounds_only"]
AnchorVisibility = Literal["visible", "outside", "occluded_unknown"]

@dataclass(frozen=True, slots=True)
class HandleCorrelation:
    handle: str
    anchor_wcs: Point3D
    anchor_image: PixelPoint | None
    visibility: AnchorVisibility
    label_rect: PixelRect | None

@dataclass(frozen=True, slots=True)
class CaptureCorrelation:
    document: DocumentIdentity
    snapshot_id: str
    fingerprint: DrawingFingerprint
    captured_at: datetime
    mode: CaptureMode
    active_context: ActiveDrawingContext
    plotted_bounds_wcs: Bounds3D
    image_size: PixelSize
    content_rect: PixelRect
    quality: CorrelationQuality
    world_to_image_2x4: tuple[float, ...] | None
    handles: tuple[HandleCorrelation, ...]
    drawing_state: Literal["unchanged"]

@dataclass(frozen=True, slots=True)
class ImageArtifact:
    variant: CaptureVariant
    mime_type: Literal["image/png", "image/svg+xml"]
    data: bytes
    byte_count: int
    sha256: str
    size: PixelSize

@dataclass(frozen=True, slots=True)
class CaptureResult:
    schema_version: CaptureSchemaVersion
    capture_id: str
    image: ImageArtifact
    correlation: CaptureCorrelation
    capability_issues: tuple[CapabilityIssue, ...]
    duration_ms: int
```

`world_to_image_2x4` contains two row-major affine rows that map homogeneous WCS `[x, y, z, 1]` to image `[x, y]`. It has exactly eight finite floats when `quality="affine"` and is `None` when `quality="bounds_only"`. Pixel origin is the top-left corner; x grows right and y grows down. `content_rect` identifies the plotted area after driver margins/letterboxing and must lie inside `image_size`.

### Request and output bounds

| Constraint | Version 1 bound |
| --- | ---: |
| Default/max width | 1,920 / 4,096 px |
| Default/max height | 1,080 / 4,096 px |
| Maximum pixels | 16,777,216 |
| Minimum actual width or height | 64 px |
| Selection handles | 1-256 in `selection` mode |
| Overlay labels | 1-100 when enabled |
| Default / maximum padding ratio | 0.05 / 0.50 |
| Default / maximum timeout | 30 / 60 seconds |
| Clean PNG bytes | 4 MiB |
| Annotated SVG bytes | 6 MiB |
| Correlation JSON | 256 KiB |
| Complete serialized MCP tool result | 10 MiB |
| Temporary files per invocation | 4 |
| Temporary directory lifetime | one invocation |

Requested width and height are maxima, not a promise to distort the plot. The adapter selects a supported raster configuration that preserves aspect ratio and fits inside both maxima. The actual `ImageArtifact.size` and `content_rect` are authoritative. A driver result below 64 pixels in either dimension, above either requested maximum, above 16,777,216 pixels, or above 4 MiB fails `IMAGE_LIMIT_EXCEEDED` before MCP encoding.

Version 1 accepts only `format="png"`. There is no silent format fallback. The clean file must have the PNG signature, a valid IHDR, 8-bit RGB or RGBA color type, finite positive dimensions, CRC-valid chunks, at least one IDAT, and IEND. The service rejects trailing files, HTML/error text, BMP renamed as PNG, decompression bombs inferred from dimensions, and mismatched adapter metadata.

`padding_ratio` is finite and non-negative. Handles are uppercase hexadecimal without `0x`, unique after normalization. Overlay handles must be a subset of visible candidate handles in the requested scope. For `selection`, an empty overlay handle list means the normalized `selection_handles`; for `current` or `extents`, `overlay.enabled=True` requires an explicit non-empty overlay handle list.

### Clean image and handle-overlay contract

- `overlay.enabled=False` returns `variant="clean"`, MIME `image/png`, and the untouched validated AutoCAD PNG bytes.
- `overlay.enabled=True` returns one `variant="handle_overlay"` image with MIME `image/svg+xml`. The SVG embeds the validated clean PNG as a `data:image/png;base64,...` image and adds handle labels after capture.
- The SVG uses a fixed allowlist of elements (`svg`, `image`, `g`, `line`, `rect`, `text`), attributes, numeric values, and system sans-serif font. It has no scripts, stylesheets, events, external URLs, foreign objects, metadata containing drawing text, or caller-supplied markup.
- Labels are sorted by numeric handle. Each anchor is the center of the entity WCS bounding box projected through the returned mapping. A deterministic eight-position placement algorithm tries offsets clockwise; if all collide, it puts the label in a right-side gutter with a leader line. No requested label disappears silently.
- Label text is exactly the normalized handle. Text, layer names, block attributes, document paths, and semantic guesses are never added to the overlay.
- Overlay rendering consumes EPIC-04 facts read-only and calls no adapter mutation method. `HandleCorrelation.label_rect` records final placement.

### Correlation and drawing-state semantics

If `source_snapshot_id` is present, the service first calls `SnapshotRepository.get_complete(source_snapshot_id, session_id=source_session_id)`; expired and unknown IDs preserve EPIC-04's distinct structured errors, and an MCP page can never be loaded through this interface. It then calls `SnapshotBuilder.build` and returns `STALE_SNAPSHOT` before image production when document ID or complete content fingerprint differs from the retained source. If no source ID is supplied, it builds one complete snapshot, inserts it, and uses it as the source. Correlation always uses the fresh pre-capture snapshot/reference, so a legitimate view-only change is represented by its fresh presentation digest rather than by the caller's older reference. Revision-token failure, partial reads, more than 10,000 entities, or more than 32 MiB return the EPIC-04 structured error; capture never substitutes a filtered/page fingerprint. The service verifies that adapter scope resolution and capture receipt use the same `document_id`, active layout, display space, and presentation digest.

For parallel 2D views with a valid plot rectangle and driver content rectangle, `build_capture_correlation(...) -> CaptureCorrelation` emits the affine mapping. Perspective, clipped/non-rectangular paper viewports, or a driver that cannot report its content rectangle return `quality="bounds_only"`, a `None` matrix, and a capability issue. Bounds-only correlation is still useful but cannot produce an overlay; an overlay request then fails `UNSUPPORTED_CORRELATION`.

After image production and before returning bytes, the service runs `SnapshotBuilder` again and reads the adapter state receipt. A builder failure, changed complete content digest, changed active document, failed state restoration, or changed covered plot/view/UCS state returns `DRAWING_CHANGED_DURING_CAPTURE` or `STATE_RESTORE_FAILED` and deletes the image. A successful result requires matching complete pre/post digests and yields only `drawing_state="unchanged"`; version 1 has no successful unverified/page-derived state.

## Capability and error bounds

The adapter reports mode-specific capabilities rather than inferring support from release number. It probes an installed PNG plot device, foreground file plotting, display/extents/window plot types, coordinate conversion, active-space support, and reversible state capture. A missing or unsuitable device returns a structured error and does not fall back to a desktop screenshot.

Version 1 adds these exact `ErrorCode` members to the stable-core error enum:

```python
CAPTURE_UNAVAILABLE
UNSUPPORTED_CAPTURE_MODE
UNSUPPORTED_IMAGE_FORMAT
UNSUPPORTED_CORRELATION
EMPTY_CAPTURE_SCOPE
SELECTION_SCOPE_MISMATCH
DOCUMENT_CHANGED
CAPTURE_TIMEOUT
CAPTURE_FAILED
INVALID_IMAGE
IMAGE_LIMIT_EXCEEDED
STATE_RESTORE_FAILED
DRAWING_CHANGED_DURING_CAPTURE
TEMPORARY_FILE_CLEANUP_FAILED
```

Existing `AUTOCAD_UNAVAILABLE`, `COM_BUSY`, `NO_ACTIVE_DOCUMENT`, `ENTITY_NOT_FOUND`, `INVALID_ARGUMENT`, `UNSUPPORTED_SCHEMA_VERSION`, `UNSUPPORTED_CAPABILITY`, `PAYLOAD_LIMIT`, `REVISION_TOKEN_UNAVAILABLE`, `SNAPSHOT_CHANGED_DURING_READ`, `COMPLETE_SNAPSHOT_LIMIT`, `SNAPSHOT_INCOMPLETE`, `SNAPSHOT_NOT_FOUND`, `SNAPSHOT_EXPIRED`, `STALE_SNAPSHOT`, and `INTERNAL_ERROR` remain in use. EPIC-05 consumes the exact `ErrorCode.STALE_SNAPSHOT` member and serialized wire value owned by EPIC-04; it does not add, alias, or redefine it. Validation, missing capability, scope, builder, repository, image, stale-state, and state-restoration failures are never retried. Only the stable-core bounded COM-busy policy may retry. The total wall-clock budget, including retries, is `timeout_seconds`.

If both the primary operation and cleanup fail, the primary error remains the top-level code and a nested `cleanup_error` records the cleanup code without absolute paths. Cleanup failure after an otherwise successful operation becomes `TEMPORARY_FILE_CLEANUP_FAILED`; the server does not return bytes whose lifecycle it cannot account for.

## Consumed and produced interfaces

### Consumed from EPIC-04 and stable core

```python
class DrawingContextService:
    def analyze_drawing(self, request: AnalyzeDrawingRequest) -> AnalyzeDrawingResult: ...
    def get_entity_context(self, request: GetEntityContextRequest) -> EntityContextBatch: ...

class SnapshotRepository(Protocol):
    def put_complete(self, snapshot: DrawingSnapshot) -> None: ...
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...

class SnapshotBuilder:
    def build(self, request: CompleteSnapshotRequest) -> DrawingSnapshot: ...

class ContextAutoCADAdapter(AutoCADAdapter, Protocol):
    def read_document_context(self) -> AdapterDocumentContext: ...
    def read_document_revision(self) -> AdapterDocumentRevisionToken: ...
    def read_entity_page(
        self, request: AdapterEntityReadRequest
    ) -> AdapterEntityPage: ...
    def entity_facts_by_handles(
        self, handles: tuple[str, ...], include: ContextInclude
    ) -> tuple[AdapterEntityFacts, ...]: ...

@dataclass(frozen=True)
class ToolSuccess:
    data: Mapping[str, JsonValue]

@dataclass(frozen=True)
class ToolFailure:
    error: ToolError

def response_payload(response: ToolResponse) -> dict[str, JsonValue]: ...
def response_json(response: ToolResponse) -> str: ...
```

The consumed EPIC-03/04 interfaces contain no capture method. The capture implementation obtains complete source snapshots through the exact `SnapshotRepository` name and consumes context through public types; it never treats a partial analysis page as a source snapshot.

### Produced by this epic

```python
CAPTURE_ADAPTER_SCHEMA_VERSION = "1.0"

@dataclass(frozen=True, slots=True)
class AdapterCaptureCapabilityReport:
    schema_version: Literal["1.0"]
    available_modes: tuple[CaptureMode, ...]
    png_devices: tuple[str, ...]
    state_neutral: bool
    issues: tuple[CapabilityIssue, ...]

@dataclass(frozen=True, slots=True)
class AdapterCaptureScopeRequest:
    schema_version: Literal["1.0"]
    mode: CaptureMode
    selection_handles: tuple[str, ...]
    padding_ratio: float

@dataclass(frozen=True, slots=True)
class AdapterCaptureScopeRecord:
    schema_version: Literal["1.0"]
    document_id: str
    mode: CaptureMode
    active_layout_name: str
    display_space: str
    plotted_bounds_wcs: tuple[float, float, float, float, float, float]
    selection_handles: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class AdapterCaptureRequest:
    schema_version: Literal["1.0"]
    scope: AdapterCaptureScopeRecord
    output_path: Path
    max_width_px: int
    max_height_px: int
    timeout_seconds: int

@dataclass(frozen=True, slots=True)
class AdapterStateReceiptRecord:
    restored: bool
    changed_fields: tuple[str, ...]
    dbmod_before: int
    dbmod_after: int
    temporary_selection_sets_remaining: int

@dataclass(frozen=True, slots=True)
class AdapterCaptureReceiptRecord:
    schema_version: Literal["1.0"]
    document_id: str
    output_path: Path
    plotted_bounds_wcs: tuple[float, float, float, float, float, float]
    image_width_px: int
    image_height_px: int
    content_rect: tuple[int, int, int, int]
    state: AdapterStateReceiptRecord
    capabilities_used: tuple[str, ...]

class CaptureAutoCADAdapter(ContextAutoCADAdapter, Protocol):
    def capture_capabilities(self) -> AdapterCaptureCapabilityReport: ...
    def resolve_capture_scope(
        self, request: AdapterCaptureScopeRequest
    ) -> AdapterCaptureScopeRecord: ...
    def capture_png(
        self, request: AdapterCaptureRequest
    ) -> AdapterCaptureReceiptRecord: ...

class CaptureAdapterProvider(Protocol):
    def get(self) -> CaptureAutoCADAdapter: ...

class StaticCaptureAdapterProvider:
    def __init__(self, adapter: CaptureAutoCADAdapter) -> None: ...
    def get(self) -> CaptureAutoCADAdapter: ...

class WindowsCaptureAdapterProvider:
    def get(self) -> CaptureAutoCADAdapter: ...

class FakeCaptureAutoCADAdapter(FakeContextAutoCADAdapter): ...
class WindowsCaptureAutoCADAdapter(WindowsContextAutoCADAdapter): ...

@dataclass(frozen=True, slots=True)
class AdapterCaptureScope:
    document_id: str
    mode: CaptureMode
    active_context: ActiveDrawingContext
    plotted_bounds_wcs: Bounds3D
    selection_handles: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class AdapterCapturePlan:
    scope: AdapterCaptureScope
    output_path: Path
    max_size: PixelSize
    background: Literal["drawing"]
    timeout_seconds: int

@dataclass(frozen=True, slots=True)
class AdapterStateReceipt:
    restored: bool
    changed_fields: tuple[str, ...]
    dbmod_before: int
    dbmod_after: int
    temporary_selection_sets_remaining: int

@dataclass(frozen=True, slots=True)
class AdapterCaptureReceipt:
    document_id: str
    output_path: Path
    plotted_bounds_wcs: Bounds3D
    image_size: PixelSize
    content_rect: PixelRect
    state: AdapterStateReceipt
    capabilities_used: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class CaptureCapabilityReport:
    available: bool
    modes: tuple[CaptureMode, ...]
    png_devices: tuple[str, ...]
    state_neutral: bool
    issues: tuple[CapabilityIssue, ...]

@dataclass(frozen=True, slots=True)
class PngInfo:
    size: PixelSize
    bit_depth: Literal[8]
    color_type: Literal[2, 6]
    byte_count: int
    sha256: str

class CaptureArtifactStore(Protocol):
    def request_directory(self, capture_id: str) -> ContextManager[Path]: ...

class CaptureService:
    def __init__(
        self,
        *,
        provider: CaptureAdapterProvider,
        context_service: DrawingContextService,
        snapshot_builder: SnapshotBuilder,
        snapshot_repository: SnapshotRepository,
        artifact_store: CaptureArtifactStore,
    ) -> None: ...
    def capture_drawing_view(self, request: CaptureRequest) -> CaptureResult: ...

class CaptureServiceFactory(Protocol):
    def create(self) -> CaptureService: ...

def inspect_png(data: bytes) -> PngInfo: ...
def map_capture_capabilities(
    raw: AdapterCaptureCapabilityReport,
) -> CaptureCapabilityReport: ...
def build_adapter_capture_request(
    plan: AdapterCapturePlan,
) -> AdapterCaptureRequest: ...
def map_adapter_capture_receipt(
    raw: AdapterCaptureReceiptRecord,
) -> AdapterCaptureReceipt: ...
def build_capture_correlation(
    snapshot: DrawingSnapshot,
    scope: AdapterCaptureScope,
    receipt: AdapterCaptureReceipt,
    entities: tuple[EntityContext, ...],
) -> CaptureCorrelation: ...
def render_handle_overlay(
    clean_png: bytes,
    correlation: CaptureCorrelation,
    options: HandleOverlayOptions,
) -> tuple[bytes, tuple[HandleCorrelation, ...]]: ...
def capture_result_to_mcp(result: CaptureResult) -> list[ContentBlock]: ...
```

`capture_result_to_mcp` returns a compact JSON text block without `ImageArtifact.data`, followed by exactly one MCP `ImageContent` block containing base64 generated by the MCP SDK. The project code does not create a second base64 JSON property.

`adapter/capture_protocol.py` is additive: it extends EPIC-04's `ContextAutoCADAdapter` without changing that interface or EPIC-03's four-method base. `adapter/fake_capture.py` extends the context fake and provides the static provider. `adapter/windows_capture.py` extends `WindowsContextAutoCADAdapter`, receives the documented `WindowsSessionManager`, and may use only `session(require_document=True)`/`AutoCADSession`; it does not reimplement COM initialization or expose a proxy. Runtime imports the Windows capture provider only inside its capture factory.

`capture_id` is `cap_` plus a UUIDv4 hex value generated after request validation and before adapter acquisition. It identifies one invocation for later client-supplied visual evidence, is included in the JSON metadata, and is never used as drawing identity, authorization, a cache key, or a substitute for `snapshot_id`.

## Windows adapter implementation boundary

CAP-C's `WindowsCaptureAutoCADAdapter` is the only owner of the following new Windows behavior. Capture feature/domain layers call it through the pure `CaptureAutoCADAdapter` protocol and never import the Windows implementation. `windows_capture.py` may use only allowlisted ActiveX plot/export members through the injected EPIC-03 `WindowsSessionManager`. AutoCAD's official ActiveX `Document.Export` formats include BMP but not PNG; version 1 must not rename BMP bytes to PNG. `Plot.PlotToFile` can target a discovered PNG PC3 file and requires foreground plotting for deterministic completion. Layout window/extents/display plot settings may be used only under complete state snapshot/restore and unchanged-state verification.

The planned backend is:

1. Probe `ActiveLayout.GetPlotDeviceNames()` and select a real installed device whose filename identifies a PNG file plotter, preferring `PublishToWeb PNG.pc3` case-insensitively. Record the exact selected device in capability evidence.
2. Snapshot active document, layout, view, UCS, plot configuration properties, `BACKGROUNDPLOT`, relevant selection-set names, and `DBMOD`.
3. Use plot type `acDisplay` for `current`, `acExtents` for `extents`, and `acWindow` plus `SetWindowToPlot` for `selection`. Configure scale-to-fit and centering in memory, use a random non-existing output path, set foreground plotting only for the call, and invoke `PlotToFile` with the selected PC3 override.
4. Wait within the request deadline, validate exactly one output file, and restore every snapped value in reverse order in `finally`.
5. Read all restored values back. Any mismatch is `STATE_RESTORE_FAILED`; do not save the document to make restoration appear successful.

If AutoCAD 2026 shows that this path changes `DBMOD` or persistent layout content even after restoration, it does not pass the epic. The adapter must choose another state-neutral AutoCAD export/plot capability or report `CAPTURE_UNAVAILABLE`. It must not weaken the unchanged-DWG criterion or substitute a screen capture.

Primary implementation references are Autodesk's [AutoCAD 2026 `Export` method](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-ActiveX-Reference/files/GUID-893F1711-3591-4DDC-8D27-DF91052F5E5A.htm), [`PlotToFile` method](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-ActiveX-Reference/files/GUID-85A6B1AF-80AA-4F56-8305-6EFD4A4D8CF8.htm), [`SetWindowToPlot`/`GetWindowToPlot` contract](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-ActiveX-Reference/files/GUID-C2F875C1-C95A-4B6E-849A-79B03BCA4666.htm), and [AutoCAD 2026 ActiveX version/ProgID guidance](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-ActiveX/files/GUID-FF023966-A01D-4B64-8957-7C0F02BF8162.htm). Capability probing and observed AutoCAD 2026 behavior remain authoritative over assumptions.

## Exact proposed files and ownership

Each path has one owning lane. Other workers may read it but must not edit it concurrently.

| Owner | File | Responsibility |
| --- | --- | --- |
| CAP-A contracts | `src/autocad_mcp/capture/__init__.py` | Public capture exports only |
| CAP-A contracts | `src/autocad_mcp/capture/models.py` | Frozen version 1 domain contracts/constants |
| CAP-A contracts | `src/autocad_mcp/capture/validation.py` | Strict request/result validation and bounds |
| CAP-A contracts | `tests/unit/capture/test_models.py` | Version, cross-field, and bounds tests |
| CAP-B correlation | `src/autocad_mcp/capture/planning.py` | Mode-to-scope planning and padding |
| CAP-B correlation | `src/autocad_mcp/capture/projection.py` | WCS-to-pixel mapping and anchors |
| CAP-B correlation | `tests/unit/capture/test_planning.py` | Current/extents/selection planning tests |
| CAP-B correlation | `tests/unit/capture/test_projection.py` | Affine/bounds-only/correlation tests |
| CAP-C adapter | `src/autocad_mcp/adapter/__init__.py` | Export additive capture interfaces without importing Windows modules |
| CAP-C adapter | `src/autocad_mcp/adapter/capture_protocol.py` | Versioned pure capture records, protocol, and provider |
| CAP-C adapter | `src/autocad_mcp/adapter/fake_capture.py` | Focused additive fake over the EPIC-04 context fake |
| CAP-C adapter | `src/autocad_mcp/adapter/windows_capture.py` | Plot/export implementation through an injected EPIC-03 `WindowsSessionManager` only |
| CAP-C adapter | `src/autocad_mcp/capture/adapter_client.py` | Translate pure capture plans/receipts through `CaptureAutoCADAdapter` |
| CAP-C adapter | `tests/adapter/test_capture_protocol.py` | Pure record, version, protocol, and provider contracts |
| CAP-C adapter | `tests/adapter/test_fake_capture.py` | Deterministic images, call count, and failure records |
| CAP-C adapter | `tests/adapter/test_windows_capture_imports.py` | Delayed COM/import isolation for capture extension |
| CAP-C adapter | `tests/adapter/test_windows_capture.py` | Injected-session plot, restoration, and cleanup tests |
| CAP-C adapter | `tests/unit/capture/test_adapter_client.py` | Pure adapter-record mapping and state-receipt tests |
| CAP-C adapter | `tests/fixtures/capture/adapter_capture_v1.json` | Deterministic scope/capability/receipt records |
| CAP-C adapter | `tests/fixtures/capture/clean_rgb_v1.png` | Small validated clean PNG returned by the fake |
| CAP-D image | `src/autocad_mcp/capture/png.py` | Bounded PNG structure and CRC inspection |
| CAP-D image | `src/autocad_mcp/capture/overlay.py` | Safe deterministic SVG overlay renderer |
| CAP-D image | `src/autocad_mcp/capture/artifacts.py` | Per-request temporary artifact lifecycle |
| CAP-D image | `tests/unit/capture/test_png.py` | Valid/invalid/bomb/size PNG tests |
| CAP-D image | `tests/unit/capture/test_overlay.py` | Escaping, labels, collision, byte-bound tests |
| CAP-D image | `tests/unit/capture/test_artifacts.py` | Success/failure/cancel cleanup tests |
| CAP-E service/fake | `src/autocad_mcp/capture/service.py` | Explicit orchestration and state/fingerprint checks |
| CAP-E service/fake | `tests/unit/capture/test_service.py` | End-to-end domain service tests |
| CAP-F MCP | `src/autocad_mcp/tools/capture_tool.py` | Request parsing and MCP content shaping |
| CAP-F MCP | `src/autocad_mcp/core/models.py` | Add capture-only errors while consuming, not redefining, EPIC-04 `STALE_SNAPSHOT` |
| CAP-F MCP | `src/autocad_mcp/runtime.py` | Compose the capture service without invoking it |
| CAP-F MCP | `src/autocad_mcp/server.py` | Register exactly one capture handler |
| CAP-F MCP | `mcp.json` | Advertise the exact version 1 input schema |
| CAP-F MCP | `tests/contract/test_capture_tool.py` | Success/error/image/size contract tests |
| CAP-F MCP | `tests/contract/test_capture_is_explicit.py` | Zero capture calls outside explicit tool invocation |
| CAP-F MCP | `tests/contract/test_server_tool_catalog.py` | Registration/metadata agreement |
| CAP-G Windows/docs | `tests/integration/windows/test_capture_autocad.py` | Real current/extents/selection/cleanup/state tests |
| CAP-G Windows/docs | `tests/windows/run_capture_autocad_2026.ps1` | Disposable-DWG runner and evidence capture |
| CAP-G Windows/docs | `docs/contracts/capture-drawing-view-v1.md` | Request/result/mode/error wire contract |
| CAP-G Windows/docs | `docs/verification/capture-autocad-2026.md` | Recorded environment and results |
| CAP-G Windows/docs | `docs/architecture.md` | Move capture from target to adopted only after evidence |
| CAP-G Windows/docs | `docs/roadmap.md` | Stage-4 evidence gate/status update |
| CAP-G Windows/docs | `docs/testing.md` | Capture test commands and evidence labels |
| CAP-G Windows/docs | `docs/compatibility.md` | Feature-specific AutoCAD 2026 capture result |

The EPIC-04 DXF fixture is consumed read-only; CAP-G does not edit it. No capture code is placed in generic context modules, `src/utils.py`, an alternate server, or historical experimental packages.

## Work packages

### CAP-01 — Freeze request/result contracts and limits

**Owner:** CAP-A contracts. **Depends on:** entry gate only.

1. Write failing tests for defaults, all three modes, selection cross-fields, overlay cross-fields, handle normalization, finite padding, timeout, width/height/pixel limits, immutable bytes metadata, content-rectangle containment, matrix length, and unknown-field/version rejection.
2. Run `uv run pytest tests/unit/capture/test_models.py -v`; expected initial result is import/collection failure because `autocad_mcp.capture` does not exist.
3. Implement the frozen dataclasses and validation constants exactly as specified. Keep request parsing separate from COM and MCP transport.
4. Re-run the focused test; expected result is all tests passing.
5. Run `uv run mypy src/autocad_mcp/capture/models.py src/autocad_mcp/capture/validation.py`; expected result is exit code 0.

### CAP-02 — Plan scopes and compute correlation

**Owner:** CAP-B correlation. **Depends on:** CAP-01 and EPIC-04 public types.

1. Write failing tests for current-view scope, padded extents, unioned selection bounds, empty extents, missing bounding boxes, cross-layout handles, parallel zero-twist projection, twisted view, non-top WCS view, letterbox content rectangles, perspective bounds-only behavior, top-left pixel convention, and anchors outside the image.
2. Run `uv run pytest tests/unit/capture/test_planning.py tests/unit/capture/test_projection.py -v`; expected initial failures identify missing pure functions.
3. Implement `plan_capture_scope(...)`, `pad_bounds(...)`, and `build_capture_correlation(...)` using finite vector math and the adapter-reported plot/content rectangle. Do not query COM from these modules.
4. Re-run the focused tests; expected result is all tests passing on Linux and Windows.
5. Run `uv run pytest tests/unit/capture/test_projection.py -k "twist or letterbox or perspective" -v`; record the exact matrix fixtures and bounds-only issue codes.

### CAP-03 — Add the capture adapter extension and Windows implementation

**Owner:** CAP-C adapter. **Depends on:** CAP-01 and the accepted EPIC-04 context adapter extension; can proceed in parallel with CAP-02 after the additive names are reviewed.

1. Write failing pure tests for adapter schema `1.0`, immutable request/scope/receipt records, additive protocol/provider conformance, fake deterministic PNG/call count/failure injection, and capture-side record mapping.
2. Write failing injected-session tests for PNG device probing, each allowlisted plot type, output-path uniqueness, foreground plotting, timeout, active-document switch, success restoration, operation failure restoration, partial-file cleanup, `DBMOD` mismatch, layout/view/UCS/system-variable mismatch, no leftover selection sets, balanced `WindowsSessionManager.session()` entry/exit, and no direct COM initialization in `windows_capture.py`.
3. Run `uv run pytest tests/adapter/test_capture_protocol.py tests/adapter/test_fake_capture.py tests/adapter/test_windows_capture_imports.py tests/adapter/test_windows_capture.py tests/unit/capture/test_adapter_client.py -v`; expected initial failures identify the absent additive extension.
4. Implement `capture_protocol.py` and `fake_capture.py` without Windows imports. Implement `windows_capture.py` as an additive `WindowsContextAutoCADAdapter` subclass receiving `WindowsSessionManager` and using only `session(require_document=True)`/`AutoCADSession`. Implement `capture/adapter_client.py` against `CaptureAutoCADAdapter`, never the Windows class.
5. Re-run the focused command; all success/failure paths must restore state, remove partial files, and exit the injected session manager context.
6. Run `uv run python -c "import autocad_mcp.adapter.capture_protocol, autocad_mcp.adapter.fake_capture, autocad_mcp.capture.models, autocad_mcp.capture.projection"` on Linux; expected result is exit code 0 with neither `adapter.windows_capture` nor COM modules loaded.
7. Freeze every CAP-C path before CAP-B/E/F integrate it. Later adapter defects return to CAP-C; no other lane edits an adapter-extension file.

### CAP-04 — Validate PNGs and render outside-DWG overlays

**Owner:** CAP-D image. **Depends on:** CAP-01; independent of CAP-02/CAP-03.

1. Write failing PNG tests using tiny committed byte literals for valid RGB/RGBA PNGs, bad signature, missing IHDR/IDAT/IEND, bad CRC, invalid color/depth, duplicate critical chunks, oversized dimensions, pixel overflow, and byte overflow.
2. Write failing overlay tests for SVG allowlist, XML escaping, numeric handle ordering, eight-position placement, gutter fallback, leader lines, top-left coordinates, requested-handle completeness, no drawing text, no external URLs/scripts, and the 6 MiB limit.
3. Write failing artifact tests that inject exceptions at directory creation, clean-file write, image read, PNG validation, overlay render, MCP shaping, cancellation, and final cleanup.
4. Run `uv run pytest tests/unit/capture/test_png.py tests/unit/capture/test_overlay.py tests/unit/capture/test_artifacts.py -v`; expected initial failures identify missing modules/functions.
5. Implement a bounded streaming PNG chunk inspector using `struct`, `zlib.crc32`, and explicit byte counters; implement SVG through XML-safe construction; implement per-invocation cleanup through `tempfile.TemporaryDirectory` and `finally`.
6. Re-run the three focused test files; expected result is all tests passing without an image-processing dependency.

### CAP-05 — Orchestrate capture with a focused fake

**Owner:** CAP-E service/fake. **Depends on:** CAP-01 through CAP-04.

1. Write failing service tests that prove validation occurs before capture-adapter acquisition; `source_snapshot_id` uses `SnapshotRepository.get_complete`; expired/missing sources fail; a 501-entity multi-page `SnapshotBuilder` result succeeds; partial/revision/10,001-entity/32-MiB-over failures stop before capture; source/fresh mismatch stops before capture; all three modes call once; clean is default; overlay is opt-in; post-builder/fingerprint mismatch discards bytes; no success can return `unverified`; active-document switch fails; state-restore failure wins over image success; timeout cleans files; and returned metadata excludes image bytes.
2. Run `uv run pytest tests/unit/capture/test_service.py -v`; expected initial result is missing service/fake behavior.
3. Configure `FakeCaptureAutoCADAdapter` through its public constructor/failure hooks with an explicit `capture_call_count`, deterministic PNG bytes, and configurable receipt/error/state records. Do not edit CAP-C files or add general AutoCAD emulation.
4. Implement `CaptureService.capture_drawing_view` in the exact order: validate; load an optional complete source from `SnapshotRepository`; build the fresh complete pre-snapshot; insert/use it when no source was supplied; check source identity/fingerprint; resolve scope/entities; create temp artifacts; invoke `CaptureAutoCADAdapter` once; inspect PNG; build correlation; optionally render overlay; build the complete post-snapshot; verify adapter state and matching complete digest; enforce limits; materialize bytes; cleanup.
5. Re-run the focused service tests, then `uv run pytest tests/unit/capture -v`; expected result is all capture unit tests passing.

### CAP-06 — Register one explicit MCP tool and prove non-invocation elsewhere

**Owner:** CAP-F MCP. **Depends on:** CAP-05.

1. Write failing contract tests for exact input schema, defaults, each mode, clean PNG image content, annotated SVG image content, metadata/image non-duplication, every capture error, total serialized size, stderr-only logs, and tool-catalog agreement. Assert the stale-source path returns the imported `ErrorCode.STALE_SNAPSHOT` with wire string `"STALE_SNAPSHOT"`, and that the EPIC-05 error additions contain no second stale-snapshot member or alias.
2. Write `test_capture_is_explicit.py` with a provider spy. Start/initialize/shutdown the server and invoke `server_status`, `list_entities`, `get_entity_info`, `query_entities`, `get_entity_context`, and `analyze_drawing`; `capture_call_count` and capture-adapter construction count must remain zero. Invoke `capture_drawing_view` once and assert both counts become exactly one. The test's inventory must be extended when later plan/edit tools land.
3. Run `uv run pytest tests/contract/test_capture_tool.py tests/contract/test_capture_is_explicit.py tests/contract/test_server_tool_catalog.py -v`; expected initial failures show the tool is absent.
4. Compose the CAP-C `CaptureAdapterProvider`, EPIC-04 `SnapshotBuilder`, singleton `SnapshotRepository`, and imported EPIC-04 `ErrorCode.STALE_SNAPSHOT`, but construct/invoke `CaptureService` only inside the capture handler. Add only capture-specific core error members, return one JSON and one image content block, register exactly `capture_drawing_view`, and update `mcp.json` to match.
5. Re-run the focused command, then `uv run pytest tests/contract -v`; expected result is all contract tests passing with protocol-clean stdout.

### CAP-07 — Verify full AutoCAD 2026 with a disposable DWG

**Owner:** CAP-G Windows/docs. **Depends on:** CAP-01 through CAP-06.

1. Write the Windows integration/runner test first. Assert acquisition of the EPIC-03 exclusive verification lease with owner `EPIC-05/capture-autocad-2026/<pid>` before AutoCAD connection/fixture access, contention refusal while base/CTX/another CAP runner holds it, and `finally` release on success, assertion failure, timeout, injected post-write failure, and cleanup failure. After acquisition the runner converts the committed EPIC-04 DXF seed to a uniquely named temporary DWG, saves and reopens that copy, then records disk hash, EPIC-04 content/presentation digests, `DBMOD`, active document/layout/view/UCS, plot settings, system variables, and selection-set names.
2. Run the exact command below. A missing PNG plot device is a structured capability result and leaves the stage incomplete; it is not converted into a screenshot or a passing skip.
3. Verify `WindowsCaptureAutoCADAdapter` capability/state handling until real `current`, `extents`, and known-handle `selection` captures each return valid non-empty PNGs within bounds and correlation metadata for the same document/snapshot. If a Windows mapping/lifecycle defect appears, return it to CAP-C and rerun CAP-C focused tests; CAP-G does not edit adapter-extension files.
4. Request one handle overlay and verify the SVG embeds the PNG, labels every requested fixture handle, contains no fixture text, and leaves the same DWG state.
5. Exercise real failure cleanup by wrapping the real adapter in the test so it raises immediately after a real PNG is written. Assert the service returns the injected structured error, removes the PNG and request directory, restores AutoCAD state, and does not return image bytes.
6. Compare pre/post content digest, `DBMOD`, layout/view/UCS/plot/system-variable/selection state, and on-disk DWG SHA-256. Close without saving, verify no modal interaction and successful temp cleanup, then release the lease. Lease release occurs after AutoCAD/temp cleanup has been attempted and cannot be skipped by cleanup failure.
7. Update docs only from recorded results. AutoCAD 2021-2025 remain `Targeted, not verified`.

Exact command from Windows PowerShell with full AutoCAD 2026:

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_capture_autocad_2026.ps1 -AutoCADProgId AutoCAD.Application.25.1 -Fixture tests/fixtures/context/context_fixture_v1.dxf -Artifacts .artifacts/capture-autocad-2026
```

### CAP-08 — Run the completion gate

**Owner:** integration lead. **Depends on:** CAP-07.

Run, in order:

```bash
uv run pytest tests/unit/capture tests/adapter/test_capture_protocol.py tests/adapter/test_fake_capture.py tests/adapter/test_windows_capture_imports.py tests/adapter/test_windows_capture.py -v
uv run pytest tests/contract/test_capture_tool.py tests/contract/test_capture_is_explicit.py tests/contract/test_server_tool_catalog.py -v
uv run pytest -v
uv run ruff check src tests
uv run mypy src/autocad_mcp
python -m compileall -q src tests
git diff --check
```

Record exact exit codes and test counts. Linux output is labelled only `unit tested` or `MCP contract tested`; only CAP-07 may produce the feature-specific label `visual capture verified on full AutoCAD 2026`.

## Independent subagent lanes

After CAP-01 freezes public contracts, the integration lead may dispatch:

```text
CAP-01 contracts
   |-- CAP-02 planning/correlation ----------------|
   |-- CAP-03 Windows adapter/protocol -------------|--> CAP-05 service/fake
   `-- CAP-04 PNG/overlay/artifacts ----------------|          |
                                                              v
                                                       CAP-06 MCP/explicitness
                                                              |
                                                              v
                                                       CAP-07 Windows/docs
                                                              |
                                                              v
                                                       CAP-08 completion
```

- CAP-02, CAP-03, and CAP-04 own disjoint files and can proceed independently after reviewing CAP-01.
- CAP-C exclusively owns `adapter/__init__.py`, `capture_protocol.py`, `fake_capture.py`, `windows_capture.py`, capture adapter tests/fixtures, and `capture/adapter_client.py`. Every other lane treats those paths as read-only.
- CAP-C owns every new COM call and AutoCAD state receipt; only `windows_capture.py` may consume the injected `WindowsSessionManager`/`AutoCADSession` boundary.
- CAP-04 owns all image parsing, SVG creation, and temporary artifact lifecycle; it never imports the Windows adapter.
- CAP-05 is the only owner of orchestration and configures the frozen CAP-C fake without editing it.
- CAP-06 is the only owner of server registration, `mcp.json`, and explicit-invocation contract tests.
- CAP-07 is the only owner of real-AutoCAD evidence and canonical documentation.
- Workers return focused test output and a diff. Contract conflicts go back to the integration lead; workers do not edit another lane's file to work around them.

## Acceptance criteria

1. `capture_drawing_view` exists in the canonical server and `mcp.json` with one exact version 1 schema.
2. Startup, initialization, shutdown, status, all EPIC-04 tools, later plan/edit handlers, and ordinary model turns make zero capture calls. Only an explicit capture invocation constructs and invokes the capture service.
3. `current`, `extents`, and `selection` modes match the semantics above and have focused pure, contract, and real-AutoCAD tests.
4. The default result is one clean PNG with no server-added labels or DWG changes.
5. Handle overlay is opt-in, generated outside AutoCAD, labels every requested handle deterministically, and returns one safe SVG image without drawing text or external content.
6. Every result includes same-document snapshot/fingerprint, active context, plotted WCS bounds, actual pixel size, content rectangle, correlation quality/matrix, state label, and any handle anchors/issues.
7. No vision provider, inference dependency, provider configuration, or API key is added.
8. Request/image/metadata/MCP payload/timeout/temp-file bounds are enforced before return, and only version 1 PNG clean capture is accepted.
9. Missing devices/modes/members, invalid scope, document switch, timeout, invalid/large image, restore failure, concurrent drawing change, and cleanup failure have stable capture errors; stale source state uses the single EPIC-04-owned serialized `ErrorCode.STALE_SNAPSHOT` and EPIC-05 defines no duplicate.
10. Success and every injected failure path leave no request temporary directory or partial output.
11. `CaptureAutoCADAdapter` is a versioned additive extension of EPIC-04 context; EPIC-03's `AutoCADAdapter` remains exactly four read-only/status methods. Its protocol/fake import without COM, and only `windows_capture.py` consumes the injected `WindowsSessionManager`.
12. A supplied `source_snapshot_id` is resolved only through `SnapshotRepository.get_complete`; expired, missing, or stale sources fail before capture.
13. Every success is correlated to complete pre/post `SnapshotBuilder` results. Partial/revision failures or drawings beyond 10,000 entities/32 MiB fail structurally; no page-derived fingerprint or successful `unverified` state exists.
14. Platform-independent capture modules import and test without Windows COM.
15. The AutoCAD 2026 runner captures all modes and overlay against a disposable DWG, proves output creation, exercises failure cleanup after a real PNG is written, observes no modal UI, and confirms unchanged drawing file/content and restored application/document state.
16. Documentation reports only obtained evidence and leaves AutoCAD 2021-2025, LT, Linux-hosted AutoCAD, and macOS unverified/out of scope as appropriate.

## Windows / AutoCAD 2026 disposable-DWG verification

The runner requires `AutoCAD.Application.25.1`, verifies the product is full AutoCAD 2026, and refuses a different release or LT. It creates a unique OS-temporary directory, opens the fixed DXF seed, saves a DWG copy there, closes the seed, and performs every capture against the copy. It never discovers or opens user drawings by scanning Documents, Desktop, recent files, or project directories.

Before the first capture, record the DWG disk SHA-256, complete EPIC-04 content fingerprint, `DBMOD`, active document, active layout/space, UCS, view, selected PNG device, layout plot properties, `BACKGROUNDPLOT`, and selection-set inventory. Run current, extents, selection for handles fixed in the fixture, and opt-in overlay. Validate PNG structure/dimensions/byte limits and same-document correlation. Save human-viewable result copies only in the explicit `.artifacts` directory; these contain only the deterministic fixture.

The failure-cleanup case calls the real adapter to create one PNG, then a test wrapper raises before the service reads it. Confirm no image content is returned, the request temp directory is absent, and all AutoCAD state equals the baseline. After all cases, compare content fingerprint, `DBMOD`, layout/view/UCS/plot/system-variable/selection state, and disk SHA-256. Close the DWG without saving, delete the disposable directory, and record whether AutoCAD showed a modal dialog or required manual interaction; either condition fails unattended verification.

Evidence JSON records Windows release, AutoCAD product/version/ProgID, Python version, dependency-lock hash, fixture hash, disposable-DWG pre/post hash, image SHA-256/MIME/dimensions/bytes for each successful mode, errors for the injected failure, selected capabilities/device, state comparisons, cleanup result, command, timestamps, test counts, and modal flag. It excludes absolute personal paths and arbitrary drawing content.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Plot APIs modify layout or `DBMOD` even when values are restored | Read back all state and fail the real gate; use another state-neutral AutoCAD capability or return `CAPTURE_UNAVAILABLE`. |
| Capture methods leak into the stable four-method base adapter | Keep them in versioned `CaptureAutoCADAdapter`; protocol-shape tests assert the base remains unchanged and CAP-C exclusively owns extension paths. |
| Feature code bypasses COM lifecycle isolation | Only `windows_capture.py` may use `AutoCADSession`, through an injected `WindowsSessionManager`; import tests reject COM names in protocol/fake/domain modules. |
| A stale or partial context page is correlated as a complete source | Resolve caller-supplied IDs only with `SnapshotRepository.get_complete`, use `SnapshotBuilder` for fresh pre/post state, and never derive a fingerprint from `AnalyzeDrawingResult`. |
| PNG PC3 is missing, renamed, localized, or configured differently | Probe real device names/capabilities; record the selected device; never silently screen-capture or relabel another format. |
| `current` capture steals focus or changes zoom | Use display plot scope without Zoom/UI automation and verify view/state before and after. |
| Selection framing is mistaken for isolation | Document and encode framing semantics; never hide non-selected objects. |
| Capture races with a user edit or document switch | Bind pre-snapshot, adapter receipt, and post-snapshot; discard bytes on document/fingerprint mismatch. |
| Large or malicious image output exhausts memory/stdio | Enforce dimensions/pixels/file bytes before full processing and a 10 MiB complete-result limit. |
| SVG introduces script or external-content risk | Generate only allowlisted elements/attributes, XML-escape labels, allow only normalized handles, and embed one validated PNG data URI. |
| Correlation is inaccurate for perspective or clipped viewports | Return `bounds_only` plus capability evidence and reject overlay when affine correlation is unavailable. |
| Temporary drawing pixels survive a failure | Random per-request temp directory, no caller paths, `finally` cleanup, injected failure tests, and no long-lived cache. |
| Visual output is treated as authoritative CAD truth | Return correlation facts only; keep vision in the client/model and preserve EPIC-04 fact/evidence separation. |
| Linux/fake evidence is reported as AutoCAD behavior | Keep evidence labels separate and require the named full AutoCAD 2026 runner. |

## Rollback

Before a released version, revert the focused epic commits. Remove `capture_drawing_view` registration and its `mcp.json` schema together, then remove capture-only modules/tests/docs. No drawing migration, cache, database, or persistent artifact cleanup is required because request directories are ephemeral.

After version `1.0` is released, an emergency rollback disables the single tool as a unit while retaining the request/result parser and fixtures for compatibility analysis. Do not make capture automatic as a fallback and do not redirect callers to a screenshot path. Previously returned images are client-owned; the server keeps no index or cache to delete. A contract change ships under a compatible minor or new major schema version, never by redefining `1.0`.

## Completion evidence

The pull request must attach or link:

- focused unit output/counts for contracts, planning, projection, Windows-proxy mapping, PNG inspection, SVG overlay, artifact cleanup, and service orchestration;
- additive adapter evidence proving the four-method read-only/status base is unchanged, pure protocol/fake imports without COM, injected Windows sessions balance, and only CAP-C edited adapter-extension files;
- builder/repository-source tests for complete lookup, 501-entity multi-page materialization, expired/missing/stale sources, revision/partial failures, and 10,001-entity/32-MiB-over rejection before capture;
- MCP contract output proving catalog/schema/image/error/size behavior, clean stdout, and explicit invocation only;
- stale-source evidence proving the handler consumes EPIC-04's one `ErrorCode.STALE_SNAPSHOT` member/wire value and adds no capture alias;
- full `pytest`, Ruff, mypy, compileall, and `git diff --check` output;
- clean PNG and opt-in overlay SHA-256/MIME/dimension/byte metadata from the deterministic fixture;
- redacted full AutoCAD 2026 evidence for all three modes, injected post-write failure cleanup, pre/post drawing and state comparisons, modal flag, and disposable-directory cleanup;
- capability evidence naming the real PNG device/backend used;
- dependency evidence showing no vision or image-processing provider was added;
- canonical documentation changes that distinguish unit, MCP, and real-AutoCAD results.

Roadmap stage 4 closes only in the pull request containing all acceptance evidence. A handler, screenshot, or passing fake alone is not completion.

## Handoff

The integration lead provides each worker this epic, EPIC-04's released contract/evidence, the modernization design, repository `AGENTS.md`, and only its lane-owned files. Each worker begins with the specified failing tests and returns exact commands/results plus any observed capability mismatch.

At completion, hand the safe-edit epic the `capture_drawing_view` wire contract, explicit-invocation guard test, `CaptureAutoCADAdapter` protocol/capability report, `SnapshotRepository` source rule, the imported EPIC-04 `ErrorCode.STALE_SNAPSHOT` ownership rule, context correlation fields, and AutoCAD 2026 state-restoration evidence. Capture remains optional before or after an edit; edit preview/application must never call it implicitly. Hand future semantic work only the image/correlation response contract—never a server-side vision provider, duplicate stale-snapshot code, or a claim that raster observations are CAD facts.
