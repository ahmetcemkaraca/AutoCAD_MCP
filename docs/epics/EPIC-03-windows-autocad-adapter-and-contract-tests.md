# EPIC-03: Windows AutoCAD Adapter and Contract Tests

## Status

Proposed. This is a future implementation epic, not a claim that COM imports, adapter contracts, or real AutoCAD operations currently pass.

**Dependencies:** E01-G4 from [EPIC-01](EPIC-01-reproducible-windows-development-baseline.md) supplies the frozen Windows environment. E02-G3 from [EPIC-02](EPIC-02-canonical-mcp-core.md) supplies the accepted request, response, error, and `BasicToolService` interfaces. Adapter protocol/fake work may begin after E02-G1 freezes names, but runtime integration and real MCP smoke work wait for E02-G3.

**Stage gate:** this epic is the final gate for Roadmap Stage 2, Stable MCP core. Stage 2 closes only after automated pure/contract suites pass and the documented full AutoCAD 2026 disposable-DWG smoke suite passes. AutoCAD 2021-2025 remain “targeted, not verified” until the same named suite runs on each real release.

**Required execution mode:** a focused Windows-capable feature branch and pull request. Implement test-first work packages in sequence, use disposable drawing copies, and pause at the safety and real-installation reviewer gates.

## Outcome

The installed `autocad_mcp` core can call full AutoCAD through one narrow `autocad_mcp.adapter.protocol.AutoCADAdapter` protocol obtained from an `AdapterProvider`. The `autocad_mcp.adapter.windows*` implementation family is the only product boundary permitted to load `pythoncom` or `win32com`; adapter-internal `WindowsSessionManager` owns delayed loading and apartment/session lifecycle, and `WindowsAutoCADAdapter` consumes it. Pure modules and the canonical server remain importable on Linux and on Windows without AutoCAD running.

The public base protocol remains exactly the four read-only/status methods defined below: status, reconnect, list, and detail. `WindowsSessionManager` is reusable only inside the Windows adapter implementation family so later context, capture, and EPIC-06 edit adapters share lifecycle code without exposing COM proxies to their domain layers.

The adapter detects connected members and reports capabilities instead of selecting one of six speculative release implementations. It does not cache COM proxies across worker threads. A focused `FakeAutoCADAdapter` supports deterministic connection, document, entity listing/detail, reconnect, and injected-failure contract tests without emulating the full AutoCAD object model.

Automated contracts cover exactly the three active MCP tools. A separately invoked Windows suite uses full AutoCAD 2026 and an automatically created disposable DWG copy opened read-only to verify dependency state, MCP startup, server status/document discovery, entity listing/detail extraction, clean shutdown, reconnect, and an unchanged file/drawing fingerprint. Results record the exact AutoCAD product/release, Windows/Python/lock state, fixture revision, command, fingerprint, and manual interaction.

## Evidence / problem

- `src/utils.py` eagerly imports `pythoncom`, `win32com.client`, and `pyautocad`, so current server import is tied to Windows packages.
- `get_autocad_instance()` targets the versioned ProgID `AutoCAD.Application.25`, mentions AutoCAD 2025, initializes COM without a paired visible `CoUninitialize()` in the observed call path, and returns nested wrapper classes that obscure lifecycle ownership.
- EPIC-02 quarantines the four legacy mutating schemas outside the active catalog. A base adapter that still exposed creation methods would undermine that safety boundary even if MCP did not currently register them.
- Existing entity output is based primarily on session-local `ObjectID`; the approved architecture prefers handles for persistent drawing identity while retaining `entity_id` for basic-client compatibility.
- `src/testing/mock_autocad.py` contains an extensive historical mock object model. Source presence does not prove it matches the canonical adapter contract or a real AutoCAD release.
- No current test initializes the selected stdio server against a focused fake adapter.
- No recorded test connects to a real AutoCAD release, validates read-only query behavior, proves the DWG remained unchanged, or reconnects.
- Full AutoCAD 2026 is available as the first planned validation environment. Full AutoCAD 2021-2025 are targets only; historical 2025 claims are not reproducible from adopted tests.

The adapter must therefore isolate COM and provide test seams, while the evidence policy must prevent fake or Linux results from being reported as AutoCAD compatibility.

## Scope

- Define immutable AutoCAD boundary types in `src/autocad_mcp/adapter/protocol.py` and a narrow synchronous `AutoCADAdapter` protocol covering exactly status, reconnect, entity listing, and entity detail.
- Define `AdapterCapability`, issue/report types, and member-based detection contracts in `src/autocad_mcp/adapter/capabilities.py`.
- Define `AdapterProvider.get() -> AutoCADAdapter`, a production Windows provider, and a static provider for focused tests in `src/autocad_mcp/adapter/provider.py`.
- Define stable adapter-domain failures and map them to EPIC-02 structured MCP errors.
- Implement the adapter-internal `WindowsSessionManager` in `src/autocad_mcp/adapter/windows_session.py` with delayed COM imports, balanced COM apartment lifecycle, unversioned running-application discovery, active-document validation, and no retained COM proxies.
- Inject and use `WindowsSessionManager` in `WindowsAutoCADAdapter` so later `windows_context.py`, `windows_capture.py`, and `windows_edit.py` extensions reuse one lifecycle contract instead of importing an adapter-private context manager or duplicating COM setup.
- Detect actual capabilities after connection through member inspection; do not select behavior by AutoCAD release number.
- Implement entity listing, entity detail, status, and reconnect paths only.
- Return both session-local `object_id` and persistent drawing `handle` where AutoCAD exposes them.
- Implement a focused fake adapter and reusable adapter/service contract tests.
- Wire `autocad_mcp.runtime.create_tool_service()` to `AdapterToolService(WindowsAdapterProvider())` without making the core import COM.
- Add focused unit tests for delayed imports, COM initialization/uninitialization, capability detection, identity/property extraction, error classification, and service result mapping.
- Add an opt-in full AutoCAD 2026 disposable-DWG smoke runner and tests.
- Update compatibility, architecture, status, testing, and roadmap documentation only from fresh evidence.
- Keep AutoCAD 2021-2025 targeted and not verified until separately run.

## Out of scope

- AutoCAD LT, Linux-hosted AutoCAD, or macOS AutoCAD operation.
- A remote COM bridge, service daemon, Docker deployment, HTTP transport, or multi-host architecture.
- Caching a long-lived COM application/document/entity proxy across calls or worker threads.
- Creating a new AutoCAD process when none is running. The baseline attaches to an already running full AutoCAD application to avoid surprise UI and license behavior.
- Automatic opening, saving, or closing of user drawings in product code.
- Exposing arbitrary `SendCommand`, Python, AutoLISP, VBA, or shell execution through MCP.
- Any line, circle, extrusion, revolution, property change, deletion, or other drawing mutation. EPIC-06 owns approved constrained edits; extrusion/revolution remain unregistered until a separately reviewed 3D edit-primitive extension.
- Structured drawing snapshots, pagination, visual capture, edit plans, semantic analysis, or destructive editing.
- Exposing `WindowsSessionManager`, `AutoCADSession`, or any COM proxy to domain, context, capture, edit, MCP, or public adapter-protocol code. Only `autocad_mcp.adapter.windows` and sibling implementation modules whose basename begins `windows_` may consume the manager.
- Reusing or extending the historical full mock object graph. The fake in this epic models only the accepted protocol.
- Adding speculative AutoCAD 2021/2022/2023/2024/2025/2026 code branches.

## Prerequisites

