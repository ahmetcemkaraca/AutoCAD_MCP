# EPIC-02: Canonical MCP Core

## Status

Proposed. This epic specifies future implementation work; it does not claim the current server starts, passes tests, or connects to AutoCAD.

**Dependencies:** E01-G4 from [EPIC-01](EPIC-01-reproducible-windows-development-baseline.md) must pass before implementation. This epic produces the installable canonical package and platform-independent MCP service contract consumed by [EPIC-03](EPIC-03-windows-autocad-adapter-and-contract-tests.md). Roadmap Stage 2 remains open after this epic until EPIC-03 passes a real full AutoCAD 2026 smoke test.

**Required execution mode:** a focused feature branch and pull request. Implement work packages in sequence, start behavior changes with failing tests, and stop at each reviewer gate. Apply the approved read-only safety reduction before any canonical-server completion claim.

## Outcome

`src/autocad_mcp/server.py` is the single canonical stdio MCP implementation and the only active owner of tool, resource, and prompt registration. EPIC-02 enables installation of the PEP 621 distribution, and `mcp.json` launches it with `uv run python -m autocad_mcp.server`. The canonical package imports and starts on Windows or Linux without importing `pythoncom`, `win32com`, or `pyautocad`.

`src/server.py` remains as a protocol-safe compatibility shim for the EPIC-01 command `uv run python -m src.server`. It re-exports/delegates to `autocad_mcp.server`, owns no registrations, and is not the canonical implementation. Its retirement requires a later dedicated pull request with configuration/caller evidence; it is not deleted in this epic.

The server advertises exactly these three non-mutating tools:

1. `server_status`
2. `list_entities`
3. `get_entity_info`

Each active tool has a closed JSON Schema, explicit semantic validation, deterministic JSON success output, and a structured error envelope. The core accepts an injected `BasicToolService`, so it can be contract-tested without AutoCAD. Redacted diagnostic logs go to standard error; standard output remains exclusively owned by the MCP stdio transport.

The four observed legacy mutating schemas—`draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile`—are copied verbatim into a compatibility decision/test fixture and are absent from runtime definitions, registrations, `mcp.json`, and the help prompt. EPIC-06 later owns approved line/circle and other constrained editing through its review and authorization controls. Extrusion and revolution remain unregistered until a separately reviewed 3D edit-primitive extension exists.

`src/mcp_server.py` and the Flask-oriented tests are retired only after replacement tests prove the canonical behavior and a decision record explains the removal. `src/mcp_integration/enhanced_mcp_server.py` remains experimental source, is not launched, and is not imported or advertised by the canonical core.

## Evidence / problem

- At the EPIC-01 boundary, `mcp.json` selects `src.server`, which uses the low-level `mcp.server.Server` and manually registers seven tools, one `autocad://server-status` resource, and one `autocad-help` prompt.
- `src/mcp_server.py` separately registers the same seven basic tools through FastMCP. Its status payload says `tools_available: 6`, demonstrating drift.
- `src/mcp_integration/enhanced_mcp_server.py` constructs another FastMCP surface with many unvalidated experimental tools, but the root command does not start it.
- The adopted `src/server.py` catches an import error for `src.utils` and continues even though later calls still reference names that may be undefined.
- The adopted `src/server.py` returns ad hoc JSON strings, catches exceptions repeatedly, and exposes raw exception text. Validation is inconsistent: for example, the circle schema permits zero radius and several schemas accept extra properties.
- `src/utils.py` imports Windows COM modules eagerly. Importing the selected server therefore fails on a clean non-Windows environment.
- `src/server.py` already configures a standard-error stream handler, while `src/mcp_server.py` calls `print()` immediately before running its transport. Duplicate entry points make stdout safety hard to reason about.
- `tests/test_server.py` and `tests/unit/test_drawing_operations.py` import `src.server.app` and exercise imagined Flask routes. The selected stdio server has no Flask `app`, so these tests cannot establish the active contract.
- The current read-only/status success payloads expose familiar top-level fields such as `success`, `count`, `entities`, `entity`, `mcp_server`, and `autocad_connected`. The consolidation should preserve those active compatibility fields while making failures structured.

These are observed source facts, not runtime verification. Current evidence remains limited to the labels in [project status](../project-status.md) and [testing](../testing.md).

## Scope

- Convert EPIC-01’s temporary non-package `uv` state into an installable PEP 621 distribution rooted at `src/autocad_mcp/`, with a concrete build backend and frozen-lock verification.
- Create a small platform-independent `src/autocad_mcp/core/` package for the three typed read-only/status requests, tool definitions, validation, responses, and the service port.
- Create `src/autocad_mcp/server.py` as the sole registration and stdio-transport implementation.
- Rewrite `src/server.py` as a tested compatibility shim that delegates to `autocad_mcp.server` without duplicating registration or writing to stdout.
- Change `mcp.json` and active documentation from `python -m src.server` to `python -m autocad_mcp.server` only after canonical and shim entry-point tests pass.
- Register exactly `server_status`, `list_entities`, and `get_entity_info`, plus one status resource and one help prompt.
- Preserve the four legacy mutating input schemas verbatim only in a compatibility fixture/decision and assert they cannot enter the active catalog.
- Preserve accepted active argument names while closing schemas with `additionalProperties: false` and adding integer-domain checks.
- Preserve familiar success fields at the top level of JSON results.
- Introduce stable structured error codes and suppress raw internal exception text.
- Inject a `BasicToolService` into the server. Provide an unavailable implementation so the core starts safely before EPIC-03 supplies the Windows adapter implementation.
- Add pure unit tests, in-process dispatch tests, and a real stdio initialization/list-tools contract test using the locked MCP client SDK.
- Prove no platform-independent import loads COM packages.
- Remove the duplicate root FastMCP server and replace the mismatched Flask tests only after replacement coverage passes.
- Keep `mcp.json`, active docs, tests, and registrations aligned.

