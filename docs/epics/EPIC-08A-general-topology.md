# EPIC-08A: General Topology

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

**Planned.** This is the first independently deliverable half of EPIC-08. It is read-only and domain-neutral. Nothing here is current functionality or evidence that topology is available.

## Outcome and user value

A user can query a bounded, deterministic topology graph for a complete EPIC-04 drawing snapshot without assuming that the drawing is architectural, mechanical, or manufacturing data. Every node, relation, loop, and component retains source handles, tolerance, method version, measurements, and unsupported/indeterminate evidence.

The result can be reused by later domains, including EPIC-08B mechanical semantics, without changing EPIC-04 CAD facts or silently expanding geometry support.

## Scope

- Normalize only released EPIC-04 point, line, arc, circle, and polyline geometry into read-only topology primitives.
- Evaluate bounded, tolerance-aware `intersects`, `touches`, `contains`, `within`, `overlaps`, `disjoint`, `parallel`, `perpendicular`, `collinear`, `concentric`, `tangent`, and `connected` relations where the primitive pair has an accepted predicate.
- Derive closed planar loops and connected components with explicit provenance.
- Materialize one complete `TopologySnapshot` per canonical `TopologyBuildSpec`, retain it in a semantic-input-keyed repository, and page it only as `TopologyResultPage`.
- Use a deterministic spatial candidate index; never materialize unbounded all-pairs or global disjoint relations.
- Return filters, pagination, signed cursor bindings, method/tolerance metadata, and structured capability issues.
- Register one read-only `query_topology` tool after the evaluator, scale, contract, and real-extraction gates pass.

## Out of scope

- Spline, ellipse, hatch, region, mesh, surface, solid, proxy, xref-owned, block-definition-expansion, or raster topology in version 1.
- Adding spline/hatch/mesh fields to EPIC-04 or changing its schema version. A later context schema-minor proposal must own extraction, serialization, compatibility, and AutoCAD evidence before topology consumes a new kind.
- Mechanical/architectural labels, geometric repair, snapping, tolerance widening, source mutation, capture, approval, editing, and code generation.
- 3D solid topology, general non-coplanar intersection, and claims of exact computational geometry beyond the published predicates/tolerance.
- AutoCAD LT and AutoCAD operation on Linux/macOS.

## Prerequisites

1. EPIC-02's installed `autocad_mcp` core, `ToolError`, canonical stdio server, and contract tests are accepted.
2. EPIC-03's adapter/session boundary and full AutoCAD 2026 smoke evidence are accepted.
3. EPIC-04's `DrawingSnapshot`, complete `SnapshotRepository`, point/line/arc/circle/polyline `GeometryFacts`, units/tolerance, bounds, handle identity, fingerprint, capability issues, and Windows extraction are accepted unchanged.
4. A labelled synthetic topology corpus and separately stored disposable AutoCAD fixture set can be reviewed without proprietary content.
5. Canonical integration uses `tests/contract/test_stdio_server.py` and `tests/contract/test_server_tool_catalog.py`.

## Proposed owned files

| Path | Responsibility | Exclusive owner |
| --- | --- | --- |
| `src/autocad_mcp/topology/models.py` | Primitive, plane, graph, query, and result contracts | E08A-A contracts |
| `src/autocad_mcp/topology/primitives.py` | EPIC-04 geometry normalization and structured rejection | E08A-A contracts |
| `tests/fixtures/topology/manifest.json` and `cases/**` | Frozen labelled topology corpus | E08A-B corpus |
| `tests/evaluation/test_topology_corpus.py` | Independent graph/loop/component evaluator | E08A-B corpus |
| `src/autocad_mcp/topology/predicates.py` | Pure accepted primitive-pair predicates | E08A-C predicates |
| `src/autocad_mcp/topology/index.py` | Bounded spatial candidate enumeration | E08A-D index |
| `src/autocad_mcp/topology/graph.py` | Deterministic edges, loops, and components | E08A-E graph/service |
| `src/autocad_mcp/topology/service.py` | Snapshot validation, filters, pagination, result shaping | E08A-E graph/service |
| `src/autocad_mcp/topology/repository.py` | Complete version-bound topology results shared with EPIC-08B | E08A-E graph/service |
| `src/autocad_mcp/tools/topology.py` | Read-only `query_topology` handler | E08A-F contract |
| `tests/contract/test_topology_tool.py` | Exact tool schema/success/error contract | E08A-F contract |
| `tests/integration/windows/test_topology_autocad.py` | Later real extraction/topology evaluation only | E08A-G real evaluation |
| `tests/windows/run_topology_autocad_2026.ps1` | EPIC-03-harness runner accepting only a source DWG | E08A-G real evaluation |
| `tests/windows/drawing_copy_guard.py` | Consumed unchanged neutral source/copy guard | EPIC-03 owner; read-only to E08A |
| `docs/general-topology.md` | Contract, supported pairs, limits, and evidence labels | Documentation owner |

