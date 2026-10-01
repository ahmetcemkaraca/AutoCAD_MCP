# EPIC-08B: Mechanical Semantics

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

**Planned and blocked on EPIC-08A acceptance.** This read-only sub-epic begins only after EPIC-08A general topology has a reviewed completion record and the EPIC-07 evidence contract is accepted. It is not current functionality.

## Outcome and user value

A mechanical user can request bounded hypotheses for parts, holes, axes, profiles, dimension roles, and tolerance roles and inspect the exact geometry/topology/annotation facts, evidence, counterevidence, confidence, ambiguity, and unsupported cases behind each result.

Geometry, native dimension properties, and literal tolerance text remain facts. Manufacturing meaning remains a separate interpretation: a circle does not become a hole, and text does not become a compliant tolerance, without independent evidence.

## Scope

- Consume accepted EPIC-08A topology nodes, edges, closed loops, connected components, method version, and tolerance.
- Extract immutable mechanical facts: closed planar loop, circular/arc geometry, repeated geometry, symmetry candidate, centerline style, native dimension, dimension reference, and literal tolerance.
- Produce evidence-based `part`, `hole`, `axis`, `profile`, `dimension`, and `tolerance` hypotheses using the accepted EPIC-07 evidence/confidence/unknown contract.
- Accept explicitly supplied `ClientVisualObservation` only under EPIC-07 provenance and aggregate `0.20` influence cap.
- Freeze a labelled corpus/evaluator before detector lanes and report precision, recall, unknown/ambiguity, conflicts, unsupported cases, detector version, and corpus digest.
- Register one read-only `analyze_mechanical_semantics` tool after all gates pass.

## Out of scope

- Mechanical edits, dimension creation, CAM/toolpaths, G-code, CNC control, stress/simulation, tolerance-stack calculations, standards/compliance certification, manufacturability guarantees, BOMs, and automatic part numbering.
- 3D solid feature history, hidden-feature inference, assembly mating, or geometry beyond accepted EPIC-08A topology.
- Treating layer/block/text/hatch/centerline/raster cues as sufficient proof.
- Automatic capture, server-side vision/ML, customer-drawing training, confirmation, approval, or EPIC-06 invocation.
- Expression evaluation or locale guessing in tolerance text.
- AutoCAD LT and AutoCAD operation on Linux/macOS.

## Prerequisites

1. EPIC-08A is accepted, registered, and hands off its exact public topology/closed-loop types, method version, corpus/evaluator digest, limits, and AutoCAD evidence.
2. EPIC-07A's `EvidenceRecord`, provenance, `InterpretationState`, `ClientVisualObservation`, deterministic score/confidence behavior, hard-contradiction rule, and visual cap are accepted. EPIC-07B is not required because this epic has no confirmation/edit flow.
3. EPIC-04 native dimension/text/style facts and capability issues remain available through complete snapshots.
4. A reviewed synthetic mechanical corpus and disposable AutoCAD 2026 fixture set can be created without proprietary content.
5. Canonical integration uses `tests/contract/test_stdio_server.py` and `tests/contract/test_server_tool_catalog.py`.

## Proposed owned files

| Path | Responsibility | Exclusive owner |
| --- | --- | --- |
| `src/autocad_mcp/semantics/mechanical/models.py` | Mechanical fact/hypothesis/request/result contracts | E08B-A facts/contracts |
| `src/autocad_mcp/semantics/mechanical/facts.py` | Facts from EPIC-04/08A without domain interpretations | E08B-A facts/contracts |
| `tests/fixtures/mechanical/manifest.json` and `cases/**` | Frozen labelled mechanical corpus | E08B-B corpus |
| `tests/evaluation/test_mechanical_corpus.py` | Independent per-kind evaluator | E08B-B corpus |
| `src/autocad_mcp/semantics/mechanical/parts_profiles.py` | Part/profile rules | E08B-C detectors |
| `src/autocad_mcp/semantics/mechanical/features.py` | Hole/axis rules | E08B-D detectors |
| `src/autocad_mcp/semantics/mechanical/annotations.py` | Dimension/tolerance facts, parser, and role rules | E08B-E detectors |
| `src/autocad_mcp/semantics/mechanical/service.py` | Scoring reuse, pagination, orchestration, issues | E08B-F service |
| `src/autocad_mcp/semantics/mechanical/repository.py` | Bounded complete mechanical-analysis snapshot repository | E08B-F service |
| `src/autocad_mcp/tools/mechanical_semantics.py` | Read-only analysis handler | E08B-G contract |
| `tests/contract/test_mechanical_semantics_tool.py` | Exact MCP schema/fake-service contract | E08B-G contract |
| `tests/integration/windows/test_mechanical_semantics_autocad.py` | Later real extraction/detector evaluation only | E08B-H real evaluation |
| `tests/windows/run_mechanical_semantics_autocad_2026.ps1` | EPIC-03-harness runner accepting only source DWGs | E08B-H real evaluation |
| `tests/windows/drawing_copy_guard.py` | Consumed unchanged neutral source/copy guard | EPIC-03 owner; read-only to E08B |
| `docs/mechanical-semantics.md` | Facts/interpretations, limits, metrics, evidence labels | Documentation owner |