## Out of scope

- Implementing or emulating Windows COM. EPIC-03 owns the adapter, fake adapter, and COM contract tests.
- Claiming successful drawing operations against real AutoCAD.
- Adding roadmap tools such as `query_entities`, `analyze_drawing`, visual capture, or edit plans.
- Registering or executing `draw_line`, `draw_circle`, `extrude_profile`, `revolve_profile`, or any other drawing mutation. EPIC-06 owns approved constrained edits; 3D edit primitives require a later design and review.
- Promoting any advanced or experimental tool from `src/mcp_integration/enhanced_mcp_server.py`.
- Rewriting or deleting the enhanced experimental module; it is classified, disconnected source, not a second active entry point.
- Pagination or handle-based drawing context beyond the three retained tools. Those belong to later roadmap stages.
- Adding Flask, FastAPI, HTTP, SSE, or WebSocket transport to the canonical server.
- Adding a schema-validation dependency. Three closed input shapes are small enough for explicit standard-library validation.
- Adding a console script or a second transport. The canonical launch is the requested module form `uv run python -m autocad_mcp.server`; the old module form remains shim-tested.
- Retiring `src/server.py`. Retirement needs a later focused decision after no active configuration/documentation/caller depends on the shim.

## Prerequisites

1. EPIC-01’s accepted `uv.lock` is present and `uv sync --frozen --group dev` passes in the implementation environment.
2. The implementer records the locked `mcp` package version before writing SDK-facing tests and obtains E02-G1 approval for the non-package-to-package migration.
3. All seven observed schemas are inventoried: the three non-mutating schemas become active, while the four mutating schemas are copied verbatim into the compatibility decision/test fixture before current server code is replaced.
4. The interface review at E02-G1 is approved before parallel code lanes start.
5. No test imports `src.utils`, `pythoncom`, `win32com`, or `pyautocad` to simulate success.
6. EPIC-03 implementers receive the accepted service and response types before building the adapter integration.

## Owned files and paths

| Path | Planned action | Responsibility |
| --- | --- | --- |
| `pyproject.toml` | Modify narrowly | Enable package installation with Hatchling and map the `src/autocad_mcp` wheel package |
| `uv.lock` | Regenerate | Freeze the build-backend/package-installation state without changing runtime requirements |
| `src/autocad_mcp/__init__.py` | Create | Installed project version export and package boundary |
| `src/autocad_mcp/core/__init__.py` | Create | Explicit public exports for the pure core |
| `src/autocad_mcp/core/models.py` | Create | Tool names, typed inputs, JSON types, success/error models |
| `src/autocad_mcp/core/tools.py` | Create | Three non-mutating MCP tool definitions and standard-library argument parsing |
| `src/autocad_mcp/core/service.py` | Create | `BasicToolService`, `UnavailableToolService`, dispatch/error boundary |
| `src/autocad_mcp/runtime.py` | Create | Composition root returning the current `BasicToolService`; EPIC-03 replaces only its factory body |
| `src/autocad_mcp/server.py` | Create | Canonical registrations, resource/prompt handlers, stdio lifecycle, stderr logging |
| `src/server.py` | Rewrite narrowly and retain | Compatibility shim delegating to `autocad_mcp.server`; no registrations |
| `src/mcp_server.py` | Delete after E02-G4 | Remove the duplicate root FastMCP implementation after coverage is accepted |
| `tests/unit/test_mcp_models.py` | Create | Response serialization and error redaction tests |
| `tests/unit/test_mcp_tools.py` | Create | Schema and semantic-validation tests |
| `tests/unit/test_mcp_dispatch.py` | Create | Injected-service dispatch tests for all three active tools |
| `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json` | Create | Verbatim observed schemas for four unregistered mutating tools |
| `tests/compatibility/test_legacy_mutating_tool_schemas.py` | Create | Prove fixture integrity and exclusion from runtime/manifest/help registrations |
| `tests/contract/test_stdio_server.py` | Create | Subprocess MCP initialization/list-tools/resource/prompt/stdout-boundary test |
| `tests/test_server.py` | Delete after E02-G4 | Remove invalid Flask assumptions after replacement coverage |
| `tests/unit/test_drawing_operations.py` | Delete after E02-G4 | Remove invalid Flask route suite after replacement coverage |
| `docs/decisions/0002-canonical-server-consolidation.md` | Create | Behavior inventory and evidence-backed deletion reasons |
| `mcp.json` | Modify for safety/agreement | Advertise only three non-mutating tools and align descriptions/version/module command; no transport change |
| `README.md` | Modify | Canonical server/tool wording only |
| `docs/architecture.md` | Modify after gates | Move canonical-core portion from target to adopted architecture |
| `docs/project-status.md` | Modify after gates | Record automated core evidence and remaining adapter limitation |
| `docs/testing.md` | Modify after gates | Document focused unit and MCP contract commands/results |
| `docs/roadmap.md` | Modify only to record partial evidence | Do not close Stage 2 before EPIC-03 |

No other source path is owned. In particular, `src/utils.py` and `src/mcp_integration/enhanced_mcp_server.py` are unchanged in this epic. `src/__init__.py` remains only to support the compatibility module namespace; active installed version metadata moves to `autocad_mcp.__version__`.