The serialized integration owner alone modifies `src/autocad_mcp/core/models.py`, `runtime.py`, `server.py`, `mcp.json`, `tests/contract/test_stdio_server.py`, `tests/contract/test_server_tool_catalog.py`, or canonical project documentation. E08A-B is the only owner permitted to change corpus labels/evaluator; real-evaluation and algorithm lanes consume them read-only.

## Consumed interfaces and types

The following exact EPIC-04 types are imported rather than redefined:

```python
@dataclass(frozen=True, slots=True)
class Point3D:
    x: float
    y: float
    z: float

@dataclass(frozen=True, slots=True)
class Bounds3D:
    minimum: Point3D
    maximum: Point3D

class SnapshotRepository(Protocol):
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...
```

`DrawingSnapshot`, `SnapshotRef`, `GeometryTolerance`, `EntityContext`, `PointGeometry`, `LineGeometry`, `ArcGeometry`, `CircleGeometry`, `PolylineGeometry`, `UnsupportedGeometry`, and `CapabilityIssue` also retain their EPIC-04 meaning. `Bounds3D` is never represented as a six-number tuple in domain topology output. A snapshot must have `materialization.complete is True`, `fingerprint.complete is True`, and matching materialization/fingerprint/entity counts; otherwise topology returns the accepted structured incomplete-snapshot failure. MCP response pagination belongs to `AnalyzeDrawingResult` and is not part of the retained complete snapshot.

## Produced interfaces and types