1. EPIC-01’s accepted `uv.lock`, PEP 621 manifest, Windows COM markers, and CPython 3.12 baseline are present.
2. EPIC-02’s installed `autocad_mcp.core.models`, `BasicToolService`, deterministic response serialization, canonical `autocad_mcp.server`, and compatibility-shim contracts are accepted.
3. The implementation agent has access to Windows 11, 64-bit CPython 3.12, `uv`, and a real licensed full AutoCAD 2026 installation for E03-WP7.
4. A small safe source DWG with at least one queryable entity is supplied for the smoke runner. The runner copies it to a unique temporary directory, opens the copy read-only, and never opens the source in AutoCAD.
5. AutoCAD 2026 is started in the same interactive Windows session as the test process and has no modal dialog open.
6. A reviewer approves the protocol at E03-G1 before production or fake implementations diverge.
7. A reviewer approves the read-only disposable-DWG and before/after fingerprint procedure at E03-G4 before the first real AutoCAD run.
8. Every environment report distinguishes unit tested, MCP contract tested, and AutoCAD verified.
9. Every runner that touches a real AutoCAD installation acquires the controller-owned exclusive `AutoCADLease` before attaching or opening a drawing; inability to prove exclusive ownership fails closed.

## Owned files and paths

| Path | Planned action | Responsibility |
| --- | --- | --- |
| `src/autocad_mcp/adapter/__init__.py` | Create | Pure public adapter exports; no COM imports |
| `src/autocad_mcp/adapter/protocol.py` | Create | Boundary dataclasses/errors and narrow `AutoCADAdapter` protocol |
| `src/autocad_mcp/adapter/capabilities.py` | Create | `AdapterCapability`, issue/report values, and pure capability evaluation |
| `src/autocad_mcp/adapter/provider.py` | Create | `AdapterProvider`, `StaticAdapterProvider`, and `WindowsAdapterProvider` |
| `src/autocad_mcp/adapter/fake.py` | Create | Focused deterministic `FakeAutoCADAdapter` |
| `src/autocad_mcp/adapter/windows_session.py` | Create | Delayed COM loader, `AutoCADSession`, and reusable adapter-internal `WindowsSessionManager` |
| `src/autocad_mcp/adapter/windows.py` | Create | `WindowsAutoCADAdapter` implementation consuming `WindowsSessionManager` |
| `src/autocad_mcp/adapter/service.py` | Create | `AdapterToolService` mapping MCP inputs/results/errors to adapter calls |
| `src/autocad_mcp/runtime.py` | Modify | Replace unavailable service factory body with production provider/service composition |
| `tests/adapter/test_protocol.py` | Create | Boundary values and protocol conformance tests |
| `tests/adapter/test_fake.py` | Create | Focused fake and reusable protocol contract tests |
| `tests/adapter/test_capabilities.py` | Create | Capability report/detection contract tests |
| `tests/adapter/test_provider.py` | Create | Static/Windows provider construction and delayed-import tests |
| `tests/adapter/test_windows_imports.py` | Create | Delayed-import and non-Windows boundary tests |
| `tests/adapter/test_windows_session.py` | Create | Apartment balance, no-retention, and extension-reuse tests |
| `tests/adapter/test_windows.py` | Create | Focused mocked-COM lifecycle/capability/conversion/error tests |
| `tests/mcp/test_adapter_tool_service.py` | Create | Three MCP tool mappings through the fake adapter/provider |
| `tests/windows/drawing_copy_guard.py` | Create | Neutral source-to-GUID-copy lifecycle, path/hash/close/cleanup evidence reusable by later epics |
| `tests/windows/autocad_lease.py` | Create | Controller-owned exclusive real-AutoCAD verification lease and owner evidence |
| `tests/windows/autocad_harness.py` | Create | EPIC-03 read-only policy wrapper consuming the neutral guard and live lease |
| `tests/windows/test_drawing_copy_guard.py` | Create | Copy uniqueness, path, hash, close, cleanup, and preserve-evidence tests |
| `tests/windows/test_autocad_lease.py` | Create | Exclusivity, owner metadata, release, fail-closed, and stale-recovery tests |
| `tests/windows/test_autocad_harness.py` | Create | Lease-required read-only-open and writable-refusal tests |
| `tests/windows/test_autocad_2026_smoke.py` | Create | Opt-in full AutoCAD/MCP smoke sequence |
| `tests/conftest.py` | Create | Explicit `--run-autocad` gate and source-DWG validation |
| `scripts/run_autocad_2026_smoke.ps1` | Create | Safe Windows preflight, test invocation, and evidence capture |
| `pyproject.toml` | Modify narrowly | Register `autocad` pytest marker; do not change dependencies/lock |
| `docs/verification/autocad-2026-smoke.md` | Create only after a passing run | Actual environment, fixture, command, results, cleanup, interaction evidence |
| `docs/architecture.md` | Modify after E03-G5 | Move adapter boundary from target to adopted architecture |
| `docs/project-status.md` | Modify after E03-G5 | Record fake/contract and real-installation evidence separately |
| `docs/testing.md` | Modify after E03-G5 | Document normal and opt-in commands plus safety preconditions |
| `docs/compatibility.md` | Modify after E03-G5 | Promote only full AutoCAD 2026 for the read-only Stable-core smoke scope |
| `docs/roadmap.md` | Modify after E03-G6 | Close Stable MCP core only when all criteria pass |

`src/utils.py` is not owned. The canonical path stops using it, but advanced/experimental consumers remain for later classification. `src/testing/mock_autocad.py` is not modified or presented as contract evidence. No `src/autocad/` package is created.

## Interfaces produced and consumed

### Boundary values and narrow protocol

`src/autocad_mcp/adapter/protocol.py` produces pure Python types and imports only the platform-independent core:

```python
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol

from autocad_mcp.core.models import JsonValue
from autocad_mcp.adapter.capabilities import AdapterCapabilityReport

class AdapterErrorCode(StrEnum):
    AUTOCAD_UNAVAILABLE = "AUTOCAD_UNAVAILABLE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    COM_BUSY = "COM_BUSY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AUTOCAD_OPERATION_FAILED = "AUTOCAD_OPERATION_FAILED"

class AdapterError(Exception):
    code: AdapterErrorCode
    public_message: str
    retryable: bool
    details: Mapping[str, JsonValue]

    def __init__(
        self,
        code: AdapterErrorCode,
        public_message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, JsonValue] | None = None,
    ) -> None: ...

@dataclass(frozen=True)
class ConnectionInfo:
    connected: bool
    product: str | None
    version: str | None
    release_hint: str | None
    active_document: str | None
    read_only: bool | None
    capabilities: AdapterCapabilityReport

@dataclass(frozen=True)
class EntitySummary:
    object_id: int
    handle: str
    object_name: str
    layer: str

@dataclass(frozen=True)
class EntityDetails:
    object_id: int
    handle: str
    object_name: str
    layer: str
    properties: Mapping[str, JsonValue] = field(default_factory=dict)

class AutoCADAdapter(Protocol):
    def status(self) -> ConnectionInfo: ...
    def reconnect(self) -> ConnectionInfo: ...
    def list_entities(self) -> tuple[EntitySummary, ...]: ...
    def get_entity_info(self, object_id: int) -> EntityDetails: ...
```

`release_hint` is informational text derived from product caption/name when available. No operation branches on it. The protocol contains no COM object, `Any` return, version-specific method, drawing-open/save operation, arbitrary command, creation, property change, or deletion operation. Four methods serve `WindowsAutoCADAdapter` and `FakeAutoCADAdapter`.

### Capability contracts

`src/autocad_mcp/adapter/capabilities.py` produces:

```python
from dataclasses import dataclass, field
from enum import StrEnum

class AdapterCapability(StrEnum):
    CONNECTION = "connection"
    ACTIVE_DOCUMENT = "active_document"
    LIST_ENTITIES = "list_entities"
    GET_ENTITY_INFO = "get_entity_info"

class AdapterCapabilityIssueCode(StrEnum):
    MEMBER_UNAVAILABLE = "MEMBER_UNAVAILABLE"
    MEMBER_ACCESS_FAILED = "MEMBER_ACCESS_FAILED"

@dataclass(frozen=True)
class AdapterCapabilityIssue:
    code: AdapterCapabilityIssueCode
    capability: AdapterCapability
    member: str
    message: str

@dataclass(frozen=True)
class AdapterCapabilityReport:
    available: frozenset[AdapterCapability] = field(default_factory=frozenset)
    issues: tuple[AdapterCapabilityIssue, ...] = ()

    def supports(self, capability: AdapterCapability) -> bool: ...
```