## Interfaces produced and consumed

### Installable package and entry-point interface

EPIC-01’s `[tool.uv] package = false` setting is temporary. This epic replaces it with:

```toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/autocad_mcp"]
```

The `[tool.uv] package = false` table is removed. `uv sync --frozen --group dev` must install the editable project distribution, so both of these imports resolve without `PYTHONPATH`:

```python
import autocad_mcp
import autocad_mcp.server
```

`src/autocad_mcp/__init__.py` produces:

```python
from importlib.metadata import version
from typing import Final

__version__: Final[str] = version("autocad-mcp")
```

The canonical launch contract becomes:

```json
{
  "command": "uv",
  "args": ["run", "python", "-m", "autocad_mcp.server"]
}
```

`src/server.py` is a compatibility module, not another implementation:

```python
import asyncio

from autocad_mcp.server import create_server, main, server

__all__ = ["create_server", "main", "server"]

if __name__ == "__main__":
    asyncio.run(main())
```

The shim emits no deprecation text to stdout because stdout is the MCP transport. Active configuration and documentation use the canonical package command. Shim retirement is allowed only in a later pull request after `git grep` proves no active repository reference uses `python -m src.server`, compatibility tests are intentionally removed, and release notes state the breaking change.

### Tool names and request models

`src/autocad_mcp/core/models.py` produces:

```python
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Mapping, TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

class ToolName(StrEnum):
    SERVER_STATUS = "server_status"
    LIST_ENTITIES = "list_entities"
    GET_ENTITY_INFO = "get_entity_info"

@dataclass(frozen=True)
class ServerStatusInput:
    tool_name: ClassVar[ToolName] = ToolName.SERVER_STATUS

@dataclass(frozen=True)
class ListEntitiesInput:
    tool_name: ClassVar[ToolName] = ToolName.LIST_ENTITIES

@dataclass(frozen=True)
class GetEntityInfoInput:
    tool_name: ClassVar[ToolName] = ToolName.GET_ENTITY_INFO
    entity_id: int

BasicToolInput: TypeAlias = (
    ServerStatusInput
    | ListEntitiesInput
    | GetEntityInfoInput
)
```

No runtime model or parser type exists for the four legacy mutating tools. Their observed JSON Schemas live only in `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json` and the consolidation decision.

### Structured response and error models

`src/autocad_mcp/core/models.py` also produces:

```python
class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    AUTOCAD_UNAVAILABLE = "AUTOCAD_UNAVAILABLE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    COM_BUSY = "COM_BUSY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AUTOCAD_OPERATION_FAILED = "AUTOCAD_OPERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

@dataclass(frozen=True)
class ToolError:
    code: ErrorCode
    message: str
    retryable: bool = False
    details: Mapping[str, JsonValue] = field(default_factory=dict)

@dataclass(frozen=True)
class ToolSuccess:
    data: Mapping[str, JsonValue]

@dataclass(frozen=True)
class ToolFailure:
    error: ToolError

ToolResponse: TypeAlias = ToolSuccess | ToolFailure

def response_payload(response: ToolResponse) -> dict[str, JsonValue]: ...
def response_json(response: ToolResponse) -> str: ...
```

Serialization is exact:

```json
{"success":true,"count":1,"entities":[{"handle":"10","id":1001,"layer":"0","type":"AcDbLine"}]}
```

or:

```json
{"success":false,"error":{"code":"AUTOCAD_UNAVAILABLE","message":"Full AutoCAD is unavailable","retryable":true,"details":{}}}
```

`response_payload()` merges `ToolSuccess.data` into the top level after reserving `success`; attempts to supply a `success` data key raise `ValueError`. JSON uses `json.dumps(..., ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)` so tests and clients receive deterministic, valid JSON.

`INTERNAL_ERROR` responses contain a generated `incident_id` in `details`, not the exception string. Stderr diagnostics retain the operation, exception class, and same incident ID, without raw exception strings or tracebacks. This 2026-10-01 correction follows the repository prohibition on logging private paths, credentials, or proprietary drawing content; public-response redaction alone was insufficient.

### Validation and schema interface

`src/autocad_mcp/core/tools.py` produces:

```python
TOOL_DEFINITIONS: tuple[mcp.types.Tool, ...]

class InvalidToolArguments(ValueError):
    tool_name: str
    field: str | None

def parse_tool_input(
    name: str,
    arguments: Mapping[str, object] | None,
) -> BasicToolInput: ...
```

All three active schemas set object type and `additionalProperties: false`. Required semantic rules are:

| Tool | Accepted fields | Domain rules |
| --- | --- | --- |
| `server_status` | none | Empty object only |
| `list_entities` | none | Empty object only |
| `get_entity_info` | `entity_id` | Non-negative integer; Boolean is rejected |

JSON Schemas express every rule representable by Draft 2020-12 keywords. `parse_tool_input()` repeats trust-boundary semantic checks because advertised schemas do not guarantee client compliance.

### Legacy mutation compatibility record

Before replacing the adopted server, copy the four observed `inputSchema` dictionaries exactly as returned by its tool-list handler into `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json`. The fixture has top-level `source_commit`, `source_path`, and `tools` fields; `tools` has exactly `draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile`. Do not tighten, normalize, or reuse these schemas in runtime code.

`tests/compatibility/test_legacy_mutating_tool_schemas.py` defines only test constants:

