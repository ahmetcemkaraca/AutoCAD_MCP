# First Safe Local AutoCAD Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first locally testable, read-only AutoCAD MCP release on `codex/local-autocad-testable`, with reproducible Windows setup and a guarded AutoCAD 2026 smoke handoff.

**Architecture:** First migrate the dependency baseline to locked PEP 621/uv metadata, then make one installable, pure canonical MCP core with three read-only tools, then add a delayed Windows adapter and an opt-in disposable-DWG smoke harness. The canonical server owns registrations; the adapter is the only COM boundary; the real smoke owns a temporary read-only drawing copy and a trusted lease.

**Tech Stack:** CPython 3.12, uv, PEP 621, Hatchling, the locked low-level MCP SDK, pytest, Ruff, mypy, PowerShell, Windows COM, and full AutoCAD 2026.

**Spec:** `docs/epics/EPIC-01-reproducible-windows-development-baseline.md`, `docs/epics/EPIC-02-canonical-mcp-core.md`, and `docs/epics/EPIC-03-windows-autocad-adapter-and-contract-tests.md`

**Execution state:** Started from `00207ed084e9ef81538b5283615e689d483632d1` on the isolated `codex/local-autocad-testable` branch. Source inventory is complete; no implementation result is implied by this plan.

## Global Constraints

- The only active tools at handoff are `server_status`, `list_entities`, and `get_entity_info`; no tool mutates a drawing.
- Preserve `draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile` only as unregistered compatibility evidence.
- The canonical command is `uv run python -m autocad_mcp.server`; `src.server` remains a protocol-safe tested shim.
- Use standard-library validation and existing locked dependencies; do not add a JSON-schema or COM abstraction dependency.
- Normal logs and tracebacks go to stderr; MCP stdout contains protocol messages only.
- COM imports are delayed behind `autocad_mcp.adapter.windows_session.load_com_modules()`; never import COM from pure/core/server modules.
- The public `AutoCADAdapter` has exactly four methods: `status`, `reconnect`, `list_entities`, and `get_entity_info`.
- The first real test attaches only to an already-running full AutoCAD 2026 instance, opens only a unique copy of an immutable source DWG as read-only, and fails closed on lease, path, writable-open, or fingerprint violations.
- Linux results are pure-Python/MCP-contract evidence only. AutoCAD 2021-2025 remain targeted, not verified.
- Before each commit/push: inspect the exact diff, run the checkpoint test, preserve unrelated changes, and verify the branch/PR destination. Never force-push or merge a PR.

## Impact-Based Test Map

| Area | First focused proof | Broader evidence | Platform boundary |
| --- | --- | --- | --- |
| EPIC-01 metadata/launch | `tests/unit/test_project_metadata.py` | lock, frozen sync, JSON, Ruff, compileall | Linux proves COM packages are absent; Windows proves they install |
| EPIC-01 Docker decision | static missing-input/disposition checks | `docker compose config` only when Docker exists | no Docker image claim without a run |
| EPIC-02 package/core | package entry, model, schema, dispatch tests | canonical + shim stdio subprocess contract | no COM package may enter `sys.modules` |
| EPIC-02 safety reduction | legacy-schema fixture/exclusion test | manifest/help/catalog/stdout agreement | mutation tools fail as `UNKNOWN_TOOL` |
| EPIC-03 protocol/fake | adapter protocol/fake/capability tests | fake adapter-to-service + core contracts | pure Linux tests only |
| EPIC-03 Windows boundary | delayed-import, session-lifecycle, mocked-COM tests | expected unavailable classification with AutoCAD closed | COM lifecycle evidence is separate from AutoCAD evidence |
| EPIC-03 real safety | copy-guard/lease/harness tests | opt-in 2026 smoke through two MCP processes | only Windows full AutoCAD can promote the named smoke scope |
| Final handoff | complete active platform-independent suite | metadata/lock/stdio/diff checks and Windows operator guide | do not claim real-AutoCAD verification without returned smoke evidence |

---

### Task 1: Freeze the source inventory and review ledger

**Files:**
- Create: `docs/verification/epic-01-work-package-review-matrix.md`
- Create: `docs/verification/epic-02-work-package-review-matrix.md`
- Create: `docs/verification/epic-03-work-package-review-matrix.md`
- Create: `docs/verification/progress-evidence-log.md`

**Interfaces:**
- Consumes: the three approved epic documents and baseline source inventory.
- Produces: reviewer assignments, checkpoint evidence locations, and a concise ongoing evidence log.

- [x] Record the baseline commit, direct dependency inventory, seven current schemas, source/launch mismatch, and stale Docker observations.
- [x] Add one row per named work package with an implementer, independent contract reviewer, independent quality reviewer, exact evidence artifact, and gate authority.
- [x] Record that Windows AutoCAD evidence is human-operator-only and is not substituted by Linux/fake checks.