The Windows detector checks only members required by accepted methods: application attachment; active document/model space; model-space iteration; and `ObjectID`, `Handle`, `ObjectName`, and `Layer` identity members. Safe member lookup records an issue when COM access fails. A method raises `UNSUPPORTED_CAPABILITY` with the exact capability when `supports()` is false. No release-year assumption enters detection.

### Adapter provider

`src/autocad_mcp/adapter/provider.py` produces the composition boundary consumed by services and later epics:

```python
from collections.abc import Callable
from typing import Protocol

from autocad_mcp.adapter.protocol import AutoCADAdapter

class AdapterProvider(Protocol):
    def get(self) -> AutoCADAdapter: ...

class StaticAdapterProvider:
    def __init__(self, adapter: AutoCADAdapter) -> None: ...
    def get(self) -> AutoCADAdapter: ...

class WindowsAdapterProvider:
    def __init__(
        self,
        factory: Callable[[], AutoCADAdapter] | None = None,
    ) -> None: ...
    def get(self) -> AutoCADAdapter: ...
```

`WindowsAdapterProvider` defaults to constructing `WindowsAutoCADAdapter` through a local import inside `get()`. Importing the provider therefore does not import the Windows module or COM packages. The provider holds no COM proxy.

### Delayed COM loader and production adapter

`src/autocad_mcp/adapter/windows_session.py` owns delayed loading and apartment/session lifecycle:

```python
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType

@dataclass(frozen=True)
class ComModules:
    pythoncom: ModuleType
    client: ModuleType

def load_com_modules() -> ComModules: ...

@dataclass(frozen=True)
class AutoCADSession:
    com: ComModules
    application: object
    document: object | None
    model_space: object | None

class WindowsSessionManager:
    def __init__(
        self,
        com_loader: Callable[[], ComModules] = load_com_modules,
    ) -> None: ...

    @contextmanager
    def session(self, require_document: bool) -> Iterator[AutoCADSession]: ...
```

`load_com_modules()` checks `sys.platform == "win32"`, then calls `importlib.import_module("pythoncom")` and `importlib.import_module("win32com.client")`. `WindowsSessionManager.session()` calls `CoInitialize()`, attaches only with `GetActiveObject("AutoCAD.Application")`, obtains the active document/model space when `require_document` is true, yields one `AutoCADSession`, and calls `CoUninitialize()` in `finally`. The manager retains only its loader callable; after the context exits, neither it nor the adapter retains the yielded session, application, document, model-space, or entity proxies.

`src/autocad_mcp/adapter/windows.py` consumes that manager:

```python
from autocad_mcp.adapter.windows_session import AutoCADSession, ComModules, WindowsSessionManager

def detect_capabilities(session: AutoCADSession) -> AdapterCapabilityReport: ...

class WindowsAutoCADAdapter:
    def __init__(
        self,
        session_manager: WindowsSessionManager | None = None,
    ) -> None: ...
```

Every adapter method executes `with self._session_manager.session(require_document=...) as session:` and uses proxies only inside that block. `reconnect()` obtains a fresh session and proves no stale proxy is required. These COM import strings do not appear in `adapter/__init__.py`, `protocol.py`, `capabilities.py`, or `provider.py` imports.

`WindowsSessionManager`, `ComModules`, and `AutoCADSession` are adapter-internal contracts. They are not exported from `autocad_mcp.adapter.__init__` and are not referenced by `protocol.py`. Consumers are restricted to `autocad_mcp.adapter.windows` and sibling adapter implementation modules named `windows_*.py`. Domain/context/capture/edit services consume typed adapter protocols and immutable values; they never receive COM proxies. Later EPIC-04/05/06 Windows extensions inject the same manager type into their Windows-only adapters and open their own short-lived `session(...)` contexts.

COM conversion helpers have concrete signatures:

```python
def _entity_summary(entity: object) -> EntitySummary: ...
def _entity_details(entity: object) -> EntityDetails: ...
```

`_entity_details()` reads only `ObjectID`, `Handle`, `ObjectName`, `Layer`, `Color`, `Linetype`, `Length`, `Area`, `Volume`, `Radius`, `Center`, `StartPoint`, and `EndPoint`. Missing optional properties are omitted. No base-adapter helper constructs a point array, invokes an `Add*` member, changes a property, sends a command, or deletes an entity.

### Adapter-to-MCP service

`src/autocad_mcp/adapter/service.py` consumes the EPIC-02 port and provider:

```python
class AdapterToolService:
    def __init__(self, provider: AdapterProvider) -> None: ...
    async def invoke(self, request: BasicToolInput) -> ToolResponse: ...
```

Each invocation gets the adapter from the provider and runs the synchronous method through `await asyncio.to_thread(...)`; production COM enters/exits in that worker. The service maps ordered entity IDs/handles/types/layers, entity details, connection fields, `tools_available: 3`, sorted available capability strings and capability issues, and every same-named adapter error to EPIC-02 `ErrorCode`. It accepts only `ServerStatusInput`, `ListEntitiesInput`, and `GetEntityInfoInput`.

`src/autocad_mcp/runtime.py` becomes:

```python
def create_tool_service() -> BasicToolService:
    return AdapterToolService(WindowsAdapterProvider())
```

Constructing the server, service, or provider does not import COM. The first Windows adapter operation does.

### Focused fake interface

`src/autocad_mcp/adapter/fake.py` produces:

```python
class FakeAutoCADAdapter:
    def __init__(
        self,
        *,
        connected: bool = True,
        document_name: str = "contract.dwg",
        entities: tuple[EntityDetails, ...] | None = None,
    ) -> None: ...
    def fail_next(self, error: AdapterError) -> None: ...
    @property
    def calls(self) -> tuple[tuple[str, object], ...]: ...
```

It implements all four methods, defaults to one deterministic `EntityDetails(object_id=1001, handle="10", ...)`, stores only supplied immutable entity records, and returns immutable tuples. `fail_next()` raises once then clears. It has no creation method, document graph, COM proxy, geometry engine, version emulation, or dependency on `windows.py`. Tests inject it with `StaticAdapterProvider`.

### Neutral drawing-copy guard

`tests/windows/drawing_copy_guard.py` is policy-neutral test infrastructure. It imports no COM package and produces:

```python
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

@dataclass(frozen=True)
class DrawingCopyEvidence:
    run_id: str
    source_path: str
    copy_path: str
    source_sha256_before: str
    source_sha256_after: str | None
    copy_sha256_before: str
    copy_sha256_after: str | None
    active_full_name: str | None
    close_without_save_attempted: bool
    preserved: bool
    preserve_reason: str | None
    cleanup_succeeded: bool

class DrawingCopyViolation(RuntimeError):
    evidence: DrawingCopyEvidence

class DrawingCopyGuard:
    @classmethod
    def prepare(cls, source_path: Path, *, temp_root: Path | None = None) -> Self: ...
    @property
    def source_path(self) -> Path: ...
    @property
    def copy_path(self) -> Path: ...
    def assert_active_full_name(self, active_full_name: str) -> None: ...
    def close_without_save(self, close_document: Callable[[bool], None]) -> None: ...
    def finalize(self, *, preserve: bool, reason: str) -> DrawingCopyEvidence: ...
```

`prepare()` resolves a regular `.dwg` source, records its hash, creates `autocad-mcp-<UUID>/drawing-copy.dwg` below the selected temporary root, uses `shutil.copy2`, proves resolved path inequality, and proves the initial copy hash equals the source hash. `assert_active_full_name()` uses normalized resolved Windows paths and refuses the source or any unexpected document. `close_without_save()` invokes the supplied callback with `False` and records that close was attempted; it never imports COM. `finalize()` records final hashes, always fails if the source changed, records whether the copy changed, and either removes the unique run directory or preserves it with a non-empty reason. Violations carry evidence and preserve the copy by default.