```python
LEGACY_MUTATING_TOOL_NAMES = frozenset(
    {"draw_line", "draw_circle", "extrude_profile", "revolve_profile"}
)
ACTIVE_TOOL_NAMES = ("server_status", "list_entities", "get_entity_info")
```

The test record contains the same four exact expected schema dictionaries and asserts fixture equality plus the exact key set. Before source replacement, its extraction check compares those dictionaries to the adopted handler; the pull request and decision record capture the fixture SHA-256 and passing output. After replacement, regression tests assert the legacy set is disjoint from `TOOL_DEFINITIONS`, the stdio `list_tools` result, `mcp.json`, and the help prompt. Importing the fixture/test module never registers a tool. This is compatibility evidence, not an executable compatibility layer.

### Service port

`src/autocad_mcp/core/service.py` produces:

```python
from typing import Protocol

class BasicToolService(Protocol):
    async def invoke(self, request: BasicToolInput) -> ToolResponse: ...

class UnavailableToolService:
    async def invoke(self, request: BasicToolInput) -> ToolResponse: ...

async def dispatch_tool(
    service: BasicToolService,
    name: str,
    arguments: Mapping[str, object] | None,
) -> ToolResponse: ...
```

`dispatch_tool()` maps `InvalidToolArguments` to `INVALID_ARGUMENT`, unknown names to `UNKNOWN_TOOL`, and unexpected exceptions to redacted `INTERNAL_ERROR`. A service may return the adapter-related error codes without the transport knowing about COM.

`UnavailableToolService` returns a structured `AUTOCAD_UNAVAILABLE` failure for query/status calls. Its error details for `server_status` include `mcp_server: "running"`, `autocad_connected: false`, `tools_available: 3`, and `transport: "stdio"` so the intermediate core reports its limitation honestly.

### Composition and server interfaces

`src/autocad_mcp/runtime.py` initially produces:

```python
from autocad_mcp.core.service import BasicToolService, UnavailableToolService

def create_tool_service() -> BasicToolService:
    return UnavailableToolService()
```

EPIC-03 consumes this seam and changes only the function body to construct the provider-backed read-only `AdapterToolService`.

`src/autocad_mcp/server.py` produces:

```python
def create_server(service: BasicToolService) -> mcp.server.Server: ...
async def main() -> None: ...
```

At module scope, `server = create_server(create_tool_service())` supports the adopted resource/prompt decorators and canonical package module entry point. Handler results remain `list[mcp.types.TextContent]` for compatibility with the locked low-level SDK; each text block contains `response_json(...)`. The core does not write ordinary output with `print()`.

### Interfaces consumed

- PEP 621 project version `0.1.0`, dependency lock, and temporary `src.server` command from EPIC-01; this epic moves version access to installed metadata and migrates the command under reviewer control.
- Seven-tool temporary manifest from EPIC-01, reduced here to the exact three-tool active catalog after compatibility snapshots and entry-point tests are in place.
- `AutoCADAdapter`, `AdapterToolService`, and error mapping supplied by EPIC-03 through the `BasicToolService` port.
- The low-level `mcp.server.Server` and `mcp.types` API resolved in EPIC-01’s accepted `uv.lock`.

## Work packages

### E02-WP1: Approve the compatibility and type contract

**Sequence:** 1. **Reviewer gate:** E02-G1.

**Files:** create `docs/decisions/0002-canonical-server-consolidation.md`, `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json`, and `tests/compatibility/test_legacy_mutating_tool_schemas.py`; no source deletion.

1. Record each existing tool name, input property, required-property list, valid example, top-level success fields, the resource URI, and prompt name from both root servers.
2. Copy the four mutating schemas verbatim to the compatibility fixture, calculate its SHA-256, and record that digest in the decision. Run the extraction/equality check against the still-present adopted handler before replacing or deleting server code.
3. Write the exclusion test and capture its red state: it must fail while the adopted seven-tool server/manifest still register legacy mutation names.

   ```powershell
   Get-FileHash tests/fixtures/compatibility/legacy-mutating-tool-schemas.json -Algorithm SHA256
   uv run pytest tests/compatibility/test_legacy_mutating_tool_schemas.py -q
   ```

   Expected result: schema extraction/equality passes, while active-catalog exclusion fails because the EPIC-01 server still exposes the four names.
4. Record these explicit decisions: EPIC-01 non-package mode is temporary; Hatchling installs `src/autocad_mcp`; `autocad_mcp.server` becomes canonical; `src.server` becomes a tested shim; low-level `Server` and stdio remain; exactly three non-mutating tools are active; four mutating schemas are evidence-only; failures adopt the `ToolError` envelope; EPIC-06 owns constrained edits; 3D edit primitives remain unregistered; duplicate FastMCP/Flask artifacts are removed after replacement coverage.
5. Record `src/mcp_integration/enhanced_mcp_server.py` as experimental and unconnected. It is not evidence of active tools and is not deleted in this epic.
6. Compare the Python interfaces and semantic table above for naming/type consistency.
7. E02-G1 passes when the reviewer accepts the package/entry migration, shim-retirement gate, three-tool active matrix, legacy-schema digest/exclusion policy, error codes, and `BasicToolService` boundary. Any interface revision must update this epic before parallel implementation starts.

### E02-WP2: Enable the installable canonical package test-first

**Sequence:** 2. **Depends on:** E02-G1. **Reviewer gate:** none; package evidence is included in E02-G2.

**Files:** `pyproject.toml`, `uv.lock`, `src/autocad_mcp/__init__.py`, `tests/unit/test_package_entrypoints.py`.

