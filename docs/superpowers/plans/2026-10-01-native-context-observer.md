# Native Context Observer Implementation Plan

> Use superpowers:subagent-driven-development task by task. Real AutoCAD tests
> are prepared now and run by the user after the portfolio implementation.

**Goal:** Provide trustworthy document-lifetime and covered-change witnesses
to the existing COM adapter, without extracting facts or granting mutation.

**Spec:** [Decision 0004](../../decisions/0004-native-context-revision-observer.md)
and EPIC-04's revision/session guarantees. This prerequisite is separate from
the context domain implementation and has no MCP registration changes.

## Global Constraints

- Keep source, docs, commits and fixed diagnostics in English.
- No arbitrary execution, AutoCAD commands, drawing writes or property setters.
- SDK access only on the host UI thread; pipe workers consume pure copied data.
- No raw exceptions, paths, drawing text, identifiers or tokens in logs.
- Actual pinned Autodesk references are required for compilation, never stubs.
- Package project output only; Autodesk references are build-time-only.
- Bounds: 128 observed open documents, four pending requests, 4 KiB request,
  8 KiB response, two-second total request timeout, one request per connection.
- A positive epoch never wraps or decreases within a bridge incarnation.
  Overflow, observer loss, unknown readiness or registry overflow fail closed.
- No AutoCAD verification claim follows from fake-host, compile or pipe tests.

## Exact private protocol

Use length-prefixed UTF-8 JSON: four-byte unsigned little-endian payload length
followed by exactly that many bytes. Reject zero/oversized lengths before
allocation, invalid UTF-8/JSON, duplicate/unknown keys and non-integral/bool IDs.
The one request is exactly:

```json
{"version":1,"operation":"read_state","nonce":"64-lowercase-hex","client_pid":1234,"document_hwnd":"0000000000001234"}
```

The window field is 16 lowercase hexadecimal digits representing an unsigned
nonzero 64-bit handle. A response echoes version/nonce and has either `error`
from the fixed set `UNAVAILABLE`, `BUSY`, `INVALID_REQUEST`, `TIMEOUT`,
`UNTRUSTED_PEER`, or `state` with exactly `bridge_id`, `session_id` (canonical
UUID strings), `epoch` (canonical positive decimal ASCII string in
`1..2**64-1`, without leading zeroes),
`database_guid` (canonical UUID or null), `ready` (true), `coverage`
(literal `context-facts-v1`). No paths, names, facts, arbitrary capability text,
timestamps or raw HWNDs are returned. Error/state are exclusive. Only a ready
trusted witness succeeds; readiness is not caller-controlled. `client_pid` is
an integer in `1..2**32-1`, never a Boolean or floating JSON number. Replay
protection uses a fresh random client nonce and exact response matching on each
single-request connection; this read-only protocol needs no server nonce cache.

Pipe name: `autocad-mcp-context-v1-{pid}-{creation_filetime:016x}`. Python derives
the expected process from the COM document HWND via Win32 and queries its
creation time, SID and Windows session; it authenticates the connected pipe's
kernel-reported server PID and rechecks process creation time. Server uses a
protected current-user DACL, first-instance creation and remote-client
rejection; kernel-reported client PID must match the claim, current SID and
interactive session. A nonce is freshly random per connection and the client
accepts one matching response only. Kernel pipe identity, not the pipe name or
JSON claim, establishes the peer. Cancellation/shutdown closes handles and
removes queued work; no abandoned request executes later.

## Task 1: Pure witness state and strict protocol

**Files:** `native/context-observer/` minimal projects/core source and
`native/context-observer/tests/` executable stdlib assertion runner; shared
wire vectors under `tests/fixtures/native-context/`; Python pure protocol in
`src/autocad_mcp/adapter/native_revision.py` plus focused unit tests.

Use C#/.NET BCL only for native production code, existing Python pytest for
Python checks. A console assertion runner needs no new test framework. Link
pure source into a net10.0 test executable rather than loading Autodesk SDK
assemblies on Linux. No native host/Windows transport implementation yet.
Keep production pure source compatible with net48, net8.0 and net10.0 so the
observer preserves the existing 2021-2026 target range. Do not accidentally
require a new runtime JSON dependency on older hosts. A strict bounded reader
using the common BCL JSON reader APIs is preferable to a custom general parser;
fixed validated ASCII response fields also need no general serializer framework.
Microsoft .NET Framework reference assemblies are permitted as pinned
build-only inputs for cross-compilation, never shipped runtime libraries.

