# EPIC-09: Validated Advanced Feature Recovery

## Status

**Planned candidate program.** Surface unfolding, automatic dimensioning, pattern optimization, and constrained code generation are four independent candidates, not a single promised release. Historical files and claims are research inputs only. Each track has its own prerequisites, safety review, measurable gates, AutoCAD evidence, registration decision, rollback, and compatibility statement. One track may be rejected or deferred without blocking or validating another.

Arbitrary execution remains forbidden across the entire epic. No track may expose Python, AutoLISP, VBA, shell, macros, dynamic expressions, or unrestricted AutoCAD `SendCommand` for execution through MCP. The code-generation candidate returns reviewed text only and cannot run, import, save, or apply it.

## Outcome and user value

Maintainers can recover useful advanced ideas without inheriting unsupported historical promises. Users receive an advanced tool only after its numerical/security correctness, safety boundary, failure modes, resource limits, supported inputs, and applicable environment behavior have been measured and documented.

The four possible outcomes are independently valuable:

- surface unfolding can produce a verifiable 2D layout from a narrowly supported triangulated surface;
- automatic dimensioning can propose explainable dimensions without silently changing a drawing;
- pattern optimization can return deterministic, collision-checked sheet placements with honest optimality limits; and
- constrained code generation can produce a digestible, static, template-backed source artifact for human review without any execution path.

## Scope

- Inventory historical research and tests for each candidate without importing its claims into current status.
- Freeze a typed, bounded input/output contract and explicit support matrix per candidate.
- Establish a simple baseline, adversarial/degenerate fixtures, measurable thresholds, and a go/revise/reject decision record per candidate.
- Keep candidate packages and MCP handlers isolated so only a passing track can register.
- Run pure/numerical/security and MCP contract tests for every track; run real full AutoCAD 2026 extraction checks only for D and P.
- Publish approximation, performance, unsupported-entity, and failure reports for every passing track.
- Integrate a passing track through the canonical server only; experimental or rejected implementations remain unregistered.

## Out of scope

- A shared “advanced features complete” status, bundle registration, or compatibility promotion based on another track's evidence.
- Direct reuse of legacy modules without contract review, focused tests, English documentation, dependency review, and target-architecture reconciliation.
- Claims of mathematically optimal unfolding/nesting without a proof, exact general-surface flattening, automatic manufacturing approval, or professionally complete dimension sets.
- Unbounded optimization, nondeterministic results without an explicit seed, hidden network services, provider API keys, or training on user drawings.
- Automatic mutation from computed results. A future apply path must use the exact EPIC-06 preview, independent human approval, stale-state checks, Undo, and rollback behavior, and may require a separately reviewed primitive-operation extension.
- Any code execution, evaluation, compilation, interpreter embedding, subprocess launch, file-system execution staging, dynamic import, macro launch, or caller-controlled `SendCommand`.
- AutoCAD LT and AutoCAD operation on Linux/macOS.

## Prerequisites

### Shared

1. EPIC-02 has completed the installable `src/autocad_mcp/` package migration; `python -m autocad_mcp.server` is the sole canonical stdio launch; structured errors, bounded schemas, fake-service contracts, and stdio integrity are verified.
2. Canonical contract integration uses `tests/contract/test_stdio_server.py` and `tests/contract/test_server_tool_catalog.py`.
3. On-demand capture remains opt-in and is not called by these candidates.
4. EPIC-06 is complete before any candidate obtains a drawing-apply path. Initial candidate delivery remains read-only/output-only.
5. Historical files stay classified as legacy/experimental until an individual track passes all gates.

### Track-specific

- **U — Surface unfolding:** no context or AutoCAD dependency in the first delivery. The caller supplies the complete bounded mesh, seam set, units label, and root face explicitly.
- **D — Dimensioning:** accepted EPIC-08B mechanical facts/interpretations plus EPIC-08A topology and supported EPIC-04 native dimension/style facts; full AutoCAD 2026 is required only for D's extraction evaluation.
- **P — Pattern optimization:** accepted EPIC-08A `ClosedLoopFact`/plane/tolerance contract plus explicit sheet/material boundaries; full AutoCAD 2026 is required only for P's profile extraction evaluation.
- **C — Constrained code generation:** EPIC-02 core models/contract harness only, plus secret/path redaction, static validators, and a security reviewer. It does not depend on EPIC-03–08, AutoCAD, or EPIC-06 apply.

## Independent candidate lifecycle

Every track maintains one decision record with one of these states:

```text
candidate -> contract_frozen -> pure_validated -> environment_validated -> registered
        \-> revise
        \-> rejected
```

- **Contract gate:** reviewed support matrix, types, limits, baselines, fixtures, thresholds, threats, and failure states.
- **Pure gate:** unit/numerical/security/MCP-fake tests and performance limits pass on recorded hosts.
- **Environment gate:** U records independent numerical/performance evaluation on a named host; D/P separately verify input extraction on disposable full AutoCAD 2026 and evaluate outputs on those extracted fixtures; C completes core-only security/non-execution contracts with no AutoCAD run.
- **Registration gate:** canonical schema/handler/docs agree, safety reviewer approves, evidence is attached, and only that track is registered.

`rejected` is a successful program decision when evidence shows insufficient value, unsafe behavior, or unacceptable maintenance cost. Rejected and revised tracks remain absent from MCP registration and product claims.

## Proposed owned files