1. Write failing tests that assert `importlib.util.find_spec("autocad_mcp")` is present after sync, `importlib.metadata.version("autocad-mcp") == "0.1.0"`, `autocad_mcp.__version__` matches installed metadata, and no `PYTHONPATH` is required.
2. Add a manifest test asserting the exact Hatchling configuration above, absence of `[tool.uv] package = false`, and wheel package path `src/autocad_mcp`.
3. Capture the red state under EPIC-01 configuration:

   ```powershell
   uv run pytest tests/unit/test_package_entrypoints.py -q
   ```

   Expected result: failure because `autocad_mcp` does not exist and the project is not installed.
4. Create `src/autocad_mcp/__init__.py`, enable Hatchling packaging exactly as specified, regenerate the lock, and perform a clean frozen sync.
5. Verify package installation on Windows and Linux:

   ```powershell
   uv lock --check
   uv sync --frozen --group dev
   uv run python -c "import autocad_mcp, importlib.metadata; assert autocad_mcp.__version__ == importlib.metadata.version('autocad-mcp') == '0.1.0'"
   uv run pytest tests/unit/test_package_entrypoints.py -q
   ```

6. Review the `uv.lock` diff and prove runtime direct requirements did not change. This work package changes installation mechanics, not product dependencies.

### E02-WP3: Build typed models and closed schemas test-first

**Sequence:** 3. **Depends on:** E02-WP2. **Reviewer gate:** E02-G2.

**Files:** `src/autocad_mcp/core/__init__.py`, `src/autocad_mcp/core/models.py`, `src/autocad_mcp/core/tools.py`, `tests/unit/test_mcp_models.py`, `tests/unit/test_mcp_tools.py`.

1. Write failing tests that import every exact name in the interfaces above.
2. Parameterize schema tests across the three ordered `ToolName` values. Assert exact order `server_status`, `list_entities`, `get_entity_info`, object type, `additionalProperties is False`, empty arguments for status/list, and non-negative integer `entity_id` for detail.
3. Parameterize parser success for `{}` status/list arguments and non-negative entity IDs.
4. Parameterize parser failures for extra fields, missing `entity_id`, Boolean/non-integer/negative entity IDs, and every legacy mutating tool name; legacy names must return `UNKNOWN_TOOL`, not parse a request.
5. Add response tests for stable compact JSON, `allow_nan=False`, top-level compatibility fields, error shape, reserved `success` key rejection, and no raw exception field.
6. Run the red tests:

   ```powershell
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/compatibility/test_legacy_mutating_tool_schemas.py -q
   ```

   Expected result: import failures because `autocad_mcp.core` does not exist.
7. Implement the smallest three request models, schemas, and explicit parser that satisfy the table. Do not add mutation request types or a JSON Schema runtime dependency.
8. Run focused and static verification:

   ```powershell
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/compatibility/test_legacy_mutating_tool_schemas.py -q
   uv run ruff check src/autocad_mcp/core tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py
   uv run python -m compileall -q src/autocad_mcp/core tests/unit
   ```

9. E02-G2 passes when frozen package installation/version evidence, schema snapshots, parser rules, and serialized examples are reviewer-approved and the focused suites pass.

### E02-WP4: Add the service port and centralized dispatch

**Sequence:** 4. **Depends on:** E02-G2. **Reviewer gate:** none; included in E02-G3.

**Files:** `src/autocad_mcp/core/service.py`, `src/autocad_mcp/runtime.py`, `tests/unit/test_mcp_dispatch.py`.

1. Write a test-local `RecordingToolService` implementing `invoke()` and returning deterministic `ToolSuccess` objects for the three active input classes.
2. Write failing tests that call `dispatch_tool()` and assert:

   - each valid tool reaches the service with the correct immutable input type;
   - missing and malformed arguments return `INVALID_ARGUMENT` without calling the service;
   - an unknown tool returns `UNKNOWN_TOOL`;
   - a raised `RuntimeError("secret COM detail")` records its class and incident ID and returns `INTERNAL_ERROR`, with the secret absent from both diagnostics and tool output;
   - every legacy mutating name returns `UNKNOWN_TOOL` without calling the service;
   - `UnavailableToolService` returns `AUTOCAD_UNAVAILABLE`, reports three tools, and never imports COM modules.

3. Capture the expected red state:

   ```powershell
   uv run pytest tests/unit/test_mcp_dispatch.py -q
   ```

4. Implement the service protocol, unavailable implementation, dispatch mapping, and composition root exactly as specified.
5. Run:

   ```powershell
   uv run pytest tests/unit/test_mcp_dispatch.py -q
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py -q
   uv run ruff check src/autocad_mcp/core src/autocad_mcp/runtime.py tests/unit/test_mcp_dispatch.py
   ```

### E02-WP5: Create the canonical package server and compatibility shim

**Sequence:** 5. **Depends on:** E02-WP4. **Reviewer gate:** E02-G3.

**Files:** `src/autocad_mcp/server.py`, `src/server.py`, `mcp.json`, `tests/contract/test_stdio_server.py`.