### Task 2: Establish EPIC-01 metadata red evidence

**Files:**
- Create: `tests/unit/test_project_metadata.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `pyproject.toml`, `mcp.json`, and `src.__version__`.
- Produces: a focused behavior check for PEP 621 metadata, version agreement, Windows COM markers, and the temporary module launch contract.

- [x] Write tests that parse TOML/JSON and exercise the module boundary through the synchronized project virtual environment; installed-distribution checks begin in EPIC-02.
- [x] Narrowly unignore `tests/**/test_*.py` so required repository tests are visible to Git while scratch tests elsewhere remain ignored.
- [x] Capture the red result before changing manifests; if current dependencies make collection unavailable, preserve that exact collection failure as the documented red state.
- [x] Keep expectations scoped to behavior consumed by uv/MCP configuration: matching version, module arguments, absent `PYTHONPATH`, no Poetry tables, no `pypiwin32`, and exact Windows markers.

### Task 3: Migrate the reproducible dependency baseline

**Files:**
- Modify: `pyproject.toml`, `src/__init__.py`, `src/server.py`, `mcp.json`
- Create: `uv.lock`
- Delete only after both-platform evidence: `poetry.lock`

**Interfaces:**
- Consumes: EPIC-01's exact dependency range translation and the metadata test from Task 2.
- Produces: PEP 621 dependencies, optional ML group, `dev` dependency group, `pywin32`/`pyautocad` Windows markers, `src.__version__ == "0.1.0"`, and `uv run python -m src.server`.

- [x] Change only packaging/dependency/version/launch mechanics; do not redesign registrations or move COM imports.
- [x] Generate `uv.lock` with CPython 3.12, then run the metadata test green, `uv lock --check`, Linux frozen sync, COM-absence probe, compileall, JSON validation, and relevant lint.
- [x] Defer deletion of `poetry.lock` until the Windows frozen-sync evidence is recorded by the operator.

### Task 4: Decide the unsupported container artifacts

**Files:**
- Create: `docs/decisions/0001-container-artifact-disposition.md`
- Delete only after documented maintainer-equivalent review gate: `Dockerfile`, `docker-compose.yml`

**Interfaces:**
- Consumes: static observations, product Windows-COM boundary, and Docker availability result.
- Produces: an evidence-backed retain/archive/remove decision with reintroduction criteria.

- [x] Record fixed headings: Context, Product runtime boundary, Reproducible observations, Options considered, Decision, Consequences, and Reintroduction criteria.
- [x] Prove missing required inputs and record that a Linux container cannot represent the supported runtime.
- [x] Defer root-artifact removal because decision 0001 requires explicit E01-G3 maintainer approval that is not available; keep them clearly unsupported.

### Task 5: Close the EPIC-01 documentation/checkpoint

**Files:**
- Modify: `README.md`, `docs/testing.md`, `docs/project-status.md`, `docs/compatibility.md` when an actual platform result requires it

**Interfaces:**
- Consumes: fresh EPIC-01 command output and the Docker disposition.
- Produces: exact reproducible setup wording without an AutoCAD claim.

- [x] Record Linux evidence and retain the Windows dependency-sync gate as operator-only pending evidence.
- [x] Run the complete active EPIC-01 checks after integrated changes: lock, frozen sync, metadata test, Ruff, compileall, JSON, and diff check.

**Execution note:** This task is intentionally deferred until final handoff assembly. It will report Windows and Docker-removal gates as pending unless fresh operator/maintainer evidence exists; it does not block the user-authorized Linux-built EPIC-02/03 preparation.

### Task 6: Freeze EPIC-02 compatibility evidence before core replacement

**Files:**
- Create: `docs/decisions/0002-canonical-server-consolidation.md`
- Create: `tests/fixtures/compatibility/legacy-mutating-tool-schemas.json`
- Create: `tests/compatibility/test_legacy_mutating_tool_schemas.py`

**Interfaces:**
- Consumes: the seven schemas in baseline `src/server.py` and temporary manifest.
- Produces: a digested verbatim four-schema record and exclusion test for the final three-tool catalog.

- [x] Snapshot only `draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile` exactly as observed.
- [x] Capture the deliberate red state while current active metadata still exposes legacy mutations.
- [x] Freeze error codes, active ordering, the `BasicToolService` seam, and the shim rule before parallel implementation starts.

### Task 7: Enable the installable canonical package

**Files:**
- Modify: `pyproject.toml`, `uv.lock`
- Create: `src/autocad_mcp/__init__.py`, `tests/unit/test_package_entrypoints.py`

**Interfaces:**
- Consumes: EPIC-01 lock/version state.
- Produces: Hatchling-installed `autocad_mcp` with installed version agreement and no `PYTHONPATH` requirement.

- [x] Write and verify failing package-entry tests before replacing `[tool.uv] package = false`.
- [x] Enable only the designated wheel package, regenerate the lock, run frozen sync, and prove import/installed metadata agreement on available hosts.

### Task 8: Implement typed core schemas and responses

**Files:**
- Create: `src/autocad_mcp/core/__init__.py`, `src/autocad_mcp/core/models.py`, `src/autocad_mcp/core/tools.py`
- Create: `tests/unit/test_mcp_models.py`, `tests/unit/test_mcp_tools.py`

**Interfaces:**
- Produces: `ToolName`, immutable three-request union, `ToolSuccess`/`ToolFailure`, redacted `ErrorCode`, deterministic JSON, three closed tool schemas, and parser validation.

- [x] Capture red import/schema/parser tests.
- [x] Implement exactly `server_status`, `list_entities`, and non-negative non-Boolean `get_entity_info.entity_id`.
- [x] Run focused model/schema/exclusion tests, lint, and compile checks.

### Task 9: Implement the service port and unavailable composition

**Files:**
- Create: `src/autocad_mcp/core/service.py`, `src/autocad_mcp/runtime.py`
- Create: `tests/unit/test_mcp_dispatch.py`

**Interfaces:**
- Consumes: Task 8 types and definitions.
- Produces: `BasicToolService`, `UnavailableToolService`, centralized dispatch, and the pure runtime composition seam.

- [x] Capture failing in-process dispatch contracts.
- [x] Map invalid/unknown/unexpected failures to structured redacted envelopes and stderr incident logging.
- [x] Prove the unavailable service reports three tools and dispatch never loads COM.

### Task 10: Implement canonical stdio server and compatibility shim

**Files:**
- Create: `src/autocad_mcp/server.py`, `tests/contract/test_stdio_server.py`
- Modify: `src/server.py`, `mcp.json`, `tests/compatibility/test_legacy_mutating_tool_schemas.py`, `tests/unit/test_project_metadata.py`

**Interfaces:**
- Consumes: Task 8 request/response/catalog interfaces and Task 9 service/runtime composition.
- Produces: the one canonical low-level stdio registration owner, a protocol-safe `src.server` shim, one resource, and one prompt.

- [x] Capture failing canonical/shim import, registration, and dual-entry subprocess contracts.
- [x] Register exactly the three ordered tools and route resource/prompt through the same catalog source; normal logs and tracebacks go only to stderr.
- [x] Convert the compatibility test from its pre-replacement handler extraction phase to post-replacement fixture-integrity/core-manifest exclusion checks; the stdio contract owns active prompt/list-tools proof.
- [x] Move the metadata test from the temporary `src.server` command to the canonical package module command as part of the tested manifest migration.
- [x] Prove both module entry points initialize, list/read/get the expected catalog surfaces, emit protocol-clean stdout, and import no COM modules.

### Task 11: Retire duplicate core paths and align documentation

**Files:**
- Delete after replacement coverage: `src/mcp_server.py`, `tests/test_server.py`, `tests/unit/test_drawing_operations.py`
- Modify: `docs/decisions/0002-canonical-server-consolidation.md`, `README.md`, `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`, `docs/roadmap.md`, `tests/unit/test_mcp_tools.py`

**Interfaces:**
- Consumes: passing canonical core and explicit replacement matrix.
- Produces: only one active server surface, correct metadata/docs, and Stage 2 still open pending EPIC-03.

- [x] Prove no active reference selects or imports the duplicate server before deletion.
- [x] Run all core model/schema/dispatch/compatibility/stdio contracts after deletion.
- [x] Record MCP-contract evidence without claiming AutoCAD verification.

### Task 12: Implement the narrow pure AutoCAD adapter contract and fake

**Files:**
- Create: `src/autocad_mcp/adapter/__init__.py`, `protocol.py`, `capabilities.py`, `provider.py`, `fake.py`
- Create: `tests/adapter/test_protocol.py`, `test_capabilities.py`, `test_provider.py`, `test_fake.py`

**Interfaces:**
- Consumes: Task 8 core types and Task 9 `BasicToolService` interface.
- Produces: exactly four read-only/status adapter methods, immutable values/errors/capabilities, delayed Windows provider, and focused deterministic fake.

- [x] Capture a failing protocol/fake contract before implementation.
- [x] Prove no creation, editing, COM proxy, or generic execution surface exists.
- [x] Run fake contract and pure adapter checks on Linux.

### Task 13: Implement delayed Windows adapter lifecycle

**Files:**
- Create: `src/autocad_mcp/adapter/windows_session.py`, `windows.py`
- Create: `tests/adapter/test_windows_imports.py`, `test_windows_session.py`, `test_windows.py`
- Modify: `tests/adapter/test_provider.py`

**Interfaces:**
- Consumes: Task 12 adapter protocol/fake.
- Produces: delayed COM loader, balanced short-lived session manager, no-proxy-retention adapter, and capability-driven conversion.

- [x] Write failing import/lifecycle/conversion tests using injected COM stubs.
- [x] Prove `GetActiveObject("AutoCAD.Application")` attachment only, no new app creation, balanced apartment cleanup, and no proxy retained across calls.
- [x] Run focused Linux delayed-import/lifecycle tests and the Windows AutoCAD-closed expected-unavailable classification when a Windows host is available.

### Task 14: Map the three active MCP tools through the adapter service

**Files:**
- Create: `src/autocad_mcp/adapter/service.py`, `tests/mcp/test_adapter_tool_service.py`
- Modify: `src/autocad_mcp/runtime.py`, `tests/unit/test_mcp_dispatch.py`

**Interfaces:**
- Consumes: Tasks 8-10 core interfaces and Task 12 adapter provider/fake contract.
- Produces: `AdapterToolService`, `asyncio.to_thread` adaptation, same-named structured errors, and production runtime composition without eager COM imports.

- [x] Write failing fake-provider service tests for status, list, detail, error mapping, and one thread crossing per synchronous operation.
- [x] Wire only `create_tool_service()` to the Windows provider; construction/import must not load COM.
- [x] Run fake/core/stdio contracts and import-boundary checks without AutoCAD.

### Task 15: Build and test the neutral drawing-copy guard

**Files:**
- Create: `tests/windows/drawing_copy_guard.py`, `tests/windows/test_drawing_copy_guard.py`

**Interfaces:**
- Produces: COM-free unique GUID source-copy lifecycle/evidence infrastructure reusable by later read-only and writable policies.

- [x] Start with failing unique-copy, path/hash, active-path, close-without-save, cleanup, and preserve-evidence tests.
- [x] Require a regular immutable source DWG, GUID temporary copy, resolved path inequality, equal initial hashes, source-after hash verification, and close callback with `False`.
- [x] Keep this guard policy-neutral: it must not load COM, open AutoCAD, require read-only/writable mode, or decide whether a changed copy is a failure.

### Task 16: Build and test the exclusive Windows AutoCAD lease

**Files:**
- Create: `tests/windows/autocad_lease.py`, `tests/windows/test_autocad_lease.py`

**Interfaces:**
- Consumes: Task 15 neutral guard.
- Produces: controller-owned trusted-fact exclusive lease usable by every real-AutoCAD runner.

- [x] Start with failing Windows-aware lease key, owner metadata, exclusivity, release, stale-recovery, and fail-closed tests.
- [x] Require a lease derived only from trusted local machine/user/session/installation/version facts; fail closed on contention, corrupt metadata, unsafe ACL, or indeterminate liveness.

### Task 17: Build and test the read-only harness and constrained runner

**Files:**
- Create: `tests/windows/autocad_harness.py`, `tests/windows/test_autocad_harness.py`, `tests/conftest.py`
- Create: `scripts/run_autocad_2026_smoke.ps1`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Tasks 15-16 neutral guard and acquired lease.
- Produces: opt-in real-test gate, read-only wrapper, fingerprint policy, and copy-paste PowerShell runner with no concurrency override.

- [x] Start with failing read-only harness and opt-in fixture tests.
- [x] Require the harness to assert owned lease, verify guard run-directory current-user/SYSTEM Windows ACL before cleanup, open only the guarded copy read-only, require `ReadOnly is True`, close without saving, preserve failed evidence, and compare file/drawing fingerprints.
- [x] Keep PowerShell arguments limited to absolute immutable SourceDwg and acad.exe paths, with no caller-provided lease key/salt/isolation/concurrency override.

### Task 18: Build the opt-in AutoCAD 2026 smoke and final handoff

**Files:**
- Create: `tests/windows/test_autocad_2026_smoke.py`, `docs/windows-testing-guide.md`
- Create after an actual pass only: `docs/verification/autocad-2026-smoke.md`
- Modify after evidence only: `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`, `docs/compatibility.md`, `docs/roadmap.md`

**Interfaces:**
- Consumes: all prior work and a human-supplied immutable DWG/full AutoCAD 2026 instance.
- Produces: a guarded real-device command, a concise operator guide, and limited evidence wording.

- [x] Test the ordered two-process MCP smoke: initialize/catalog, status, list, detail, shutdown, fingerprint, reconnect, and final fingerprint.
- [x] On Linux, run the complete active platform-independent suite plus lock/metadata/lint/type/compile/JSON/stdio/diff checks at the final gate.
- [x] Preserve the harness and handoff guide without a Windows result; keep 2026 targeted and do not create a passing verification record.
- [x] Inspect the exact final diff, push `origin/codex/local-autocad-testable`, create draft PR #2 with evidence/limitations/rollback, and read back matching local, remote, and PR head SHAs.
