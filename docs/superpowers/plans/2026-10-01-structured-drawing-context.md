# Structured Drawing Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete agent-owned EPIC-04 delivery, with real AutoCAD execution handed to the user after the remaining portfolio is built.

**Architecture:** Add immutable drawing facts and a separate context adapter extension to the existing read-only core. Build complete revision-checked snapshots before storing or paging them. Compose one repository for subsequent capture, edit, and semantic services.

**Tech Stack:** Existing Python 3.12, stdlib dataclasses/hashlib/hmac/json, locked MCP SDK, pytest, Windows COM behind the existing session manager.

**Spec:** `docs/epics/EPIC-04-structured-drawing-context.md`; `docs/superpowers/specs/2026-08-25-maintenance-and-modernization-design.md`.

## Global Constraints

- Implement the exact version `1.0` domain/adapter interfaces and limits in EPIC-04. No new dependency.
- Preserve EPIC-03's four-method base protocol. Context is an additive protocol; only its Windows implementation consumes COM sessions.
- No mutation, capture, or analysis at startup. No raw paths, token values, exception strings, or proprietary text in logs.
- Only complete revision-checked snapshots enter the repository; query pages never become drawing fingerprints.
- Limits: 500 entities per adapter/page, 10,000 per complete snapshot, 32 MiB complete object, 4 MiB MCP result, 256 KiB entity, 100,000 complete relationships, 4 snapshots/128 MiB/600 seconds.
- AutoCAD tests are prepared but not executed here. Their acceptance stays pending. All portable implementation and tests proceed under the user's explicit scheduling instruction.
- Implementers own only their task paths, commit tested changes, and do not dispatch other agents. Contract and quality review precede subsequent integration.

## Review Focus

1. A COM member fails midway: preserve an explicit capability issue or fail the required read; never silently omit facts.
2. Saved document reopened with different object IDs: stable content identity; session correlations remain separate.
3. Mutation/document switch during a multi-page read: no partial snapshot, reference, or repository insertion.
4. Oversized single entity/Unicode text/nested mappings: enforce real encoded-byte bounds and immutable retained facts.
5. Cursor replay/tampering/expiry plus live drawing change: reject with distinct structured errors before returning misleading pages.

### Task 1: Freeze the complete domain contract (CTX-01)

**Files:** Create `src/autocad_mcp/context/{__init__,models,validation,serialization}.py`; `tests/unit/context/test_models.py`, `tests/unit/context/test_serialization.py` and a local test fixture helper only if shared by both files.

**Interfaces:** Produce every frozen/slotted dataclass/type alias in the spec's Exact Python data contract, from `Point2D` through `AnalyzeDrawingResult`, with the exact field names/types. Also implement the explicitly described `EntitySummary` subset and `EntityContextBatch`. Export `snapshot_to_json`, `snapshot_from_json`, `analyze_result_to_json`; strict reusable validation and serialization for these records. Do not invent adapter records or wire requests owned by later tasks.

- [x] Read the exact data-contract, evidence, bounds, and CTX-01 sections; inspect existing core model conventions.
- [x] Write failing behavior tests for unknown version/field rejection, bool-vs-number and finite/1e15 bounds, inverted bounds, normalized handles, deep immutability, interpretation confirmation/evidence rules, 10,000 vs 10,001 vertices, 256 KiB entity limit, timezone-aware UTC millisecond serialization, and exact round-trip.
- [x] Run `.venv/bin/python -m pytest tests/unit/context/test_models.py tests/unit/context/test_serialization.py -q`; record expected missing implementation failure.
- [x] Implement the minimum complete contract. Frozen dataclasses must not retain mutable mappings/lists from callers. Non-finite numbers and unknown fields are rejected, not coerced or silently dropped. Use strict dataclass decoding rather than a new validation dependency. Keep fingerprint computation out of this task.
- [x] Run focused tests, the full existing suite, scoped Ruff, and mypy on new source. Record exact output and any remaining limitations.
- [x] Commit as `feat: add immutable drawing context contract` and report exact public helpers/constructors for downstream tasks.

### Task 2: Identity, canonical fingerprints, signed cursors (CTX-02)