1. Write failing import tests that remove any loaded server modules, import canonical `autocad_mcp.server` and compatibility `src.server`, assert both expose the same `server`, `create_server`, and `main` objects, and assert these names are absent from `sys.modules`: `pythoncom`, `win32com`, `win32com.client`, and `pyautocad`.
2. Write an in-process registration test around `create_server(RecordingToolService())` and assert exactly the three ordered definitions, resource URI, and prompt name. Assert the four legacy mutating names are absent from registrations and help.
3. Write a parameterized subprocess contract using the locked SDK’s `mcp.client.stdio.stdio_client`, `StdioServerParameters`, and `ClientSession`. Run it once with `args=["-m", "autocad_mcp.server"]` and once with `args=["-m", "src.server"]`. Both must:

   - initialize successfully;
   - list exactly `server_status`, `list_entities`, and `get_entity_info`;
   - list/read `autocad://server-status` and parse its JSON;
   - list/get `autocad-help`;
   - call `server_status` and receive a structured unavailable result before EPIC-03;
   - capture stderr separately and prove any startup log is there;
   - complete without a non-protocol stdout line.

4. Run the tests before replacing the server:

   ```powershell
   uv run pytest tests/contract/test_stdio_server.py -q
   ```

   Expected result: failure because the canonical package server does not exist and the adopted server reaches COM.
5. Create `src/autocad_mcp/server.py` as registration/transport composition around `create_server()`, `dispatch_tool()`, and `response_json()`. Configure logging only to `sys.stderr`. Remove repeated tool-level exception handlers and every ordinary stdout write.
6. Use `autocad_mcp.__version__` in `InitializationOptions`. Keep the status resource and help prompt routed through the same definitions so their tool count cannot drift. Rewrite `src/server.py` to the exact compatibility shim above; it contains no decorators or tool definitions.
7. Run focused contract verification:

   ```powershell
   uv run pytest tests/contract/test_stdio_server.py -q
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py -q
   uv run ruff check src/autocad_mcp src/server.py tests/contract/test_stdio_server.py
   uv run python -m compileall -q src tests
   ```

8. On both Linux and Windows without starting AutoCAD, run:

   ```powershell
   uv run python -c "import autocad_mcp.server, src.server, sys; assert 'pythoncom' not in sys.modules; assert 'win32com' not in sys.modules; assert 'pyautocad' not in sys.modules"
   uv run pytest tests/contract/test_stdio_server.py -q
   ```

9. Change `mcp.json` to `uv run python -m autocad_mcp.server` only after both subprocess variants pass. E02-G3 passes when both platforms initialize through the canonical command and shim, all output is protocol-safe, the shim owns no registrations, and the reviewer sees no COM import in the core call path.

### E02-WP6: Retire duplicate server and mismatched Flask tests

**Sequence:** 6. **Depends on:** E02-G3. **Reviewer gate:** E02-G4 before deletion merge.

**Files:** finish `docs/decisions/0002-canonical-server-consolidation.md`; delete `src/mcp_server.py`, `tests/test_server.py`, and `tests/unit/test_drawing_operations.py`.

1. Complete a replacement matrix in the decision record:

   | Removed behavior claim | Replacement evidence |
   | --- | --- |
   | Three non-mutating root tools | Canonical schema/order/dispatch plus stdio `list_tools` contracts |
   | Four legacy mutating tool schemas | Verbatim fixture/digest retained; explicit runtime/manifest/help exclusion tests; implementation deliberately not replaced in Stable core |
   | FastMCP status resource | Canonical status resource contract |
   | FastMCP help prompt | Canonical prompt contract |
   | Flask `/health` | Not an MCP behavior; remove rather than replace |
   | Flask `/acad-status` | `server_status` structured contract; real connection deferred to EPIC-03 |
   | Imagined Flask draw routes | Not selected MCP behavior; no replacement or registration; EPIC-06 owns future constrained edits |

2. Prove no active configuration imports or starts the duplicate files:

   ```powershell
   git grep -n -E 'src\.mcp_server|src/mcp_server\.py|enhanced_mcp_server' -- ':!docs/legacy/**'
   python -m json.tool mcp.json > $null
   ```

3. E02-G4 passes when a reviewer confirms each valid selected-server behavior has replacement coverage and Flask-only expectations were never part of the adopted MCP surface.
4. Delete only the three approved files. Do not delete the enhanced experimental module or historical documents.
5. Run all replacement tests immediately after deletion:

   ```powershell
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
   uv run python -m compileall -q src tests
   git diff --name-status -- src/mcp_server.py tests/test_server.py tests/unit/test_drawing_operations.py docs/decisions/0002-canonical-server-consolidation.md
   ```

### E02-WP7: Align manifest and canonical documentation

**Sequence:** 7. **Depends on:** E02-G4. **Reviewer gate:** E02-G5.

**Files:** `README.md`, `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`, `docs/roadmap.md`. `mcp.json` remains owned by E02-WP5.

1. Add a test in `tests/unit/test_mcp_tools.py` that parses `mcp.json` and compares the exact ordered tool names with `TOOL_DEFINITIONS`. Make it fail before correcting any drift.
2. Confirm E02-WP5 changed `mcp.json` to `uv run python -m autocad_mcp.server` and aligned exactly three tool descriptions, one resource, one prompt, and version. This documentation package does not edit the manifest.
3. Move the canonical server, pure schema modules, structured errors, and stdio logging from target to adopted architecture. Record the active catalog as three non-mutating tools and route constrained edits to EPIC-06. Keep the Windows adapter labelled target until EPIC-03.
4. In project status and testing, record named unit/MCP contract commands and platforms. Explicitly state that successful fake/unavailable-service tests are not AutoCAD verification.
5. Do not mark roadmap Stage 2 complete. Revise its obsolete line/circle Stable-core criteria to read-only/status adapter contracts and an unchanged-DWG AutoCAD 2026 gate; record that canonical-core criteria passed and EPIC-03 remains.
6. Run the complete epic verification on Windows and Linux:

   ```powershell
   uv sync --frozen --group dev
   uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
   uv run ruff check src tests
   uv run python -m compileall -q src tests
   uv run python -c "import autocad_mcp.server, src.server, sys; assert not {'pythoncom','win32com','pyautocad'} & set(sys.modules)"
   python -m json.tool mcp.json > $null
   git diff --check
   ```

