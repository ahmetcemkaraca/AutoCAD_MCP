# EPIC-07: Architectural Semantics

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

**Planned as two sequential sub-epics.** **EPIC-07A** is read-only architectural analysis and may ship without any approval broker. **EPIC-07B** is the later semantic-confirmation/edit bridge and cannot start until EPIC-07A is accepted and EPIC-06's human broker, persistent store, and safe edit path pass. Neither sub-epic is current functionality.

## Outcome and user value

In EPIC-07A, a user can ask for architectural interpretation of a versioned 2D drawing snapshot and receive bounded wall, door, window, column, room, dimension, and text hypotheses that explain their evidence, counterevidence, confidence, and uncertainty. Deterministic CAD facts remain visibly distinct from client-provided visual observations. Ambiguous geometry stays unknown rather than being promoted by plausible language.

In EPIC-07B, when a user wants to develop the drawing from a hypothesis, the system first requires trusted human semantic confirmation of that exact hypothesis through an additive EPIC-06 broker/UI/store purpose. Only a confirmed hypothesis may be compiled into EPIC-06 primitive operations, and those operations still require a new EPIC-06 preview and separate human edit approval. Semantic confirmation is not edit authorization and cannot be reused as an edit token.

## Scope

- Read-only analysis of 2D model-space and paper-space snapshots for seven hypothesis kinds: wall, door, window, column, room, dimension, and text.
- Deterministic feature extraction from entity geometry, layers, blocks/attributes, text/dimension facts, bounding boxes, and general spatial relationships.
- Explicit evidence and counterevidence records with source, observed fact, rule identifier, weight, and affected handles.
- Versioned, deterministic confidence scoring with a conservative unknown state.
- Client-provided visual observations as advisory evidence with provenance and strict influence limits.
- EPIC-07B human semantic confirmation through a versioned extension to the EPIC-06 broker/UI/store, with expiry, replay protection, atomic persistence, and named human evidence; there is no MCP/model confirmation method.
- EPIC-07B limited compiler from confirmed semantic intents to existing EPIC-06 primitives.
- Architectural fixture drawings and labelled expectation files for common layers, blocks, openings, parallel-line wall patterns, enclosures, dimensions, and text.
- Evaluation reports that include per-kind precision, recall, unknown rate, ambiguity, conflicts, unsupported entities, detector version, and fixture digest.

The initial compiler may express only changes already safe as EPIC-06 primitives, such as moving or rotating a confirmed block reference, changing an existing component's layer/properties, adding non-destructive reference geometry, or editing allowlisted text/dimension properties when the adapter supports them. It must reject any intent that requires deletion, trim/extend, wall-opening cuts, arbitrary block execution, architectural operation kinds, or an unsupported EPIC-06 primitive.

## Out of scope

- 3D building information modelling, IFC/Revit interoperability, code compliance, structural adequacy, energy analysis, quantity/cost estimation, clash detection, and construction-document certification.
- Automatic truth claims from layer names, block names, text labels, raster vision, or a single geometric cue.
- Server-side vision models, vision provider dependencies, implicit capture, or automatic image capture during analysis.
- Learning or retraining from customer drawings, opaque model confidence, and network inference.
- Model-callable confirmation, conversational phrases treated as approval, or semantic confirmation inferred from MCP request fields.
- Direct mutation from a hypothesis or intent, bypass of EPIC-06, reuse of a semantic confirmation receipt as an edit approval, and extension of EPIC-06 with `create_wall`/`insert_door`-style operations.
- Deletion, wall opening creation, room-boundary repair, or any edit not representable by the accepted EPIC-06 primitive union.
- Mechanical/manufacturing interpretation, which belongs to EPIC-08.
- Claims that a hypothesis is professionally validated architectural information.

## Prerequisites

1. EPIC-02 has completed the installable `src/autocad_mcp/` package migration; `python -m autocad_mcp.server` is the sole canonical stdio launch; structured errors are verified with the fake service.
2. EPIC-04 `DrawingSnapshot` and `EntityContext` expose document/session/snapshot identities, content fingerprint, active space, UCS, units, pagination, handle identity, geometry, layers, blocks, attributes, text, dimensions, bounding boxes, and supported relationship facts.
3. EPIC-04 relationship extraction provides `same_owner`, bounding-box, endpoint-touch, and parallel facts with normalized tolerance metadata and reports unsupported properties rather than omitting them silently. Architectural feature extraction owns any additional domain-specific pairing or enclosure work; it does not depend on the later EPIC-08 topology stage.
4. EPIC-05 capture is explicitly optional and non-gating for EPIC-07A. EPIC-07A must install, register, evaluate, and ship when capture is absent; it never invokes capture. A supplied visual observation may use `capture_id=None` or cite a separately obtained capture without making capture availability a prerequisite.
5. Disposable architectural DWG fixtures and a real full AutoCAD 2026 installation are available for EPIC-07A extraction/evaluation.
6. For EPIC-07B only, EPIC-06 provides canonical `EditPlan` primitives, `preview_edit_plan`, broker-backed apply authorization, persistent trusted store, named operator UI, stale-state validation, per-operation outcomes, Undo rollback, and `rollback_failed` handling.

EPIC-07A begins after prerequisites 1-5 and has no broker dependency. EPIC-07B begins only after EPIC-07A acceptance and prerequisite 6; no 07B file, tool, or status claim merges in the 07A delivery.