The serialized integration owner alone changes core error models if required, runtime, server, `mcp.json`, canonical catalog/stdio tests, and canonical docs. E08B-B exclusively owns labels/evaluator. Detector and real-evaluation lanes cannot revise expected results.

## Consumed interfaces and types

EPIC-08B injects both accepted repositories; it does not receive a page as a complete source:

```python
class SnapshotRepository(Protocol):
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...

class TopologyRepository(Protocol):
    def get_complete(self, spec: TopologyBuildSpec) -> TopologySnapshot: ...
```

`DrawingSnapshot`/`SnapshotRepository` are imported unchanged from EPIC-04. `TopologyBuildSpec`, complete `TopologySnapshot`, `TopologyNode`, `TopologyEdge`, `TopologyPlane`, `ClosedLoopFact`, `ConnectedComponentFact`, `TopologyRelation`, and their exact EPIC-04 `Point3D`, `Bounds3D`, `GeometryTolerance`, `SnapshotRef`, and `CapabilityIssue` members are imported unchanged from accepted EPIC-08A. `TopologyResultPage` is not a valid facts input.

From accepted EPIC-07A, E08B imports `EvidenceRecord`, `EvidenceSource`, `EvidencePolarity`, `InterpretationState`, `ClientVisualObservation`, canonical evidence ordering, score/confidence rules, and visual cap unchanged.

## Produced interfaces and types

```python
class MechanicalFactKind(StrEnum):
    CLOSED_PLANAR_LOOP = "closed_planar_loop"
    CIRCULAR_GEOMETRY = "circular_geometry"
    ARC_GEOMETRY = "arc_geometry"
    REPEATED_GEOMETRY = "repeated_geometry"
    SYMMETRY_CANDIDATE = "symmetry_candidate"
    CENTERLINE_STYLE = "centerline_style"
    NATIVE_DIMENSION = "native_dimension"
    DIMENSION_REFERENCE = "dimension_reference"
    LITERAL_TOLERANCE = "literal_tolerance"

@dataclass(frozen=True, slots=True)
class MechanicalFact:
    fact_id: str
    snapshot_id: str
    topology_method_version: str
    topology_spec_digest: str
    kind: MechanicalFactKind
    subject_handles: tuple[str, ...]
    topology_ids: tuple[str, ...]
    values: Mapping[str, JsonValue]
    source_entity_types: tuple[str, ...]
    issues: tuple[CapabilityIssue, ...]

class MechanicalKind(StrEnum):
    PART = "part"
    HOLE = "hole"
    AXIS = "axis"
    PROFILE = "profile"
    DIMENSION = "dimension"
    TOLERANCE = "tolerance"

@dataclass(frozen=True, slots=True)
class MechanicalHypothesis:
    hypothesis_id: str
    hypothesis_digest: str
    detector_version: str
    snapshot_id: str
    snapshot_fingerprint: str
    topology_method_version: str
    topology_spec_digest: str
    kind: MechanicalKind
    subject_handles: tuple[str, ...]
    fact_ids: tuple[str, ...]
    attributes: Mapping[str, JsonValue]
    evidence: tuple[EvidenceRecord, ...]
    counterevidence: tuple[EvidenceRecord, ...]
    score: float
    confidence: float | None
    state: InterpretationState
    ambiguity_codes: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class MechanicalAnalysisSpec:
    schema_version: Literal["1.0"]
    source: SnapshotRef
    topology_spec: TopologyBuildSpec
    detector_version: str
    kinds: tuple[MechanicalKind, ...]
    handle_scope: tuple[str, ...]
    visual_observations: tuple[ClientVisualObservation, ...]
    spec_digest: str

@dataclass(frozen=True, slots=True)
class MechanicalAnalysisSnapshot:
    schema_version: Literal["1.0"]
    mechanical_snapshot_id: str
    source: SnapshotRef
    topology_method_version: str
    topology_spec_digest: str
    detector_version: str
    analysis_spec_digest: str
    facts: tuple[MechanicalFact, ...]
    hypotheses: tuple[MechanicalHypothesis, ...]
    issues: tuple[CapabilityIssue, ...]
    complete: Literal[True]

@dataclass(frozen=True, slots=True)
class MechanicalAnalysisRequest:
    spec: MechanicalAnalysisSpec
    page_size: int
    cursor: str | None

@dataclass(frozen=True, slots=True)
class MechanicalPageInfo:
    page_size: int
    returned: int
    has_more: bool
    next_cursor: str | None

@dataclass(frozen=True, slots=True)
class MechanicalAnalysisResultPage:
    schema_version: Literal["1.0"]
    mechanical_snapshot_id: str
    detector_version: str
    topology_method_version: str
    topology_spec_digest: str
    analysis_spec_digest: str
    source: SnapshotRef
    facts: tuple[MechanicalFact, ...]
    hypotheses: tuple[MechanicalHypothesis, ...]
    issues: tuple[CapabilityIssue, ...]
    page: MechanicalPageInfo

class MechanicalAnalysisRepository(Protocol):
    def put_complete(self, snapshot: MechanicalAnalysisSnapshot) -> None: ...
    def get_complete(self, spec: MechanicalAnalysisSpec) -> MechanicalAnalysisSnapshot: ...

class MechanicalSemanticsService:
    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        topology_repository: TopologyRepository,
        mechanical_repository: MechanicalAnalysisRepository,
    ) -> None: ...
    def analyze(self, request: MechanicalAnalysisRequest) -> MechanicalAnalysisResultPage: ...
```