7. E02-G5 passes when a reviewer compares registrations, manifest, tests, and docs; sees exactly three non-mutating tools; sees the four legacy names only in compatibility evidence; and confirms no AutoCAD release was promoted.

## Parallel subagent lanes

Parallel lanes begin only after E02-G1 freezes names and types. File ownership is exclusive even when a lane waits for another lane’s interface.

| Lane | Work packages | Exclusive file ownership | Dependency | Integration order |
| --- | --- | --- | --- | --- |
| E02-P: package installation | E02-WP2 | `pyproject.toml`, `uv.lock`, `src/autocad_mcp/__init__.py`, `tests/unit/test_package_entrypoints.py` | E02-G1 | First |
| E02-A: types and validation | E02-WP3 | `src/autocad_mcp/core/__init__.py`, `src/autocad_mcp/core/models.py`, `src/autocad_mcp/core/tools.py`, `tests/unit/test_mcp_models.py`, `tests/unit/test_mcp_tools.py` | E02-WP2 | Second, after E02-G2 |
| E02-B: service and transport | E02-WP4, E02-WP5 | `src/autocad_mcp/core/service.py`, `src/autocad_mcp/runtime.py`, `src/autocad_mcp/server.py`, `src/server.py`, `mcp.json`, `tests/unit/test_mcp_dispatch.py`, `tests/contract/test_stdio_server.py` | Uses Lane A interfaces | Third, after E02-G3 |
| E02-C: consolidation evidence | E02-WP1, E02-WP6 | `docs/decisions/0002-canonical-server-consolidation.md`, `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json`, `tests/compatibility/test_legacy_mutating_tool_schemas.py`, `src/mcp_server.py`, `tests/test_server.py`, `tests/unit/test_drawing_operations.py` | Deletion waits for E02-G4 | Fourth |
| E02-D: evidence docs | E02-WP7 | `README.md`, `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`, `docs/roadmap.md` | E02-G4 plus merged results | Last |

Lane A owns `tests/unit/test_mcp_tools.py`, including the manifest-agreement test; Lane B owns the manifest it checks. Lane A communicates the accepted expected values and never edits `mcp.json`. Lane P owns package/lock conflicts. The integrating agent merges P, rebases A, integrates B, integrates C after approval, then lets D document the merged result.

## Windows / AutoCAD test matrix

| Host/product | Core import | Unit/schema/dispatch | Real stdio session | COM activity | Evidence label after this epic |
| --- | --- | --- | --- | --- | --- |
| Linux, CPython 3.12 | Required to pass without COM modules | Required | Required through canonical `python -m autocad_mcp.server` and shim `python -m src.server` | None | Pure Python unit tested; MCP contract tested |
| Windows 11, CPython 3.12, AutoCAD closed | Required to pass without loading COM | Required | Required | None | Pure Python unit tested; MCP contract tested |
| Windows 11 + full AutoCAD 2026 | Same tests may run with application closed | Required | Required | Deliberately none | Still targeted; not AutoCAD verified by EPIC-02 |
| Windows + full AutoCAD 2021-2025 | Not required on every installation in this epic | Portable core expected | No release-specific run claimed | None | Targeted, not verified |
| AutoCAD LT / Linux-hosted AutoCAD / macOS | Pure core may import where Python supports it | Optional pure tests only | Not a product-runtime claim | None | Out of scope for AutoCAD operation |

The default unavailable service is an honest intermediate composition. EPIC-03 replaces it with the Windows adapter and owns all claims about connected operations.

## Acceptance criteria