This guard does not require a read-only copy and does not judge a changed copy as failure; that policy belongs to its consumer. EPIC-03’s wrapper requires unchanged copy hashes. EPIC-06 may import only this neutral guard for file/path/source protection and must own a separate writable-policy wrapper.

### Exclusive AutoCAD verification lease

`tests/windows/autocad_lease.py` is controller-owned infrastructure for every real-AutoCAD runner:

```python
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

@dataclass(frozen=True)
class LeaseOwner:
    lease_key: str
    pid: int
    process_created_at_100ns: int
    user_sid: str
    computer_name: str
    windows_session_id: int
    acquired_at_utc: str
    command: tuple[str, ...]

@dataclass(frozen=True)
class LeaseEvidence:
    owner: LeaseOwner
    metadata_path: str
    acquired_at_utc: str
    released_at_utc: str | None
    stale_owner_recovered: LeaseOwner | None

def build_autocad_lease_key(
    *,
    installation_path: Path,
) -> str: ...

class AutoCADLease:
    @classmethod
    def acquire(cls, lease_key: str) -> Self: ...
    def assert_owned(self) -> None: ...
    def release(self) -> LeaseEvidence: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
```

The implementation creates a lease directory below `%LOCALAPPDATA%/AutoCADMCP/verification-leases`, uses `win32security` to create/verify a Windows ACL granting the current user SID and `SYSTEM` only, takes a non-blocking exclusive file lock with `msvcrt.locking`, and writes owner metadata only while holding that lock. The key is derived solely from trustworthy local facts: machine identity, current user SID, Windows interactive-session ID, normalized AutoCAD installation path/file identity, and product release/build read from verified `acad.exe` file/version metadata. No runner argument, requested release string, environment variable, configuration field, fixture value, or MCP input may override or salt the key. Separate VMs, machines, installations, users, or genuine Windows interactive sessions naturally produce distinct derived keys. A requested release such as `2026` is checked only as a validation assertion after lease acquisition and cannot influence the key.

Lock contention, corrupt metadata, an unprotected metadata path, indeterminate owner liveness, and release without ownership all fail closed. While held, metadata has `released_at_utc = None`; normal release writes the release timestamp before unlocking, so a later acquirer may replace conclusively released metadata without treating it as stale. Held metadata may be replaced only after the contender owns the OS lock and a Windows `OpenProcess`/`GetProcessTimes` check proves the recorded PID and creation time no longer identify a live owner; PID existence without matching creation time is recorded as a recovered dead owner, not silently ignored. A missing metadata file is valid only for the first acquisition of a newly created, protected lease path. Acquisition and release return/emit `LeaseEvidence`. OS-lock acquisition and release are paired in `finally`/context-manager paths.

### EPIC-03 read-only harness policy

`tests/windows/autocad_harness.py` consumes `DrawingCopyGuard`, a live `AutoCADLease`, and the Windows test connection helpers. Its `ReadOnlyAutoCADHarness` calls `lease.assert_owned()` before attaching, opens only `guard.copy_path` with AutoCAD’s read-only flag, calls `guard.assert_active_full_name()`, and refuses a document whose `ReadOnly` property is not true. It owns `ReadOnlyDrawingFingerprint` and the read-only unchanged-copy comparison. It closes through `guard.close_without_save()` and finalizes evidence through the guard.

`ReadOnlyAutoCADHarness` is not neutral infrastructure and is not handed to EPIC-06. EPIC-06 must combine `DrawingCopyGuard` and `AutoCADLease` with its own separately reviewed writable harness/policy; importing or subclassing the read-only wrapper is prohibited.

## Work packages

### E03-WP1: Approve protocol, error, and safety boundaries

**Sequence:** 1. **Depends on:** E02-G1. **Reviewer gate:** E03-G1.

**Files:** no implementation mutation; attach an interface review to the pull request and update this epic if names change.

1. Compare the three EPIC-02 `BasicToolInput` variants with `status()`, `list_entities()`, and `get_entity_info()`; `reconnect()` is lifecycle-only and supports the smoke/recovery contract.
2. Confirm `AUTOCAD_OPERATION_FAILED` exists in the accepted EPIC-02 `ErrorCode` for redacted query failures. No edit-specific error belongs in this base contract.
3. Confirm no protocol type exposes COM objects, unrestricted commands, deletion, open/save, a generic `execute()` method, `WindowsSessionManager`, or `AutoCADSession`. The manager is an adapter-internal extension seam and does not change the four-method public protocol.
4. Confirm the real smoke has no mutation method or Undo path and must prove unchanged file/drawing fingerprints.
5. E03-G1 passes when a reviewer accepts the four-method protocol, four read-only/status capabilities, public errors, thread confinement, and unchanged-DWG test boundary.

### E03-WP2: Build boundary models, focused fake, and reusable contracts test-first

**Sequence:** 2. **Depends on:** E03-G1. **Reviewer gate:** E03-G2.

**Files:** `src/autocad_mcp/adapter/__init__.py`, `src/autocad_mcp/adapter/protocol.py`, `src/autocad_mcp/adapter/capabilities.py`, `src/autocad_mcp/adapter/provider.py`, `src/autocad_mcp/adapter/fake.py`, `tests/adapter/test_protocol.py`, `tests/adapter/test_capabilities.py`, `tests/adapter/test_provider.py`, `tests/adapter/test_fake.py`.

1. Write a failing protocol conformance test:

   ```python
   def accepts_adapter(adapter: AutoCADAdapter) -> AutoCADAdapter:
       return adapter

   fake = accepts_adapter(FakeAutoCADAdapter())
   assert fake.status().connected is True
   assert StaticAdapterProvider(fake).get() is fake
   ```

2. Write one reusable `exercise_basic_adapter_contract(adapter: AutoCADAdapter) -> None` helper that asserts status/capabilities, reconnect, ordered listing, detail-by-ID, handles, and entity-not-found behavior.
3. Add focused tests for deterministic existing IDs/handles, immutable tuple results, disconnected/no-document states, each `AdapterErrorCode`, `fail_next()` clearing, call recording, and absence of creation/edit methods.
4. Run the red suite:

   ```powershell
   uv run pytest tests/adapter/test_protocol.py tests/adapter/test_capabilities.py tests/adapter/test_provider.py tests/adapter/test_fake.py -q
   ```

   Expected result: import failures because the adapter package and fake do not exist.
5. Implement only the boundary dataclasses/protocol and focused fake needed by those tests.
6. Run:

   ```powershell
   uv run pytest tests/adapter/test_protocol.py tests/adapter/test_capabilities.py tests/adapter/test_provider.py tests/adapter/test_fake.py -q
   uv run ruff check src/autocad_mcp/adapter/protocol.py src/autocad_mcp/adapter/capabilities.py src/autocad_mcp/adapter/provider.py src/autocad_mcp/adapter/fake.py tests/adapter
   uv run python -m compileall -q src/autocad_mcp/adapter tests/adapter
   ```

7. E03-G2 passes when the reviewer confirms the fake implements exactly four methods, contains no mutation/COM emulation, and all public values/errors are immutable or read-only.

### E03-WP3: Prove delayed imports and implement the Windows COM boundary

**Sequence:** 3. **May begin after:** E03-G1. **Depends on model names from:** E03-WP2. **Reviewer gate:** E03-G3.

**Files:** `src/autocad_mcp/adapter/windows_session.py`, `src/autocad_mcp/adapter/windows.py`, `tests/adapter/test_windows_imports.py`, `tests/adapter/test_windows_session.py`, `tests/adapter/test_windows.py`.

