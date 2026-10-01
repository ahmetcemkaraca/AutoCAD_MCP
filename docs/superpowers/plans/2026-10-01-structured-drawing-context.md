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
    last_handle: str | None
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

- [x] Add failing identity/privacy/NFC/handle, complete-set digest invariance, content vs presentation, signed cursor tamper/expiry/context-binding tests from CTX-02. Include Windows path case/slash/prefix equivalence; GUID precedence; unsaved session changes; schema/session/ObjectID/pagination exclusion; duplicate NFC object keys; nested entity fact changes; cursor kind mixing, 2,048-byte boundary, overlong/unknown fields, future issue time and exact expiry.
- [x] Implement numeric canonicalization, stable entity order and snapshot IDs; no page-derived fingerprints.
- [x] Verify focused tests and stable digests over shuffled inputs, then commit.

### Task 3: Complete snapshot repository (CTX-02R)

**Files:** `context/repository.py`, `tests/unit/context/test_repository.py`.

**Interfaces:** `Clock.now()`, `SnapshotRepository`, `SnapshotRepositoryError`, `InMemorySnapshotRepository` exactly as specified. Canonical-byte storage, defensive reconstruction, original-expiry idempotency.

Re-export the accepted `Clock` from `pagination.py` instead of defining another
clock interface. Add `expires_at(snapshot_id: str, *, session_id: str | None = None) -> datetime` to the repository
protocol and implementation so signed continuation cursors can bind the actual
retained insertion expiry. It performs the same purge/not-found/expired checks
as `get_complete`; it neither extends TTL nor returns drawing facts. This is a
necessary internal metadata accessor, not a new MCP tool or wire field.

Snapshot storage uses the accepted deterministic `record_to_json` UTF-8 encoding
to preserve exact record values; identity comparison uses the separate
`snapshot_identity_bytes` fact normalization. Compute `canonical_byte_count`
with just that count field omitted, and check actual full stored bytes too.
Store only serialized payloads and expiry metadata; do not retain duplicate
full identity-byte blobs outside the total-byte budget. On same-ID insertion,
compare normalized identity bytes reconstructed from the retained payload.

Validate complete markers, schema/type, reference/document/session/fingerprint
agreement, non-required issues, duplicate handles, and exact entity/relationship/
byte counts before admitting a record. Preserve the epic's distinct error codes
for invalid/incomplete, limits, identity collision, expired and not found. A
valid repeated identity in the same session retains the original payload and
expiry, including diagnostic data; it is not a freshness refresh.

[Decision 0003](../../decisions/0003-session-qualified-snapshot-retention.md)
amends ID-only retention: key records and tombstones by `(snapshot_id, session_id)`.
Both `get_complete` and `expires_at` accept optional keyword `session_id`.
Qualified lookup never falls back to another session; unqualified lookup only
succeeds for one live match, otherwise multiple live matches return
`SNAPSHOT_ID_COLLISION`. Compare normalized facts across every live same-ID
record before admission. A new session with equal facts retains a separate
payload/expiry and counts separately toward all limits. All consumers with a
reference/cursor pass its session. Test changed ObjectIDs after reopen, old and
new retained payloads, independent TTL, ambiguity, cross-session collisions,
pair-qualified tombstones and shared capacity. This corrects the previous
literal plan; it is not an implementation defect in commit `8166e57`.

Constructor tuning may lower but never raise the published limits. Reject bools,
non-positive sizes/TTLs and over-ceiling values. Serialize operations with one
stdlib lock because runtime services can call the singleton from worker threads;
test competing insertions cannot exceed four live records or total bytes.
Tombstone expiry is the original record expiry plus its configured tombstone
TTL, not the time a late caller notices expiration. Purge before every operation;
retain at most eight most-recent expiry markers, never evict a live snapshot.

- [x] Test and implement complete-only insertion, matching counts/bytes, same-ID collisions, immutable reads, exact TTL/count/byte limits and bounded expiry tombstones. Include concurrent final-slot insertion, idempotency without expiry refresh, expired lookup after a long idle interval, expiry accessor behavior, preserved raw Unicode values with normalized identity equality, and unchanged original metadata on idempotent reinsert.
- [x] Verify focused tests and typing; commit.

### Task 3B: Correct owner-frame coordinate contract before adapters

**Files:** context models/validation and affected strict-codec/fingerprint tests,
shared fixtures and canonical epic examples. No adapter/service implementation.