```python
PrimitiveKind = Literal["point", "line", "arc", "circle", "polyline_segment"]

@dataclass(frozen=True, slots=True)
class TopologyPlane:
    origin_wcs: Point3D
    normal_wcs: Point3D
    x_axis_wcs: Point3D
    y_axis_wcs: Point3D

@dataclass(frozen=True, slots=True)
class NormalizedPrimitive:
    primitive_id: str
    snapshot_id: str
    owner_handle: str
    kind: PrimitiveKind
    plane: TopologyPlane
    geometry: Mapping[str, JsonValue]
    bounds_wcs: Bounds3D

class TopologyRelation(StrEnum):
    INTERSECTS = "intersects"
    TOUCHES = "touches"
    CONTAINS = "contains"
    WITHIN = "within"
    OVERLAPS = "overlaps"
    DISJOINT = "disjoint"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    COLLINEAR = "collinear"
    CONCENTRIC = "concentric"
    TANGENT = "tangent"
    CONNECTED = "connected"

@dataclass(frozen=True, slots=True)
class TopologyNode:
    node_id: str
    primitive: NormalizedPrimitive

@dataclass(frozen=True, slots=True)
class RelationMeasurement:
    distance: float | None
    angle_radians: float | None
    overlap_length: float | None
    intersection_points_wcs: tuple[Point3D, ...]

@dataclass(frozen=True, slots=True)
class TopologyEdge:
    edge_id: str
    left_node_id: str
    right_node_id: str
    relation: TopologyRelation
    method_version: str
    tolerance: GeometryTolerance
    measurement: RelationMeasurement
    owner_handles: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class ClosedLoopFact:
    loop_id: str
    node_ids: tuple[str, ...]
    owner_handles: tuple[str, ...]
    plane: TopologyPlane
    signed_area: float
    orientation: Literal["clockwise", "counterclockwise"]

@dataclass(frozen=True, slots=True)
class ConnectedComponentFact:
    component_id: str
    node_ids: tuple[str, ...]
    owner_handles: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class TopologyBuildSpec:
    schema_version: Literal["1.0"]
    source: SnapshotRef
    snapshot_schema_version: Literal["1.0"]
    topology_method_version: str
    handle_scope: tuple[str, ...]
    relations: tuple[TopologyRelation, ...]
    tolerance_override: GeometryTolerance | None
    spec_digest: str

@dataclass(frozen=True, slots=True)
class TopologySnapshot:
    schema_version: Literal["1.0"]
    topology_snapshot_id: str
    source: SnapshotRef
    build_spec: TopologyBuildSpec
    effective_tolerance: GeometryTolerance
    nodes: tuple[TopologyNode, ...]
    edges: tuple[TopologyEdge, ...]
    loops: tuple[ClosedLoopFact, ...]
    components: tuple[ConnectedComponentFact, ...]
    issues: tuple[CapabilityIssue, ...]
    complete: Literal[True]

@dataclass(frozen=True, slots=True)
class TopologyQuery:
    source_snapshot_id: str
    source_document_id: str
    source_session_id: str
    source_fingerprint: str
    snapshot_schema_version: Literal["1.0"]
    topology_method_version: str
    handle_scope: tuple[str, ...]
    relations: tuple[TopologyRelation, ...]
    tolerance_override: GeometryTolerance | None
    topology_spec_digest: str
    include_loops: bool
    include_components: bool
    page_size: int
    cursor: str | None

@dataclass(frozen=True, slots=True)
class TopologyPageInfo:
    page_size: int
    returned: int
    has_more: bool
    next_cursor: str | None

@dataclass(frozen=True, slots=True)
class TopologyResultPage:
    schema_version: Literal["1.0"]
    topology_snapshot_id: str
    source: SnapshotRef
    topology_method_version: str
    topology_spec_digest: str
    effective_tolerance: GeometryTolerance
    nodes: tuple[TopologyNode, ...]
    edges: tuple[TopologyEdge, ...]
    loops: tuple[ClosedLoopFact, ...]
    components: tuple[ConnectedComponentFact, ...]
    issues: tuple[CapabilityIssue, ...]
    page: TopologyPageInfo

class TopologyRepository(Protocol):
    def put_complete(self, snapshot: TopologySnapshot) -> None: ...
    def get_complete(self, spec: TopologyBuildSpec) -> TopologySnapshot: ...
```

`TopologyPlane` requires finite vectors, unit normal, orthonormal axes, right-handed `x_axis_wcs × y_axis_wcs == normal_wcs` within angular tolerance, and all primitive points coplanar within linear tolerance. Version 1 point/line/polyline normalization accepts one constant-Z plane parallel to WCS XY; arc/circle normals define their plane. A sloped line/polyline, non-coplanar, or degenerate input is indeterminate/unsupported, never projected silently.

`TopologyBuildSpec.spec_digest` is lowercase SHA-256 over canonical structured fields excluding `spec_digest` itself: source snapshot ID/document/session/fingerprint, snapshot schema version, topology method version, normalized sorted handle scope, normalized relation set, and exact tolerance override. `topology_snapshot_id` binds that digest plus the complete canonical topology bytes. Every semantic input therefore participates in the repository key `(source.snapshot_id, source.fingerprint, snapshot_schema_version, topology_method_version, spec_digest)`; a mismatch is a miss/stale failure, never a fallback. The repository retains at most four complete topology snapshots, 32 MiB each and 128 MiB total, for 10 minutes and fails capacity explicitly without eviction.

Edge IDs bind the build-spec digest, sorted node IDs, relation, method version, and effective tolerance. Symmetric relations store sorted nodes once. `contains`/`within` are directional linked results. `disjoint` is computed only for the explicit bounded build scope and is not materialized globally.

`TopologySnapshot` is the complete immutable server-side/downstream object and contains no page size, cursor, last key, or response filtering state. `TopologyQuery` must repeat and exactly match all build-semantic fields/digest before paging that retained object. `TopologyResultPage` alone carries `TopologyPageInfo`; its signed cursor binds topology snapshot ID, spec digest, deterministic result ordering, page size, last key, and expiry.

Build/query scopes allow 1-256 handles and result pages allow 1-500 items, matching EPIC-04. All numbers are finite. An explicit tolerance override must satisfy EPIC-04 validation and is stored in the build spec/effective result; the service never widens it automatically.

