# EPIC-06: Human-Approved Safe Edit Plans

## Status

**Planned.** This epic describes target behavior only. It depends on the stable canonical MCP server, structured errors, the Windows adapter boundary, and versioned drawing snapshots being delivered and verified first. Nothing in this document is evidence that drawing mutation is currently safe or available.

## Outcome and user value

A user can inspect a deterministic preview of a constrained drawing edit, approve that exact preview through a trusted human-facing broker, and apply it once without granting the model a general execution channel. Every apply attempt revalidates the live document and records enough evidence to distinguish success, rejection before mutation, verified Undo rollback, and an unverified or failed rollback.

The critical trust property is that an MCP caller cannot approve its own plan. `preview_edit_plan` returns a `preview_id` and `plan_digest`, never an approval token. A separate broker, outside the model-callable MCP tool surface, issues a short-lived single-use token only after a human confirms the displayed document, operations, effects, warnings, and digest. A deployment without a reachable and authenticated broker fails closed.

## Scope

The first delivery supports these declarative primitive operations:

- `create_line` and `create_circle` with explicit layer and geometry;
- `move`, `rotate`, and `scale_uniform` for identified existing handles;
- `set_geometry` for allowlisted entity-specific numeric fields;
- `set_properties` for allowlisted color, linetype, lineweight, and visibility fields; and
- `change_layer` to an existing layer or to a layer created by an explicit `ensure_layer` operation in the same plan.

Every plan contains a source snapshot, document and session identities, expected prior entity states, ordered operations, and client-supplied rationale treated as untrusted display text. Preview is read-only. Apply is permitted only after all preflight gates pass and is executed inside one adapter-owned AutoCAD Undo group.

The delivery also includes:

- canonical plan encoding and SHA-256 digests;
- bounded preview storage and expiry;
- a trusted local broker process and human confirmation surface that are not MCP tools;
- server-side approval bindings and atomic single-use token consumption;
- a typed edit-adapter provider with static and Windows compositions, so editing services never downcast the base adapter or receive COM state;
- per-operation outcomes and an overall application state;
- Undo rollback on the first operation failure;
- post-failure drawing fingerprint verification; and
- an atomic persistent document-identity edit block after `rollback_failed` until the recovery UI records human acknowledgement and validates a complete fresh safe snapshot.

## Out of scope

- Deletion, purge, explode, trim, extend, boolean, or any operation whose primary effect removes drawing data.
- Architectural semantic operations such as `create_wall`, `insert_door`, `resize_window`, or `assign_room`. EPIC-07 may later compile a separately confirmed semantic intent into the primitive operations above, but it does not extend this epic's operation enum.
- Arbitrary Python, AutoLISP, VBA, shell commands, macros, expressions, dynamic imports, or caller-controlled `SendCommand` strings.
- Claims of database-transaction atomicity. An AutoCAD Undo group is a recovery mechanism, not a transaction.
- Automatic image capture before or after an edit.
- Background approval, approval inferred from conversation text, reusable approval sessions, wildcard approvals, and approval by the model or MCP client.
- Mutation of xrefs, locked layers, proxy entities, external databases, read-only drawings, or unsupported entity/capability combinations.
- AutoCAD LT and AutoCAD hosted on Linux or macOS.

## Prerequisites

1. EPIC-02 has completed the installable `src/autocad_mcp/` package migration; `python -m autocad_mcp.server` is the sole canonical stdio launch; structured error envelopes and the focused fake service pass without eager COM imports.
2. Structured context supplies immutable complete `DrawingSnapshot` records. Edit identity comes from `DrawingSnapshot.reference.snapshot_id`, `.reference.document_id`, `.reference.session_id`, and `.reference.fingerprint`; live session comparison also uses `.document.session_document_id`, stale-state comparison uses `.fingerprint.content_digest`, and active space/entity prior state comes from `.active_context` and handle-addressed `.entities`.
3. EPIC-03 exposes its adapter-internal `WindowsSessionManager`, which owns delayed COM acquisition, apartment/thread confinement, and proxy lifetime. The EPIC-06 Windows edit adapter consumes that manager rather than opening an independent COM path; no manager or COM proxy crosses into domain/editing code.
4. EPIC-04's accepted `ContextAutoCADAdapter`, `WindowsContextAutoCADAdapter`, context provider, complete `SnapshotRepository`, and immutable context types are available. EPIC-06 owns the additive edit/Undo methods; no prerequisite is allowed to claim those methods already exist.
5. The canonical contract harness contains `tests/contract/test_stdio_server.py` and `tests/contract/test_server_tool_catalog.py`, which prove protocol-clean stdout and catalog/configuration agreement.
6. A trusted Windows host can launch the approval broker and the named human operator UI with the trust-root controls defined below.
7. AutoCAD 2026 and disposable DWG fixtures are available for the first real integration run. AutoCAD 2021-2025 remain targeted, not verified.

If any prerequisite interface differs when this epic starts, the integration owner must update this epic and its contract tests in one review before feature implementation. Individual lanes must not invent adapters around unresolved mismatches.

## Proposed owned files