1. Write an import test that clears relevant modules, imports `autocad_mcp.adapter`, `.protocol`, `.capabilities`, `.provider`, `.windows_session`, and `.windows`, then asserts `pythoncom`, `win32com`, `win32com.client`, and `pyautocad` are absent from `sys.modules`.
2. On non-Windows, write a test that calling `load_com_modules()` raises `AdapterError(AUTOCAD_UNAVAILABLE)` without a raw `ModuleNotFoundError` message.
3. With a tiny injected `ComModules` stub, write failing tests for:

   - one balanced `CoInitialize()`/`CoUninitialize()` pair for each `WindowsSessionManager.session()` context on success, application-lookup failure, document-lookup failure, consumer exception, and normal exit;
   - `session(require_document=False)` yielding application-only access and `session(require_document=True)` requiring document/model space;
   - `GetActiveObject("AutoCAD.Application")` with no release suffix;
   - no application creation call;
   - manager and adapter instance dictionaries retaining only configuration/manager references and no yielded application, document, model-space, session, or entity proxy after context exit;
   - a test-local `WindowsContextExtension` and `WindowsCaptureExtension` receiving the same `WindowsSessionManager`, independently opening/closing fresh sessions, and producing a balanced initialize/uninitialize pair per use without importing `WindowsAutoCADAdapter._session`;
   - `WindowsAutoCADAdapter(session_manager=manager)` using the same adapter-internal manager contract as those extensions;
   - connected/no-document/read-only status;
   - capability inclusion/omission from the exact member set;
   - allowlisted entity properties only;
   - lookup by object ID and `ENTITY_NOT_FOUND`;
   - classification of unavailable, busy, unsupported, and operation failures;
   - no COM proxy stored on the adapter after each method returns.

   The lifecycle tests have exact names `test_session_balances_com_on_success`, `test_session_balances_com_on_consumer_error`, `test_session_balances_com_on_connection_error`, `test_manager_does_not_retain_proxies_after_exit`, and `test_windows_extensions_share_manager_without_lifecycle_duplication`.

4. Run the red tests:

   ```powershell
   uv run pytest tests/adapter/test_windows_imports.py tests/adapter/test_windows_session.py tests/adapter/test_windows.py -q
   ```

5. Implement the delayed loader and `WindowsSessionManager` first, then inject it into `WindowsAutoCADAdapter` and implement the capability detector, identity/property helpers, public-property allowlist, and four protocol methods. No extension imports a private method from `WindowsAutoCADAdapter`. Log internal COM exceptions with `logger.exception`; return public messages through `AdapterError`.
6. Run focused tests on Linux and Windows without AutoCAD:

   ```powershell
   uv run pytest tests/adapter/test_windows_imports.py tests/adapter/test_windows_session.py tests/adapter/test_windows.py -q
   uv run python -c "import autocad_mcp.adapter.windows_session, autocad_mcp.adapter.windows, sys; assert not {'pythoncom','win32com','pyautocad'} & set(sys.modules)"
   uv run ruff check src/autocad_mcp/adapter/windows_session.py src/autocad_mcp/adapter/windows.py tests/adapter/test_windows_imports.py tests/adapter/test_windows_session.py tests/adapter/test_windows.py
   ```

7. On Windows with dependencies installed but AutoCAD closed, run this expected-failure classification check:

   ```powershell
   uv run python -c "from autocad_mcp.adapter.protocol import AdapterError,AdapterErrorCode; from autocad_mcp.adapter.windows import WindowsAutoCADAdapter; a=WindowsAutoCADAdapter(); exec('try:\n a.status()\nexcept AdapterError as e:\n assert e.code == AdapterErrorCode.AUTOCAD_UNAVAILABLE\nelse:\n raise AssertionError(\"AutoCAD unexpectedly connected\")')"
   ```

8. E03-G3 passes when the reviewer sees balanced apartment lifecycle, no proxy retention, reuse by test-local Windows extensions, read-only capability-based behavior, delayed imports, and public-error redaction. The reviewer also confirms that `WindowsSessionManager` is absent from public/domain protocols and restricted to Windows adapter implementation modules.

### E03-WP4: Map the three active MCP tools through the fake adapter

**Sequence:** 4. **Depends on:** E02-G3 and E03-G2. **Reviewer gate:** included in E03-G3.

**Files:** `src/autocad_mcp/adapter/service.py`, `src/autocad_mcp/runtime.py`, `tests/mcp/test_adapter_tool_service.py`.

1. Write failing tests that instantiate `AdapterToolService(StaticAdapterProvider(FakeAutoCADAdapter()))` and invoke `ServerStatusInput`, `ListEntitiesInput`, and `GetEntityInfoInput`.
2. Assert exact compatibility and new identity fields:

   - list results contain `count` and ordered entities with `id`, `handle`, `type`, and `layer`;
   - detail results contain the allowlisted entity dictionary;
   - status contains three tools, stdio transport, document, product/version, and sorted capability strings.

3. Parameterize each base `AdapterErrorCode` and assert its same-named MCP `ErrorCode`, retryable flag, details, and redacted message.
4. Patch `asyncio.to_thread` with a recording wrapper and prove each synchronous adapter operation crosses that boundary once.
5. Import canonical `autocad_mcp.server` and compatibility `src.server` after production wiring and assert no COM module loads until an actual tool invocation.
6. Run the red suite:

   ```powershell
   uv run pytest tests/mcp/test_adapter_tool_service.py -q
   ```

7. Implement `AdapterToolService`, then change only `autocad_mcp.runtime.create_tool_service()` to return `AdapterToolService(WindowsAdapterProvider())`.
8. Run fake and canonical contracts together:

   ```powershell
   uv run pytest tests/adapter tests/mcp/test_adapter_tool_service.py tests/contract/test_stdio_server.py -q
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py -q
   uv run ruff check src/autocad_mcp/adapter src/autocad_mcp/runtime.py tests/adapter tests/mcp/test_adapter_tool_service.py
   uv run python -m compileall -q src tests
   ```

### E03-WP5: Build the copy guard, exclusive lease, and read-only harness

**Sequence:** 5. **Depends on:** E03-G3. **Reviewer gate:** E03-G4 before use with AutoCAD.

**Files:** `tests/windows/drawing_copy_guard.py`, `tests/windows/autocad_lease.py`, `tests/windows/autocad_harness.py`, `tests/windows/test_drawing_copy_guard.py`, `tests/windows/test_autocad_lease.py`, `tests/windows/test_autocad_harness.py`, `tests/conftest.py`, `scripts/run_autocad_2026_smoke.ps1`, and the pytest marker entry in `pyproject.toml`.

1. Register `autocad` as an opt-in marker and `--run-autocad` as an explicit command-line option. Without that option, all real-installation tests skip with the reason “requires explicit disposable-DWG authorization.” The session-scoped real-test fixture must acquire `AutoCADLease` before yielding any AutoCAD fixture and release it in `finally`.
2. Write failing neutral-guard tests named `test_prepare_creates_unique_guid_copy`, `test_prepare_rejects_same_or_non_dwg_path`, `test_source_hash_change_fails_and_preserves_copy`, `test_active_full_name_must_equal_copy`, `test_close_without_save_passes_false`, and `test_finalize_records_cleanup_or_preservation`.
3. Write failing lease tests that use subprocesses, not same-process mocks:

   - `test_same_key_is_exclusive_across_processes` holds a lease in a child and proves a second controller fails closed with owner metadata;
   - `test_key_ignores_requested_release_and_uses_os_installation_facts` proves no caller-supplied release/override exists and changes only trusted machine/user/session/installation/file-version facts;
   - `test_distinct_real_windows_sessions_derive_distinct_keys` proves genuinely distinct OS session IDs produce distinct keys without a public override;
   - `test_release_records_evidence_and_allows_reacquire` checks paired release;
   - `test_live_owner_is_never_stolen` checks PID plus process-creation time;
   - `test_stale_owner_recovers_only_after_process_death` terminates the owner, proves death, then verifies recorded recovery;
   - `test_corrupt_or_unprotected_metadata_fails_closed` checks controller refusal;
   - `test_lease_path_is_current_user_protected` checks the `%LOCALAPPDATA%`/SID boundary.