## Work packages

### E08A-WP01: Freeze contracts and normalization

**Owned files:** `topology/models.py`, `topology/primitives.py`, matching unit tests.

**TDD steps:**

1. Write failing type/validation/deterministic-ID tests and exact vectors for `Point3D`, imported `Bounds3D`, `TopologyPlane`, primitives, edges, loops, components, `TopologyBuildSpec`, complete `TopologySnapshot`, paged `TopologyResultPage`, limits, and issues.
2. Add positive and rejection tests for each released EPIC-04 geometry union member; block reference and unsupported geometry produce explicit issues, while spline/hatch fields are rejected as unknown schema data.
3. Implement pure normalization only, with no COM, domain labels, or context schema changes.
4. Publish canonical primitive/build-spec/complete-snapshot/result-page vectors to downstream lanes.

**Exact verification:**

```bash
uv run pytest tests/unit/topology/test_models.py tests/unit/topology/test_primitives.py -q
uv run ruff check src/autocad_mcp/topology/models.py src/autocad_mcp/topology/primitives.py tests/unit/topology
uv run python -c "from autocad_mcp.context.models import Bounds3D; from autocad_mcp.topology.models import TopologyPlane, TopologySnapshot, TopologyResultPage"
```

### E08A-WP02: Freeze corpus and evaluator

**Owned files:** topology fixture manifest/cases and `tests/evaluation/test_topology_corpus.py` only.

**TDD steps:**

1. Freeze at least 50 reviewed cases covering every supported relation, exact/tolerance-boundary negatives, degeneracy, direction/symmetry, gaps, nested loops, self-intersections, duplicates, mixed owners, unsupported geometry, and page/scope limits.
2. Write the independent evaluator before predicates; it compares canonical nodes/edges/loops/components/issues and reports exact mismatches.
3. Record corpus version/digest and two reviewer approvals; future label changes require a new version.
4. Run against empty results to prove failure, then grant detector/index lanes read-only access.

**Exact verification:**

```bash
uv run pytest tests/evaluation/test_topology_corpus.py -q
git diff --check -- tests/fixtures/topology tests/evaluation/test_topology_corpus.py
```

### E08A-WP03: Implement accepted predicates

**Owned files:** `topology/predicates.py`, predicate tests.

**TDD steps:**

1. Add failing table tests for each accepted primitive-pair/relation at exact, just-inside, and just-outside tolerance values.
2. Add reversed-order, degenerate, non-coplanar, duplicate, and unsupported cases; indeterminate is typed, not guessed.
3. Implement only pairs present in the frozen corpus using existing dependencies/standard library.
4. Run the frozen evaluator without editing labels.

**Exact verification:**

```bash
uv run pytest tests/unit/topology/test_predicates.py tests/evaluation/test_topology_corpus.py -q
uv run ruff check src/autocad_mcp/topology/predicates.py tests/unit/topology/test_predicates.py
```

### E08A-WP04: Bound candidate enumeration

**Owned files:** `topology/index.py`, index/scale tests and immutable measurement artifacts.

**TDD steps:**

1. Add failing boundary/cell/tolerance tests proving all expected candidates are returned deterministically.
2. Instrument candidate counts for sparse, clustered, and maximum-scope fixtures and assert explicit request/candidate ceilings fail before allocation.
3. Implement the minimum bounding-box index; no new dependency without recorded evidence.
4. Measure, but do not universalize, wall time/RSS on the recorded runner and preserve the environment with the artifact.

**Exact verification:**

```bash
uv run pytest tests/unit/topology/test_index.py tests/unit/topology/test_scale_bounds.py -q
uv run python tests/performance/measure_topology.py --fixture tests/fixtures/topology/scale-256.json --output .artifacts/epic-08a-topology-performance.json
```

### E08A-WP05: Build graph/service deterministically

**Owned files:** `topology/graph.py`, `topology/service.py`, `topology/repository.py`, graph/service/repository/determinism tests.

**TDD steps:**

1. Add failing tests for deduplication, provenance, direction, components, loops, nested/self-intersecting/gapped/duplicate cases, and issue propagation.
2. Add complete source snapshot/fingerprint validation, 256-handle build scope, relation set/tolerance/version/spec-digest canonicalization, complete topology repository key, 500-result pages, stale/tampered cursor, unsupported tests, and proof that stored snapshots contain no cursor/page state.
3. Add input-order and two-hash-seed determinism tests.
4. Implement without domain labels, capture, source mutation, or COM.