`MechanicalAnalysisSpec.spec_digest` is canonical SHA-256 over source identity/fingerprint, the complete topology build spec/digest, detector version, normalized kind/scope, and canonical visual-observation content. `MechanicalAnalysisRepository` retains at most four complete snapshots, 32 MiB each and 128 MiB total, for 10 minutes; capacity fails explicitly without eviction. It keys every semantic input `(source snapshot/fingerprint, topology method/spec digest, detector version, mechanical spec digest)`. A mismatch is a miss/stale failure, never fallback.

Before extracting a fact or interpretation, `analyze()` loads `DrawingSnapshot` by `request.spec.source.snapshot_id` and complete `TopologySnapshot` by `request.spec.topology_spec`. It requires exact equality among `DrawingSnapshot.reference`, spec source, topology build source, and topology snapshot source, including document/session/snapshot IDs and content fingerprint. It also requires exact snapshot schema, topology method/spec/scope/relation/tolerance, `TopologySnapshot.complete is True`, detector version, mechanical spec digest, and every requested handle's membership. Any mismatch produces no facts.

The service materializes/stores one complete `MechanicalAnalysisSnapshot` before response filtering. That object contains no cursor/page metadata. `MechanicalAnalysisResultPage` alone carries `MechanicalPageInfo`; its cursor binds mechanical snapshot ID/spec digest, ordering, page size, last key, and expiry. A page or incomplete object is never inserted or supplied to downstream EPIC-09 D.

Mechanical confidence exactly follows EPIC-07A. `inferred` requires score/confidence at least `0.75`, at least two independent evidence sources, and no hard contradiction. Unknown retains diagnostic score and sets `confidence=None`. This read-only epic emits no `confirmed` state.

`LITERAL_TOLERANCE` records only supported native properties or bounded literal text: nominal, plus/minus or upper/lower values, explicit unit/locale, source range, and parser version. It never asserts standards compliance, applicability, or manufacturability. The parser accepts versioned decimal, `+/-`/`±`, and explicit upper/lower forms only; it rejects formulas, expressions, control characters, non-finite values, unknown locale, and input over 256 characters.

## Initial interpretation rules

- **Part:** candidate outer closed profiles and optional contained loops form a coherent component; a closed loop alone is not a part.
- **Hole:** a contained circular/closed inner profile plus independent center mark, concentric relation, dimension reference, repeated pattern, or explicit metadata evidence; a free circle/logo is unknown.
- **Axis:** centerline style plus symmetry/aligned centers/dimension reference; style alone is insufficient and no physical datum claim is made.
- **Profile:** accepted non-self-intersecting closed loop; outer/inner/machined role remains interpretation.
- **Dimension:** native type/measurement is fact; diameter/radius/size/location/inspection role needs supported references and geometry.
- **Tolerance:** literal tolerance is fact; size/position/surface/feature role requires a supported association and never implies compliance.