### Program coordination

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/advanced/bounds.py` | Shared cooperative deadline/cancellation/item/iteration policy | E09-0 program contracts |
| `tests/unit/advanced/test_bounds.py` | Deterministic fake-clock/cancellation contract | E09-0 program contracts |
| `docs/advanced/surface-unfolding-decision.md` | U gate decisions/support matrix; no lane writes it | Track U lead only |
| `docs/advanced/dimensioning-decision.md` | D gate decisions/support matrix; no lane writes it | Track D lead only |
| `docs/advanced/pattern-optimization-decision.md` | P gate decisions/support matrix; no lane writes it | Track P lead only |
| `docs/advanced/constrained-code-generation-decision.md` | C gate decisions/threat disposition; no lane writes it | Track C lead only |
| `docs/advanced/evidence/{unfolding,dimensioning,patterns,codegen}/**` | Content-addressed immutable run artifacts | Matching evidence lane |

### Track U — surface unfolding

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/advanced/unfolding/models.py` | Supported mesh, seam, layout, metric, failure contracts | Lane E09-U1 |
| `src/autocad_mcp/advanced/unfolding/validation.py` | Manifold, connectivity, seam, bounds, degeneracy validation | Lane E09-U1 |
| `src/autocad_mcp/advanced/unfolding/solver.py` | Deterministic rigid-triangle unfolding | Lane E09-U2 |
| `src/autocad_mcp/advanced/unfolding/metrics.py` | Independent edge/area/angle/overlap/reversibility verifier | Lane E09-U3 independent verification |
| `tests/performance/measure_unfolding.py` | In-process named-host wall-time/RSS measurement | Lane E09-U3 independent verification |
| `src/autocad_mcp/advanced/unfolding/service.py` | Caller-supplied mesh orchestration and result shaping | Lane E09-U4 contract |
| `src/autocad_mcp/tools/surface_unfolding.py` | Pure-data candidate handler if U gates pass | Lane E09-U4 contract |
| `tests/unit/advanced/unfolding/**` | Contract, numerical, property, performance tests | Matching U lane |
| `tests/contract/test_surface_unfolding_tool.py` | Exact U tool/core contract | Lane E09-U4 contract |

### Track D — automatic dimensioning

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/advanced/dimensioning/models.py` | Objective, witness, proposal, score, conflict, result contracts | Lane E09-D1 |
| `tests/fixtures/dimensioning/manifest.json` and `cases/**` | Independently frozen labelled D corpus | Lane E09-D0 corpus/verifier |
| `tests/evaluation/test_dimensioning_corpus.py` | Independent precision/duplicate/clearance/conflict evaluator | Lane E09-D0 corpus/verifier |
| `src/autocad_mcp/advanced/dimensioning/candidates.py` | Deterministic candidate generation from facts/topology | Lane E09-D2 |
| `src/autocad_mcp/advanced/dimensioning/layout.py` | Duplicate/conflict/clearance ranking; no drawing mutation | Lane E09-D2 |
| `src/autocad_mcp/advanced/dimensioning/verification.py` | Independent measurement/duplicate/clearance/conflict verification | Lane E09-D3 verifier |
| `src/autocad_mcp/advanced/dimensioning/service.py` | Injected-source validation, bounded orchestration, output | Lane E09-D4 service |
| `src/autocad_mcp/tools/dimension_proposals.py` | Read-only proposal handler if D gates pass | Lane E09-D4 service |
| `tests/unit/advanced/dimensioning/**` | Contract, geometry, golden, evaluation tests | Matching D lane |
| `tests/contract/test_dimension_proposals_tool.py` | Exact D tool schema/fake-service contract | Lane E09-D4 service |
| `tests/integration/windows/test_dimension_proposals_autocad.py` | Native fact extraction and proposal evaluation | Lane E09-D5 evidence |
| `tests/windows/run_dimension_proposals_autocad_2026.ps1` | EPIC-03-harness D runner accepting source DWG | Lane E09-D5 evidence |

### Track P — pattern optimization

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/advanced/patterns/models.py` | Sheet, part, rotations, placement, objective, result contracts | Lane E09-P1 |
| `src/autocad_mcp/advanced/patterns/validation.py` | Polygon, clearance, units, limits, feasibility validation | Lane E09-P1 |
| `src/autocad_mcp/advanced/patterns/baseline.py` | Deterministic shelf baseline used for comparison | Lane E09-P2 |
| `src/autocad_mcp/advanced/patterns/optimizer.py` | Bounded deterministic placement heuristic | Lane E09-P2 |
| `tests/performance/run_pattern_benchmarks.py` | In-process frozen benchmark measurement | Lane E09-P2 |
| `src/autocad_mcp/advanced/patterns/verification.py` | Independent bounds, overlap, clearance, utilization checks | Lane E09-P3 |
| `src/autocad_mcp/advanced/patterns/service.py` | Bounded orchestration and result shaping | Lane E09-P3 |
| `src/autocad_mcp/tools/pattern_optimization.py` | Read-only placement handler if P gates pass | Lane E09-P3 |
| `tests/unit/advanced/patterns/**` | Contract, property, benchmark, performance tests | Matching P lane |
| `tests/contract/test_pattern_optimization_tool.py` | Exact P tool schema/fake-service contract | Lane E09-P3 |
| `tests/integration/windows/test_pattern_optimization_autocad.py` | Profile extraction/result correlation | Lane E09-P4 evidence |
| `tests/windows/run_pattern_optimization_autocad_2026.ps1` | EPIC-03-harness P runner accepting source DWG | Lane E09-P4 evidence |

### Track C — constrained code generation

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/advanced/codegen/models.py` | Typed recipe, template, artifact, finding, result contracts | Lane E09-C1 |
| `src/autocad_mcp/advanced/codegen/templates.py` | Versioned allowlisted built-in templates only | Lane E09-C2 |
| `src/autocad_mcp/advanced/codegen/render.py` | Literal-only deterministic rendering and digest | Lane E09-C2 |
| `src/autocad_mcp/advanced/codegen/validate.py` | Python AST and target-specific static deny/allow checks | Lane E09-C3 |
| `src/autocad_mcp/advanced/codegen/service.py` | Output-only orchestration; no file write or execution | Lane E09-C3 |
| `src/autocad_mcp/tools/constrained_code_generation.py` | Output-only handler if C gates pass | Lane E09-C4 |
| `tests/unit/advanced/codegen/**` | Contract, golden, injection, security tests | Matching C lane |
| `tests/contract/test_constrained_code_generation_tool.py` | Exact C output-only contract | Lane E09-C4 |
| `tests/contract/test_no_execution_tools.py` | Registry and capability-deny contract | Lane E09-C4 |
| `tests/windows/drawing_copy_guard.py` | Consumed unchanged by D/P read-only runners | EPIC-03 owner; read-only to E09 |

The canonical registry, `mcp.json`, and canonical project documents remain integration-owner files and are modified for only one passing track at a time. No candidate lane modifies a different track's package or decision record.

## Consumed interfaces

```python
MAX_ADVANCED_ITEMS = 200_000
MAX_ADVANCED_ITERATIONS = 1_000_000
MAX_ADVANCED_DEADLINE_SECONDS = 30.0
MAX_CANCELLATION_CHECK_INTERVAL = 1_024
MAX_ADVANCED_REQUEST_BYTES = 1 * 1024 * 1024
MAX_ADVANCED_RESULT_BYTES = 4 * 1024 * 1024

@dataclass(frozen=True)
class BoundedExecutionPolicy:
    max_items: int
    max_iterations: int
    deadline_seconds: float
    cancellation_check_interval: int
    deterministic_seed: int

class MonotonicClock(Protocol):
    def now(self) -> float: ...

class CancellationProbe(Protocol):
    def is_cancelled(self) -> bool: ...

class BoundedFailureCode(StrEnum):
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLED = "CANCELLED"

@dataclass(frozen=True)
class BoundedExecutionFailure:
    code: BoundedFailureCode
    completed_iterations: int
    message: str
```

These immutable server ceilings and `BoundedExecutionPolicy` are owned by `src/autocad_mcp/advanced/bounds.py`. A request value above a ceiling, below a positive minimum, or with serialized request bytes over the ceiling is rejected before allocation; values are never clamped. Services stop before serializing results beyond `MAX_ADVANCED_RESULT_BYTES`. The policy uses an injected monotonic clock and `CancellationProbe.is_cancelled()` at intervals no greater than the requested/server maximum. It does not promise a hard wall-clock/RSS kill, launch a subprocess, or authorize code execution.

Deterministic success uses only normalized input, algorithm/version, seed, and a fixed iteration/work budget. Elapsed time/RSS are evidence metadata outside result objects and canonical digests. If the injected deadline expires or cancellation fires before the fixed work budget completes, U/P return only `BoundedExecutionFailure`; no incumbent, partial layout, partial unfolding, success result, or cacheable digest is returned.

Track U consumes no snapshot/AutoCAD type. Track D imports `SnapshotRef`, `CapabilityIssue`, topology/fact/hypothesis types, and `EvidenceRecord` through accepted EPIC-08B/08A/07A contracts. Track P imports accepted EPIC-08A `SnapshotRef`, `ClosedLoopFact`, `TopologyPlane`, and tolerance. Track C imports only EPIC-02 `JsonValue`, `ToolError`, and canonical service/contract interfaces.

## Produced interfaces and types

Each candidate produces its own bounded, versioned result contract below. There is no shared advanced-feature runtime result, registry, completion flag, or implicit conversion between tracks.

## Work packages

Work-package IDs are track-prefixed (`E09-U`, `E09-D`, `E09-P`, and `E09-C`). Each track freezes its contract before algorithm work, follows red/green TDD, runs its own exact commands, and reaches an independent registration decision. The detailed packages and produced types follow in their respective track sections.

## Track U: surface unfolding

### Supported first contract

The candidate supports one connected orientable two-manifold triangular mesh with:

- 3-2,000 vertices and 1-4,000 triangular faces;
- finite coordinates in one caller-declared unit label;
- consistent face winding;
- explicit boundary and optional caller-selected seam edges;
- each non-boundary edge shared by exactly two faces;
- no zero-area triangles, duplicate faces, non-manifold vertices/edges, or self-intersecting input triangles; and
- a seam set that cuts the face-adjacency graph into one or more acyclic islands.

The caller supplies the mesh directly; version 1 does not accept a snapshot ID, entity handle, AutoCAD surface, or extraction request. Automatic seam optimization, NURBS flattening, thick solids, doubly curved distortion minimization, allowance compensation, kerf, bend deduction, and manufacturing guarantees are excluded.

```python
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

UnfoldingResponse = UnfoldingResult | BoundedExecutionFailure
```

The solver places a root triangle and propagates adjacent triangles by rigid edge-preserving transforms. It returns overlap as an explicit metric/failure; it does not move islands heuristically to conceal overlaps. Canonical results are deterministic for the same normalized input, seam set, root, and solver version.

Version-1 layout clarification (2026-10-01): all returned points share a global
2D frame. Disconnected rigid charts receive one deterministic initial horizontal
strip placement, with the requested-root island first and the others ordered by
minimum source face ID. The first root anchor is preserved; subsequent chart
bounds are placed after the preceding maximum x with a positive scale-relative
gap and minimum y at zero. This initial placement is not sheet nesting or an
overlap-driven retry. The independent verifier checks all triangles globally,
including distinct islands; rejected layouts are never repositioned to conceal
an overlap. `faces_2d` is ordered by source face ID and indexes `vertices_2d`;
indexed source vertex IDs preserve each original oriented face. Seam cuts may
produce multiple output corners with the same source vertex/island identity,
distinguished by output vertex index.

For multiple charts, the gap is `1e-6` times the largest pre-placement chart
bounding-box x/y span. It must be finite and positive, and placement arithmetic
must produce finite coordinates with a representable positive separation.
Otherwise the operation returns a structured numerical failure; it never
clamps values or returns a partial layout. A single chart needs no gap.

### Track U gates

- Published fixtures include planar grids, cylinders/prisms, cones/frusta, branched strips, multiple islands, reversed faces, non-manifold edges, degeneracies, overlaps, and unsupported curved surfaces.
- For all accepted fixtures, `max_relative_edge_error <= 1e-9`, `max_relative_area_error <= 1e-9`, and `max_angle_error_radians <= 1e-9` against double-precision reference geometry.
- Round-trip reconstruction of accepted fixtures matches source edge lengths within `1e-9` relative error.
- Invalid topology and non-finite input fail before solving; overlap is never reported as a valid non-overlapping layout.
- Preflight rejects more than 2,000 vertices/4,000 faces, excessive seams, over-ceiling policy values, or request/result byte estimates beyond immutable server ceilings before solver allocation; values are never clamped.
- Canonical exact-maximum fixtures prove the complete 2,000-vertex/4,000-face request serializes within 1 MiB and its worst-case accepted result (all cuts/islands, metrics/issues at declared bounds) serializes within 4 MiB; a one-item or one-byte overflow rejects before solving/serialization.
- Solver and verifier check the injected monotonic deadline/cancellation probe at least every 1,024 processed faces and return a typed deadline/cancelled result without a subprocess.
- Wall time and peak RSS are measured on the named performance host at 500/2,000/4,000 faces and recorded as immutable evidence; they are not hard enforcement or cross-host claims.
- Independent verifier results, not solver self-report, determine whether a layout passes numerical/overlap/reversibility gates.

### Track U work packages

#### E09-U01: Contract, validation, and reference corpus

**Owned files:** U `models.py`, `validation.py`, contract/validation fixtures/tests. The Track U lead alone updates the decision record; this lane writes content-addressed evidence artifacts only.

**TDD steps:** add failing tests for every support rule, bounds, topology error, canonical ordering, and structured failure; freeze ten accepted/rejected fixtures plus exact 2,000-vertex/4,000-face request and worst-case-result serialization vectors; assert 1 MiB/4 MiB ceilings and one-byte/item rejection; implement only models/validation; record the Contract Gate decision.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/unfolding/test_models.py tests/unit/advanced/unfolding/test_validation.py tests/unit/advanced/test_bounds.py -q
uv run ruff check src/autocad_mcp/advanced/unfolding/models.py src/autocad_mcp/advanced/unfolding/validation.py tests/unit/advanced/unfolding
```

#### E09-U02: Deterministic solver with cooperative bounds

**Owned files:** U `solver.py` and solver/golden/cancellation tests only. It cannot edit metrics/verifier code or expected results.

**TDD steps:** add failing golden/invariant/input-order/fixed-work-budget/deadline/cancellation tests; implement rigid propagation and required 1,024-face cooperative checks; return a layout only on success and only typed failure on interruption, without partial geometry/digest or acceptance metrics; emit immutable solver artifacts.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/unfolding/test_solver.py tests/unit/advanced/unfolding/test_solver_bounds.py tests/unit/advanced/unfolding/test_properties.py -q
uv run ruff check src/autocad_mcp/advanced/unfolding/solver.py tests/unit/advanced/unfolding/test_solver.py tests/unit/advanced/unfolding/test_solver_bounds.py
```

#### E09-U03: Independent numerical verifier and measurements

**Owned files:** U `metrics.py`, corrupt-layout/adversarial verifier tests, performance measurement script, immutable evidence artifacts. This owner is independent of E09-U02.

**TDD steps:** first make the verifier reject deliberately stretched/flipped/overlapping/incomplete layouts; implement edge/area/angle/overlap/reversibility checks without importing solver internals; evaluate solver goldens; measure 500/2,000/4,000-face wall time/RSS in-process on a named host without claiming enforcement; write content-addressed artifacts for the Track U lead.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/unfolding/test_metrics.py tests/unit/advanced/unfolding/test_verifier_adversarial.py -q
uv run python tests/performance/measure_unfolding.py --faces 500 2000 4000 --seed 9041 --output-dir docs/advanced/evidence/unfolding
```

#### E09-U04: Pure-data service, MCP contract, and registration decision

**Owned files:** U `service.py`, tool handler, `tests/contract/test_surface_unfolding_tool.py`; shared registry/configuration only during a serialized window.

**TDD steps:** add failing caller-supplied schema, preflight item/iteration, deadline/cancellation, verifier-rejection, output-bound, and exact contract tests; prove zero context/AutoCAD/capture/mutation/subprocess calls; implement thin orchestration; register only after independent U evidence/lead decision.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/unfolding tests/contract/test_surface_unfolding_tool.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run mypy src/autocad_mcp/advanced/unfolding src/autocad_mcp/tools/surface_unfolding.py
```

## Track D: automatic dimensioning

### Supported first contract

The candidate consumes accepted EPIC-08B mechanical facts/interpretations and EPIC-08A topology to propose, but not create, 2D linear, aligned, angular, radius, and diameter dimensions for explicitly scoped supported geometry. Each proposal identifies witness handles/points, measurement, style reference, placement line/arc, rationale, conflicts, evidence, confidence, and snapshot fingerprint. Objectives are explicit: `overall_extent`, `feature_size`, `feature_location`, or `radius_diameter`. It does not promise a complete professional dimension scheme.

```python
class DimensionObjective(StrEnum):
    OVERALL_EXTENT = "overall_extent"
    FEATURE_SIZE = "feature_size"
    FEATURE_LOCATION = "feature_location"
    RADIUS_DIAMETER = "radius_diameter"

@dataclass(frozen=True)
class DimensionProposalRequest:
    source: SnapshotRef
    topology_spec: TopologyBuildSpec
    mechanical_spec: MechanicalAnalysisSpec
    handle_scope: tuple[str, ...]
    objectives: tuple[DimensionObjective, ...]
    style_name: str
    minimum_clearance: float
    max_proposals: int

@dataclass(frozen=True)
class DimensionProposal:
    proposal_id: str
    kind: Literal["linear", "aligned", "angular", "radius", "diameter"]
    objective: DimensionObjective
    witness_handles: tuple[str, ...]
    witness_points: tuple[tuple[float, float, float], ...]
    measurement: float
    placement: Mapping[str, JsonValue]
    style_name: str
    evidence: tuple[EvidenceRecord, ...]
    confidence: float
    conflicts: tuple[str, ...]

@dataclass(frozen=True)
class DimensionProposalResult:
    source: SnapshotRef
    topology_method_version: str
    topology_spec_digest: str
    mechanical_detector_version: str
    planner_version: str
    verifier_version: str
    proposals: tuple[DimensionProposal, ...]
    uncovered_objectives: tuple[DimensionObjective, ...]
    unsupported: tuple[CapabilityIssue, ...]
    verification: "DimensionVerificationReport"

class MechanicalSnapshotProvider(Protocol):
    def get_complete(
        self,
        spec: MechanicalAnalysisSpec,
    ) -> MechanicalAnalysisSnapshot: ...

@dataclass(frozen=True)
class DimensionVerificationReport:
    verifier_version: str
    accepted: bool
    recomputed_measurements: Mapping[str, float]
    duplicate_pairs: tuple[tuple[str, str], ...]
    clearance_violations: tuple[tuple[str, str], ...]
    conflict_pairs: tuple[tuple[str, str], ...]
    errors: tuple[str, ...]

class DimensionProposalVerifier(Protocol):
    def verify(
        self,
        snapshot: DrawingSnapshot,
        topology: TopologySnapshot,
        mechanical: MechanicalAnalysisSnapshot,
        proposals: tuple[DimensionProposal, ...],
        minimum_clearance: float,
    ) -> DimensionVerificationReport: ...

class DimensionProposalService:
    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        topology_repository: TopologyRepository,
        mechanical_provider: MechanicalSnapshotProvider,
        verifier: DimensionProposalVerifier,
    ) -> None: ...
```

Requests allow 1-256 handles, 1-100 proposals, finite positive clearance, one existing supported style, accepted 08A/08B versions, and complete non-stale retained inputs. The service loads the injected EPIC-04 snapshot repository, EPIC-08A topology repository, and EPIC-08B complete mechanical-snapshot provider. It requires exact equality of full `SnapshotRef`/content fingerprint, snapshot schema, topology method/spec digest/scope/relation/tolerance, mechanical source/topology/detector/spec digests, and handle membership before proposing. `MechanicalAnalysisResultPage`, incomplete mechanical snapshots, and mixed detector/topology versions are rejected before proposer/verifier calls. Existing native dimensions are inputs for duplicate/conflict detection, not assumed correct.

`verification.py` imports only immutable source/result contracts and geometry helpers; it never imports `candidates.py`, `layout.py`, or proposer internals. It independently recomputes every measurement, existing/proposal duplicate, placement clearance, proposal conflict, witness membership, and corpus precision/confusion count. A proposal result is released only when the verifier accepts it and records `verifier_version`.

### Track D gates

- At least 60 labelled fixtures cover the five dimension kinds, four objectives, duplicates, conflicting placements, empty/unsupported scopes, rotated UCS, paper/model space, and ambiguous geometry.
- Every proposal references existing scoped handles and finite witness/placement geometry; its independently recomputed measurement matches within snapshot linear/angular tolerance.
- Exact duplicates of existing dimensions and proposal-proposal duplicates are zero on the corpus.
- Clearance/conflict checks have zero known violations on accepted proposals; unresolved placement conflict excludes the proposal and is reported.
- Per-kind proposal precision is at least `0.90` against reviewed eligible fixture proposals. Recall and uncovered objectives are published; abstention is allowed.
- AutoCAD 2026 evidence is split: **dimensioning input extraction verified on full AutoCAD 2026** and **dimension proposals evaluated on AutoCAD-extracted fixtures**.
- Initial registration is proposal-only. Dimension creation requires a later EPIC-06 primitive extension with its own TDD and AutoCAD rollback evidence.

### Track D work packages

#### E09-D00: Freeze independent D corpus and evaluator

**Owned files:** `tests/fixtures/dimensioning/manifest.json`, cases, `tests/evaluation/test_dimensioning_corpus.py`, verifier contract vectors. This owner cannot edit proposer files.

**TDD steps:** before proposer implementation, freeze at least 60 labelled eligible/ineligible cases covering every kind/objective, witnesses, expected measurement, native/proposal duplicates, clearance/conflicts, abstention, and unsupported cases; write the evaluator to recompute confusion/precision and consume verifier reports without importing candidates/layout; record reviewer approvals/digests; prove empty/corrupt proposals fail.

**Exact verification:**

```bash
uv run pytest tests/evaluation/test_dimensioning_corpus.py -q
git diff --check -- tests/fixtures/dimensioning tests/evaluation/test_dimensioning_corpus.py
```

#### E09-D01: Contract, objectives, and baseline

**Owned files:** D `models.py`, model tests, baseline tests. The Track D lead alone edits the decision record; lanes write immutable evidence artifacts.

**TDD steps:** add failing bounds/type/source-version/determinism tests against the frozen D00 vectors; define the baseline as one overall extent proposal per orthogonal axis when valid; freeze the Contract Gate without editing labels/evaluator.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/dimensioning/test_models.py tests/unit/advanced/dimensioning/test_baseline.py -q
uv run ruff check src/autocad_mcp/advanced/dimensioning/models.py tests/unit/advanced/dimensioning
```

#### E09-D02: Candidate geometry, ranking, and conflict checks

**Owned files:** D `candidates.py`, `layout.py`, geometry/golden/property tests.

**TDD steps:** add failing cases for every objective/kind and negative/ambiguous cases; implement candidate generation; implement independent duplicate/clearance/conflict filtering; recompute measurements in tests rather than trusting output.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/dimensioning/test_candidates.py tests/unit/advanced/dimensioning/test_layout.py tests/unit/advanced/dimensioning/test_geometry_properties.py -q
uv run pytest tests/evaluation/test_dimensioning_corpus.py -q
```

#### E09-D03: Independently verify every proposal and corpus metric

**Owned files:** D `verification.py`, adversarial verifier tests, D evaluator integration. This owner cannot edit `candidates.py`, `layout.py`, proposer expectations, or decision records.

**TDD steps:** make the verifier reject deliberately wrong measurements, foreign witnesses, existing/proposal duplicates, clearance violations, conflicts, missing objectives, and precision manipulation; implement independent recomputation without proposer imports; run the frozen evaluator and emit content-addressed verifier evidence.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/dimensioning/test_verification.py tests/unit/advanced/dimensioning/test_verifier_adversarial.py tests/evaluation/test_dimensioning_corpus.py -q
uv run python -c "from autocad_mcp.advanced.dimensioning.verification import verify_dimension_proposals"
```

#### E09-D04: Inject sources, expose service, and register proposal-only MCP

**Owned files:** D `service.py`, tool handler, service/MCP tests; shared registry only during integration window.

**TDD steps:** inject fake snapshot/topology/complete-mechanical providers and independent verifier; reject `MechanicalAnalysisResultPage`, incomplete mechanical snapshots, mixed topology/detector versions, and each one-field source/fingerprint/schema/method/spec/detector/handle mismatch before proposer calls; add stale/style/capability/bounds/schema and verifier-rejection tests; assert no mutation/capture/approval; implement proposal-only orchestration; register only after D00-D03 gates pass.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/dimensioning/test_service.py tests/contract/test_dimension_proposals_tool.py -q
uv run pytest tests/evaluation/test_dimensioning_corpus.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run mypy src/autocad_mcp/advanced/dimensioning src/autocad_mcp/tools/dimension_proposals.py
```

#### E09-D05: AutoCAD 2026 proposal evaluation

**Owned files:** D Windows test/PowerShell runner and content-addressed immutable evidence artifacts only; EPIC-03 harness is read-only and the Track D lead alone updates the decision record.

**TDD steps:** review expected facts/proposals first; label native style/dimension/08B fact extraction separately from proposal evaluation; evaluate through the independent D verifier/evaluator without changing expected labels; for every case reuse EPIC-03's neutral drawing-copy guard, assert GUID copy/path inequality/hash equality/active `FullName`, close without saving, rehash and preserve failures; acquire/release the exclusive AutoCAD verification lease around every real run; record unsupported entities.

**Exact verification:**

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_dimension_proposals_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\dimensioning-source.dwg
```

## Track P: pattern optimization

### Supported first contract

The candidate places simple, valid, non-self-intersecting 2D polygon parts with quantities onto one or more rectangular sheets. It honors explicit clearance and an allowlist of rotations. It returns a feasible deterministic layout or structured unplaced reasons; it does not claim global optimality.

```python
@dataclass(frozen=True)
class PatternPart:
    part_id: str
    source_loop_id: str
    polygon: tuple[tuple[float, float], ...]
    quantity: int
    allowed_rotations_degrees: tuple[int, ...]

@dataclass(frozen=True)
class PatternSheet:
    sheet_id: str
    width: float
    height: float
    quantity: int

@dataclass(frozen=True)
class PatternOptimizationRequest:
    source: SnapshotRef
    topology_spec: TopologyBuildSpec
    parts: tuple[PatternPart, ...]
    sheets: tuple[PatternSheet, ...]
    clearance: float
    policy: BoundedExecutionPolicy

@dataclass(frozen=True)
class PartPlacement:
    part_id: str
    instance: int
    sheet_id: str
    sheet_instance: int
    rotation_degrees: int
    translation: tuple[float, float]

@dataclass(frozen=True)
class PatternOptimizationResult:
    source: SnapshotRef
    topology_method_version: str
    topology_spec_digest: str
    optimizer_version: str
    verifier_version: str
    placements: tuple[PartPlacement, ...]
    unplaced: tuple[Mapping[str, JsonValue], ...]
    sheet_utilization: Mapping[str, float]
    total_utilization: float
    feasibility_verified: bool
    baseline_total_utilization: float
    iterations: int

@dataclass(frozen=True)
class PatternVerificationReport:
    verifier_version: str
    accepted: bool
    overlap_pairs: tuple[tuple[str, str], ...]
    clearance_violations: tuple[tuple[str, str], ...]
    out_of_bounds_instances: tuple[str, ...]
    utilization: float
    errors: tuple[str, ...]

class PatternFeasibilityVerifier(Protocol):
    def verify(
        self,
        snapshot: DrawingSnapshot,
        topology: TopologySnapshot,
        request: PatternOptimizationRequest,
        placements: tuple[PartPlacement, ...],
    ) -> PatternVerificationReport: ...

class PatternOptimizationService:
    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        topology_repository: TopologyRepository,
        verifier: PatternFeasibilityVerifier,
    ) -> None: ...
    def optimize(
        self,
        request: PatternOptimizationRequest,
    ) -> PatternOptimizationResult | BoundedExecutionFailure: ...

PatternOptimizationResponse = PatternOptimizationResult | BoundedExecutionFailure
```

The service loads the injected EPIC-04 snapshot and EPIC-08A complete topology repositories. It requires exact equality among request/source/build-spec/topology `SnapshotRef` and content fingerprint, snapshot schema, topology method/spec digest/scope/relation/tolerance, and loop/handle membership before optimization. Each part references an accepted `ClosedLoopFact`; its polygon is the deterministic projection and is revalidated. Limits are 1-100 part definitions, 1-1,000 expanded instances, 1-20 sheet definitions, 1-100 expanded sheets, 3-2,000 vertices per polygon, rotations in integer degrees `0..359`, finite positive dimensions, non-negative finite clearance, and shared immutable ceilings. Holes, concave polygons, grain direction, guillotine cuts, common-line cutting, kerf, remnants, and irregular sheets are excluded initially.

Successful deterministic output uses the fixed requested iteration/work budget and contains no elapsed time. Elapsed time/RSS exist only in external evidence and never enter result bytes/digests. Deadline/cancellation returns only typed `BoundedExecutionFailure`; no incumbent/unplaced/partial layout is returned.

### Track P gates

- An independent verifier proves every accepted placement is inside its sheet, uses an allowed rotation, has exact requested multiplicity or an unplaced reason, and has no overlap or clearance violation.
- Fixed request/seed/version produces byte-identical placements and metrics.
- On 40 frozen benchmarks, the optimizer is never less feasible than the shelf baseline, improves utilization by at least five percentage points at the median, and is no worse than baseline utilization on at least 70% of cases.
- On exact small cases with at most eight rectangular parts, utilization matches exhaustive reference optimum for at least 90% of cases and reports the gap for all cases; this does not become a general optimality claim.
- Preflight rejects any request/policy/serialized size above immutable server ceilings without clamping; the optimizer checks deadline/cancellation at least every 256 iterations and returns only typed failure on interruption, never an incumbent.
- Wall time/RSS are measured at frozen benchmark sizes on a named host and stored as immutable evidence, not enforced as a universal hard kill or via subprocess.
- AutoCAD evidence is split: **EPIC-08A closed-profile extraction verified on full AutoCAD 2026** and **pattern optimizer evaluated on AutoCAD-extracted profiles**.

### Track P work packages

#### E09-P01: Contract, polygon validation, and benchmark freeze

**Owned files:** P `models.py`, `validation.py`, contract/validation tests, benchmark manifest. The Track P lead alone edits the decision record; lanes write immutable evidence artifacts.

**TDD steps:** add failing type/limit/degenerate/self-intersection/rotation/unit tests; freeze 40 benchmarks and small exact cases before optimizer code; implement only validation/contracts; record Contract Gate.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/patterns/test_models.py tests/unit/advanced/patterns/test_validation.py tests/unit/advanced/test_bounds.py -q
uv run ruff check src/autocad_mcp/advanced/patterns/models.py src/autocad_mcp/advanced/patterns/validation.py tests/unit/advanced/patterns
```

#### E09-P02: Baseline and bounded optimizer

**Owned files:** P `baseline.py`, `optimizer.py`, baseline/optimizer/determinism/performance tests.

**TDD steps:** implement the tested shelf baseline first; add failing fixed-work-budget determinism, over-ceiling rejection/no-clamp, deadline/cancellation tests; implement the minimum deterministic heuristic with 256-iteration cooperative checks; interruption returns typed failure and never an incumbent/intermediate placement.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/patterns/test_baseline.py tests/unit/advanced/patterns/test_optimizer.py tests/unit/advanced/patterns/test_determinism.py tests/unit/advanced/patterns/test_cooperative_bounds.py -q
uv run python tests/performance/run_pattern_benchmarks.py --manifest tests/fixtures/patterns/manifest.json --output-dir docs/advanced/evidence/patterns
```

#### E09-P03: Independent feasibility verifier, service, and MCP gate

**Owned files:** P `verification.py`, `service.py`, tool handler, verification/service/MCP tests; shared registry only during integration window.

**TDD steps:** develop verifier tests independently from optimizer fixtures, including deliberately corrupt layouts; inject fake snapshot/topology repositories and reject every one-field source/fingerprint/schema/method/spec/scope/relation/tolerance/loop mismatch before optimizer calls; make service reject any result the verifier does not accept; assert elapsed time is absent from result/digest and typed deadline/cancel failure has no incumbent; add exact request/result-byte ceiling tests and prove no mutation/capture; register only after P gates pass.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/patterns/test_verification.py tests/unit/advanced/patterns/test_service.py tests/contract/test_pattern_optimization_tool.py -q
uv run pytest tests/unit/advanced/patterns tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run mypy src/autocad_mcp/advanced/patterns src/autocad_mcp/tools/pattern_optimization.py
```

#### E09-P04: AutoCAD 2026 profile extraction and correlation

**Owned files:** P Windows test/PowerShell runner and content-addressed immutable evidence artifacts only; EPIC-03 harness is read-only and the Track P lead alone updates the decision record.

**TDD steps:** review expected EPIC-08A closed profiles first; label extraction separately from optimizer evaluation; optimize and independently verify returned layouts without changing expected data; for every case reuse EPIC-03's neutral drawing-copy guard, assert GUID copy/path inequality/hash equality/active `FullName`, close without saving, rehash and preserve failures; acquire/release the exclusive AutoCAD verification lease around every real run; record performance only outside result/digest.

**Exact verification:**

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_pattern_optimization_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\patterns-source.dwg
```

## Track C: constrained code generation

### Supported first contract

This candidate is output-only, built-in-template generation from a typed recipe. The caller selects a reviewed `template_id`, `target` (`python`, `autolisp`, or `vba`), and bounded literal parameters. Callers cannot submit templates, source fragments, expressions, imports, identifiers outside schema allowlists, or post-processing instructions. The server returns source text, template version, artifact digest, static findings, and an explicit “not executed; human review required” warning.

```python
class CodeTarget(StrEnum):
    PYTHON = "python"
    AUTOLISP = "autolisp"
    VBA = "vba"

@dataclass(frozen=True)
class CodeRecipe:
    schema_version: Literal["1"]
    template_id: str
    template_version: str
    target: CodeTarget
    literals: Mapping[str, JsonValue]

@dataclass(frozen=True)
class StaticFinding:
    rule_id: str
    severity: Literal["error", "warning"]
    location: str
    message: str

@dataclass(frozen=True)
class GeneratedCodeArtifact:
    target: CodeTarget
    template_id: str
    template_version: str
    source: str
    digest: str
    findings: tuple[StaticFinding, ...]
    executed: Literal[False]
    warning: Literal["Generated text was not executed; review it outside AutoCAD MCP."]
```

The first template catalogue contains only three audited educational/export templates per target: construct literal line/circle data in memory, serialize supplied literal entity facts to a caller-visible string, and show a read-only iteration pattern over explicitly supplied handles. Templates may not access credentials, environment variables, arbitrary paths, network, subprocesses, dynamic imports/evaluation, COM command strings, macro runners, or unrestricted drawing mutation. If a target cannot express a template within these rules, that target/template pair is unsupported.

The MCP response is at most 64 KiB. The tool does not write files, place text on a clipboard, invoke an editor/compiler/interpreter, call AutoCAD, create an EPIC-06 plan, or provide a companion execute/apply tool.

### Track C gates

- Template catalogue and every rendered golden artifact receive security-owner review and immutable version/digest records.
- Literal escaping round-trips for each target across quotes, newlines, Unicode, delimiters, comments, and control characters without breaking syntax or injecting statements/forms.
- A corpus of at least 500 malicious literal/schema cases produces either safely escaped data or structured rejection, with zero injected executable constructs.
- Python output parses with `ast.parse` and passes the allowlisted AST policy. AutoLISP/VBA output passes conservative tokenizer/structure policies and exact golden review; inability to validate safely rejects that target.
- Static deny rules reject execution/evaluation, dynamic import, process, shell, network, credential/environment, arbitrary file I/O, macro/command dispatch, and unrestricted `SendCommand` constructs.
- Registry and source scans prove no execute/run/eval/repl/shell tool and no path from output to an interpreter, file writer, COM adapter, or EPIC-06 apply.
- Core-only contract tests prove no import or call reaches adapter/context/capture/edit/COM modules. Track C has no AutoCAD prerequisite or AutoCAD evidence gate.

### Track C work packages

#### E09-C01: Threat model, contract, catalogue, and rejection corpus

**Owned files:** C `models.py`, model tests, malicious corpus. The Track C lead alone edits the decision record; lanes write immutable security evidence.

**TDD steps:** enumerate attacker-controlled fields and forbidden sinks; add failing strict-schema/size/target/template/version tests; freeze template catalogue and malicious corpus; obtain security review before rendering implementation.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/codegen/test_models.py tests/unit/advanced/codegen/test_contract_rejections.py -q
uv run ruff check src/autocad_mcp/advanced/codegen/models.py tests/unit/advanced/codegen
```

#### E09-C02: Built-in templates and literal-only rendering

**Owned files:** C `templates.py`, `render.py`, golden/escaping/determinism tests.

**TDD steps:** add failing goldens before each target/template; add delimiter/comment/control/Unicode injection cases; implement built-in constants and target-specific literal encoders only; make request-provided template text/source fragments impossible by type/schema.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/codegen/test_goldens.py tests/unit/advanced/codegen/test_literal_escaping.py tests/unit/advanced/codegen/test_determinism.py -q
uv run ruff check src/autocad_mcp/advanced/codegen/templates.py src/autocad_mcp/advanced/codegen/render.py tests/unit/advanced/codegen
```

#### E09-C03: Static validation and output-only service

**Owned files:** C `validate.py`, `service.py`, validator/security/service tests.

**TDD steps:** first make validators reject known forbidden goldens and malicious corpus; add Python AST allowlist and conservative target token policies; implement service with no file/COM/execution capabilities; assert every error finding prevents artifact release.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/codegen/test_validate.py tests/unit/advanced/codegen/test_malicious_corpus.py tests/unit/advanced/codegen/test_service.py -q
uv run bandit -q -r src/autocad_mcp/advanced/codegen
rg -n "\b(exec|eval|compile|subprocess|os\.system|SendCommand|Shell|CreateObject)\b" src/autocad_mcp/advanced/codegen tests/unit/advanced/codegen
```

The `rg` output must be limited to deny-rule constants and negative tests; a security reviewer records the reviewed matches.

#### E09-C04: Core-only MCP non-execution contract

**Owned files:** C tool handler, MCP contract/non-execution tests; shared registry only during integration window.

**TDD steps:** add exact schema/64-KiB/error/golden tests; inject spies for file/process and import guards for adapter/context/capture/edit/COM modules; assert zero calls/imports; prove registry lacks execute/run/eval/repl/shell/apply companions; write immutable core security evidence for the Track C lead.

**Exact verification:**

```bash
uv run pytest tests/unit/advanced/codegen tests/contract/test_constrained_code_generation_tool.py tests/contract/test_no_execution_tools.py -q
uv run pytest tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run mypy src/autocad_mcp/advanced/codegen src/autocad_mcp/tools/constrained_code_generation.py
```

## Parallel lanes and exclusive file ownership

E09-0 freezes `advanced/bounds.py` first. The four candidate tracks may then run concurrently because runtime/tests/fixtures/evidence are disjoint. Each decision record has one track-lead writer; worker/evidence lanes write only content-addressed immutable artifacts and cannot edit decisions.

| Track | Exclusive tree | Shared-file rule |
| --- | --- | --- |
| E09-U | unfolding package/tests/fixtures/tool; solver and verifier have different owners | Pure-data registration only after independent U evidence |
| E09-D | dimensioning package/tests/fixtures/tool and D immutable evidence | Registration only after accepted 08B and D gates |
| E09-P | patterns package/tests/fixtures/tool and P immutable evidence | Registration only after accepted 08A and P gates |
| E09-C | codegen package/tests/corpus/tool and C immutable evidence | Core-only registration after security sign-off |

No algorithm lane edits canonical registration, `mcp.json`, canonical docs, another track's files, or shared safety/core code. The integration owner schedules one registration window per passing track, reruns the entire active tool/MCP/security suite, and can decline one track without delaying the others.

## Acceptance criteria

### Shared program

- Four single-owner decision records contain contract, immutable-evidence digests, gate result, support limits, risk review, exact commands, environment, and `registered`, `revise`, or `rejected` decision.
- A track appears in canonical MCP metadata/docs only after its applicable pure/environment/safety/registration gates pass; only D/P have AutoCAD extraction gates.
- Candidate packages import without Windows COM; Linux numerical tests are not described as AutoCAD verification.
- All tools are explicit, bounded, deterministic for stated inputs/seed/version, return structured unsupported/resource-limit results, and perform no automatic capture.
- D/P read-only AutoCAD tests prove identical before/after drawing fingerprints; U/C have no AutoCAD dependency or claim.
- Historical claim/code presence does not count as acceptance evidence.
- Failure/rejection of one candidate has no runtime, status, or compatibility effect on another.
- Immutable `advanced/bounds.py` ceilings cover items, iterations, deadline, check interval, request bytes, and result bytes; over-ceiling requests reject without clamping.
- Successful result/digest determinism uses a fixed work budget and excludes elapsed time/RSS. Deadline/cancellation returns typed failure only, never a partial/incumbent result.

### Surface unfolding

- Only the frozen supported triangular mesh contract is accepted; invalid/non-manifold/unsupported input fails before solving.
- Advertised U limits are exactly 2,000 vertices/4,000 faces, with canonical exact-max request/result fixtures below 1 MiB/4 MiB and one-item/byte overflow rejection.
- Numerical, overlap, reversibility, determinism, and resource gates meet the U thresholds.
- Results retain caller face/vertex IDs and input digest and openly report cut edges, islands, overlap, distortion, warnings, and invalid/unsupported input.
- Solver and independent verifier have exclusive owners; verifier evidence determines acceptance.

### Automatic dimensioning

- Proposals have valid witnesses, independently verified measurements, supported styles, explainable objectives/evidence, no known duplicates/clearance violations, and stated conflicts/unsupported cases.
- The independently owned frozen D corpus/evaluator predates proposer work; `verification.py` imports no proposer and recomputes measurements, duplicates, clearance, conflicts, and precision.
- Injected snapshot/topology/complete-mechanical sources pass exact full fingerprint/schema/method/spec/detector/handle agreement before proposal generation; pages, incomplete snapshots, and mixed versions are rejected.
- The D corpus meets per-kind precision and publishes recall/uncovered objectives.
- Initial delivery proposes only; it creates no dimension and has no mutation capability.

### Pattern optimization

- Every released layout passes the independent feasibility verifier; invalid intermediate/bounded results are never returned as feasible.
- Determinism, baseline improvement, small-case gap, and resource gates meet P thresholds, with no general optimality claim.
- Pattern results carry source `SnapshotRef`, topology method version, and topology spec digest; injected snapshot/topology repositories pass exact fingerprint/spec/loop agreement before optimization.
- Successful pattern results contain no elapsed time; deadline/cancellation returns typed failure with no incumbent.
- EPIC-08A input extraction and returned placements preserve units, loop/handle provenance, and source drawing fingerprint, with extraction/evaluation labels separated.

### Constrained code generation

- Only reviewed built-in templates and typed literals are accepted; output is bounded text with digest/findings and `executed: false`.
- All golden, escaping, 500-case malicious corpus, static validator, registry, file/process spies, adapter/COM import guards, and source-scan gates pass in the core-only environment.
- No execute, run, eval, REPL, shell, file-write, COM-command, apply, or companion execution path exists.
- User documentation states that output is unexecuted text requiring independent human review and that AutoCAD MCP provides no safe-execution claim.

## Windows and AutoCAD verification

Only D and P use full AutoCAD. Each runner reuses EPIC-03 neutral `tests/windows/drawing_copy_guard.py` for a fresh unique-GUID source copy per case, resolved-path inequality, initial/final hashes, active `FullName`, read-only close-without-save, and failed-copy preservation. Before attachment each acquires the EPIC-03 exclusive verification lease keyed by installation/build and interactive-session ID, fails closed on live contention, and records release outcome. Each records product/build, Windows, Python, frozen lock digest, fixture digest, upstream snapshot/topology/semantic versions, units/tolerance, exact command, metrics, modal interaction, and identical before/after fingerprint.

For D, label evidence **dimensioning input extraction verified on full AutoCAD 2026** and **dimension proposals evaluated on AutoCAD-extracted fixtures**. For P, use **EPIC-08A closed-profile extraction verified on full AutoCAD 2026** and **pattern optimizer evaluated on AutoCAD-extracted profiles**. U is numerically evaluated on caller-supplied meshes; C is security/contract tested in the core-only environment. Never combine these into “advanced features verified.”

## Safety and security gates

- **Independent promotion:** no shared completion flag, bundled registration, or evidence borrowing.
- **Read-only first:** initial candidates return data/artifacts only and receive no mutation adapter. Any later drawing application uses EPIC-06 and a separately reviewed primitive extension.
- **No arbitrary execution:** no interpreter, compiler invocation, eval/exec, subprocess, shell, macro, file staging, dynamic import, VBA/AutoLISP execution, or unrestricted `SendCommand` anywhere in MCP.
- **Bounded resources:** hard item/vertex/face/iteration/output limits validate before allocation; injected monotonic deadlines and cancellation are checked cooperatively; time/RSS are measured, not claimed as hard enforcement; no subprocess is launched.
- **Determinism and provenance:** normalized input, fixed work budget, seed/version/tolerance, and applicable source IDs travel with results; elapsed time/RSS never enters result/digest and nondeterministic iteration order is rejected.
- **Independent verification:** unfolding metrics, dimension measurements/conflicts, and pattern feasibility are recalculated outside their proposing algorithm.
- **Untrusted data:** drawing text, names, code literals, geometry, and model/client descriptions are untrusted, strictly bounded, and never evaluated.
- **Codegen isolation:** built-in templates only, literal encoders, static deny/allow validation, output-only response, zero file/COM/execution dependencies, explicit human-review warning.
- **Privacy:** logs/evidence contain digests and aggregate metrics, not tokens, credentials, personal paths, proprietary drawing content, or full generated artifacts unless fixtures are synthetic.
- **Honest claims:** approximation, abstention, unsupported cases, performance host, and lack of professional/manufacturing/optimality guarantees are mandatory documentation.

A safety gate failure forces `revise` or `rejected`; it cannot be downgraded to a warning to permit registration.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Legacy code smuggles obsolete architecture or claims | Reimplement only frozen contracts against current interfaces; compare evidence, not line reuse |
| Four tracks create a shared integration bottleneck | Exclusive trees and one serialized registration window per passing track |
| Numerical output looks correct but violates invariants | Independent metrics/verifiers, golden/property/adversarial fixtures, real extraction checks |
| Performance becomes unbounded | Preflight item/iteration ceilings, cooperative deadline/cancellation checks, measured named-host time/RSS, and no subprocess |
| Unfolding is mistaken for fabrication-ready output | Narrow support, distortion/overlap metrics, no allowances/kerf/manufacturing claim |
| Dimension proposals are mistaken for complete documentation | Explicit objectives/uncovered list, precision/recall reporting, proposal-only first delivery |
| Heuristic placement is marketed as optimal | Baseline/gap reporting and explicit “no global optimality” contract |
| Generated text is executed through an adjacent feature | No execution/file/COM capability, registry-deny tests, security source scan, no companion tool |
| Static validators miss language edge cases | Built-in templates, literal-only encoding, conservative rejection, target removal if safe validation is not demonstrable |
| One track's success promotes all AutoCAD releases/features | Separate decision/evidence/compatibility records per track and release |

## Rollback

Rollback is per track:

1. Remove only the affected handler from the canonical registry and `mcp.json` in the same corrective change.
2. Mark that track `revise` or `rejected`; retain other tracks' registrations and evidence.
3. Revert user/status/compatibility claims for the affected feature and invalidate cursors/artifacts/results by algorithm/template version.
4. Preserve redacted failing fixtures, numerical/security evidence, and decision history.
5. Because initial tools are read-only/output-only, no drawing recovery is expected. If a later separately approved apply extension exists, use EPIC-06 Undo/rollback/incident-lock procedure rather than candidate-specific recovery.

For code generation, a suspected injection or execution bridge triggers immediate unregistration of the generation tool and all template versions, even if only one target/template is implicated. Generated artifacts are content-addressed but never recalled or executed by the server.

## Completion evidence

Each candidate decision record must include:

- frozen types, limits, support matrix, threat/failure analysis, baseline, fixture manifest/digests, and thresholds;
- focused red/green TDD output for every work package;
- complete candidate unit/numerical/property/security/MCP results;
- deterministic results and resource measurements with exact host details;
- independent verifier/metric results and adversarial/unsupported coverage;
- D frozen corpus/evaluator digest plus no-proposer-import verifier evidence for measurements, duplicates, clearance, conflicts, and precision;
- exact tool-registry diff and stdio-integrity result if registered;
- D/P AutoCAD 2026 command/report/JUnit, separate extraction/evaluation labels, capability observations, and before/after fingerprint; U/C explicitly record no AutoCAD gate;
- D/P EPIC-03 neutral-copy-guard and exclusive-lease evidence for every case: GUID copy, source/copy path inequality and hashes, active `FullName`, close-without-save, preserved failures, and lease acquisition/release;
- lint, type-check, compile, JSON, link, and `git diff --check` output;
- precise approximation, performance, unsupported-entity, and compatibility documentation; and
- explicit `registered`, `revise`, or `rejected` review decision with reviewer roles.

Track C additionally requires the reviewed template catalogue/goldens, all 500 malicious cases, static/source-scan findings, zero-call file/process spies, adapter/COM import guards, and no-execution registry snapshot. It requires no connected-AutoCAD evidence.

Program-level completion means all four tracks have explicit decisions and evidence; it does not mean all four are registered. A rejected candidate needs a complete rejection record, not a hidden or empty result.

## Handoff

The program owner freezes E09-0 bounds and assigns one decision-record owner/lead per candidate. Each lead freezes its Contract Gate with numerical/domain/security reviewers, then hands lanes concrete types, vectors, fixture digests, commands, and limits. Lanes return changed-file lists, signatures, failures, measurements, and content-addressed evidence; they never edit decision records, other tracks, or shared registry files. The lead alone records gate decisions from immutable evidence digests.

When a track reaches its applicable environment gate, the integration owner opens a track-specific registration window, reruns canonical catalog/stdio and safety regressions, and updates only claims supported by that track. D/P compatibility labels move per feature/release only after real-installation evidence. U/C never create AutoCAD compatibility claims. Security review is mandatory for every track and independent for C.

Related plans and constraints: [EPIC-06](EPIC-06-human-approved-safe-edit-plans.md), [EPIC-08 index](EPIC-08-general-and-mechanical-semantics.md), [EPIC-08A](EPIC-08A-general-topology.md), [EPIC-08B](EPIC-08B-mechanical-semantics.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing](../testing.md), [compatibility](../compatibility.md), and the [approved modernization design](../superpowers/specs/2026-08-25-maintenance-and-modernization-design.md).