- `uv sync --frozen --group dev` installs the `autocad-mcp` distribution from `src/autocad_mcp`, and installed metadata reports version `0.1.0`.
- `uv run python -m autocad_mcp.server` initializes as the canonical MCP stdio process using the locked SDK.
- `uv run python -m src.server` initializes through a retained compatibility shim with the same protocol behavior and no duplicate registration.
- `src/autocad_mcp/server.py` is the only active stdio implementation and owns all active registrations; `src/server.py` only delegates/re-exports.
- Exactly `server_status`, `list_entities`, and `get_entity_info` are present in `TOOL_DEFINITIONS`, `autocad_mcp.server`, `mcp.json`, the help prompt, tests, and active docs.
- `draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile` exist only in the decision/test fixture, are absent from every active catalog surface, and return `UNKNOWN_TOOL` if called.
- Valid active examples parse into the specified immutable inputs; invalid, extra, Boolean, non-integer, and negative entity-ID values return `INVALID_ARGUMENT`.
- Every schema is closed with `additionalProperties: false` and expresses the applicable bounds.
- Success JSON preserves `success` and existing top-level status/query fields.
- All failures use the structured `ToolError` envelope and stable `ErrorCode` values.
- Unexpected exceptions are logged by class with an incident ID to stderr; raw exception details and traceback content are absent from diagnostics and tool output.
- Importing `autocad_mcp.server`, `src.server`, and all `autocad_mcp.core` modules on Linux and Windows does not load any COM package.
- A subprocess client initializes, lists tools/resources/prompts, reads status, and shuts down without non-protocol stdout.
- `src/mcp_server.py` and the two Flask-oriented test files are deleted only after E02-G4 and their decision record identifies replacement evidence.
- `src/mcp_integration/enhanced_mcp_server.py` is not imported, launched, or advertised by the canonical core and remains documented as experimental.
- Focused tests, Ruff, compileall, JSON validation, and `git diff --check` pass with fresh output on Linux and Windows.
- Docs record canonical-core evidence without closing Stable MCP core or promoting AutoCAD compatibility.
- E02-G1 through E02-G5 are approved.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Consolidation breaks clients that parse current read-only/status fields | Preserve top-level `success`, `count`, `entities`, `entity`, and status fields; snapshot them before deletion. |
| A legacy mutating tool is accidentally re-registered | Keep its schema only in a test fixture, define no runtime input model, and assert exclusion from definitions, dispatch, manifest, prompt, and stdio results. |
| Safety reduction surprises a client using legacy mutations | Record the intentional incompatibility, return `UNKNOWN_TOOL`, route future constrained edits to EPIC-06, and do not preserve an unsafe executable shim. |
| Error standardization leaks COM paths or drawing data | Expose stable public messages and correlate redacted operation/class diagnostics with generated incident IDs; never log raw exception text or tracebacks. |
| Startup logs corrupt MCP stdout | Remove `print()`, configure stderr explicitly, and exercise a real subprocess through the SDK client. |
| A type-only import reintroduces COM at runtime | Core types are defined in `autocad_mcp.core`; use no adapter import in core and assert `sys.modules` after import. |
| Package migration breaks the EPIC-01 command before consumers move | Keep `src.server` as a subprocess-tested delegation shim and change `mcp.json` only after both entry forms pass. |
| `UnavailableToolService` is mistaken for completed AutoCAD functionality | Document it as an intermediate composition, keep Stage 2 open, and require EPIC-03 for connected claims. |
| Deleting stale tests reduces line count and looks like lost coverage | Require the explicit replacement matrix and passing canonical contract tests before deletion. |
| Experimental enhanced code is mistaken for a second supported server | Keep it disconnected, remove broken launch references in EPIC-01, and label it experimental in current status/architecture docs. |
| Hand-written validation diverges from advertised schemas | Parameterize the same boundary cases through schema inspection and `parse_tool_input`; keep both in one owned module. |

## Rollback

Use focused Git reverts; do not reset or overwrite unrelated changes.

1. Revert documentation claims first if a core verification result is invalidated.
2. Restore `src/mcp_server.py` or the Flask test files only if a concrete current consumer is identified. Restored code must remain unselected and documented; do not restore it as a competing canonical entry point.
3. Revert `src/autocad_mcp/server.py`, `src/autocad_mcp/core/`, `src/autocad_mcp/runtime.py`, and the `src/server.py` shim as one behavior unit if the locked MCP SDK cannot initialize the new composition.
4. Revert Hatchling configuration and `uv.lock` together if the installed package cannot be reproduced; restore EPIC-01’s temporary non-package state and command as one unit.
5. Retain the consolidation decision record and append rollback evidence so the history remains intelligible.
6. Restore `mcp.json` only to the EPIC-01 module command, never to an enhanced or HTTP server.
7. After rollback run:

   ```powershell
   uv run python -m compileall -q src tests
   python -m json.tool mcp.json > $null
   git diff --check
   ```

Rollback returns the project to the previous evidence level; it does not make the old Flask tests valid or either duplicate server supported.

## Completion evidence

The pull request must include:

- The accepted package/entry migration, three-tool active matrix, and four-schema evidence-only decision from E02-G1.
- Hatchling configuration, `uv.lock` diff review, frozen installation output, and installed metadata/version proof on Windows and Linux.
- The locked `mcp` version used by tests.
- Focused red-then-green output for models/schemas, dispatch, and stdio work packages.
- Linux and Windows `sys.modules` evidence showing no COM modules loaded by core import.
- Subprocess MCP session results for canonical `autocad_mcp.server` and compatibility `src.server`, each showing initialization, exactly three tools, one resource, one prompt, structured status failure, and clean shutdown.
- Captured stderr/stdout separation evidence.
- Three active schema snapshots, the digested verbatim legacy-mutating fixture, exclusion-test output, and serialized success/failure examples.
- The completed replacement matrix and `git diff --name-status` for deleted duplicate/test files.
- Full Ruff, compileall, manifest JSON, whitespace, and focused pytest outputs.
- Updated architecture/status/testing/roadmap wording with Stage 2 still open pending EPIC-03.
- Reviewer approvals for E02-G1 through E02-G5.

## Handoff

Give the EPIC-03 implementer:

- the `BasicToolInput` union and all exact dataclass field types;
- `BasicToolService.invoke(request) -> ToolResponse`;
- stable error codes and public-message/redaction rules;
- deterministic success payload expectations for the three active tools;
- the `autocad_mcp.runtime.create_tool_service()` composition seam;
- accepted tool schemas and contract tests;
- the rule that synchronous COM work must never enter the pure core import path;
- the regenerated package-enabled `uv.lock`, installed `autocad_mcp` import boundary, and Windows CPython 3.12 baseline.
- the reserved adapter namespace `src/autocad_mcp/adapter/` with required `protocol.py`, `capabilities.py`, `provider.py`, `fake.py`, and `windows.py` ownership assigned to EPIC-03.

EPIC-03 must implement the three-tool service port through a four-method read-only/status adapter, run those contracts with a focused fake, and obtain unchanged-DWG full AutoCAD 2026 evidence before anyone closes Stable MCP core. EPIC-06 receives ownership of approved editing; neither EPIC-02 nor EPIC-03 may register a mutation.