## Work packages

### E08B-WP01: Freeze mechanical contracts and facts

**Owned files:** mechanical `models.py`, `facts.py`, matching unit tests.

**TDD steps:**

1. Add failing tests for every fact/hypothesis field, canonical IDs/digests, imported topology snapshot/spec references, `MechanicalAnalysisSpec`, complete `MechanicalAnalysisSnapshot`, paged `MechanicalAnalysisResultPage`, score/confidence/state rules, strict bounds, and issues.
2. Add fact tests for each kind plus explicit proof that facts contain none of `part`, `hole`, `axis`, `outer_profile`, `manufacturable`, or compliance labels.
3. Add bounded literal-tolerance parser positive/negative/locale/security tests.
4. Implement immutable pure contracts/facts only and publish canonical vectors.

**Exact verification:**

```bash
uv run pytest tests/unit/semantics/mechanical/test_models.py tests/unit/semantics/mechanical/test_facts.py tests/unit/semantics/mechanical/test_tolerance_parser.py -q
uv run python -c "from autocad_mcp.semantics.mechanical.facts import extract_mechanical_facts"
uv run ruff check src/autocad_mcp/semantics/mechanical tests/unit/semantics/mechanical
```

### E08B-WP02: Freeze labelled corpus and evaluator

**Owned files:** mechanical fixture manifest/cases and independent evaluator only.

**TDD steps:**

1. Freeze at least 20 positive and 10 negative/ambiguous reviewed instances per kind with exact source fact/topology IDs, evidence, expected unknowns, and issues.
2. Write the evaluator before detectors; report per-kind confusion counts, precision, recall, unknown/ambiguity/conflict/unsupported counts and all version/digests.
3. Record mechanical-domain and evidence-contract reviewer approval; revisions require a new corpus version.
4. Run against empty hypotheses to prove failure and grant detector lanes read-only access.

**Exact verification:**

```bash
uv run pytest tests/evaluation/test_mechanical_corpus.py -q
git diff --check -- tests/fixtures/mechanical tests/evaluation/test_mechanical_corpus.py
```

### E08B-WP03: Detect parts and profiles

**Owned files:** `parts_profiles.py`, matching tests.

**TDD steps:** write positive/negative/ambiguous tests for outer/inner/nested/open/self-intersecting profiles, connected components, title blocks, and misleading layers; require explicit evidence/counterevidence; implement deterministic rules; run frozen evaluator read-only.

**Exact verification:**

```bash
uv run pytest tests/unit/semantics/mechanical/test_parts_profiles.py tests/evaluation/test_mechanical_corpus.py -q -k "part or profile"
uv run ruff check src/autocad_mcp/semantics/mechanical/parts_profiles.py tests/unit/semantics/mechanical/test_parts_profiles.py
```

### E08B-WP04: Detect holes and axes

**Owned files:** `features.py`, matching tests.

**TDD steps:** write positive/negative/ambiguous tests for free/contained circles, center marks, repeated holes, centerlines, symmetry, aligned centers, logos, and conflicts; require two independent sources; implement rules; run frozen evaluator read-only.

**Exact verification:**

```bash
uv run pytest tests/unit/semantics/mechanical/test_features.py tests/evaluation/test_mechanical_corpus.py -q -k "hole or axis"
uv run ruff check src/autocad_mcp/semantics/mechanical/features.py tests/unit/semantics/mechanical/test_features.py
```

### E08B-WP05: Detect dimension and tolerance roles

**Owned files:** `annotations.py`, matching annotation/security tests.

**TDD steps:** add native diameter/radius/linear/angular, orphan/exploded/dimension-like-text, plus/minus/upper-lower, proxy, locale, expression/control/Unicode-lookalike cases; prove fact/role separation; implement non-evaluating parser/rules; run frozen evaluator.

**Exact verification:**

```bash
uv run pytest tests/unit/semantics/mechanical/test_annotations.py tests/unit/semantics/mechanical/test_tolerance_parser_security.py tests/evaluation/test_mechanical_corpus.py -q -k "dimension or tolerance"
uv run ruff check src/autocad_mcp/semantics/mechanical/annotations.py tests/unit/semantics/mechanical
uv run bandit -q -r src/autocad_mcp/semantics/mechanical
```