4. Implement `DrawingCopyGuard` using only the standard library and make its tests pass. The neutral guard owns creation, path inequality, initial/final hashes, active-full-name checking, close-without-save callback, and cleanup/preserve evidence; it does not open AutoCAD or require read-only/writable policy.
5. Implement `AutoCADLease` with non-blocking Windows OS locking, PID/creation-time liveness checks, current-user owner metadata, fail-closed behavior, evidence, and context-managed release. Add `test_every_real_autocad_fixture_requires_owned_lease`, which inspects/invokes the controller fixture and fails if the smoke can reach its harness without `assert_owned()`.
6. Make the PowerShell runner accept only required absolute `-SourceDwg` and `-AutoCADInstallationPath` arguments. It validates paths but does not create the copy; the Python guard owns copying. It has no lease-key, isolation, salt, namespace, or concurrency-override parameter. It sets:

   ```text
   AUTOCAD_MCP_SMOKE_SOURCE_DWG=<absolute immutable source path>
   AUTOCAD_MCP_AUTOCAD_INSTALLATION=<absolute acad.exe path>
   AUTOCAD_MCP_SMOKE_RELEASE=2026
   AUTOCAD_MCP_SMOKE_DISPOSABLE=YES
   ```

7. Implement `ReadOnlyAutoCADHarness` as a wrapper around an acquired lease and prepared guard. It calls `lease.assert_owned()`, opens only `guard.copy_path` with the COM read-only flag, calls `guard.assert_active_full_name()`, and refuses `ReadOnly is not True`. Define test-only `ReadOnlyDrawingFingerprint(file_sha256: str, file_size: int, file_mtime_ns: int, dbmod: int, entity_count: int, entity_digest: str)` and require unchanged copy/drawing fields. Close and cleanup only through guard methods.
8. Write policy tests named `test_harness_requires_owned_lease`, `test_harness_opens_guard_copy_not_source`, `test_harness_refuses_writable_document`, `test_harness_requires_unchanged_copy_fingerprint`, and `test_harness_preserves_guard_evidence_on_failure`. Assert the module has no writable-policy class.
9. The runner invokes exactly:

   ```powershell
   uv sync --frozen --group dev
   uv run pytest tests/windows/test_autocad_2026_smoke.py -m autocad --run-autocad -vv --tb=short
   ```

10. Run all controller/guard/harness tests without AutoCAD:

   ```powershell
   uv run pytest tests/windows/test_drawing_copy_guard.py tests/windows/test_autocad_lease.py tests/windows/test_autocad_harness.py -q
   uv run pytest tests/windows/test_autocad_2026_smoke.py -m "not autocad" -q
   ```

11. E03-G4 passes when a maintainer reviews neutral-guard separation, current-user lease exclusivity/stale recovery, mandatory runner acquisition, forced read-only wrapper, canonical fingerprint construction, source/copy hash checks, close-without-save, and cleanup/preserve evidence. The read-only harness contains no writable, Undo, or command-execution path.

### E03-WP6: Write the full AutoCAD 2026 smoke sequence test-first

**Sequence:** 6. **Depends on:** E03-G4. **Reviewer gate:** real read-only execution waits for E03-WP7.

**Files:** `tests/windows/test_autocad_2026_smoke.py`.

1. Write an opt-in test that validates all four required environment values and refuses any release value other than `2026` in this file. Require the session fixture’s acquired `AutoCADLease`, call `assert_owned()` before constructing the harness, and attach acquire/release evidence to the test report.
2. Through `ReadOnlyAutoCADHarness` and the production adapter, assert the guard copy is active/read-only, connection info, list/detail capabilities, and reconnect.
3. Through a real canonical MCP subprocess using `python -m autocad_mcp.server`, perform this ordered sequence:

   1. initialize and list exactly `server_status`, `list_entities`, and `get_entity_info`;
   2. call `server_status` and match the disposable document;
   3. call `list_entities`, require at least one entity, and record its ordered summaries;
   4. call `get_entity_info` for the first entity ID and match handle/type/layer;
   5. close the MCP session/process cleanly;
   6. capture and compare the full fingerprint with the initial value;
   7. start a new MCP process, call status/list/detail, and prove reconnect to the same read-only disposable document;
   8. close the second process cleanly;
   9. capture and compare the full fingerprint again.

4. In `finally`, close without saving and assert source/copy hashes, file metadata, `DBMOD`, entity count, and entity digest are unchanged.
5. The smoke has no registered mutation. Record that EPIC-06 owns future approved edits and that extrusion/revolution remain unregistered pending a separate 3D edit-primitive review.
6. Confirm the test cannot run on Linux, without `--run-autocad`, without `AUTOCAD_MCP_SMOKE_DISPOSABLE=YES`, against a missing copy, or against the source path.
7. Run only non-real collection/preflight before E03-WP7:

   ```powershell
   uv run pytest --collect-only tests/windows/test_autocad_2026_smoke.py -q
   uv run pytest tests/windows/test_autocad_2026_smoke.py -m "not autocad" -q
   uv run ruff check tests/windows tests/conftest.py scripts
   ```

### E03-WP7: Execute and review the real AutoCAD 2026 gate

**Sequence:** 7. **Depends on:** E03-WP6 and E03-G4. **Reviewer gates:** E03-G5 and E03-G6.

**Files:** create `docs/verification/autocad-2026-smoke.md` from actual output; then update canonical docs.