**Files:** `context/identity.py`, `context/fingerprint.py`, `context/pagination.py`; corresponding tests.

**Interfaces:** Exact identity/digest functions and `CursorCodec` from spec, plus these frozen helper contracts:

```python
# pagination.py: shared clock re-exported by repository.py in Task 3
class Clock(Protocol):
    def now(self) -> datetime: ...
class SystemClock:
    def now(self) -> datetime: ...  # aware UTC

@dataclass(frozen=True, slots=True)
class PageCursor:
    kind: Literal["snapshot", "live_query"]
    document_id: str
    session_id: str
    filter_digest: str
    page_size: int
    last_sort_key: tuple[int, str, int, str] | None
    issued_at: datetime
    expires_at: datetime
    snapshot_id: str | None = None
    revision_token_digest: str | None = None
    adapter_cursor: str | None = None

class CursorCodec:
    def __init__(self, *, clock: Clock, secret: bytes) -> None: ...
    def encode(self, cursor: PageCursor) -> str: ...
    def decode(self, value: str) -> PageCursor: ...

def entity_sort_key(entity: EntityContext) -> tuple[int, str, int, str]: ...
def normalize_filters(filters: EntityQueryFilters) -> EntityQueryFilters: ...
def filter_digest(filters: EntityQueryFilters, include: Mapping[str, bool]) -> str: ...
# fingerprint.py
def canonical_bytes(value: object) -> bytes: ...
def entity_state_digest(entity: EntityContext) -> str: ...
def snapshot_id(document: DocumentIdentity, fingerprint: DrawingFingerprint) -> str: ...
def snapshot_identity_bytes(snapshot: DrawingSnapshot) -> bytes: ...
```

`identity.py` normalizes handles by re-exporting the existing validated helper.
Its `build_document_identity` consumes the specified pure adapter identity by
structural attributes until Task 4 creates `context_protocol.py`; use a local
typing protocol (no Windows import or duplicate runtime record). A saved path
must be an absolute Windows drive/UNC path, normalize extended-path prefixes,
separators, dot segments, NFC and case folding, and never return/log the raw
path. Normalize GUIDs with `uuid.UUID`. An unsaved identity requires the adapter's
UUID; it is not synthesized from a proxy or ObjectID. Tests use a small
`SimpleNamespace` fixture matching the frozen adapter fields.

Snapshot cursors require a snapshot ID and no live revision/adapter cursor;
live cursors require a revision digest and no snapshot ID. Require a secret of
at least 32 bytes. Bound cursor UTF-8 to 2,048 bytes, reject unknown fields,
invalid base64/signature/shape as `INVALID_CURSOR`, and expire at `now >= expires_at`
as `CURSOR_EXPIRED`. Issued/expiry times are aware UTC; lifetime is positive and
at most 600 seconds for snapshot cursors or 900 for live cursors. The service
later bounds snapshot expiry to the repository insertion expiry. Decode never
queries AutoCAD/repository; service owns distinct `STALE_CURSOR`/repository
errors on comparing the decoded binding to current state.

`canonical_bytes` emits NFC strings/keys, sorted object keys, compact UTF-8 JSON,
finite float tokens using `.17g` (negative zero is `0`), and rejects normalization
key collisions. Boolean tokens remain booleans. Filter normalization sorts and
deduplicates equivalent set-like selectors; layer globs support only literal
characters, `*` and `?` when later matched. Canonical filter/include digests
preserve case-sensitive layer matching and do not include page size (cursor
binds it separately). Fingerprint and snapshot identity exclusions follow the
epic exactly; `snapshot_identity_bytes` excludes captured time and revision but
retains complete normalized observed facts using the same identity exclusions
as the content/presentation fingerprint (including ObjectID and session IDs),
so a forged same-ID different fact object can be rejected by the repository.