Freeze `RevisionWitness(bridge_id, session_id, epoch, database_guid)` as a
frozen Python dataclass and `NativeRevisionSource.witness(document_hwnd)` as
the adapter injection seam. Protocol failures use a private fixed-code error,
translated later at the context boundary. Opaque token encoding is fixed
`native-context-epochs-v1:{bridge_id}:{session_id}:{epoch}` (under 512 bytes).
Do not invent an MCP result or duplicate domain identity.

- [ ] Write red checks for create/activate/change/revert/close-cancel/reopen,
  monotonically changing epochs, bridge restart, bounds/overflow and busy/lost
  observation. Live-set reconciliation receives pure stable registration keys;
  never derive public UUID from the native key.
- [ ] Implement the small locked state store, immutable witness and strict
  request/response framing/codec. Validate both peers against shared vectors,
  including fragmented/truncated data, duplicate keys, nonce mismatch, surrogate
  text, integer limits, unknown operations and no drawing-content fields.
- [ ] Run focused Python/native checks, lint/type/import isolation, record
  commands/results and commit. Independent contract/quality review before Task2.

## Task 2: Actual SDK observer and local Windows transport

**Files:** owned native host/plugin/pipe source and build/package files,
`adapter/windows_native_revision.py`, focused injected/Windows pipe tests.

- [ ] Inspect existing Windows session/lease ctypes helpers before adding any
  equivalent. Keep COM imports inside the existing session manager; the new
  transport uses bounded Win32 pipe calls and consumes a supplied HWND only.
- [ ] Compile actual host APIs against pinned official references in three
  profiles: net48 with AutoCAD.NET.Core `[24.0.0]`, net8.0-windows with
  `[25.0.0]`, and net10.0-windows with `[25.0.2]`. Pin matching Model references
  explicitly where the older package has a version range. Autodesk's cited
  application compatibility table allows 2021 APIs for 2021-2024 and 2025 APIs
  for 2025-2026 in the corresponding runtime. If full AutoCAD.NET is needed
  for modal notifications, use the same exact version and document the reason.
  Locked restores required. Detect missing capabilities without pretending
  compile evidence is actual host compatibility.
- [ ] Register existing/new documents and event subscriptions once. Native
  lifetime objects exist only to unsubscribe/reconcile. Mutation/open-for-modify,
  undo/redo, sysvar, view, command, activation and lock transitions advance the
  epoch. Close-start marks busy; UI live-set reconciliation distinguishes actual
  destruction from cancellation. Never access a destroyed SDK object.
- [ ] Enqueue at most four requests and sample at safe Application.Idle on the
  UI thread. Validate active HWND, quiescence, command/modal state and global
  LockMode(true); writer transitions invalidate readiness immediately. Workers
  await copied results under the total deadline without touching SDK objects.
- [ ] Implement authenticated local transport per the exact protocol. Test
  fake-host local Windows roundtrip, wrong PID/SID/session, wrong nonce,
  first-instance collision, truncated/oversized/slow peer, timeout, shutdown and
  handle cleanup. Linux runs injected protocol/state checks only.
- [ ] Build all three real SDK profiles; run focused/native/Windows-compatible tests,
  lint/type/import checks. Commit/report independent reviews before integration.

## Task 3: Reproducible builds and operator evidence

**Files:** minimal bundle manifests/build helper, canonical setup/compatibility
guidance, native CI extension and opt-in operator observer runner.

- [ ] Produce loadable own-assembly packages with exact runtime/profile metadata,
  no Autodesk binaries. Provide explicit NETLOAD/bundle instructions and record
  observed host runtime without globally modifying TRUSTEDPATHS/security policy.
- [ ] Extend clean CI to locked native restore/build and pure state/protocol
  checks on Ubuntu/Windows; exercise actual named pipes only on Windows.
- [ ] Prepare guarded operator checks for unchanged repeated COM getters,
  change/revert, undo/redo, modal/modeless writes, cancelled close, actual reopen,
  window reuse, bridge/process loss/restart and read-only DWG preservation.
  Report precise release/runtime/profile; no observation yields no acceptance.
- [ ] Run complete affected verification, independent final review and focused
  PR. Mark code/build/portable/Windows API evidence separately from AutoCAD.

## Dependency rulings

Task1 produces strict pure state/codec consumed by host and Python transport;
Task2 supplies the callable witness consumed later by EPIC-04 adapters; Task3
packages those exact implementations. Transport owns no entity cache or fact
schema. Context adapter tests use the protocol seam, never claim fake witnesses
prove native coverage. The controller serializes shared CI/docs integration.
Older releases remain targeted; compile the declared profiles now, with host
acceptance still required before any observer compatibility claim. Package each
runtime profile separately so bundle auto-loading cannot select incompatible
assemblies by year alone.