### E08B-WP06: Score and orchestrate read-only analysis

**Owned files:** `mechanical/service.py`, `mechanical/repository.py`, service/repository/determinism tests.

**TDD steps:** inject fake EPIC-04 snapshot, EPIC-08A topology, and mechanical repositories; test exact full `SnapshotRef`/fingerprint/schema/method/spec/scope/relation/tolerance/detector agreement and reject every one-field mismatch before facts; test canonical mechanical spec digest, bounded count/bytes/TTL repository keys, complete-only insertion, no cursor in stored snapshot, page-only cursors, EPIC-07 scoring, issues, no capture/mutation, and two-hash-seed determinism; implement pure orchestration.

**Exact verification:**

```bash
uv run pytest tests/unit/semantics/mechanical/test_service.py tests/unit/semantics/mechanical/test_repository.py -q
PYTHONHASHSEED=1 uv run pytest tests/unit/semantics/mechanical/test_determinism.py -q
PYTHONHASHSEED=947 uv run pytest tests/unit/semantics/mechanical/test_determinism.py -q
uv run pytest tests/unit/semantics/mechanical tests/evaluation/test_mechanical_corpus.py -q
```

### E08B-WP07: Register read-only mechanical analysis

**Owned files:** tool handler and exact contract test; shared integration files remain serialized-owner files.

**TDD steps:** add exact schema/fake-service tests carrying canonical `MechanicalAnalysisSpec` with source/topology/detector/spec digests, complete materialization, paged results, stale/mismatch/unsupported/cursor cases; prove no edit/confirmation/capture/code-generation call; implement thin handler; register only kinds meeting `0.90` precision; update canonical catalog/configuration in one window.

**Exact verification:**

```bash
uv run pytest tests/contract/test_mechanical_semantics_tool.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run pytest tests/unit/topology tests/unit/semantics/mechanical tests/evaluation/test_mechanical_corpus.py -q
uv run ruff check src tests
uv run mypy src/autocad_mcp/topology src/autocad_mcp/semantics/mechanical src/autocad_mcp/tools/mechanical_semantics.py
```

### E08B-WP08: Evaluate AutoCAD-extracted mechanical fixtures

**Owned files:** Windows integration test, mechanical PowerShell runner, immutable run artifacts, AutoCAD evidence section only; EPIC-03 harness is consumed read-only.

**TDD steps:** review expected EPIC-04/08A facts before running; label extraction only **mechanical semantic input extraction verified on full AutoCAD 2026**; run frozen detectors/evaluator and label only **mechanical detectors evaluated on AutoCAD-extracted fixtures**; for every case reuse EPIC-03's neutral drawing-copy guard to create a unique-GUID copy, prove source/copy path inequality/hash equality and active `FullName`, close without saving, rehash, and preserve failures; acquire/release the exclusive AutoCAD verification lease around every real attach/run; preserve detector disagreements and report issues/performance.