1. Start full AutoCAD 2026 in the interactive test session, close modal dialogs, and ensure the supplied source fixture is backed up or reproducible.
2. Run from Windows PowerShell with actual safe fixture and installation paths:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_autocad_2026_smoke.ps1 -SourceDwg C:\autocad-mcp-fixtures\basic-smoke.dwg -AutoCADInstallationPath "C:\Program Files\Autodesk\AutoCAD 2026\acad.exe"
   ```

3. Record actual values in `docs/verification/autocad-2026-smoke.md`: date/time zone, AutoCAD product/edition/release/build, Windows edition/build, Python version, `uv` version, `uv.lock` blob ID, source fixture SHA-256, disposable path classification with personal directory components redacted, exact command, lease key/owner/acquire/release evidence and any stale-owner recovery, collected/passed/skipped/failed counts, three registered tools, detected read-only capabilities, all initial/final fingerprint fields, reconnect result, duration, modal-dialog observation, and whether any manual interaction occurred.
4. Record only status/entity-query behavior as canonical-smoke verified if every assertion and fingerprint comparison passes. State that editing is outside Stable core, EPIC-06 owns approved constrained edits, and extrusion/revolution remain unregistered.
5. If the test fails or any source/copy/drawing fingerprint field changes, do not create a passing verification record, do not promote compatibility, preserve the disposable copy for diagnosis, and keep Roadmap Stage 2 open.
6. E03-G5 passes when a reviewer checks the raw output, exclusive lease acquisition/release evidence, environment record, source/copy hashes, entity digest/count, file metadata, `DBMOD`, read-only flag, and reconnect evidence.
7. After E03-G5, update architecture, status, testing, compatibility, and roadmap. `docs/testing.md` must make the exclusive lease and acquire/release evidence mandatory for every real-AutoCAD command. Promote only full AutoCAD 2026 for the exact read-only Stable-core smoke scope, keep 2021-2025 targeted/not verified, and keep all editing under EPIC-06 or a later 3D edit-primitive extension.
8. Run final automated regression on Windows:

   ```powershell
   uv lock --check
   uv sync --frozen --group dev
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/adapter tests/windows/test_drawing_copy_guard.py tests/windows/test_autocad_lease.py tests/windows/test_autocad_harness.py tests/mcp/test_adapter_tool_service.py tests/contract/test_stdio_server.py -q
   uv run ruff check src tests scripts
   uv run python -m compileall -q src tests
   python -m json.tool mcp.json > $null
   git diff --check
   ```

9. Run the platform-independent subset on Linux and confirm it does not install/load COM:

   ```bash
   uv sync --frozen --group dev
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/adapter/test_protocol.py tests/adapter/test_capabilities.py tests/adapter/test_provider.py tests/adapter/test_fake.py tests/adapter/test_windows_imports.py tests/adapter/test_windows_session.py tests/mcp/test_adapter_tool_service.py tests/contract/test_stdio_server.py -q
   uv run python -c "import autocad_mcp.server, autocad_mcp.adapter.windows_session, autocad_mcp.adapter.windows, src.server, sys; assert not {'pythoncom','win32com','pyautocad'} & set(sys.modules)"
   ```

10. E03-G6 passes when a maintainer confirms all three foundation epics’ acceptance criteria, closes only Stable MCP core, and preserves all compatibility qualifiers.

## Parallel subagent lanes

Parallel lanes require the E03-G1 interface freeze. File ownership is non-overlapping; runtime integration occurs in the stated order.

| Lane | Work packages | Exclusive file ownership | Start/dependency | Integration order |
| --- | --- | --- | --- | --- |
| E03-A: protocol, capabilities, provider, fake | E03-WP2 | `src/autocad_mcp/adapter/__init__.py`, `src/autocad_mcp/adapter/protocol.py`, `src/autocad_mcp/adapter/capabilities.py`, `src/autocad_mcp/adapter/provider.py`, `src/autocad_mcp/adapter/fake.py`, `tests/adapter/test_protocol.py`, `tests/adapter/test_capabilities.py`, `tests/adapter/test_provider.py`, `tests/adapter/test_fake.py` | E03-G1 | First, after E03-G2 |
| E03-B: Windows session and adapter | E03-WP3 | `src/autocad_mcp/adapter/windows_session.py`, `src/autocad_mcp/adapter/windows.py`, `tests/adapter/test_windows_imports.py`, `tests/adapter/test_windows_session.py`, `tests/adapter/test_windows.py` | E03-G1; imports Lane A names | Second, after E03-G3 |
| E03-C: MCP service integration | E03-WP4 | `src/autocad_mcp/adapter/service.py`, `src/autocad_mcp/runtime.py`, `tests/mcp/test_adapter_tool_service.py` | E02-G3 and Lane A | Third |
| E03-D: real-test harness and evidence | E03-WP5 through E03-WP7 | `tests/windows/**`, `tests/conftest.py`, `scripts/run_autocad_2026_smoke.ps1`, pytest marker in `pyproject.toml`, `docs/verification/autocad-2026-smoke.md`, `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`, `docs/compatibility.md`, `docs/roadmap.md` | E03-G3; real run waits for E03-G4 | Last |

Lane D alone edits `pyproject.toml` and canonical docs in this epic. Lane C alone edits the EPIC-02 composition seam. The integrating agent merges A, rebases/tests B, merges C and reruns fake/stdio contracts, then merges D. A subagent without access to real AutoCAD may prepare Lane D’s harness but must stop before E03-WP7 and must not fabricate verification evidence.

## Windows / AutoCAD test matrix

| Product/host | Python/dependencies | Pure import/unit | Fake adapter + MCP contracts | Real disposable-DWG suite | Required status wording |
| --- | --- | --- | --- | --- | --- |
| Linux, CPython 3.12 | Frozen lock; COM markers skipped | Required | Required | Prohibited | Pure Python unit tested / MCP contract tested only |
| Windows 11, CPython 3.12, AutoCAD closed | Frozen lock; COM packages installed | Required; delayed imports | Required; unavailable classification | Not applicable | No AutoCAD verification |
| Full AutoCAD 2026 on Windows 11 | Same accepted lock | Required | Required | Required for E03-G5: status, list/detail, unchanged fingerprint/DWG, shutdown, reconnect | “AutoCAD 2026 verified for read-only Stable-core smoke scope” only after pass |
| Full AutoCAD 2025 on Windows | Same suite design | Portable tests may pass | Fake tests do not count | Not scheduled in this epic | Targeted, not verified |
| Full AutoCAD 2024 on Windows | Same suite design | Portable tests may pass | Fake tests do not count | Not scheduled in this epic | Targeted, not verified |
| Full AutoCAD 2023 on Windows | Same suite design | Portable tests may pass | Fake tests do not count | Not scheduled in this epic | Targeted, not verified |
| Full AutoCAD 2022 on Windows | Same suite design | Portable tests may pass | Fake tests do not count | Not scheduled in this epic | Targeted, not verified |
| Full AutoCAD 2021 on Windows | Same suite design | Portable tests may pass | Fake tests do not count | Not scheduled in this epic | Targeted, not verified |
| AutoCAD LT | Irrelevant | Pure modules may import | No product claim | Prohibited | Out of scope |
| macOS or Linux-hosted AutoCAD | COM runtime unavailable | Pure modules only | Fake contracts only | Prohibited | Out of scope |

Every real-installation row requires an acquired `AutoCADLease` and acquire/release evidence. Distinct lease keys arise only from the trusted machine/user/Windows-session/AutoCAD-installation/file-version facts inside `build_autocad_lease_key`; callers cannot request a release-specific or other concurrency override.

### Promotion policy for AutoCAD 2021-2025

A release-year branch, passing fake test, successful import, user anecdote, or historical claim cannot change a row. Promotion requires a real installation, the same locked or explicitly recorded dependency state, the same read-only disposable-copy guards, the same canonical smoke steps, unchanged fingerprints, successful reconnect, an actual verification record, and reviewer approval. Editing and feature-specific 3D compatibility require separate later evidence for every release.

## Acceptance criteria

- `AutoCADAdapter` has exactly the four typed methods specified above and exposes no COM, creation, edit, or arbitrary-execution surface.
- `AdapterProvider.get() -> AutoCADAdapter` is the only service composition seam; the static provider returns the injected fake and the Windows provider delays importing `windows.py` until `get()`.
- `autocad_mcp.adapter`, its protocol/capabilities/provider/fake modules, `autocad_mcp.adapter.windows_session`, and `autocad_mcp.adapter.windows` import on Linux and Windows without importing any COM package.
- `pythoncom` and `win32com.client` load only from `load_com_modules()` after a Windows adapter operation begins.
- `WindowsSessionManager.session(require_document: bool) -> Iterator[AutoCADSession]` is the single reusable COM apartment/session lifecycle for base and future Windows adapter extensions.
- Every successful `CoInitialize()` has exactly one `CoUninitialize()` on normal exit and every subsequent failure path, and neither the manager nor its consumers retain yielded COM proxies.
- Only `autocad_mcp.adapter.windows` and sibling `autocad_mcp.adapter.windows_*` implementation modules consume `WindowsSessionManager`; public protocols and domain/context/capture/edit layers never see `AutoCADSession` or COM proxies.
- The production adapter attaches through unversioned `AutoCAD.Application`, does not create a new application, and does not cache proxies across threads/calls.
- Capability detection reflects observed members and never branches on release year.
- Missing capabilities return `UNSUPPORTED_CAPABILITY` with the exact capability name.
- List, detail, status, and reconnect implement the complete base protocol; no creation or edit method exists.
- Entity outputs include a non-empty handle and retain session-local `entity_id` compatibility.
- The fake supports all four methods, deterministic existing identities, document/connection states, and one-shot failures without modeling COM.
- Reusable fake adapter contracts and three-tool service contracts pass on Linux and Windows.
- The canonical stdio server remains importable without COM and invokes synchronous adapter work via `asyncio.to_thread`.
- `DrawingCopyGuard` is COM-free and policy-neutral: it exclusively owns unique GUID-copy creation, resolved-path/source protection, initial/final hashes, active-full-name checking, close-without-save, and cleanup/preserve evidence.
- `ReadOnlyAutoCADHarness` consumes the neutral guard plus a live lease, refuses writable opens, and is not imported or inherited by EPIC-06.
- `AutoCADLease` provides exclusive current-user Windows controller ownership with owner metadata, fail-closed contention/corruption handling, paired acquire/release evidence, and stale recovery only after PID/process-creation-time death proof.
- Every real-AutoCAD runner, including future EPIC-06 runners, requires an owned lease. Isolated VMs or Windows sessions receive distinct keys only through their derived trustworthy OS/installation identities; there is no bypass parameter.
- Real tests are skipped unless `--run-autocad` and all disposable-copy guards are present.
- The AutoCAD 2026 suite uses a unique source-derived copy opened read-only, verifies status/query results, proves the source and copy file/drawing fingerprints unchanged, closes without saving, and reconnects through a new MCP process.
- A passing AutoCAD 2026 verification record contains all named environment, fixture, result, cleanup, and interaction evidence.
- AutoCAD 2021-2025 remain targeted, not verified; all editing is outside this verification, and extrusion/revolution remain unregistered.
- All final Windows and Linux regression commands pass with fresh output.
- E03-G1 through E03-G6 are approved before Roadmap Stage 2 closes.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| COM objects are used from a different apartment/thread | Acquire, use, and release every proxy inside one adapter method’s `asyncio.to_thread` worker and balanced `WindowsSessionManager.session()` context; cache no proxies. |
| Later Windows extensions duplicate apartment handling or import a private adapter method | Give `windows_context.py`, `windows_capture.py`, and `windows_edit.py` the same adapter-internal manager contract; prohibit manager/proxy exposure outside `windows*` implementation modules and test extension reuse. |
| Importing the adapter breaks Linux tests | Delay imports with `importlib.import_module` inside `load_com_modules()` and assert `sys.modules` after all pure imports. |
| Release-specific COM differences cause incorrect assumptions | Detect required members and return structured unsupported capability; keep release text informational. |
| `hasattr`/member inspection itself raises a COM exception | Centralize safe member lookup, catch COM access errors, and omit the capability without treating it as present. |
| A base adapter accidentally exposes or invokes mutation | Keep only four protocol methods/capabilities, assert no `Add*`, property setter, delete, or command path, and keep legacy mutating names outside runtime code. |
| A smoke test changes a drawing despite read-only intent | Open only a disposable copy with the read-only flag, refuse a writable document, never save or send commands, and compare file/drawing fingerprints before and after. |
| The fingerprint misses an unintended change | Combine source/copy SHA-256, size, mtime, `DBMOD`, entity count, and canonical entity-detail digest; fail if any field differs. |
| A process crash leaves the disposable copy open | Never open the source, close the read-only copy without saving when possible, preserve its path for diagnosis, and verify the source hash independently. |
| Full AutoCAD 2026 pass is generalized to all releases/features | Scope wording to the canonical smoke, retain the matrix, and require per-release/per-feature records. |
| Fake adapter grows into a misleading AutoCAD emulator | Store only contract values, reject new object-graph features, and require real integration evidence for COM behavior. |
| Internal COM errors leak machine paths or drawing content | Log only to stderr, return public error messages/details, redact personal path components in committed evidence. |
| Active document changes between read-only calls | Every operation reacquires the active document; the harness asserts the exact disposable full path and fingerprint before and after both MCP sessions. |
| Two verification controllers drive the same interactive AutoCAD installation | Require the current-user `AutoCADLease` in every runner and fail closed with owner metadata on contention. |
| A stale lease is stolen from a live or PID-reused owner | Recover only after owning the OS lock and conclusively checking PID plus process-creation time; corrupt or indeterminate state remains blocked. |
| EPIC-06 reuses the read-only wrapper for writable tests | Expose the neutral `DrawingCopyGuard` and controller lease as separate contracts; prohibit importing/subclassing `ReadOnlyAutoCADHarness` and require EPIC-06 to own a writable policy wrapper. |

## Rollback

Rollback uses focused Git reverts and never discards unrelated work.

1. If adapter integration fails before real verification, restore `autocad_mcp.runtime.create_tool_service()` to `UnavailableToolService()` while keeping pure core tests and the adapter work on its feature branch for repair.
2. Revert any compatibility/roadmap promotion before reverting code or verification documentation that supported it.
3. If a real smoke fails, close the disposable document without saving when safe, preserve the copy path for diagnosis, and keep the source fixture untouched. Do not mark E03-G5 passed.
4. If the runner loses lease ownership or cannot release normally, stop all real-AutoCAD work, preserve owner/evidence metadata, and do not recover until process death is conclusively checked.
5. If capability detection is faulty, disable only the affected capability by returning `UNSUPPORTED_CAPABILITY`; do not add a release-year branch as an emergency shortcut.
6. If any fingerprint field changes or the copy is not read-only, stop the smoke suite until the harness/adapter is corrected and re-reviewed at E03-G4.
7. Revert `src/autocad_mcp/adapter/**`, adapter tests, and runtime composition as one coherent implementation unit if the protocol itself is rejected. Keep decision/evidence history describing why.
8. After rollback run pure core/MCP tests, compileall, JSON validation, and `git diff --check`. No rollback may reintroduce eager COM imports into `autocad_mcp.server`, `src.server`, or `autocad_mcp.core`.

## Completion evidence

The pull request must provide:

- E03-G1 protocol review mapping three active tools to four read-only/status adapter methods and public errors.
- Red-then-green output for fake adapter contracts, Windows adapter import/unit tests, and adapter-to-MCP service contracts.
- Linux and Windows import evidence proving delayed COM loading.
- Mocked-COM evidence that every successful `WindowsSessionManager` initialization has exactly one uninitialization on normal and exceptional exits, plus no proxy retention, reuse by multiple Windows extensions, unversioned attachment, no application creation, read-only capability detection, allowlisted properties, and error redaction.
- Fake contract output for connected/disconnected/document/read-only states, four operations, deterministic existing handles/IDs, and every injected failure.
- Canonical stdio output using the production composition while AutoCAD is closed, showing a structured unavailable result rather than import failure.
- E03-G4 approval of the read-only disposable-copy and fingerprint harness.
- Neutral guard test evidence for unique copies, immutable source, path inequality, close-without-save, final hashes, and cleanup/preservation.
- Cross-process lease test evidence for exclusivity, protected owner metadata, paired release, live-owner refusal, conclusive stale recovery, corrupt-state refusal, absence of caller override, and distinct keys derived from genuinely distinct OS sessions.
- Raw AutoCAD 2026 smoke output and the completed `docs/verification/autocad-2026-smoke.md` actual-result record.
- Evidence that every initial/final fingerprint field matches, source/copy hashes are unchanged, both MCP processes shut down, and the second process reconnects.
- AutoCAD product/release/build, Windows build, Python/`uv` versions, `uv.lock` blob, fixture hash, exact command, duration, modal/manual interaction record.
- Full final Windows and Linux regression output.
- Compatibility and roadmap diff showing only 2026 canonical-smoke promotion and 2021-2025 still targeted/not verified.
- Reviewer approvals for E03-G1 through E03-G6.

## Handoff

After E03-G6, hand future roadmap agents:

- the stable `AutoCADAdapter` protocol and immutable identity/capability/error types;
- `AdapterProvider`, `StaticAdapterProvider`, and `WindowsAdapterProvider` as the stable adapter acquisition boundary;
- the adapter-internal `WindowsSessionManager` as the only reusable COM apartment/session lifecycle for `autocad_mcp.adapter.windows` and future sibling `windows_*` implementations, never for domain services;
- the production `WindowsAutoCADAdapter` thread/lifecycle rules;
- the focused fake and reusable contract helpers;
- the exact service mapping and structured response shapes;
- the AutoCAD 2026 verification record and disposable-DWG runner;
- neutral `DrawingCopyGuard` as the only drawing-copy/harness artifact EPIC-06 may consume; separately, every EPIC-06 real runner must acquire the controller-owned `AutoCADLease`;
- the explicit prohibition on EPIC-06 importing/subclassing `ReadOnlyAutoCADHarness`; EPIC-06 owns its writable wrapper and policy;
- the explicit evidence gap for AutoCAD 2021-2025 and all edit behavior;
- the handoff of approved line/circle and other constrained edits to EPIC-06, with extrusion/revolution unregistered until a separate 3D edit-primitive extension;
- the prohibition on version branching, proxy caching, arbitrary commands, and source/DWG mutation.

Stage 3 agents may extend drawing context through new focused interfaces without broadening this basic adapter blindly. Any new AutoCAD capability requires its own schema, fake contract, capability detection, disposable real test, and compatibility-scoped evidence.