**Exact verification:**

```bash
uv run pytest tests/unit/topology/test_graph.py tests/unit/topology/test_service.py tests/unit/topology/test_repository.py -q
PYTHONHASHSEED=1 uv run pytest tests/unit/topology/test_determinism.py -q
PYTHONHASHSEED=947 uv run pytest tests/unit/topology/test_determinism.py -q
```

### E08A-WP06: Register read-only topology

**Owned files:** `tools/topology.py`, `tests/contract/test_topology_tool.py`; shared integration files remain serialized-owner files.

**TDD steps:**

1. Add exact schema/fake-service tests for all `TopologyBuildSpec`/`TopologyQuery` semantic inputs and digest, valid build/load, bounded pagination, stale source/method/spec, unsupported, invalid, and explicit-disjoint queries.
2. Prove zero capture, mutation, approval, EPIC-06, semantic detector, and execution calls.
3. Implement a thin handler after the corpus evaluator passes.
4. Have the serialized owner update core error members if required, runtime, server, `mcp.json`, catalog, and stdio tests in one window.

**Exact verification:**

```bash
uv run pytest tests/contract/test_topology_tool.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run pytest tests/unit/topology tests/evaluation/test_topology_corpus.py -q
uv run ruff check src/autocad_mcp/topology src/autocad_mcp/tools/topology.py tests/unit/topology tests/contract/test_topology_tool.py
uv run mypy src/autocad_mcp/topology src/autocad_mcp/tools/topology.py
```

### E08A-WP07: Evaluate full AutoCAD 2026 extraction and topology

**Owned files:** Windows integration test, topology PowerShell runner, immutable run artifacts, AutoCAD evidence section only; EPIC-03 harness is consumed read-only.

**TDD steps:**

1. Review EPIC-04 expected geometry/bounds before the run and record fixture/expectation digests.
2. Extract disposable fixtures and label that result only **general topology input extraction verified on full AutoCAD 2026**.
3. Run frozen topology/evaluator and label it only **topology evaluated on AutoCAD-extracted fixtures**; preserve disagreements and do not edit corpus or code in this lane.
4. For every case reuse EPIC-03's neutral `tests/windows/drawing_copy_guard.py`: create a unique-GUID source copy, assert resolved-path inequality/initial hash equality, open under the lane's read-only policy, assert `ActiveDocument.FullName`, close without saving, rehash source/copy, and preserve failed copies.
5. Acquire/release the EPIC-03 exclusive AutoCAD verification lease around every real attach/open/run; lease contention fails closed.
6. Prove unchanged drawing/on-disk fingerprints and report unsupported geometry separately.