**Exact verification:**

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_mechanical_semantics_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\mechanical-source.dwg
```

## Parallel lanes and exclusive file ownership

E08B-A and E08B-B freeze first. Part/profile, hole/axis, and annotation lanes may then run concurrently with read-only corpus access. Service follows published detector vectors; MCP follows the metric gate; real evaluation runs last and cannot edit labels/evaluator/detectors. The serialized registry window is separate from EPIC-08A.

## Acceptance criteria

- EPIC-08A acceptance and exact method/tolerance/result version are verified before implementation.
- `MechanicalSemanticsService` receives EPIC-04 snapshot, EPIC-08A topology, and EPIC-08B mechanical repositories; it accepts/stores only complete retained objects with exact full `SnapshotRef`, fingerprint, schema/method/spec/scope/relation/tolerance/detector agreement.
- Complete `MechanicalAnalysisSnapshot` and paged `MechanicalAnalysisResultPage` are separate; only the page carries cursor metadata. The bounded repository keys source/topology/detector/mechanical spec and rejects pages/incomplete/mixed versions.
- Mechanical facts contain literal geometry/topology/annotation data only; interpretations are separate immutable hypotheses.
- Every hypothesis includes fact/topology IDs, evidence, counterevidence, score/confidence, state, ambiguity, fingerprint, and detector versions.
- Inferred results meet EPIC-07 evidence rules; ambiguous/conflicting/unsupported cases remain unknown.
- Literal tolerance parsing is bounded, locale-explicit, non-evaluating, versioned, and makes no compliance claim.
- Frozen corpus/evaluator predates detectors, stays exclusively owned, and every registered kind reaches `0.90` precision with recall/unknown/issues visible.
- Tool is read-only and never captures, mutates, confirms, approves, executes, or invokes EPIC-06.
- AutoCAD evidence separates input extraction verified from detectors evaluated and records unchanged fingerprints.

## Windows and AutoCAD verification

Use full AutoCAD 2026 disposable fixtures containing plate/shaft/profile views, outer/inner profiles, holes, center marks/lines, repeated geometry, native/exploded dimensions, explicit tolerances, misleading circles/layers/text, proxy/unsupported entities, paper-space title blocks, and ambiguous locale text. Record environment/fixture/topology/detector/parser versions, units/tolerance, issues, metrics, timing/RSS, modal interaction, and identical before/after fingerprints.

Every real run acquires the EPIC-03 exclusive verification lease keyed by installation/build and interactive-session ID and records release outcome. An unleased or concurrently owned run cannot satisfy this gate.

Only input extraction is AutoCAD verified. Mechanical detectors are evaluated on AutoCAD-extracted fixtures and are not described as verified manufacturing semantics. Earlier AutoCAD releases remain targeted until separate records exist.

## Safety and security gates

- Accepted complete EPIC-04 snapshot and EPIC-08A topology only; exact version/tolerance binding.
- Facts/interpretations remain separate; unknown/unsupported is visible.
- Visual observations are untrusted, bounded, provenance-labelled, and influence-capped.
- Literal text is parsed as data without expressions, imports, command construction, or execution.
- No mutation, capture, confirmation, approval, code generation, arbitrary execution, or unrestricted `SendCommand`.
- Exclusive corpus/evaluator and real-evidence ownership; no result-driven relabelling.
- Logs/evidence redact drawing text/paths/proprietary geometry.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Topology changes invalidate semantics | Bind exact accepted EPIC-08A method/tolerance and fail stale/mismatch |
| Circle/centerline overclassification | Require containment plus independent evidence; preserve counterevidence/unknown |
| Literal tolerance implies compliance | Separate literal fact from role and prohibit standards/manufacturing claims |
| Parser becomes execution surface | Strict bounded grammar, no evaluation, adversarial security corpus |
| Synthetic metrics hide real failures | Separate AutoCAD-extracted evaluation and immutable disagreements/labels |

## Rollback

Unregister `analyze_mechanical_semantics` or the affected kind, invalidate detector-version results/cursors, and retain accepted EPIC-08A topology. Preserve failing corpus/evidence. No drawing recovery is required because the epic is read-only. A topology regression blocks/reverts mechanical registration until EPIC-08A is accepted again.

## Completion evidence

- Accepted EPIC-08A dependency/version record.
- Mechanical contract/fact/hypothesis canonical vectors and fact/interpretation separation tests.
- Canonical mechanical analysis spec/complete-snapshot/result-page vectors and bounded repository complete-only/key/TTL/byte tests.
- Frozen labelled corpus/evaluator with reviewer approvals and immutable digest.
- Per-kind confusion counts, precision, recall, unknown/ambiguity/conflict/issues and all versions.
- Parser security results and proof of no confirmation/edit/capture/execution surface.
- Unit/evaluator/determinism/contract/catalog/stdio/lint/type/compile/diff results.
- AutoCAD 2026 record with separate extraction-verification/detector-evaluation labels and unchanged fingerprints.
- Per-case EPIC-03 neutral-copy-guard and exclusive-lease evidence: GUID copy, source/copy path inequality and hashes, active `FullName`, close-without-save, preserved failed copy, and lease acquisition/release.

## Handoff

The owner verifies EPIC-08A and EPIC-07 evidence contracts, then freezes facts/models and corpus before detector lanes. Each lane hands off public signatures, rule/parser versions, canonical vectors, commands/results, limitations, and changed-file list. The serialized integration owner performs the separate 08B registry window. The Windows lane consumes accepted code/corpus read-only. Completion never changes EPIC-08A evidence or promotes untested AutoCAD releases.

Related plans: [EPIC-08 index](EPIC-08-general-and-mechanical-semantics.md), [EPIC-08A](EPIC-08A-general-topology.md), [EPIC-07](EPIC-07-architectural-semantics.md), and [EPIC-04](EPIC-04-structured-drawing-context.md).