**Contract:** [Decision 0005](../../decisions/0005-owner-scoped-entity-coordinates.md)
replaces entity-only WCS field names with owner-frame-neutral names. Existing
`EntitySpace` supplies the discriminator; do not add redundant frame metadata.
Enforce paper layout and block owner constraints; retain document view/UCS WCS
names and explicitly WCS query bounds. This is an unreleased version-1 contract
correction. Keep stable identity exclusions, session retention and byte limits.

- [x] Add red regressions for owner-space invariants, renamed exact serialized
  fields/JSON pointers, rejection of obsolete keys, frame-dependent identity,
  and unchanged document WCS semantics. Update existing affected fixtures/tests.
- [x] Implement the minimal model/validation changes, update downstream epic
  field examples, run context/full portable tests plus lint/types, commit and
  independently review before Task4. Spatial filter/relation behavior is owned
  by Task4/5 and must consume these exact owner-frame rules.

### Task 3C: Projection guards and bounded continuation identity

**Files:** context models/validation/fingerprint/pagination and focused tests;
no adapter/service/registry implementation. Execute this bounded prerequisite
inline, then obtain a fresh independent review before consumers are implemented.

**Spec:** decisions0006 and0007. Nullable projected geometry needs the explicit
geometry NOT_REQUESTED marker. Complete models/repository/digest helpers refuse
projected entities, while response records preserve their complete source digest.
Replace private PageCursor.last_sort_key with normalized last_handle. Keep
canonical entity_sort_key, all other cursor bindings, HMAC/expiry and2,048 bytes.

- [ ] Add red tests for projection roundtrip/marker validation, full-model and
  entity/drawing/repository refusal, including omitted nongeometry groups; valid
  complete entities still hash/store unchanged. Add maximum-handle and Unicode
  layout/nested-live cursor checks, invalid handles and obsolete field rejection.
- [ ] Implement the minimum shared completeness guard and cursor field change;
  update affected old cursor tests to the unreleased contract without weakening
  signature, time or byte-boundary checks. No compression/cache or partial digest.
- [ ] Run focused changed tests (expect pass), the context/full suites, scoped
  lint/types/syntax/import checks. Record commands/results and commit. Independent
  review is required; Task4/5 must consume these exact guards and boundary rules.

### Task 4: Additive context adapters and fact mapping (CTX-03)

Execute as two reviewable pieces:4A owns pure context_protocol/fake_context/
adapter_reader, pure exports and their fixture/tests;4B owns Windows extraction,
injected session/native witness tests and delayed provider integration.4B
consumes the accepted4A records and native observer contracts; it does not
replace either. Keep the overall CTX-03 gate incomplete until both pass.

Canonical services request full adapter coverage. The fake and Windows adapter
may return full facts for smaller internal include sets, as decision0006 allows;
only public services project responses. A mapper refuses raw NOT_REQUESTED
omissions before generating state_digest. This avoids inventing a nullable raw
geometry or an unsupported-geometry claim for an unrequested group.


**Files:** The CTX-C paths enumerated by the spec, including `context_protocol.py`, `fake_context.py`, `windows_context.py`, `context/adapter_reader.py`, their tests, and raw entity fixture.

**Interfaces:** Exact pure records, `ContextAutoCADAdapter`, provider interfaces, and mapper functions from the spec. Keep the base protocol unchanged. Use the separate native-context-observer prerequisite for trustworthy lifetime/revision witnesses. Read the recorded Task4 preflight report and implement every supported mapping; observer loss fails closed. Add the missing `layer_globs` tuple to `AdapterEntityReadRequest` so public glob filtering happens before paging.

Consume the accepted pre-release model/fingerprint guards from Task3C and
[decision 0006](../../decisions/0006-context-include-projection.md): nullable
projected geometry requires its explicit NOT_REQUESTED issue; complete snapshots,
entity/drawing digest helpers and repository admission reject projected records.
The mapper produces a complete entity digest from full raw coverage only. Task5
owns public response projection and requests all-true adapter includes first,
preserving complete source identity for every public include combination.
Never derive a partial-data digest. Use decision0007's handle-bound cursors;
resolve actual canonical order after binding/revision checks.

- [ ] Test pure protocol/fake bounds and injected Windows-session extraction, revision consistency, required/optional failures and cleanup before implementation.
- [ ] Implement OCS-to-owner-frame conversion and geometry/layer/style/block/text/dimension/context reads with no proxy escape; use only the existing session lifecycle.
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