These paths are the ownership proposal for this epic; they are not current files.

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/autocad_mcp/editing/models.py` | Immutable request, plan, preview, operation-outcome, and apply-result types | Lane E06-A |
| `src/autocad_mcp/editing/canonical.py` | Versioned canonical JSON encoding and plan digest calculation | Lane E06-A |
| `src/autocad_mcp/editing/validation.py` | Pure schema and semantic validation, limits, prior-state checks | Lane E06-B |
| `src/autocad_mcp/editing/preview.py` | Read-only preview orchestration and impact summaries | Lane E06-B |
| `src/autocad_mcp/editing/preview_store.py` | Bounded expiring preview records; no raw approval tokens | Lane E06-B |
| `src/autocad_mcp/editing/fresh_snapshot.py` | Named wrapper over the exact EPIC-04 `SnapshotBuilder`/repository | Lane E06-B |
| `src/autocad_mcp/approval/models.py` | Approval binding, decision, grant, and consumption types | Lane E06-C |
| `src/autocad_mcp/approval/broker.py` | Trusted broker service, token issuance, atomic consume, invalidation | Lane E06-C |
| `src/autocad_mcp/approval/windows_pipe.py` | Current-user-SID named-pipe verifier transport and inherited-handle authentication | Lane E06-C |
| `src/autocad_mcp/approval/windows_operator_ui.py` | Named human operator Confirm/Reject UI; decision never enters IPC | Lane E06-C |
| `src/autocad_mcp/editing/executor.py` | Apply preflight, ordered execution, Undo rollback, result shaping | Lane E06-D |
| `src/autocad_mcp/adapter/edit_protocol.py` | Typed edit/Undo extension of the EPIC-03 adapter protocol | Lane E06-D |
| `src/autocad_mcp/adapter/edit_provider.py` | `EditAdapterProvider`, static test provider, and delayed Windows provider | Lane E06-D |
| `src/autocad_mcp/adapter/windows_edit.py` | Constrained COM operation and Undo implementation | Lane E06-D |
| `src/autocad_mcp/editing/incident_store.py` | Atomic persistent `rollback_failed` locks and recovery-clear verification | Lane E06-D |
| `src/autocad_mcp/tools/edit_plans.py` | Plan handlers and preview-only line/circle compatibility shims | Lane E06-E |
| `tests/editing/**` | Pure plan, validation, preview, apply, and rollback tests | Matching implementation lane |
| `tests/approval/**` | Broker isolation, issuance, expiry, replay, and IPC tests | Lane E06-C |
| `tests/adapter/test_edit_provider.py` | Static/Windows edit-provider composition and delayed-boundary tests | Lane E06-D |
| `tests/contract/test_edit_plan_tools.py` | Tool schemas, compatibility shims, and fake-adapter contracts | Lane E06-E |
| `tests/integration/windows/test_edit_plans_autocad.py` | Disposable-DWG AutoCAD 2026 verification harness | Lane E06-F |
| `tests/windows/run_edit_plans_autocad_2026.ps1` | EPIC-03-harness runner accepting only a source DWG | Lane E06-F |
| `tests/windows/edit_autocad_harness.py` | EPIC-06 writable-copy policy over the neutral guard | Lane E06-F |
| `tests/windows/drawing_copy_guard.py` | Consumed unchanged neutral source/copy guard | EPIC-03 owner; read-only to E06 |
| `docs/safe-edit-plans.md` | User/operator contract and recovery guidance | Lane E06-F |
| `src/autocad_mcp/core/models.py` | Add exact EPIC-06 `ErrorCode` members without changing `ToolError` | Serialized integration owner |
| `src/autocad_mcp/runtime.py` | Compose context/edit providers, persistent incident store, and broker verifier | Serialized integration owner |
| `src/autocad_mcp/server.py` | Register plan tools and preview-only compatibility shims | Serialized integration owner |
| `mcp.json` | Match the accepted plan/shim schemas and descriptions | Serialized integration owner |
| `tests/contract/test_stdio_server.py` | Canonical subprocess protocol/stdout regression | Serialized integration owner |
| `tests/contract/test_server_tool_catalog.py` | Exact tool catalog and `mcp.json` agreement | Serialized integration owner |

The integration owner alone modifies the canonical server registration file, `mcp.json`, `docs/architecture.md`, `docs/roadmap.md`, `docs/testing.md`, and `docs/compatibility.md`. Lanes must not modify legacy modules or expose the broker through `src/autocad_mcp/tools/`.

## Consumed interfaces

The epic consumes these prerequisite contracts. Equivalent immutable types are acceptable only after the epic is updated before implementation.

`JsonValue`, `ErrorCode`, `ToolError`, `ToolSuccess`, and `ToolFailure` are imported unchanged from EPIC-02. `DrawingSnapshot`, `SnapshotRef`, `DocumentIdentity`, `DrawingFingerprint`, `EntityContext`, `CapabilityIssue`, `SnapshotRepository`, `CompleteSnapshotRequest`, `RelationshipOptions`, `SnapshotBuilder`, `AdapterDocumentContext`, `AdapterEntityFacts`, `ContextInclude`, `ContextAutoCADAdapter`, `ContextAdapterProvider`, `FakeContextAutoCADAdapter`, and `WindowsContextAutoCADAdapter` are imported unchanged from EPIC-04. `SnapshotRepository.get_complete(snapshot_id)` refuses partial snapshots. Edit freshness uses `DrawingSnapshot.reference`, `DrawingSnapshot.document.session_document_id`, `DrawingSnapshot.fingerprint.content_digest`, and `EntityContext.state_digest`; this epic does not define a second identity, fingerprint, context enumerator, context provider, or error envelope.

`src/autocad_mcp/adapter/windows_edit.py` consumes the adapter-internal `WindowsSessionManager` frozen by EPIC-03. That manager is the only path to a live AutoCAD application, document, entity, COM apartment, or COM proxy. It is not imported by `edit_provider.py`, re-exported from `autocad_mcp.editing`, stored in plan/domain models, or returned by an edit-provider method.

The canonical server consumes only this restricted broker view:

```python
@dataclass(frozen=True)
class HumanOperationSummary:
    operation_id: str
    kind: str
    target_handles: tuple[str, ...]
    before: Mapping[str, JsonValue] | None
    after: Mapping[str, JsonValue]
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class HumanSummary:
    schema_version: Literal["1"]
    document_display_name: str
    document_id: str
    session_id: str
    snapshot_id: str
    snapshot_fingerprint: str
    plan_digest: str
    ordered_operations: tuple[HumanOperationSummary, ...]
    warnings: tuple[str, ...]

def canonical_human_summary_bytes(summary: HumanSummary) -> bytes: ...
def human_summary_digest(summary: HumanSummary) -> str: ...

class ApprovalVerifier(Protocol):
    def register_preview(self, binding: ApprovalBinding, summary: HumanSummary) -> None: ...
    def consume(self, token: str, expected: ApprovalBinding, now: datetime) -> ApprovalReceipt: ...
    def invalidate_preview(self, preview_id: str, reason: str) -> None: ...
    def available(self) -> bool: ...
```

The token-issuing interface is available only inside the broker process and is never injected into an MCP handler:

```python
@dataclass(frozen=True)
class HumanDecisionEvidence:
    prompt_instance_id: str
    operator_sid_digest: str
    displayed_plan_digest: str
    displayed_human_summary_digest: str
    action: Literal["confirmed", "rejected"]
    occurred_at: datetime
    ui_name: Literal["AutoCAD MCP Human Approval"]
    ui_version: str

@dataclass(frozen=True)
class Rejection:
    preview_id: str
    evidence: HumanDecisionEvidence

class HumanOperatorDecisionSink(Protocol):
    def decide_from_ui_event(
        self,
        preview_id: str,
        evidence: HumanDecisionEvidence,
    ) -> ApprovalGrant | Rejection: ...
```

`HumanOperatorDecisionSink` exists only inside the broker process and is called directly by the named Windows UI event handler. It is absent from the named-pipe protocol, MCP, prompts, resources, command-line entry points, environment configuration, and test fixture APIs.

## Produced interfaces and types

### Edit adapter and provider

```python
EditCapability = Literal[
    "create_line", "create_circle", "ensure_layer", "move", "rotate",
    "scale_uniform", "set_geometry", "set_properties", "change_layer",
    "undo_group",
]

@dataclass(frozen=True)
class UndoGroupId:
    value: str

@dataclass(frozen=True)
class AdapterOperationResult:
    operation_id: str
    target_handles: tuple[str, ...]
    created_handles: tuple[str, ...]
    readback: tuple[AdapterEntityFacts, ...]

class EditAutoCADAdapter(ContextAutoCADAdapter, Protocol):
    def edit_capabilities(self) -> tuple[EditCapability, ...]: ...
    def start_undo_group(self, label: str) -> UndoGroupId: ...
    def apply_primitive(self, operation: PrimitiveOperation) -> AdapterOperationResult: ...
    def end_undo_group(self, group_id: UndoGroupId) -> None: ...
    def rollback_undo_group(self, group_id: UndoGroupId) -> None: ...

class EditAdapterProvider(Protocol):
    def get(self) -> EditAutoCADAdapter: ...

class StaticEditAdapterProvider:
    def __init__(self, adapter: EditAutoCADAdapter) -> None: ...
    def get(self) -> EditAutoCADAdapter: ...

class WindowsEditAdapterProvider:
    def __init__(
        self,
        factory: Callable[[], EditAutoCADAdapter] | None = None,
    ) -> None: ...
    def get(self) -> EditAutoCADAdapter: ...

class FakeEditAutoCADAdapter(FakeContextAutoCADAdapter): ...

class WindowsEditAutoCADAdapter(WindowsContextAutoCADAdapter):
    def __init__(self, session_manager: WindowsSessionManager) -> None: ...

def create_windows_edit_adapter() -> WindowsEditAutoCADAdapter: ...

class FreshSnapshotReader(Protocol):
    def read_complete(self) -> DrawingSnapshot: ...

class SnapshotBuilderFreshSnapshotReader:
    def __init__(
        self,
        builder: SnapshotBuilder,
        repository: SnapshotRepository,
        request: CompleteSnapshotRequest,
    ) -> None: ...
    def read_complete(self) -> DrawingSnapshot: ...

class EditPlanPreviewService:
    def __init__(
        self,
        fresh_snapshot_reader: FreshSnapshotReader,
        approval_verifier: ApprovalVerifier,
    ) -> None: ...

class EditPlanExecutor:
    def __init__(
        self,
        adapter_provider: EditAdapterProvider,
        fresh_snapshot_reader: FreshSnapshotReader,
        approval_verifier: ApprovalVerifier,
        incident_store: IncidentLockStore,
    ) -> None: ...
```

`StaticEditAdapterProvider.get()` returns the exact injected fake/contract adapter. `WindowsEditAdapterProvider.get()` locally imports and calls `create_windows_edit_adapter()` unless a test factory is supplied; `edit_provider.py` never imports or names `WindowsSessionManager`. The `windows_edit.py` factory constructs `WindowsEditAutoCADAdapter(WindowsSessionManager())`, satisfying EPIC-03's rule that only `windows_*.py` implementation modules consume the manager. Importing or constructing the provider does not import COM modules, initialize an apartment, attach to AutoCAD, or retain a COM proxy. Every inherited context method and new edit method executes inside a fresh manager session; only adapter-internal callbacks see session/proxy objects, and those objects expire before an `AdapterDocumentContext`, `AdapterEntityFacts`, or `AdapterOperationResult` crosses back to editing code.

`EditAutoCADAdapter` additively extends the released EPIC-04 context protocol and accepts typed primitive operations only. Live document/writability facts come from inherited `read_document_context()`; live handle/prior-state facts come from inherited `entity_facts_by_handles()`; a complete fresh fingerprint comes from the EPIC-04 context service/repository flow. If the Windows implementation needs a fixed AutoCAD command for Undo on a supported release, that constant is private, has no caller interpolation, and is covered by an exact-string test. No adapter method accepts free-form command text. Preview/preflight and `EditPlanExecutor` depend on `EditAdapterProvider`, never the base/context provider, a concrete Windows adapter, or a COM/session type.

`SnapshotBuilderFreshSnapshotReader.read_complete()` calls the injected EPIC-04 `SnapshotBuilder.build()` with the frozen complete version-1 request, inserts the returned complete object into the injected repository, and returns that exact immutable object. It contains no adapter enumeration, mapping, relationship, state-digest, canonicalization, or fingerprint code. `autocad_mcp.runtime` constructs one `SnapshotBuilder`/`SnapshotRepository`/`SnapshotBuilderFreshSnapshotReader` graph and shares the same reader with preview, apply preflight, success readback, rollback verification, incident recovery, and downstream services. No edit path computes a fingerprint from filtered entities or response pages.

### Edit plan and primitive operations

```python
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

@dataclass(frozen=True)
class ExpectedEntityState:
    handle: str
    entity_type: str
    state_digest: str

@dataclass(frozen=True)
class CreateLine:
    operation_id: str
    kind: Literal["create_line"]
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    layer: str

@dataclass(frozen=True)
class CreateCircle:
    operation_id: str
    kind: Literal["create_circle"]
    center: tuple[float, float, float]
    radius: float
    layer: str

@dataclass(frozen=True)
class EnsureLayer:
    operation_id: str
    kind: Literal["ensure_layer"]
    name: str
    color_index: int | None
    linetype: str | None

@dataclass(frozen=True)
class MoveEntity:
    operation_id: str
    kind: Literal["move"]
    target: ExpectedEntityState
    displacement: tuple[float, float, float]

@dataclass(frozen=True)
class RotateEntity:
    operation_id: str
    kind: Literal["rotate"]
    target: ExpectedEntityState
    base_point: tuple[float, float, float]
    angle_radians: float

@dataclass(frozen=True)
class ScaleUniform:
    operation_id: str
    kind: Literal["scale_uniform"]
    target: ExpectedEntityState
    base_point: tuple[float, float, float]
    factor: float

@dataclass(frozen=True)
class SetGeometry:
    operation_id: str
    kind: Literal["set_geometry"]
    target: ExpectedEntityState
    changes: Mapping[str, JsonValue]

@dataclass(frozen=True)
class SetProperties:
    operation_id: str
    kind: Literal["set_properties"]
    target: ExpectedEntityState
    changes: Mapping[str, JsonValue]

@dataclass(frozen=True)
class ChangeLayer:
    operation_id: str
    kind: Literal["change_layer"]
    target: ExpectedEntityState
    layer: str

PrimitiveOperation = (
    CreateLine | CreateCircle | EnsureLayer | MoveEntity | RotateEntity |
    ScaleUniform | SetGeometry | SetProperties | ChangeLayer
)

@dataclass(frozen=True)
class EditPlan:
    schema_version: Literal["1"]
    source: SnapshotRef
    operations: tuple[PrimitiveOperation, ...]
    rationale: str | None
```

Plan limits are part of validation: 1-100 operations, unique operation IDs of 1-64 ASCII alphanumeric/underscore/hyphen characters, at most 256 referenced handles matching EPIC-04, finite coordinates and angles, positive radii and scale factors, layer names valid under AutoCAD rules, at most 4 KiB of rationale, and a 256 KiB canonical request limit. Geometry/property allowlists are keyed by `entity_type`; unknown fields fail rather than pass through to COM. Operations whose computed after-state equals their before-state, and plans with no net effect after cross-operation simulation, are rejected before preview registration.

Canonicalization uses UTF-8 JSON, sorted object keys, no insignificant whitespace, JSON booleans/null, decimal rendering that rejects NaN and infinities, normalized uppercase handles, and `schema_version`. `plan_digest` is lowercase `sha256:<64 hex characters>` over those bytes. The digest excludes `preview_id`, timestamps, impact prose, and token data.

### Preview and approval

```python
@dataclass(frozen=True)
class OperationPreview:
    operation_id: str
    kind: str
    target_handles: tuple[str, ...]
    before: Mapping[str, JsonValue] | None
    after: Mapping[str, JsonValue]
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class PreviewEditPlanResult:
    preview_id: str
    plan_digest: str
    human_summary_digest: str
    created_at: datetime
    preview_expires_at: datetime
    source: SnapshotRef
    document_display_name: str
    operations: tuple[OperationPreview, ...]
    impact_summary: str
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class ApprovalBinding:
    preview_id: str
    plan_digest: str
    document_id: str
    session_id: str
    snapshot_id: str
    snapshot_fingerprint: str
    human_summary_digest: str

@dataclass(frozen=True)
class ApprovalGrant:
    token: str
    issued_at: datetime
    expires_at: datetime
    binding: ApprovalBinding
    human_summary_digest: str
    human_evidence: HumanDecisionEvidence

@dataclass(frozen=True)
class ApprovalReceipt:
    approval_id: str
    consumed_at: datetime
    binding: ApprovalBinding
    human_summary_digest: str
```

`canonical_human_summary_bytes()` uses the same UTF-8, sorted-key, no-whitespace, NFC, normalized-handle, finite-number rules as plan canonicalization and omits no structured summary field. `human_summary_digest` is `sha256:<64 lowercase hex>` over those bytes. Display prose is derived only from the structured summary and is not a second authority.

Successful preview stores the immutable canonical plan and canonical structured `HumanSummary`, returns its digest, and registers the seven-field `ApprovalBinding` plus exact summary bytes with the broker. The broker recomputes/verifies `human_summary_digest` before rendering and displays at least document name/identity, snapshot fingerprint suffix, ordered operations and changed handles, before/after values, warnings, plan digest, summary digest, and expiry. It issues a 256-bit token using `secrets.token_urlsafe(32)` only from an explicit Confirm control. The token expires 120 seconds after issue, is displayed once, is never logged, and is stored only as a SHA-256 digest.

The broker stores the full binding and summary digest server-side. Token contents carry no trusted client assertions. `consume` compares the token digest with `hmac.compare_digest`, verifies all binding fields and the recomputed summary digest, and atomically marks the grant consumed before returning a receipt containing the same digest. A recognized token is invalidated on its first apply attempt even if later preflight rejects the drawing. Preview records expire after 10 minutes and are invalidated by broker rejection, explicit cancellation, session/document close, a detected snapshot mismatch, successful token issuance for a superseding preview of the same plan, apply completion, or any apply failure. Expired, consumed, cancelled, wrong-binding, summary-digest-mismatched, or unknown tokens return the same external `APPROVAL_INVALID` code without revealing which check failed.

### Concrete Windows broker trust root

The trusted launcher creates a 256-bit process-authentication secret and provisions it to the canonical MCP process and broker only through inheritable anonymous-pipe handles selected with an explicit Windows handle list. The handles and secret never appear in environment variables, command-line arguments, configuration, registry values, or files. Each child reads once, closes the inherited handle, and keeps the secret only in process memory. The broker and server authenticate every request with a nonce-bound HMAC and reject reuse.

Broker verifier IPC uses a local Windows named pipe named `\\.\pipe\AutoCADMCP-Approval-v1-<sid-digest>`. Creation applies a DACL granting the current interactive user's SID only, rejects remote clients, verifies the connected client SID by pipe impersonation, authenticates the inherited-secret challenge, bounds every frame, and exposes only `register_preview`, `consume`, `invalidate_preview`, and `health`. There is no `decide`, `approve`, `reject`, `clear_incident`, generic dispatch, or forwarded UI-event method on the pipe.

The broker process owns a visible window whose exact product name is **AutoCAD MCP Human Approval**. It renders the registered immutable summary and provides distinct **Confirm** and **Reject** controls. A direct trusted Windows UI event calls `HumanOperatorDecisionSink`; network/named-pipe messages, MCP arguments, conversation text, synthetic events from the contract fake, and test fixtures cannot call that sink. Each action persists `HumanDecisionEvidence`; confirmation evidence is stored with the grant and rejection evidence is stored with the terminal preview record.

Automated tests may prove schema, ACL construction, authentication, replay, state transitions, and mocked UI-event routing, but they cannot close the human-authority acceptance gate. Closure requires a named human operator to use the real **AutoCAD MCP Human Approval** window on Windows, confirm one preview, reject another, compare both displayed digests, and attach redacted `HumanDecisionEvidence` for both actions.

### Apply states and per-operation outcomes

```python
class ApplyState(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED_ROLLED_BACK = "failed_rolled_back"
    ROLLBACK_FAILED = "rollback_failed"

class OperationState(StrEnum):
    NOT_ATTEMPTED = "not_attempted"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_UNVERIFIED = "rollback_unverified"

@dataclass(frozen=True)
class OperationOutcome:
    operation_id: str
    state: OperationState
    target_handles: tuple[str, ...]
    created_handles: tuple[str, ...]
    error: ToolError | None

@dataclass(frozen=True)
class ApplyEditPlanResult:
    state: ApplyState
    preview_id: str
    plan_digest: str
    approval_id: str | None
    before_fingerprint: str
    after_fingerprint: str | None
    rollback_fingerprint: str | None
    operations: tuple[OperationOutcome, ...]
    error: ToolError | None
    edits_blocked: bool
```

`rollback_failed` includes rollback command failure, Undo-group closure uncertainty, inability to calculate a post-rollback fingerprint, or a post-rollback fingerprint different from `before_fingerprint`. In that state, outcomes already attempted become `rollback_unverified`, the persistent incident store blocks further previews and applies for the document identity across session/restart boundaries, and the response directs the human to use the recovery UI. MCP cannot clear the lock.

### Exact error-code consumption and additions

EPIC-06 consumes `SNAPSHOT_NOT_FOUND`, `SNAPSHOT_EXPIRED`, `SNAPSHOT_INCOMPLETE`, `SNAPSHOT_CHANGED_DURING_READ`, `COMPLETE_SNAPSHOT_LIMIT`, `STALE_SNAPSHOT`, and the other snapshot-builder/repository/shared stale codes unchanged from EPIC-04. It does not re-add or rename them. The serialized integration owner adds only the missing `READ_ONLY_DRAWING` plus these EPIC-06-unique preview/approval/edit/incident codes to EPIC-02 `ErrorCode` in `src/autocad_mcp/core/models.py`:

```python
READ_ONLY_DRAWING = "READ_ONLY_DRAWING"
PREVIEW_NOT_FOUND = "PREVIEW_NOT_FOUND"
PREVIEW_EXPIRED = "PREVIEW_EXPIRED"
APPROVAL_UNAVAILABLE = "APPROVAL_UNAVAILABLE"
APPROVAL_INVALID = "APPROVAL_INVALID"
EDIT_PLAN_REJECTED = "EDIT_PLAN_REJECTED"
ROLLBACK_FAILED = "ROLLBACK_FAILED"
EDITING_BLOCKED = "EDITING_BLOCKED"
```

Existing EPIC-02/04 codes remain authoritative for invalid arguments, unavailable AutoCAD, no active document, COM busy, unsupported capabilities, missing entities, operation failure, snapshot construction/repository failures, and redacted internal failure. All handlers continue returning `ToolFailure(error=ToolError(...))`; no lowercase string is an error code.

### Persistent incident-lock contract

```python
@dataclass(frozen=True)
class IncidentLockRecord:
    schema_version: Literal["1"]
    incident_id: str
    document_id: str
    incident_session_id: str
    source_snapshot_id: str
    source_fingerprint: str
    before_fingerprint: str
    observed_after_fingerprint: str | None
    rollback_fingerprint: str | None
    plan_digest: str
    reason_code: str
    recorded_at: datetime

@dataclass(frozen=True)
class HumanRecoveryEvidence:
    prompt_instance_id: str
    operator_sid_digest: str
    incident_id: str
    acknowledged_at: datetime
    fresh_snapshot_id: str
    fresh_fingerprint: str
    ui_name: Literal["AutoCAD MCP Human Recovery"]

class IncidentLockStore(Protocol):
    def load_for_document(self, document_id: str) -> IncidentLockRecord | None: ...
    def record_atomic(self, record: IncidentLockRecord) -> None: ...
    def clear_after_recovery(
        self,
        record: IncidentLockRecord,
        evidence: HumanRecoveryEvidence,
        fresh_snapshot: DrawingSnapshot,
    ) -> None: ...

class WindowsIncidentLockStore(IncidentLockStore):
    @classmethod
    def open_current_user(cls) -> "WindowsIncidentLockStore": ...
```

`WindowsIncidentLockStore` writes versioned DPAPI-current-user-protected state below `%LOCALAPPDATA%\AutoCADMCP\state\incident-locks-v1`, with a DACL restricted to the current user SID. It writes a sibling temporary file, flushes it, and atomically replaces the prior file; an unreadable, corrupt, partially written, unknown-version, or ACL-invalid record fails closed as `EDITING_BLOCKED`. Records contain identities/digests and reason codes only, never drawing paths, geometry, text, tokens, or COM data.

The runtime loads incident records before registering edit handlers. A record is keyed by persistent `document_id`, includes the incident session and all available before/observed/rollback fingerprints, and survives MCP, broker, and AutoCAD restart. A new AutoCAD `session_id` does not clear a saved-document lock. An unsaved session-scoped document record remains visible to the recovery UI as an orphaned lock and is never matched to a different unsaved document.

Only the separate **AutoCAD MCP Human Recovery** UI receives the internal recovery capability. After the human acknowledges the incident and inspects or recovers the drawing, the recovery controller calls the same runtime-shared `FreshSnapshotReader`. `clear_after_recovery` requires matching persistent document identity, evidence bound to the incident, and `fresh_snapshot.fingerprint.content_digest == evidence.fresh_fingerprint`; then it atomically removes the record. MCP, broker verifier IPC, model output, process restart, session change, expiry, and a bare acknowledgement cannot clear it.

## Mandatory preflight order

`apply_edit_plan` performs these gates in order and starts no Undo group until every gate passes:

1. Parse the bounded request and reject additional fields.
2. Require a configured, authenticated, available broker; otherwise return `APPROVAL_UNAVAILABLE`.
3. Load the unexpired preview by `preview_id` and recompute the digest from its stored canonical plan.
4. Ask the broker to atomically consume the presented token against the stored complete seven-field binding. Require `ApprovalReceipt.human_summary_digest` to equal the stored binding and recomputed canonical summary digest; otherwise return `APPROVAL_INVALID`. From this point, the token cannot be retried.
5. Load the persistent incident store and reject with `EDITING_BLOCKED` if the active persistent document identity has a record, regardless of current AutoCAD session ID. Store load/integrity uncertainty also fails closed.
6. Call the shared `FreshSnapshotReader.read_complete()` once for preflight. Require its exact document/session identities to match the plan, stored source, and broker binding.
7. Require its document facts to report writable/not closing and the expected active space; adapter capability checks may add observed edit support but cannot replace the fresh snapshot.
8. Require the fresh snapshot content fingerprint to equal both the source snapshot and broker binding fingerprints.
9. Resolve every target from the fresh snapshot's complete handle map and require entity type, layer/geometry/property values represented by `state_digest`, and document ownership to match the expected state.
10. Validate capabilities, operation allowlists, numeric ranges, layer locks, xrefs, proxy entities, cross-operation dependencies, and creation name collisions.
11. Recompute every operation preview and canonical `HumanSummary` from the fresh live snapshot. Require byte equality with the broker-displayed summary and constant-time digest equality with `ApprovalReceipt.human_summary_digest` before any Undo call.
12. Record `before_fingerprint`; only then create the Undo group and begin mutation.

Any failure in steps 1-11 returns `rejected`, leaves all operations `not_attempted`, invalidates the preview and any recognized token, and makes no drawing change.

## Mutation and rollback sequence

Operations execute in listed order. After each success, the executor records adapter evidence and created handles. On the first failure it stops immediately, records that operation as `failed`, leaves later operations `not_attempted`, closes the Undo group if required by the adapter, and requests rollback of that exact group. It then calls the shared `FreshSnapshotReader`; no executor/adapter helper re-enumerates context or calculates a fingerprint.

- If rollback reports success and the fresh snapshot fingerprint equals `before_fingerprint`, prior `applied` outcomes become `rolled_back` and the overall state is `failed_rolled_back`.
- If rollback throws, times out, leaves the Undo group uncertain, cannot produce a fingerprint, or produces a different fingerprint, all previously attempted outcomes become `rollback_unverified`. The executor atomically persists `IncidentLockRecord` before returning `rollback_failed`. If persistence itself fails, it disables edit handling for the process, returns `EDITING_BLOCKED`, and requires operator recovery; it never reports an unlocked failure.
- On complete success, the executor closes the Undo group, calls the same `FreshSnapshotReader`, uses that snapshot's content fingerprint as `after_fingerprint`, requires it to differ from `before_fingerprint`, returns `applied`, invalidates the preview, and retains the Undo group for ordinary user Undo.

No automatic retry is allowed after mutation begins. COM-busy retry is allowed only before the Undo group starts and is bounded by the stable-core transient retry policy.

## Work packages

### E06-WP01: Freeze contracts and canonical digests

**Owned files:** `src/autocad_mcp/editing/models.py`, `src/autocad_mcp/editing/canonical.py`, `tests/editing/test_models.py`, `tests/editing/test_canonical.py`.

**TDD steps:**

1. Add failing tests for every operation discriminator, rejected extra fields, duplicate operation IDs, normalized handles, finite-number validation, bounds, deterministic key order, and published digest vectors.
2. Run the focused tests and preserve the expected failures in the lane handoff.
3. Implement only the immutable types, parser, canonical byte encoding, and digest function required by those tests.
4. Run the focused tests, then pure-Python compilation and lint.
5. Publish the canonical JSON bytes and digest for three fixtures so other lanes can test without importing implementation details.

**Exact verification:**

```bash
uv run pytest tests/editing/test_models.py tests/editing/test_canonical.py -q
uv run ruff check src/autocad_mcp/editing/models.py src/autocad_mcp/editing/canonical.py tests/editing/test_models.py tests/editing/test_canonical.py
uv run python -m compileall -q src/autocad_mcp/editing tests/editing
```

### E06-WP02: Build fail-closed validation and preview

**Owned files:** `src/autocad_mcp/editing/validation.py`, `src/autocad_mcp/editing/preview.py`, `src/autocad_mcp/editing/preview_store.py`, `src/autocad_mcp/editing/fresh_snapshot.py`, `tests/editing/test_validation.py`, `tests/editing/test_preview.py`, `tests/editing/test_preview_store.py`, `tests/editing/test_fresh_snapshot.py`.

**TDD steps:**

1. Add failing table tests for all pre-mutation failures: missing snapshot, stale fingerprint, wrong document/session, missing or changed handle, read-only drawing, locked layer, unsupported entity, unsupported capability, invalid values, operation-count/payload limits, and unavailable broker.
2. Add a fake EPIC-04 `SnapshotBuilder` test proving `SnapshotBuilderFreshSnapshotReader` calls `build()` once, stores/returns that exact complete snapshot, and contains no enumeration/fingerprint implementation. Inject the same reader into preview and executor fixtures.
3. Add a spy adapter test proving preview performs no mutation, starts no Undo group, and does not invoke drawing capture.
4. Add clock-controlled tests for bounded storage, 10-minute expiry, cancellation, session-close invalidation, and broker-registration failure cleanup.
5. Freeze canonical `HumanSummary` vectors/bytes/digests and prove changing any structured operation/before/after/warning/identity/digest changes `human_summary_digest`.
6. Implement the pure validator, exact structured summary builder, preview store, shared fresh-reader wrapper, and broker registration call.
7. Verify successful preview returns `preview_id`, `plan_digest`, and `human_summary_digest` and contains no token/grant field.

**Exact verification:**

```bash
uv run pytest tests/editing/test_validation.py tests/editing/test_preview.py tests/editing/test_preview_store.py tests/editing/test_fresh_snapshot.py -q
uv run pytest tests/editing -q
uv run ruff check src/autocad_mcp/editing tests/editing
```

### E06-WP03: Implement the trusted approval broker

**Owned files:** `src/autocad_mcp/approval/models.py`, `src/autocad_mcp/approval/broker.py`, `src/autocad_mcp/approval/windows_pipe.py`, `src/autocad_mcp/approval/windows_operator_ui.py`, `tests/approval/test_broker.py`, `tests/approval/test_windows_pipe.py`, `tests/approval/test_windows_operator_ui.py`.

**TDD steps:**

1. Add failing tests proving no token exists before a direct trusted human-confirm UI event, rejection issues no token, and both paths persist exact plan/summary digests in `HumanDecisionEvidence`.
2. Add clock- and concurrency-controlled tests for 120-second expiry, one-time display, atomic single consumption, all seven binding fields, canonical summary-byte verification, wrong summary digest, replay, cancellation, session close, preview supersession, and token redaction.
3. Add Windows named-pipe tests for the current-user SID DACL, remote-client rejection, peer-SID verification, bounded frames, nonce/HMAC replay, inherited-handle secret provisioning, and the absence of environment/CLI/file secret paths.
4. Assert the pipe method allowlist is exactly `register_preview`, `consume`, `invalidate_preview`, and `health`; `decide`, `approve`, and `reject` must be unrepresentable on IPC and absent from MCP tools, prompts, and resources.
5. Implement token generation with the Python standard library, digest-only storage, the named **AutoCAD MCP Human Approval** UI, direct UI-event decision sink, and verifier-only IPC.
6. Run security-focused log capture and assert raw tokens, secrets, operator SID, proprietary entity values, and drawing paths are absent.
7. Perform the separate manual human-authority gate: a named operator confirms one preview and rejects another in the real UI, checks both digests, and attaches redacted evidence. Automated fixture output is explicitly insufficient to close this gate.

**Exact verification:**

```bash
uv run pytest tests/approval -q
uv run pytest tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run ruff check src/autocad_mcp/approval tests/approval
uv run python -m compileall -q src/autocad_mcp/approval tests/approval
```

### E06-WP04: Execute, roll back, and persist uncertain-document locks

**Owned files:** `src/autocad_mcp/editing/executor.py`, `src/autocad_mcp/editing/incident_store.py`, `tests/editing/test_executor.py`, `tests/editing/test_incident_store.py`.

**TDD steps:**

1. Add failing tests that inject the spy adapter through `StaticEditAdapterProvider`, assert the mandatory preflight order, and prove every rejection occurs before `start_undo_group`; direct concrete-adapter construction in the executor is forbidden.
2. Add success tests proving preflight, success readback, rollback verification, and recovery each call the same injected `FreshSnapshotReader`; no executor/adapter function enumerates context or builds fingerprints. Assert summary/receipt digest equality before `start_undo_group`.
3. Inject failure at every operation index and assert stop-on-first-failure, exact per-operation states, one rollback request, and `failed_rolled_back` only when the restored fingerprint equals the baseline.
4. Add tests for rollback exception, close uncertainty, fingerprint exception, and mismatched restored fingerprint; each must atomically persist `IncidentLockRecord` before returning `rollback_failed` and reject later preview/apply attempts.
5. Recreate the MCP service, broker, and fake AutoCAD session separately and together; reload the record and assert the same saved `document_id` remains blocked despite a new `session_id`. Verify an unsaved session lock never transfers to a different unsaved document.
6. Add fail-closed tests for truncated, corrupt, wrong-version, ACL-invalid, and atomic-replace failure, plus tests proving expiry, process restart, session change, and model/MCP calls cannot clear a record.
7. Add recovery tests requiring a direct **AutoCAD MCP Human Recovery** UI acknowledgement, matching incident ID/document ID, and a complete snapshot from the shared fresh reader whose content fingerprint equals the evidence; only then may an atomic clear succeed.
8. Add tests proving no post-mutation retry and no path invokes drawing capture or accepts executable text, then implement the minimum provider-driven executor and DPAPI/current-user incident store.

**Exact verification:**

```bash
uv run pytest tests/editing/test_executor.py tests/editing/test_incident_store.py -q
uv run pytest tests/editing tests/approval -q
uv run ruff check src/autocad_mcp/editing tests/editing
```

### E06-WP05: Implement constrained Windows adapter operations

**Owned files:** `src/autocad_mcp/adapter/edit_protocol.py`, `src/autocad_mcp/adapter/edit_provider.py`, `src/autocad_mcp/adapter/windows_edit.py`, `tests/adapter/test_edit_provider.py`, `tests/adapter/test_windows_edit.py`, `tests/integration/windows/test_edit_plans_autocad.py`, `tests/windows/edit_autocad_harness.py`, `tests/windows/run_edit_plans_autocad_2026.ps1`; `tests/windows/drawing_copy_guard.py` is consumed read-only.

**TDD steps:**

1. Add failing provider-contract tests proving `StaticEditAdapterProvider.get()` returns the exact injected additive `EditAutoCADAdapter`, and that `EditPlanExecutor` accepts the provider without downcasting to a Windows or context adapter.
2. Add failing Windows-provider tests proving module import/provider construction does not import COM or construct a session; `edit_provider.py` never imports/names `WindowsSessionManager`; and `windows_edit.py` constructs `WindowsEditAutoCADAdapter` with the exact manager while retaining no application/document/entity proxy.
3. Add fake-COM contract tests for each primitive operation, allowlisted property, capability rejection, locked/xref/proxy rejection, COM exception translation, and exact Undo lifecycle calls.
4. Add an exact-string test for any fixed internal Undo command and prove no request field reaches that string.
5. Implement `EditAutoCADAdapter` as an additive `ContextAutoCADAdapter`, `FakeEditAutoCADAdapter` as an additive context fake, and `WindowsEditAutoCADAdapter` as an additive `WindowsContextAutoCADAdapter` through `WindowsSessionManager`; do not duplicate context reads, COM loading, apartment lifecycle, application attachment, proxy caching, or release branches.
6. Run provider and fake-COM tests on all hosts.
7. Build `edit_autocad_harness.py` as the EPIC-06-owned writable policy over EPIC-03's neutral `drawing_copy_guard.py`; never import/reuse EPIC-03's read-only `autocad_harness.py`. For every case, the neutral guard creates the unique-GUID copy and proves source/copy path inequality/hash equality. The edit harness alone opens that copy writable, verifies `ActiveDocument.FullName`, closes successful cases without saving, rechecks the immutable source, and preserves uncertain/`rollback_failed` copies for human diagnosis.
8. Acquire the EPIC-03 exclusive AutoCAD verification lease before attaching/opening; record owner/epic/work-package/fixture/acquisition/release outcome and fail closed when another live owner holds the same installation/build/session key.

**Exact verification:**

```bash
uv run pytest tests/adapter/test_edit_provider.py tests/adapter/test_windows_edit.py -q
uv run ruff check src/autocad_mcp/adapter/edit_protocol.py src/autocad_mcp/adapter/edit_provider.py src/autocad_mcp/adapter/windows_edit.py tests/adapter/test_edit_provider.py tests/adapter/test_windows_edit.py
```

Windows integration command (the runner accepts a source fixture only, uses EPIC-03's neutral guard, and delegates writable-open policy to EPIC-06's edit harness):

```powershell
uv sync --frozen --group dev
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows/run_edit_plans_autocad_2026.ps1 -SourceDwg C:\autocad-mcp-fixtures\safe-edits-source.dwg
```

### E06-WP06: Register MCP tools and freeze the protocol contract

**Owned files:** `src/autocad_mcp/tools/edit_plans.py`, `tests/contract/test_edit_plan_tools.py`; `core/models.py`, `runtime.py`, `server.py`, `mcp.json`, `test_stdio_server.py`, and `test_server_tool_catalog.py` are reserved to the serialized integration owner.

**TDD steps:**

1. Add failing schema tests for the exact preview/apply inputs, bounded strings and arrays, `additionalProperties: false`, structured errors, operation outcomes, and overall states.
2. Add end-to-end fake-adapter tests for preview, broker confirmation fixture, apply, expired/replayed/wrong-binding token, stale state, rollback success, and `rollback_failed`.
3. Freeze the starting catalog as exactly six read-only tools: EPIC-02 `server_status`, `list_entities`, and `get_entity_info`, plus EPIC-04 `query_entities`, `get_entity_context`, and `analyze_drawing`. Add subprocess/catalog tests for protocol-clean stdout and exact `mcp.json` agreement.
4. Register `preview_edit_plan` and `apply_edit_plan`. If compatibility names are retained, `draw_line` and `draw_circle` are preview-producing shims only: they build one-operation plans and return `PreviewEditPlanResult` without mutation, token issuance, or implicit approval. `extrude_profile` and `revolve_profile` remain unregistered pending a separate 3D primitive/safety review.
5. Implement thin handlers that delegate to the services and never receive `HumanOperatorDecisionSink` or a recovery clear capability.
6. Have the serialized integration owner consume EPIC-04 snapshot/`STALE_SNAPSHOT` codes unchanged, add only `READ_ONLY_DRAWING` and EPIC-06-unique codes, and update `runtime.py`, canonical registration, `mcp.json`, and both canonical catalog/stdio tests together. `runtime.py` must compose one EPIC-04 `SnapshotBuilder`, one complete repository, and one shared `SnapshotBuilderFreshSnapshotReader` injected into preview, executor, rollback/recovery, and downstream readers.

**Exact verification:**

```bash
uv run pytest tests/contract/test_edit_plan_tools.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q
uv run pytest tests/editing tests/approval tests/adapter tests/contract -q
uv run ruff check src tests
uv run mypy src/autocad_mcp/editing src/autocad_mcp/approval src/autocad_mcp/tools/edit_plans.py
```

### E06-WP07: Document, threat-test, and record completion evidence

**Owned files:** `docs/safe-edit-plans.md`; canonical documentation files are reserved to the integration owner.

**TDD steps:**

1. Write operator steps for preview, digest comparison, broker confirmation, apply, normal Undo, rejection, and `rollback_failed` response using a disposable drawing.
2. Add documentation assertions for the plan-tool surface, optional preview-only line/circle compatibility shims, six-tool read-only baseline, broker separation, no token in preview, canonical summary digest, unregistered 3D tools, initial operation allowlist, and exclusions.
3. Run the complete Linux-safe suite and documentation checks.
4. Run the AutoCAD 2026 matrix in the Windows section and attach redacted evidence.
5. Update roadmap/architecture/status only in the implementation pull request and only to the level proven by those results.

**Exact verification:**

```bash
uv run pytest tests/editing tests/approval tests/adapter tests/contract -q
uv run ruff check src tests
uv run mypy src/autocad_mcp
python3 -m compileall -q src tests
python3 -m json.tool mcp.json >/dev/null
git diff --check
```

## Parallel lanes and exclusive ownership

After E06-WP01 publishes its types and digest vectors, these lanes may run in parallel:

| Lane | Work packages | Exclusive files/directories | Must not edit |
| --- | --- | --- | --- |
| E06-A Contracts | E06-WP01 | `src/autocad_mcp/editing/models.py`, `canonical.py`, matching two tests | Broker, executor, server registration |
| E06-B Preview/freshness | E06-WP02 | `validation.py`, `preview.py`, `preview_store.py`, `fresh_snapshot.py`, matching tests | Contract types, broker internals, EPIC-04 builder implementation |
| E06-C Broker | E06-WP03 | `src/autocad_mcp/approval/**`, `tests/approval/**` | MCP handlers and runtime registry |
| E06-D Execution | E06-WP04 and fake portion of WP05 | `executor.py`, `incident_store.py`, `adapter/edit_protocol.py`, `adapter/edit_provider.py`, `adapter/windows_edit.py`, `test_edit_provider.py`, matching tests | Preview and broker files |
| E06-E MCP handlers | E06-WP06 | `tools/edit_plans.py`, `tests/contract/test_edit_plan_tools.py` | Core models, runtime, canonical server/configuration |
| E06-F Evidence/docs | AutoCAD portion of WP05 and E06-WP07 | edit integration test/PowerShell runner, `docs/safe-edit-plans.md`, evidence artifacts | Runtime implementation and EPIC-03 harness |
| Serialized integration owner | Final portion of E06-WP06 | `core/models.py`, `runtime.py`, `server.py`, `mcp.json`, `test_stdio_server.py`, `test_server_tool_catalog.py` | All lane-owned implementation files except reviewed integration calls |

Only the serialized integration owner receives a merge window for shared core models, composition, canonical registration, configuration, catalog/stdio tests, and canonical documentation. That owner merges contract types first, resolves interfaces without copying implementations, runs all affected suites, and rejects a lane that changed another lane's files without an explicit handoff.

## Acceptance criteria

- A valid preview is demonstrably read-only and returns `preview_id`, `plan_digest`, canonical `human_summary_digest`, expiry, source identity, ordered effects, and warnings without an approval token.
- The broker is a separate authenticated local process with current-user-SID named-pipe ACL, remote-client rejection, inherited-handle secret provisioning, verifier-only methods, and no MCP/model-callable decision path.
- The named **AutoCAD MCP Human Approval** UI records one real human Confirm and Reject action with bound evidence; automated fixtures cannot satisfy the human-authority gate.
- Broker unavailability or authentication failure prevents approval registration and all application.
- A token is issued only after explicit human confirmation, expires 120 seconds after issuance, is single-use under concurrency, is stored as a digest, and is bound server-side to document, session, snapshot ID/fingerprint, preview ID, plan digest, and human-summary digest.
- A recognized token is consumed on the first apply attempt; expiry, cancellation, rejection, stale state, success, failure, session/document close, and preview supersession invalidate the applicable grant/preview.
- All mandatory preflight checks pass before the Undo group begins; every listed failure produces no drawing mutation.
- Preview, apply preflight, success readback, rollback verification, incident recovery, and downstream freshness all use the same runtime-shared wrapper over EPIC-04 `SnapshotBuilder`; no edit code reimplements enumeration or fingerprinting.
- Broker registration/rendering/decision/receipt and apply preflight agree on canonical summary bytes/digest; receipt digest mismatch rejects before Undo.
- Preview/preflight and `EditPlanExecutor` obtain the edit extension only through `EditAdapterProvider.get() -> EditAutoCADAdapter`; they never downcast the EPIC-03 base provider/adapter or import a Windows implementation.
- `EditAutoCADAdapter` extends `ContextAutoCADAdapter`; `WindowsEditAutoCADAdapter` extends `WindowsContextAutoCADAdapter`; the static and Windows providers expose no COM/session/proxy object across the adapter boundary.
- Supported operations execute in one Undo group and report one outcome per operation in original order.
- First operation failure stops execution, invokes Undo rollback once, and verifies the restored fingerprint.
- `failed_rolled_back` is returned only after fingerprint equality. Any uncertainty atomically persists a `rollback_failed` record before responding and blocks further edits for that persistent document identity across MCP, broker, AutoCAD, and session restarts.
- An incident lock clears only through **AutoCAD MCP Human Recovery** after acknowledgement and an exact complete fresh safe snapshot; MCP, model output, restart, session change, and expiry cannot clear it.
- The starting catalog contains exactly six read-only tools: EPIC-02 `server_status`, `list_entities`, and `get_entity_info`, plus EPIC-04 `query_entities`, `get_entity_context`, and `analyze_drawing`, with no active mutation tool. `draw_line`/`draw_circle`, if reintroduced, return preview only; `extrude_profile`/`revolve_profile` remain unregistered.
- Deletion and architectural semantic operation kinds are rejected by parser, validator, adapter, and MCP contract tests.
- Arbitrary execution and caller-controlled `SendCommand` input are absent from schemas and code paths.
- Pure modules import and test without Windows COM. Linux results are not described as AutoCAD verification.
- Real AutoCAD 2026 evidence covers success, stale preflight rejection, expiry/replay, injected mid-plan failure with restored fingerprint, and induced rollback uncertainty with an edit lock.

## Windows and AutoCAD verification

Use full AutoCAD 2026 on the recorded Windows release and a fresh disposable copy of a purpose-built DWG. Record AutoCAD product/build, Windows release, Python version, lockfile digest, fixture digest, broker build, exact command, start/end fingerprints, Undo outcomes, modal dialogs, and manual interaction.

Before every real command, acquire the EPIC-03 exclusive verification lease keyed by AutoCAD installation/build and Windows interactive-session ID. An unleased run, concurrent live owner, or unrecorded lease release cannot satisfy this epic.

The real matrix must include:

1. One plan containing each supported primitive against supported entities.
2. A preview followed by a manual drawing change; apply must reject stale state before an Undo mark.
3. Token expiry, token replay, a token from another document, and a token from another AutoCAD session.
4. Read-only drawing, locked layer, xref/proxy target, missing handle, and unsupported capability.
5. Failure injected after at least two successful operations; Undo must restore the exact baseline fingerprint and return `failed_rolled_back`.
6. A controlled rollback failure or fingerprint mismatch on a disposable copy; result must be `rollback_failed`, and subsequent preview/apply attempts remain blocked after separate MCP, broker, and AutoCAD restarts and a changed session ID.
7. Successful apply followed by ordinary user Undo, proving the group remains usable.
8. Broker stopped, wrong SID, remote pipe client, bad/replayed HMAC, and missing inherited secret; no token can be issued or consumed and no mutation occurs.
9. Import and construct `WindowsEditAdapterProvider` with COM modules unavailable, then use the real EPIC-03 `WindowsSessionManager` on Windows and prove all application/document/entity proxies remain inside the manager callback lifetime.
10. For every case, use EPIC-03's neutral `drawing_copy_guard.py` through EPIC-06-owned `edit_autocad_harness.py`; never use the read-only harness. Assert source/copy inequality/hash equality and `ActiveDocument.FullName`, keep the source immutable, close successful copies without saving, and preserve uncertain rollback copies.
11. Record exclusive verification-lease acquisition/release output; fail closed while a live owner holds the same AutoCAD installation/build/session key.

Run the Windows command from E06-WP05. Store JUnit XML and a redacted Markdown run record under the pull request's evidence convention; never commit raw DWGs, tokens, user paths, or proprietary drawing content.

AutoCAD 2021-2025 remain `Targeted, not verified` until this same matrix passes on each real installation. Capability differences are recorded from observed runs, not encoded speculatively by release number.

## Safety and security gates

- **Human authority:** Conversation text, model output, MCP arguments, environment variables, and preview rationale cannot represent approval. Only the broker's explicit human Confirm action can issue a grant.
- **Least capability:** MCP receives `ApprovalVerifier`, never `HumanOperatorDecisionSink` or incident-clear capability. The broker pipe has no decision method and no remote listener.
- **Adapter isolation:** Editing services receive only `EditAdapterProvider`; `WindowsEditAutoCADAdapter` uses EPIC-03's adapter-internal `WindowsSessionManager`, and application/document/entity COM proxies never enter provider results, domain models, operation outcomes, or logs.
- **Binding and replay:** All seven binding fields, including `human_summary_digest`, are checked server-side; token comparison is constant-time; consumption is atomic; raw tokens are never persisted or logged.
- **Fail closed:** Missing broker, inherited-secret/ACL/peer-auth failure, incident-store load/write/integrity error, clock uncertainty, digest mismatch, unsupported capability, COM uncertainty, and fingerprint failure reject or lock editing.
- **Input safety:** Exact schemas reject additional fields, executable strings, non-finite numbers, excessive payloads, invalid handles, and unallowlisted entity/property combinations.
- **Drawing safety:** Preflight is complete before mutation, deletion is unavailable, xrefs/locked/proxy targets are rejected, and development/integration uses disposable copies.
- **Recovery honesty:** Undo is never called transactional. Fingerprint equality is required before rollback is described as successful.
- **Privacy:** Human summaries contain only facts required for approval; logs redact tokens, paths, entity values, and drawing content.
- **Protocol integrity:** Normal logs use stderr or structured results; stdout remains MCP protocol only.

No safety gate may be waived to make a test pass. A required capability that cannot be observed on AutoCAD 2026 returns a structured unsupported result and keeps the corresponding operation unavailable.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The model calls an approval endpoint indirectly | Named human UI calls a direct sink; named pipe exposes verifier methods only; catalog/IPC tests reject decision methods |
| A token is replayed or moved across drawings | High-entropy token, digest-only storage, atomic consume, short TTL, and complete server-side binding |
| Preview differs from what the broker displays | Store canonical plan/summary once, include digest in UI, and compare a recomputed live preview before Undo starts |
| Drawing changes between preview and apply | Bind snapshot fingerprint and expected entity state; recalculate immediately before mutation; consume the token even on stale rejection |
| Undo does not fully restore state | Verify the fingerprint; return `rollback_failed` and lock edits on any mismatch or uncertainty |
| COM reports success before state is durable | Read back operation state and compute fingerprints through the adapter before declaring success |
| Fixed AutoCAD Undo command becomes locale/version sensitive | Prefer COM APIs; if a fixed command is unavoidable, use an internal non-interpolated global form, capability-test it, and verify each release |
| A long plan makes human review ineffective | Cap at 100 operations and present ordered concise effects, changed handles, warnings, digest, and expiry |
| Broker crashes after issuance or consumption | Persist only binding/token digest/state with atomic updates; treat uncertain consume as invalid and require a new preview/approval |
| Incident lock disappears on restart or is cleared by the model | DPAPI/current-user ACL atomic store, startup reload, restart/session tests, and recovery-UI-only clear with a fresh matching snapshot |
| The edit adapter creates a second COM lifecycle or leaks proxies | Require `WindowsEditAutoCADAdapter(WindowsSessionManager)`, local-import Windows provider tests, and no-proxy assertions at every provider/operation boundary |

## Rollback

### Runtime drawing rollback

The executor follows the mutation and rollback sequence above. A failed fingerprint verification is not retried and is never relabelled as successful. The operator retains the disposable original, inspects AutoCAD's Undo/recovery state, and captures a new snapshot only after the drawing is known safe.

### Feature rollback

If post-merge evidence reveals an unsafe path, remove `preview_edit_plan`, `apply_edit_plan`, and any preview-only compatibility shims from canonical registration together, stop the broker, preserve the six read-only EPIC-02/04 tools, retain incident-lock state, and mark the roadmap stage in progress. Do not leave a mutating claim advertised when apply is disabled; diagnostic preview requires an explicit reviewed contract.

Approval ledger migrations must be backward-rejecting: a newer broker may invalidate old pending previews, but it must never accept an unknown schema version. Disabling the feature invalidates all outstanding previews and grants.

## Completion evidence

The implementation pull request must attach or link all of the following:

- focused red/green TDD output for each work package;
- complete `tests/editing`, `tests/approval`, adapter, and `tests/contract` results;
- lint, type-check, compile, JSON, and diff-check output;
- `test_server_tool_catalog.py`/`test_stdio_server.py` evidence for the six-tool read-only baseline, plan tools, any preview-only line/circle shims, and no approval/recovery/3D tool;
- exact `ErrorCode` addition and `ToolError` serialization evidence;
- published canonical digest vectors;
- canonical `HumanSummary` bytes/digest vectors, tamper tests, and identical binding/evidence/grant/receipt/apply digests;
- concurrency evidence for single-use consumption;
- current-user SID pipe ACL/peer verification, remote rejection, inherited-handle secret, HMAC replay, and no-decision-IPC evidence;
- real named-operator Confirm and Reject records from **AutoCAD MCP Human Approval**; automated fixture evidence is insufficient;
- provider-contract evidence for static injection, delayed Windows composition, the exact `WindowsSessionManager` handoff, and no COM-proxy escape;
- shared `SnapshotBuilderFreshSnapshotReader` call evidence for preview/preflight/success/rollback/recovery and proof no edit-local fingerprint implementation exists;
- redacted logs proving no raw token or drawing content leakage;
- the AutoCAD 2026 run record and JUnit XML for every matrix item;
- per-case neutral-guard plus EPIC-06 writable-harness evidence: source/copy resolved paths differ, initial hashes match, only the copy opens writable, active `FullName` is the copy, source remains immutable, successful close-without-save/source rehash passes, and uncertain rollback copy is preserved;
- EPIC-03 exclusive verification-lease acquisition/release evidence for every real run;
- before, after, and restored fingerprints for success and injected failure;
- the induced `rollback_failed` result, atomic incident record, MCP/broker/AutoCAD restart and session-change blocks, fail-closed corrupt-store results, and recovery-UI/fresh-snapshot clear evidence;
- exact AutoCAD/Windows/Python/lockfile/fixture/broker versions;
- a statement that AutoCAD 2021-2025 remain targeted unless separately tested; and
- documentation/roadmap diffs whose claims match only the recorded evidence.

Code presence, fake-adapter results, Linux tests, or a manually observed successful edit alone cannot close this epic.

## Handoff

Before implementation, the epic owner freezes the consumed snapshot/error interfaces and the EPIC-03 `WindowsSessionManager` constructor, session callback/lifetime rules, thread confinement, capability surface, and no-proxy-escape invariant with their owners. E06-D then freezes the additive `EditAutoCADAdapter`, `EditAdapterProvider`, `StaticEditAdapterProvider`, and `WindowsEditAdapterProvider` together so executor and provider implementations cannot diverge. Each lane hands off its public signatures, digest/test vectors, exact commands/results, known limitations, and changed-file list. The serialized integration owner verifies production composition injects `WindowsEditAdapterProvider`, tests inject `StaticEditAdapterProvider`, startup reloads `WindowsIncidentLockStore`, and the exact core/catalog/configuration set changes atomically; that owner rejects hidden cross-lane edits and performs the only changes to shared server/configuration/canonical documentation files.

After all automated gates pass, a Windows operator performs the AutoCAD 2026 matrix on disposable copies. The epic can move from **Planned** to **Delivered for AutoCAD 2026** only when the pull request contains the completion evidence and a reviewer independently confirms the provider/session-manager boundary, no COM-proxy escape, broker separation, token lifecycle, preflight order, and rollback-fingerprint behavior. Release verification labels are updated individually; this handoff never promotes untested AutoCAD releases.

Related target documents: [architecture](../architecture.md), [roadmap](../roadmap.md), [testing](../testing.md), [compatibility](../compatibility.md), and the [approved modernization design](../superpowers/specs/2026-08-25-maintenance-and-modernization-design.md).