**Exact verification:**

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_topology_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\topology-source.dwg
```

## Parallel lanes and exclusive file ownership

E08A-A and E08A-B freeze first. Predicates and index may then run in parallel against their respective exclusive files. Graph/service follows their public outputs; MCP integration follows the evaluator gate; real evaluation runs last. No lane edits corpus/evaluator, another implementation lane, or serialized registry/configuration files.

The EPIC-08B owner receives only accepted public topology types/vectors after EPIC-08A closes. EPIC-08B work does not begin on partial code presence.

## Acceptance criteria

- Version 1 accepts only released EPIC-04 point, line, arc, circle, and polyline geometry and adds no context schema field.
- `Bounds3D` is the exact EPIC-04 type; `TopologyPlane` satisfies the exact finite/orthonormal/right-handed/coplanar contract above.
- Every result retains source snapshot/handle, method, tolerance, measurements, and issues; no domain label enters topology facts.
- Complete `TopologySnapshot` and paged `TopologyResultPage` are distinct types; only the page has cursor/page metadata.
- Canonical `TopologyBuildSpec` and `TopologyQuery` bind source `SnapshotRef`/fingerprint, snapshot/method versions, handle scope, relation set, tolerance override, and spec digest. Repository lookup keys every semantic input and never falls back across mismatches.
- Frozen corpus/evaluator predates algorithms and has exclusive ownership.
- Predicates cover positive, negative, tolerance-boundary, direction/symmetry, degeneracy, and unsupported cases deterministically.
- Request/candidate/page ceilings prevent unbounded all-pairs/disjoint work; scale performance is measured on named hardware rather than generalized.
- `query_topology` is explicit, read-only, bounded, paginated, stale-safe, and protocol-clean.
- AutoCAD evidence uses separate input-extraction verification and topology-evaluation labels and leaves the drawing fingerprint unchanged.

## Windows and AutoCAD verification

Use full AutoCAD 2026 disposable copies containing every supported geometry kind, tolerance boundaries, nested/gapped/self-intersecting loops, paper/model space, unsupported block/proxy geometry, and the maximum 256-handle scope. Record AutoCAD/Windows/Python/lockfile/fixture versions, units/tolerance, capability issues, method version, candidate counts, measured timing/RSS, modal interaction, and before/after fingerprints.

Every real run acquires the EPIC-03 exclusive verification lease keyed by installation/build and interactive-session ID and records release outcome. An unleased or concurrently owned run cannot satisfy this gate.

Only input extraction is described as AutoCAD verified. The topology algorithm is described as evaluated on AutoCAD-extracted fixtures. AutoCAD 2021-2025 remain targeted until their separate extraction/evaluation records exist.

## Safety and security gates

- Complete, fingerprinted EPIC-04 snapshots only; no automatic capture or live COM in pure topology.
- Strict finite/tolerance/scope/page/candidate limits; no silent tolerance widening or projection.
- No spline/hatch/mesh fields, domain labels, repair, mutation, approval, code generation, or arbitrary execution.
- Unsupported/indeterminate results are visible and never guessed.
- Fixture labels/evaluator and real evidence have independent exclusive owners.
- Logs/evidence redact paths and proprietary geometry while retaining digests/aggregate metrics.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Tolerance changes graph meaning | Bind exact tolerance/method to IDs/results/cursors and test both threshold sides |
| Algorithm drifts beyond EPIC-04 | Exhaustive geometry-union normalization tests and explicit schema-minor prerequisite for new kinds |
| Pair enumeration becomes quadratic | Spatial index, 256-handle bound, candidate ceiling instrumentation, no global disjoint materialization |
| Plane/projection invents relations | Exact `TopologyPlane` validation and unsupported non-coplanar results |
| Synthetic corpus overstates real behavior | Separate AutoCAD-extracted evaluation, preserved disagreements, honest labels |

## Rollback

Unregister `query_topology`, restore the last method version, invalidate affected cursors/results, and keep EPIC-04 context tools available. Preserve failing fixtures/evidence. No drawing recovery is required because the epic is read-only. EPIC-08B remains blocked until a corrected EPIC-08A acceptance record exists.

## Completion evidence

- Frozen contract and canonical vectors for types/primitives/results.
- Versioned corpus/evaluator with reviewer approvals and immutable digest.
- Focused red/green, full unit/evaluator/contract, determinism, lint, type, compile, catalog, stdio, and diff checks.
- Supported-pair/tolerance/degeneracy/unsupported coverage and bounded candidate-count evidence.
- Named-runner performance/RSS measurements without universal claims.
- Full AutoCAD 2026 record with separate extraction-verification/topology-evaluation labels and unchanged fingerprints.
- Per-case EPIC-03 neutral-copy-guard and exclusive-lease evidence: GUID copy, source/copy path inequality and hashes, active `FullName`, close-without-save, preserved failed copy, and lease acquisition/release.
- Exact registered catalog/configuration and known unsupported geometry.

## Handoff

The owner freezes contracts and corpus before assigning implementation lanes. Each lane returns signatures, vectors, exact commands/results, changed-file list, and limits. The serialized integration owner performs the only registry/configuration window. The Windows lane consumes all prior artifacts read-only. EPIC-08B receives the accepted topology package, corpus digest, public closed-loop contract, method version, and completion evidence only after independent review closes EPIC-08A.

Related plans: [EPIC-08 index](EPIC-08-general-and-mechanical-semantics.md), [EPIC-08B](EPIC-08B-mechanical-semantics.md), [EPIC-07](EPIC-07-architectural-semantics.md), and [EPIC-04](EPIC-04-structured-drawing-context.md).