## Proposed owned files

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/semantics/evidence.py` | EPIC-07A evidence/provenance/state and owned `ClientVisualObservation` | Lane E07A-A contracts |
| `src/autocad_mcp/semantics/architecture/models.py` | Architectural hypothesis and analysis types | Lane E07A-A contracts |
| `tests/fixtures/architecture/manifest.json` and `cases/**` | Frozen labelled corpus, negative/ambiguous cases, digests | Lane E07A-B corpus |
| `tests/evaluation/test_architectural_corpus.py` | Independent frozen evaluator and metric report | Lane E07A-B corpus |
| `src/autocad_mcp/semantics/architecture/features.py` | Pure normalized feature extraction from snapshot facts | Lane E07A-C features |
| `src/autocad_mcp/semantics/architecture/walls_openings.py` | Wall, door, and window candidate rules | Lane E07A-D detectors |
| `src/autocad_mcp/semantics/architecture/spaces_components.py` | Room, column, dimension, and text rules | Lane E07A-E detectors |
| `src/autocad_mcp/semantics/architecture/scoring.py` | Versioned deterministic confidence and unknown policy | Lane E07A-F service |
| `src/autocad_mcp/semantics/architecture/service.py` | Read-only analysis orchestration, pagination, result shaping | Lane E07A-F service |
| `src/autocad_mcp/tools/architectural_semantics.py` | EPIC-07A read-only analysis handler | Lane E07A-G contract |
| `tests/contract/test_architectural_semantics_tools.py` | EPIC-07A exact MCP schema/fake-service contract | Lane E07A-G contract |
| `tests/integration/windows/test_architectural_semantics_autocad.py` | Later real AutoCAD extraction/detector evaluation only | Lane E07A-H real evaluation |
| `tests/windows/run_architectural_semantics_autocad_2026.ps1` | EPIC-03-harness runner accepting only source DWGs | Lane E07A-H real evaluation |
| `tests/windows/drawing_copy_guard.py` | Consumed unchanged neutral source/copy guard | EPIC-03 owner; read-only to E07 |
| `src/autocad_mcp/approval/semantic_models.py` | EPIC-07B binding, receipt, human evidence, expiry/replay types | Lane E07B-A broker extension |
| `src/autocad_mcp/approval/semantic_store.py` | EPIC-07B atomic persistent pending/decision/consumption state | Lane E07B-A broker extension |
| `src/autocad_mcp/approval/windows_semantic_ui.py` | EPIC-07B named human semantic Confirm/Reject panel | Lane E07B-A broker extension |
| `src/autocad_mcp/semantics/architecture/confirmation.py` | EPIC-07B verifier-only receipt consumption | Lane E07B-B bridge |
| `src/autocad_mcp/semantics/architecture/intents.py` | EPIC-07B confirmed-intent validation and primitive compilation | Lane E07B-B bridge |
| `src/autocad_mcp/tools/architectural_intents.py` | EPIC-07B compile handler; no confirmation or mutation handler | Lane E07B-C contract |
| `tests/contract/test_architectural_intent_tools.py` | EPIC-07B receipt/compiler contract | Lane E07B-C contract |
| `docs/architectural-semantics.md` | 07A evidence/evaluation and 07B confirmation/edit limitations | Evidence/documentation owner |

Only a serialized integration owner modifies the EPIC-06 broker host/UI registration, canonical server registry, `mcp.json`, `tests/contract/test_server_tool_catalog.py`, `tests/contract/test_stdio_server.py`, or canonical architecture/roadmap/testing/compatibility documents. The E07A-B corpus owner is the only writer of labels, manifest, evaluator, and expected metrics; detector and real-evaluation lanes cannot edit them. Fixture JSON contains synthetic facts, not proprietary drawing content.

## Consumed interfaces

```python
class SnapshotRepository(Protocol):
    def get_complete(self, snapshot_id: str, *, session_id: str | None = None) -> DrawingSnapshot: ...
```

`SnapshotRepository` is imported from `autocad_mcp.context.repository` and accepts complete snapshots only. `DrawingSnapshot`, `SnapshotRef`, `DocumentIdentity`, `DrawingFingerprint`, `DrawingUnits`, `GeometryTolerance`, `EntityContext`, `RelationshipFact`, and `CapabilityIssue` are imported from EPIC-04. The analysis source is `DrawingSnapshot.reference`; stale-state checks use `DrawingSnapshot.fingerprint.content_digest`; handle and prior-state evidence uses `EntityContext.identity.handle` and `EntityContext.state_digest`. This epic does not define parallel context identities or broaden EPIC-04 relationship facts in place.

EPIC-07A has no dependency on EPIC-06 services, broker, tokens, or mutation types. EPIC-07B imports `EditPlan`, primitive operation types, and plan canonicalization from accepted EPIC-06 only after its gate.

EPIC-07B consumes this verifier-only capability from the extended trusted broker host; EPIC-07A does not:

```python
class SemanticDecisionVerifier(Protocol):
    def consume_confirmation(
        self,
        receipt: str,
        expected: SemanticConfirmationBinding,
        now: datetime,
    ) -> SemanticConfirmationReceipt: ...
```

No MCP service receives an issuer or `confirm` method.

## Produced interfaces and types

### Evidence and hypothesis contract

```python
class ArchitecturalKind(StrEnum):
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    COLUMN = "column"
    ROOM = "room"
    DIMENSION = "dimension"
    TEXT = "text"

class EvidenceSource(StrEnum):
    CAD_FACT = "cad_fact"
    CAD_RELATIONSHIP = "cad_relationship"
    LAYER_METADATA = "layer_metadata"
    BLOCK_METADATA = "block_metadata"
    TEXT_OR_DIMENSION = "text_or_dimension"
    CLIENT_VISUAL_OBSERVATION = "client_visual_observation"

class EvidencePolarity(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"

class InterpretationState(StrEnum):
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class ClientVisualObservation:
    observation_id: str
    snapshot_id: str
    capture_id: str | None
    subject_handles: tuple[str, ...]
    label: str
    confidence: float
    description: str

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source: EvidenceSource
    polarity: EvidencePolarity
    rule_id: str
    subject_handles: tuple[str, ...]
    observed: Mapping[str, JsonValue]
    weight: float
    provenance_id: str | None

@dataclass(frozen=True)
class ArchitecturalHypothesis:
    hypothesis_id: str
    hypothesis_digest: str
    detector_version: str
    snapshot_id: str
    snapshot_fingerprint: str
    kind: ArchitecturalKind
    subject_handles: tuple[str, ...]
    attributes: Mapping[str, JsonValue]
    evidence: tuple[EvidenceRecord, ...]
    counterevidence: tuple[EvidenceRecord, ...]
    score: float
    confidence: float | None
    state: InterpretationState
    ambiguity_codes: tuple[str, ...]
```

`hypothesis_id` is deterministic for detector version, snapshot ID, kind, and sorted subject handles. `hypothesis_digest` covers the complete canonical hypothesis except display prose and confirmation fields. Hypotheses never overwrite `EntityContext` or relationship records.

`ClientVisualObservation` is owned by `semantics/evidence.py`, not supplied by EPIC-04 or an MCP client library. Observations arrive explicitly as untrusted request data. EPIC-07A validates confidence in `[0.0, 1.0]`, snapshot/capture references, handle membership, count/text limits, and provenance; it does not claim to verify visual truth.

When `capture_id` is non-null, EPIC-07A validates only the supplied provenance identifier against an already available capture record; it never requests capture. When no capture subsystem/record exists, callers omit visual observations or use `capture_id=None`, and deterministic CAD analysis remains fully available.

### Confidence policy

Detector rules emit evidence, not a final label. `scoring.py` applies the published rule table in a stable order:

- weights are finite values in `[-1.0, 1.0]` and are versioned with the detector;
- repeated observations of the same fact/rule/handles are deduplicated;
- the total contribution of all client visual observations is capped at `0.20` and visual evidence can never be the sole supporting source;
- direct contradictory CAD geometry sets `unknown` even when the numeric score would otherwise exceed the threshold;
- the internal/public `score` is clamped to `[0.0, 1.0]` and rounded to four decimal places;
- `inferred` requires score/confidence at least `0.75`, at least two independent evidence sources, and no hard contradiction;
- results below `0.75`, with incomplete enclosure/opening data, with competing hypotheses within `0.10`, or with unsupported required geometry are `unknown`; and
- only a consumed trusted human semantic decision can produce `confirmed`.

For `inferred` and `confirmed`, `confidence` equals the score. For `unknown`, `confidence` is `None` to preserve the EPIC-04 interpretation contract while `score` remains available as diagnostic evidence. A human may confirm or reject an exact hypothesis. Rejection is recorded as a decision event but the returned interpretation remains `unknown` with `ambiguity_codes` containing `human_rejected`; no alternative label is invented.

### EPIC-07A analysis contract

```python
@dataclass(frozen=True)
class ArchitecturalAnalysisRequest:
    snapshot_id: str
    kinds: tuple[ArchitecturalKind, ...]
    handle_scope: tuple[str, ...]
    visual_observations: tuple[ClientVisualObservation, ...]
    page_size: int
    cursor: str | None
    source_session_id: str | None = None

@dataclass(frozen=True)
class ArchitecturalAnalysisResult:
    analysis_id: str
    detector_version: str
    source: SnapshotRef
    hypotheses: tuple[ArchitecturalHypothesis, ...]
    unsupported: tuple[CapabilityIssue, ...]
    next_cursor: str | None
```

Analysis is bounded to 1-200 results per page, at most 256 scoped handles (matching EPIC-04), 100 visual observations, 2 KiB per observation description, and a 512 KiB request. Cursors bind detector version, snapshot fingerprint, filters, and sort order. A stale or mismatched cursor fails. EPIC-07A emits only `inferred` and `unknown`; it has no confirmation receipt or broker dependency.

### EPIC-07B semantic confirmation contract

```python
@dataclass(frozen=True)
class SemanticHumanSummary:
    schema_version: Literal["1"]
    document_id: str
    session_id: str
    snapshot_id: str
    snapshot_fingerprint: str
    hypothesis_id: str
    hypothesis_digest: str
    kind: ArchitecturalKind
    subject_handles: tuple[str, ...]
    attributes: Mapping[str, JsonValue]
    evidence: tuple[EvidenceRecord, ...]
    counterevidence: tuple[EvidenceRecord, ...]
    score: float
    confidence: float | None
    state: InterpretationState
    ambiguity_codes: tuple[str, ...]

def canonical_semantic_human_summary_bytes(summary: SemanticHumanSummary) -> bytes: ...
def semantic_human_summary_digest(summary: SemanticHumanSummary) -> str: ...

@dataclass(frozen=True)
class SemanticHumanEvidence:
    prompt_instance_id: str
    operator_sid_digest: str
    displayed_hypothesis_digest: str
    displayed_human_summary_digest: str
    action: Literal["confirmed", "rejected"]
    occurred_at: datetime
    ui_name: Literal["AutoCAD MCP Human Approval"]
    ui_version: str

@dataclass(frozen=True)
class SemanticConfirmationBinding:
    decision_id: str
    document_id: str
    session_id: str
    snapshot_id: str
    snapshot_fingerprint: str
    hypothesis_id: str
    hypothesis_digest: str
    human_summary_digest: str

@dataclass(frozen=True)
class SemanticConfirmationReceipt:
    receipt_id: str
    binding: SemanticConfirmationBinding
    human_summary_digest: str
    human_evidence: SemanticHumanEvidence
    consumed_at: datetime

class SemanticConfirmationStore(Protocol):
    def register_pending(
        self,
        binding: SemanticConfirmationBinding,
        human_summary: SemanticHumanSummary,
    ) -> None: ...
    def consume(
        self,
        receipt: str,
        expected: SemanticConfirmationBinding,
        now: datetime,
    ) -> SemanticConfirmationReceipt: ...
    def invalidate(self, decision_id: str, reason: str) -> None: ...
```

`canonical_semantic_human_summary_bytes()` uses EPIC-06 canonical UTF-8/sorted-key/NFC/finite-number/normalized-handle rules and includes every structured summary field. The digest is lowercase `sha256:<64 hex>`. The broker recomputes it before rendering and derives display prose only from those bytes; the UI evidence records the displayed digest.

EPIC-07B adds a versioned `semantic_confirmation` purpose to the accepted EPIC-06 broker process, named **AutoCAD MCP Human Approval** UI, and current-user protected store. The verifier pipe may add only `register_semantic`, `consume_semantic`, and `invalidate_semantic`; decision remains a direct trusted UI event and is never IPC or MCP. Confirm creates a 256-bit raw receipt secret shown once and stored only as a digest with `SemanticHumanEvidence`; Reject stores evidence and creates no secret. The secret expires after five minutes, is single-use under concurrency, and is bound server-side to all eight binding fields including `human_summary_digest`. `consume()` accepts the raw secret as input but returns only sanitized `SemanticConfirmationReceipt(receipt_id, binding, human_summary_digest, human_evidence, consumed_at)`; raw secret, secret digest, issuance time, and expiry are not serialized to the compiler/MCP result. Pending/confirmed/rejected/consumed state is written atomically under the same current-user SID ACL/DPAPI policy as EPIC-06 and reloads across broker/server restart until expiry. Expired, replayed, wrong-purpose, wrong-binding, summary-digest-mismatched, corrupt, or unknown receipts fail identically. Automated fixtures cannot close semantic human authority; a named operator must Confirm and Reject real prompts and attach redacted evidence.

### Confirmed intent and EPIC-06 bridge

```python
class ArchitecturalIntentKind(StrEnum):
    MOVE_COMPONENT = "move_component"
    ROTATE_COMPONENT = "rotate_component"
    CHANGE_COMPONENT_LAYER = "change_component_layer"
    SET_COMPONENT_PROPERTIES = "set_component_properties"
    ADD_REFERENCE_LINE = "add_reference_line"
    ADD_REFERENCE_CIRCLE = "add_reference_circle"

@dataclass(frozen=True)
class ArchitecturalIntent:
    schema_version: Literal["1"]
    kind: ArchitecturalIntentKind
    hypothesis_id: str
    hypothesis_digest: str
    parameters: Mapping[str, JsonValue]

@dataclass(frozen=True)
class CompiledArchitecturalIntent:
    intent: ArchitecturalIntent
    semantic_decision_id: str
    plan: EditPlan
    compiler_version: str
```

The compiler reconstructs canonical `SemanticHumanSummary` from the current hypothesis, verifies its bytes/digest against the sanitized receipt, binding, and human evidence, and then verifies the fresh receipt, hypothesis digest, snapshot fingerprint, supported intent kind, and current facts. Any digest mismatch rejects before plan construction. It emits only EPIC-06 `move`, `rotate`, `change_layer`, `set_properties`, `create_line`, or `create_circle` operations with expected prior states. It never invokes apply. The caller must submit the compiled `EditPlan` to EPIC-06 preview, compare the new digest and effects, obtain a separate edit token, and apply through EPIC-06. The semantic receipt is single-use for compilation and is not accepted by EPIC-06.

## Detector rules for the first delivery

- **Wall:** paired line/polyline runs that are parallel within snapshot tolerance, have consistent separation over an overlapping interval, and participate in continuity/junction evidence. Layer/name evidence may support but never establish a wall alone. Single lines and variable-width or broken pairs remain unknown unless a recognized block/property supplies independent evidence.
- **Door:** a block reference with explicit attribute/name evidence, or a swing arc/leaf-line arrangement located at a detected wall interruption. A free arc without opening context is unknown.
- **Window:** a recognized block/property or repeated parallel components located within a detected wall interruption. Short parallel lines away from a wall are not windows.
- **Column:** a closed rectangle/circle/polyline or recognized block with independent structural/layer/placement evidence. Shape alone is insufficient.
- **Room:** a closed enclosure in the relationship graph, optionally correlated with one interior room label. Open, self-intersecting, multiply labelled, or competing enclosures are unknown and report the reason.
- **Dimension:** supported AutoCAD dimension entities are direct type facts; their architectural role remains inferred from references, layer/style, and nearby components. Text that resembles a dimension is not converted into a dimension fact.
- **Text:** text and MText entities are direct type facts. Architectural role such as room label, component tag, or note is a hypothesis with location, content pattern, and referenced component evidence. Raw text is returned as drawing content and follows existing privacy/logging rules.

Every rule has synthetic positive, negative, ambiguous, and unsupported fixtures. Names such as `A-WALL` or `DOOR-900` are supporting metadata only.

## Work packages

### E07A-WP01: Freeze evidence and hypothesis contracts

**Owned files:** `src/autocad_mcp/semantics/evidence.py`, `src/autocad_mcp/semantics/architecture/models.py`, `tests/semantics/architecture/test_models.py`, `tests/semantics/architecture/test_hypothesis_digest.py`.

**TDD steps:**

1. Add failing tests for every enum/type, finite confidence/weight bounds, normalized/sorted handles, immutable fact separation, deterministic IDs/digests, rejected extra fields, and bounded analysis inputs.
2. Publish canonical hypothesis vectors for one result of every kind, including an unknown result with counterevidence.
3. Implement the minimal immutable types and canonical digest logic.
4. Run focused tests, compilation, and lint; hand the vectors to all detector lanes.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_models.py tests/semantics/architecture/test_hypothesis_digest.py -q
uv run ruff check src/autocad_mcp/semantics/evidence.py src/autocad_mcp/semantics/architecture/models.py tests/semantics/architecture
uv run python -m compileall -q src/autocad_mcp/semantics tests/semantics
```

### E07A-WP02: Freeze the labelled corpus and independent evaluator

**Owned files:** `tests/fixtures/architecture/manifest.json`, `tests/fixtures/architecture/cases/**`, `tests/evaluation/test_architectural_corpus.py`.

**TDD steps:**

1. Before detector implementation, freeze at least 20 labelled positive and 10 negative/ambiguous instances for each kind, including evidence pointers, expected unknowns, unsupported cases, units/tolerance, and canonical snapshot/label digests.
2. Write the independent evaluator first; it reports per-kind confusion counts, precision, recall, unknown rate, ambiguity codes, unsupported counts, detector version, and corpus digest without importing detector internals.
3. Review labels with one architecture-domain reviewer and one evidence-contract reviewer; record approvals in the manifest and make later edits require a new corpus version/digest.
4. Run the evaluator against an empty detector result to prove the gate fails. After freeze, only Lane E07A-B may modify labels/evaluator; detector and real-evaluation lanes consume them read-only.

**Exact verification:**

```bash
uv run pytest tests/evaluation/test_architectural_corpus.py -q
uv run python -m compileall -q tests/evaluation
git diff --check -- tests/fixtures/architecture tests/evaluation/test_architectural_corpus.py
```

### E07A-WP03: Normalize snapshot features without domain claims

**Owned files:** `src/autocad_mcp/semantics/architecture/features.py`, `tests/semantics/architecture/test_features.py`.

**TDD steps:**

1. Add failing tests for line/polyline runs, arcs, circles, closed loops, block attributes, text/dimension facts, bounds, layer/style metadata, and relationship indexing.
2. Add tests for units/tolerances, invalid geometry, missing capabilities, unsupported entity facts, page completeness, and deterministic ordering.
3. Implement pure normalized feature extraction; emit no architectural label and perform no COM access.
4. Run focused tests and an import test in an environment without Windows modules.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_features.py -q
uv run python -c "from autocad_mcp.semantics.architecture.features import extract_features"
uv run ruff check src/autocad_mcp/semantics/architecture/features.py tests/semantics/architecture/test_features.py
```

### E07A-WP04: Detect walls, doors, and windows

**Owned files:** `src/autocad_mcp/semantics/architecture/walls_openings.py`, `tests/semantics/architecture/test_walls_openings.py`.

**TDD steps:**

1. Add failing positive/negative/ambiguous tests for parallel-line walls, polylines, junctions, gaps, wall openings, swing arcs, door/window blocks, misleading layer names, isolated arcs, and competing door/window candidates.
2. Assert each candidate contains rule-addressable evidence and counterevidence rather than a bare label.
3. Implement deterministic candidate rules using only normalized features.
4. Run focused detector tests and fixture evaluation for these three kinds.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_walls_openings.py -q
uv run pytest tests/evaluation/test_architectural_corpus.py -q -k "wall or door or window"
uv run ruff check src/autocad_mcp/semantics/architecture/walls_openings.py tests/semantics/architecture/test_walls_openings.py
```

### E07A-WP05: Detect rooms, columns, dimensions, and text roles

**Owned files:** `src/autocad_mcp/semantics/architecture/spaces_components.py`, `tests/semantics/architecture/test_spaces_components.py`.

**TDD steps:**

1. Add failing tests for closed/open/self-intersecting/competing enclosures, room labels, closed column shapes, column blocks, dimension entities and references, text/MText roles, duplicate labels, and misleading names.
2. Add unsupported tests for incomplete relationship pages, proxy dimensions, invalid text bounds, and enclosures spanning spaces/xrefs.
3. Implement deterministic candidate rules and ambiguity codes.
4. Run focused tests and fixture evaluation for these four kinds.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_spaces_components.py -q
uv run pytest tests/evaluation/test_architectural_corpus.py -q -k "room or column or dimension or text"
uv run ruff check src/autocad_mcp/semantics/architecture/spaces_components.py tests/semantics/architecture/test_spaces_components.py
```

### E07A-WP06: Score conservatively and orchestrate analysis

**Owned files:** `src/autocad_mcp/semantics/architecture/scoring.py`, `src/autocad_mcp/semantics/architecture/service.py`, `tests/semantics/architecture/test_scoring.py`, `tests/semantics/architecture/test_service.py`.

**TDD steps:**

1. Add failing tests for deduplication, score clamping/rounding, source independence, the visual `0.20` cap, hard contradictions, competing hypotheses, unknown thresholds, deterministic ordering, and detector versioning.
2. Add service tests for filters, 200-result pages, cursor binding, stale snapshot rejection, unsupported reporting, no automatic capture, and no COM import.
3. Implement scoring and analysis orchestration without ML or network dependencies.
4. Run all pure semantics tests twice with different hash seeds and require byte-identical canonical results.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_scoring.py tests/semantics/architecture/test_service.py -q
PYTHONHASHSEED=1 uv run pytest tests/semantics/architecture/test_determinism.py -q
PYTHONHASHSEED=947 uv run pytest tests/semantics/architecture/test_determinism.py -q
uv run pytest tests/semantics/architecture -q
```

### E07A-WP07: Register read-only architectural analysis

**Owned files:** `src/autocad_mcp/tools/architectural_semantics.py`, `tests/contract/test_architectural_semantics_tools.py`; shared registry/configuration remain serialized-integration files.

**TDD steps:**

1. Add failing exact-schema tests for `analyze_architectural_semantics`, including bounds, `additionalProperties: false`, evidence provenance, state, ambiguity, unsupported results, pagination, and structured errors.
2. Add fake-context tests for complete, ambiguous, stale, paginated, visual-advisory, and unsupported snapshots.
3. Assert the handler never imports/calls capture, mutation, EPIC-06, approval, semantic confirmation, or code execution, and that every EPIC-07A result state is `inferred` or `unknown`.
4. Implement the thin read-only handler, then have the serialized integration owner update canonical registration, `mcp.json`, `test_server_tool_catalog.py`, and `test_stdio_server.py` together.
5. Run the full labelled evaluator and register only kinds meeting the stated precision gate.

**Exact verification:**

```bash
uv run pytest tests/contract/test_architectural_semantics_tools.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run pytest tests/semantics/architecture tests/evaluation/test_architectural_corpus.py -q
uv run ruff check src/autocad_mcp/semantics src/autocad_mcp/tools/architectural_semantics.py tests/semantics tests/evaluation
uv run mypy src/autocad_mcp/semantics src/autocad_mcp/tools/architectural_semantics.py
```

### E07A-WP08: Evaluate AutoCAD-extracted architectural fixtures

**Owned files:** `tests/integration/windows/test_architectural_semantics_autocad.py`, `tests/windows/run_architectural_semantics_autocad_2026.ps1`, immutable run artifacts, and the AutoCAD evaluation section of `docs/architectural-semantics.md`. This lane cannot edit the EPIC-03 harness, corpus, labels, evaluator, detector rules, or scoring.

**TDD steps:**

1. Review expected EPIC-04 fact extraction for disposable architectural fixtures before running detectors; record fixture and expectation digests.
2. Extract complete snapshots in full AutoCAD 2026 and label this evidence only **architectural context extraction verified on full AutoCAD 2026**.
3. Run the frozen detector/evaluator against those extracted snapshots, preserve every disagreement, and label the result only **architectural detectors evaluated on AutoCAD-extracted fixtures**. This is not semantic truth or professional verification.
4. For every case reuse EPIC-03's neutral `tests/windows/drawing_copy_guard.py`: copy the source to a unique GUID directory, assert source/copy path inequality and initial hash equality, open the copy under the lane's read-only policy, assert `ActiveDocument.FullName`, close without saving, and recheck both hashes. Preserve a failed copy for diagnosis without altering the source.
5. Acquire/release the EPIC-03 exclusive AutoCAD verification lease around every real attach/open/run, keyed by installation/build and interactive-session ID; an unleased/concurrent run cannot satisfy the gate.
6. Prove no capture construction/call, no broker dependency, no mutation, and visible unsupported/unknown results.
7. Publish limitations and both separately named evidence records before closing EPIC-07A.

**Exact verification:**

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_architectural_semantics_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\architecture-source.dwg
```

### E07B-WP01: Extend the EPIC-06 broker/UI/store for semantic decisions

**Owned files:** `src/autocad_mcp/approval/semantic_models.py`, `src/autocad_mcp/approval/semantic_store.py`, `src/autocad_mcp/approval/windows_semantic_ui.py`, matching approval tests; base broker/UI host integration is serialized.

**TDD steps:**

1. Freeze canonical `SemanticHumanSummary` bytes/digest vectors. Add failing tests for all eight binding fields, five-minute expiry, digest-only secret persistence, atomic single consumption, summary tampering, replay, wrong purpose/binding, rejection, invalidation, corrupt state, and restart. Assert the sanitized receipt has exactly `receipt_id`, `binding`, `human_summary_digest`, `human_evidence`, and `consumed_at` and no raw secret/secret digest/issuance/expiry.
2. Add trust-boundary tests proving `register_semantic`, `consume_semantic`, and `invalidate_semantic` are verifier-only; semantic Confirm/Reject is a direct named UI event and is absent from MCP and IPC.
3. Add evidence tests for exact hypothesis and canonical human-summary digests rendered by **AutoCAD MCP Human Approval** and persisted in `SemanticHumanEvidence` on Confirm and Reject.
4. Implement the additive purpose using EPIC-06 inherited-handle authentication, current-user SID ACL, DPAPI/atomic local persistence, and no second broker process or trust root.
5. Run a manual named-operator gate for one real Confirm and Reject; automated fixtures cannot close human semantic authority.

**Exact verification:**

```bash
uv run pytest tests/approval/test_semantic_models.py tests/approval/test_semantic_store.py tests/approval/test_windows_semantic_ui.py -q
uv run pytest tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run ruff check src/autocad_mcp/approval tests/approval
```

### E07B-WP02: Consume confirmation once and compile safe primitives

**Owned files:** `src/autocad_mcp/semantics/architecture/confirmation.py`, `src/autocad_mcp/semantics/architecture/intents.py`, `tests/semantics/architecture/test_confirmation.py`, `tests/semantics/architecture/test_intents.py`, `tests/semantics/architecture/test_safe_edit_sequence.py`.

**TDD steps:**

1. Add failing tests for missing, expired, replayed, rejected, wrong-document/session/snapshot/hypothesis/summary-digest confirmations and prove compilation produces no plan in each case.
2. Add one success and one rejection test for each supported intent; assert the output union contains only accepted EPIC-06 primitive kinds and exact expected prior states.
3. Reject deletion, opening cuts, trim/extend, unconfirmed inferred hypotheses, stale snapshots, unsupported component/entity types, and architectural operation discriminators.
4. Implement verifier-only receipt consumption and deterministic compilation; do not call preview or apply.
5. Prove the sequence is 07A hypothesis -> human semantic confirmation -> single-use compile -> EPIC-06 preview -> separate human edit approval -> EPIC-06 apply.

**Exact verification:**

```bash
uv run pytest tests/semantics/architecture/test_confirmation.py tests/semantics/architecture/test_intents.py tests/semantics/architecture/test_safe_edit_sequence.py -q
uv run pytest tests/editing tests/approval -q
uv run ruff check src/autocad_mcp/semantics/architecture tests/semantics/architecture
```

### E07B-WP03: Register the compile-only bridge

**Owned files:** `src/autocad_mcp/tools/architectural_intents.py`, `tests/contract/test_architectural_intent_tools.py`; shared broker host/core/catalog/configuration remain serialized-integration files.

**TDD steps:**

1. Add exact-schema tests for `compile_confirmed_architectural_intent`, sanitized-receipt serialization/redaction, structured expiry/replay/wrong-purpose failures, and bounded intent inputs.
2. Prove no `confirm_architectural_hypothesis`, approve, broker decision, direct edit, or apply tool is registered by EPIC-07B.
3. Implement a thin compile-only handler that receives `SemanticDecisionVerifier`, never a decision sink or EPIC-06 apply capability.
4. Have the serialized integration owner update the EPIC-06 broker host, canonical server, `mcp.json`, `test_server_tool_catalog.py`, and `test_stdio_server.py` together.
5. Run all 07A, 07B, EPIC-06 approval/edit, and canonical contract regressions.

**Exact verification:**

```bash
uv run pytest tests/contract/test_architectural_intent_tools.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run pytest tests/semantics/architecture tests/approval tests/editing tests/contract -q
uv run ruff check src tests
uv run mypy src/autocad_mcp/semantics src/autocad_mcp/approval src/autocad_mcp/tools/architectural_intents.py
```

## Parallel lanes and exclusive file ownership

EPIC-07A completes before any EPIC-07B implementation starts. Within 07A, contracts and the labelled corpus/evaluator freeze first; feature extraction follows; the two detector lanes may then run concurrently; scoring/service and read-only MCP integration follow; the real AutoCAD lane runs last and cannot alter expected data. After the 07A acceptance record, 07B executes broker extension, compiler, then compile-only contract registration.

| Lane | Work packages | Exclusive ownership | Dependency |
| --- | --- | --- | --- |
| E07A-A Contracts | E07A-WP01 | `semantics/evidence.py`, `architecture/models.py`, matching tests | EPIC-04 contracts |
| E07A-B Corpus/evaluator | E07A-WP02 | architecture fixture manifest/cases, independent evaluator | E07A-A; sole label/evaluator writer |
| E07A-C Features | E07A-WP03 | `architecture/features.py`, matching test | E07A-A/B |
| E07A-D Walls/openings | E07A-WP04 | `architecture/walls_openings.py`, matching test | E07A-C; corpus read-only |
| E07A-E Spaces/components | E07A-WP05 | `architecture/spaces_components.py`, matching test | E07A-C; corpus read-only |
| E07A-F Scoring/service | E07A-WP06 | `architecture/scoring.py`, `service.py`, matching tests | E07A-D/E vectors |
| E07A-G Read-only MCP | E07A-WP07 | `tools/architectural_semantics.py`, 07A contract test | E07A-F/evaluator gate |
| E07A-H Real evaluation | E07A-WP08 | Windows integration test and immutable run artifacts | Accepted 07A code; cannot edit labels/code |
| E07B-A Broker extension | E07B-WP01 | semantic approval models/store/UI extension and tests | Accepted 07A and EPIC-06 |
| E07B-B Confirmation/compiler | E07B-WP02 | `confirmation.py`, `intents.py`, matching tests | E07B-A |
| E07B-C Compile MCP | E07B-WP03 | `tools/architectural_intents.py`, 07B contract test | E07B-B |

No lane edits another lane's modules, the frozen corpus/evaluator, shared broker host, server registration, `mcp.json`, or canonical docs. Detector lanes exchange canonical candidate JSON vectors, not copied helper code. The serialized integration owner opens separate 07A and 07B registry windows and runs EPIC-06 regressions only for 07B.

## Acceptance criteria

- All seven architectural kinds return hypotheses with handles, attributes, evidence, counterevidence, confidence, state, ambiguity codes, snapshot fingerprint, and detector version.
- Hypotheses are separate immutable interpretations; no semantic label is written into CAD facts.
- Deterministic CAD facts/relationships and client visual observations have distinct provenance. Visual contribution is capped at `0.20`, cannot be sole support, and cannot force `confirmed`.
- Conflicting geometry, incomplete required context, close competitors, unsupported facts, and confidence below `0.75` return `unknown` with actionable ambiguity codes.
### EPIC-07A

- Analysis is explicit, bounded, paginated, deterministic, AutoCAD-independent, and never invokes capture, broker, confirmation, EPIC-06, or mutation.
- 07A returns only `inferred` or `unknown`; it can ship with no broker process or semantic confirmation store.
- EPIC-05 capture is optional/non-gating; 07A ships and all CAD-fact analysis works when capture is absent or unregistered.
- Every registered kind reaches at least `0.90` inferred-result precision on its versioned synthetic corpus; recall, abstention, ambiguity, and unsupported counts remain visible.
- Corpus labels/evaluator freeze before detector lanes and only the corpus owner may revise them under a new version/digest.
- AutoCAD evidence uses two honest labels: **architectural context extraction verified on full AutoCAD 2026** and **architectural detectors evaluated on AutoCAD-extracted fixtures**.

### EPIC-07B

- Only a trusted direct human UI decision bound to the exact hypothesis/snapshot can produce a single-use confirmation receipt; no confirmation MCP/IPC/model tool exists.
- Raw semantic receipt secrets have five-minute expiry, atomic digest-only persistence, restart reload, replay/wrong-purpose rejection, and persisted human Confirm/Reject evidence; the sanitized receipt contains five non-secret fields including canonical human-summary digest.
- Broker rendering/evidence/binding/receipt and compiler reconstruction agree on canonical `SemanticHumanSummary` bytes/digest; mismatch prevents intent compilation.
- The confirmed-intent compiler accepts only fresh exact confirmations and produces only existing EPIC-06 primitives with expected prior state.
- Semantic confirmation never authorizes drawing mutation. A separate EPIC-06 preview and human edit approval are required, and all EPIC-06 failure/rollback behavior remains intact.
- Deletion, wall cuts, trim/extend, direct apply, executable text, and architectural operation discriminators are rejected by tests and schemas.
- Automated fixtures cannot close semantic human authority; a named operator supplies Confirm and Reject evidence from the real UI.

## Windows and AutoCAD verification

Use full AutoCAD 2026 and fresh disposable copies representing at least:

- conventional `A-WALL`-style layer naming and neutral/misleading layer names;
- exploded linework and equivalent block-based doors/windows/columns;
- parallel-line walls with T/L junctions, gaps, and inconsistent widths;
- valid and broken room enclosures, duplicate/missing labels, and paper/model-space separation;
- native dimension entities, text resembling dimensions, MText room labels, and proxy/unsupported entities; and
- one ambiguous drawing where the correct result is predominantly `unknown`.

The runner acquires the EPIC-03 exclusive verification lease before any real attachment and records release outcome. Lease contention fails closed; stale-owner recovery requires evidence that the recorded process is dead.

Run E07A-WP08's Windows command. Record AutoCAD product/build, Windows, Python, lockfile and fixture digests, extraction capability report, detector version, result/evaluation JSON, modal interaction, and exact command. Review false positives against the frozen labelled copies without changing labels. Do not use raster vision unless the test explicitly supplies a separately captured observation; record it as client visual evidence.

Only EPIC-04-compatible extraction receives the label **verified on full AutoCAD 2026**. Detector output receives the separate label **evaluated on AutoCAD-extracted fixtures**, not AutoCAD-verified semantics. AutoCAD 2021-2025 remain targeted until the same extraction contract and separately reported detector evaluation run on real installations.

## Safety and security gates

- Semantic output is advisory and never overwrites structured CAD facts.
- Layer, block, text, and visual evidence cannot establish truth alone.
- All visual observations are untrusted client input with bounded size, handle/snapshot validation, provenance, and capped influence.
- Capture availability is never a 07A gate; no observation causes capture construction/invocation, and `capture_id=None` remains valid.
- No server-side provider, API key, implicit capture, network inference, or learning from customer drawings is introduced.
- EPIC-07A contains no broker dependency, confirmation state change, intent compiler, or edit capability.
- EPIC-07B reuses the EPIC-06 broker trust root and named UI; direct human semantic decisions bind all eight fields including summary digest, persist evidence, expire, and reject replay. Decision is never MCP or IPC.
- Compilation consumes a semantic receipt once, rejects stale or mismatched facts, and does not apply.
- EPIC-06 performs a second human approval, live-state preflight, Undo grouping, rollback verification, and token invalidation.
- No deletion, executable code, unrestricted command text, xref/proxy mutation, or unsupported primitive passes the compiler.
- Text/entity content and personal drawing paths are redacted from logs and evidence reports.
- Unknown is a successful safe result, not an error to conceal or automatically resolve.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Layer/block conventions create false certainty | Treat names as one evidence source; require independent geometry/relationship evidence |
| Visual confidence overwhelms facts | Cap aggregate visual weight, preserve provenance, and make hard CAD contradictions force unknown |
| Heuristics vary with units or drawing precision | Consume snapshot units/tolerance, use normalized features, and version all rule thresholds |
| Enclosure and opening algorithms scale poorly | Require bounded scopes/pages, indexed relationships, fixture performance budgets, and structured unsupported results |
| Human confirms the wrong hypothesis | Show document/snapshot, handles, evidence, counterevidence, digest, and ambiguity in the trusted UI; expire receipts |
| Confirmation is confused with edit approval | Use separate receipt/token types, purposes, stores, UI copy, expiry, and tests for cross-use rejection |
| Semantic decision disappears/replays across restart | Atomic current-user protected semantic store, digest-only receipt, expiry, startup reload, and concurrency/restart tests |
| Compiler sneaks in semantic or destructive operations | Exhaustive primitive-union tests and rejection of unknown discriminators; EPIC-06 validates again |
| Fixture precision hides real-drawing failures | Report real drawing disagreements and abstentions separately; never relabel output as ground truth |
| Detector changes invalidate old confirmation | Include detector version and hypothesis digest in confirmations; reject after any changed output |

## Rollback

The semantics layer is additive and read-only by default. A detector regression is rolled back by unregistering only the affected hypothesis kind, restoring the last versioned rule table, invalidating outstanding semantic confirmations for that detector version, and retaining raw structured context tools. Do not silently change thresholds under the same detector version.

If the confirmed-intent bridge is unsafe, unregister `compile_confirmed_architectural_intent` while keeping analysis available and labelled advisory. Invalidate all semantic receipts and EPIC-06 previews derived from the affected compiler version. Any drawing already mutated follows EPIC-06 Undo and `rollback_failed` procedure; semantic code must not attempt separate recovery.

Roadmap and project-status claims revert in the same corrective pull request. Fixture and incident evidence is preserved in redacted form for regression tests.

## Completion evidence

- Contract and canonical digest vectors for all seven hypothesis kinds.
- Focused red/green output for every work package and the complete pure/MCP suites.
- Determinism results under two hash seeds and proof of AutoCAD-independent imports.
- A labelled fixture manifest with digests, detector version, counts, positive/negative/ambiguous coverage, and reviewed expectations.
- Evidence that the corpus/evaluator froze before detector implementation and retained exclusive ownership thereafter.
- Per-kind precision, recall, unknown rate, ambiguity, conflict, and unsupported reports; every registered kind meets the stated precision gate.
- Separate 07A/07B registry evidence for the read-only analysis tool and compile-only bridge, with no semantic confirmation tool.
- Tests proving visual evidence caps and hard-contradiction behavior.
- Tests proving semantic decision expiry, atomic persistence/restart, one-time receipt use, cross-purpose/replay rejection, persisted human evidence, and the separate EPIC-06 approval sequence.
- Canonical semantic summary vectors and exact sanitized receipt serialization proving human-summary digest mirrors binding/evidence/receipt/compiler while raw secret/secret digest/issuance/expiry never leave the broker verifier.
- Named-operator semantic Confirm and Reject evidence; automated fixture output is not human-authority evidence.
- AutoCAD 2026 run record with separate extraction-verification and detector-evaluation labels.
- EPIC-03 neutral drawing-copy guard and exclusive verification-lease evidence for every Windows case: GUID copy, path inequality, initial/final hashes, active `FullName`, close-without-save, preserved failure copy, and lease acquisition/release.
- Lint, type-check, compile, stdio-integrity, link, and diff-check results.
- Documentation limitations and compatibility labels that match the recorded environments.

## Handoff

The epic owner first freezes evidence/snapshot contracts and the labelled corpus/evaluator, then assigns 07A lanes with the exclusive paths above. Detector authors receive normalized feature and canonical hypothesis vectors; they do not depend on AutoCAD COM or each other's internals and cannot revise expected labels. Each lane returns signatures, rule IDs, test vectors, commands/results, limitations, and a changed-file list.

The serialized integration owner closes and publishes EPIC-07A independently after corpus metrics and Windows extraction/evaluation evidence. Only then are 07B lanes assigned. A safety reviewer audits the additive EPIC-06 broker/UI/store purpose, human evidence, expiry/replay/persistence, and compile bridge. The integration owner registers the compile-only tool separately. EPIC-07B closes only after independent review confirms the absence of model/IPC confirmation and the two distinct human gates before any drawing mutation.

Related plans and constraints: [EPIC-06](EPIC-06-human-approved-safe-edit-plans.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing](../testing.md), [compatibility](../compatibility.md), and the [approved modernization design](../superpowers/specs/2026-08-25-maintenance-and-modernization-design.md).