- [ ] Add failing identity/privacy/NFC/handle, complete-set digest invariance, content vs presentation, signed cursor tamper/expiry/context-binding tests from CTX-02. Include Windows path case/slash/prefix equivalence; GUID precedence; unsaved session changes; schema/session/ObjectID/pagination exclusion; duplicate NFC object keys; nested entity fact changes; cursor kind mixing, 2,048-byte boundary, overlong/unknown fields, future issue time and exact expiry.
- [ ] Implement numeric canonicalization, stable entity order and snapshot IDs; no page-derived fingerprints.
- [ ] Verify focused tests and stable digests over shuffled inputs, then commit.

### Task 3: Complete snapshot repository (CTX-02R)

**Files:** `context/repository.py`, `tests/unit/context/test_repository.py`.

**Interfaces:** `Clock.now()`, `SnapshotRepository`, `SnapshotRepositoryError`, `InMemorySnapshotRepository` exactly as specified. Canonical-byte storage, defensive reconstruction, original-expiry idempotency.

- [ ] Test and implement complete-only insertion, matching counts/bytes, same-ID collisions, immutable reads, exact TTL/count/byte limits and bounded expiry tombstones.
- [ ] Verify focused tests and typing; commit.

### Task 4: Additive context adapters and fact mapping (CTX-03)

**Files:** The CTX-C paths enumerated by the spec, including `context_protocol.py`, `fake_context.py`, `windows_context.py`, `context/adapter_reader.py`, their tests, and raw entity fixture.

**Interfaces:** Exact pure records, `ContextAutoCADAdapter`, provider interfaces, and mapper functions from the spec. Keep the base protocol unchanged. Freeze a trustworthy covered-facts revision-token strategy before coding.

- [ ] Test pure protocol/fake bounds and injected Windows-session extraction, revision consistency, required/optional failures and cleanup before implementation.
- [ ] Implement WCS conversion and geometry/layer/style/block/text/dimension/context reads with no proxy escape; use only the existing session lifecycle.
- [ ] Verify adapter/mapper tests, import isolation, type checks; commit the frozen extension.

### Task 5: Complete builder, relationships, and services (CTX-04)

**Files:** `context/relationships.py`, `context/builder.py`, `context/service.py`, corresponding tests.

**Interfaces:** Freeze `RelationshipOptions`, `CompleteSnapshotRequest`, the three service request/result types in the task brief; implement exact `SnapshotBuilder`/`DrawingContextService` signatures from the epic.

- [ ] Test 0/1/500/501/10,000 entities, all revision/document/context/partial/duplicate/cursor failures, exact limits, and zero repository insertion on any failed build.
- [ ] Implement bounded deterministic spatial candidates and relationships; complete build/store precedes analyze filtering, while live reads never populate the repository.
- [ ] Test filters, include projection, payload-driven pagination, live/snapshot cursor continuations and expiry; verify and commit.

### Task 6: Fixtures, tools, catalog integration (CTX-05/06)

**Files:** Golden snapshot/page/DXF fixtures; `tools/context_tools.py`, `core/models.py`, `runtime.py`, `server.py`, `mcp.json`, context/catalog/stdio contracts and existing affected tests.

**Interfaces:** Preserve existing `BasicToolService`. Add one `ContextToolService` using existing envelopes and one singleton repository. Register three additional tools exactly as specified.

- [ ] Add failing golden fixture, structured-error, complete-reference, no-COM-import and actual stdio tests.
- [ ] Add owned error codes exactly once, validate requests before service calls, integrate tools/resources/help/manifest consistently.
- [ ] Verify complete portable suite, catalog agreement, active lint/type/compile/import checks; commit.

### Task 7: Windows runner and operator handoff (CTX-07 portable work)

**Files:** Windows integration test and PowerShell runner, DXF fixture, contract documentation, testing/compatibility/status/roadmap updates.

- [ ] Test runner/lease/cleanup/failure paths without a real COM installation; generate the deterministic fixture.
- [ ] Prepare exact disposable-DWG assertions and redacted evidence for repeated reads, zoom-only presentation change, restoration, paging and unchanged source.
- [ ] Publish commands and honest evidence labels. Do not create a passing `context-autocad-2026.md` report without operator results.
- [ ] Update portfolio/epic work-package evidence; run portable completion commands and independent full diff review.
- [ ] Open focused EPIC-04 PR and retain real-installation acceptance as pending; continue to the next agent-owned portfolio task.
