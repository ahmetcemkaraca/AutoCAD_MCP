# Testing

## Constrained code-generation contracts

Run `uv run pytest tests/unit/advanced/codegen tests/contract/test_constrained_code_generation_tool.py tests/contract/test_no_execution_tools.py tests/contract/test_server_tool_catalog.py tests/contract/test_stdio_server.py -q`.
These checks cover all nine pairs, frozen malicious classifications, closed
schemas, preserved basic-service injection, adapter-free default startup, real
stdio C calls, request-scoped effect spies and actual SDK body byte limits.
They parse generated text statically and never execute it. Source/artifact size
checks alone cannot prove the complete 65,536-byte `CallToolResult` body bound.
The [C decision](advanced/constrained-code-generation-decision.md) records
content-addressed evidence and pending independent/hosted CI gates.

AutoCAD MCP requires separate evidence for pure Python behavior, MCP protocol behavior, and real AutoCAD behavior. Evidence from one layer must not be reported as proof of another.

## Current core evidence

The canonical core has named Linux automated coverage for the exact
`server_status`, `list_entities`, and `get_entity_info` catalog, closed input
schemas, dispatch, legacy-mutation exclusion, manifest agreement, canonical
stdio entry point, and the `src.server` compatibility shim. The status path is
exercised through unavailable or injected services, not a real AutoCAD adapter.

Run the focused core suite with:

```bash
uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
```

The replacement record for the retired duplicate server and invalid Flask
tests is [decision 0002](decisions/0002-canonical-server-consolidation.md).
Its evidence does not make an HTTP route, mutation tool, Windows adapter, or
AutoCAD session available.

## Pure Python tests

Pure data models, validation, geometry processing, context relationships, edit-plan checks, and MCP result shaping should run without AutoCAD or Windows COM. These tests may run on Windows or Linux.

Passing them proves only the tested platform-independent behavior. Linux is not a supported AutoCAD runtime.

## MCP contract tests

Failure tests also assert that raw COM/import/cleanup/property exception text is
absent from diagnostics, including debug logs. Incident IDs and exception class
names remain available; redacting only the public tool envelope is insufficient.

Contract tests start the canonical server with unavailable or focused injected
services and verify:

- advertised tool, prompt, and resource schemas;
- valid and invalid input handling;
- structured success and error results;
- stdio output integrity;
- the status resource and help prompt;
- exclusion of the four historical mutation names.

The fake adapter should implement only the contract needed by active tools. It should not attempt to emulate the complete AutoCAD object model.

Full stdio protocol checks inject `UnavailableToolService` in a test subprocess
before executing each entry module with `runpy`. They assert that no COM module
loads. Separate `python -m` startup/catalog checks exercise the production module
entry commands without invoking the adapter or attaching to a drawing.

## Real AutoCAD tests

Real integration tests run only on Windows with full AutoCAD. Each result must record:

- AutoCAD product and release;
- Windows release;
- Python and dependency-lock state;
- test drawing or fixture revision;
- exact command and result;
- whether AutoCAD displayed a modal dialog or required manual interaction.

Use a disposable copy of every DWG. Mutation tests should group created entities for Undo cleanup and avoid deletion by default.

AutoCAD 2026 is the first planned validation environment. Earlier targeted releases remain unverified until the same documented contract checks pass on a real installation.

The neutral drawing guard pins the original source, copy, and marker file
identities until cleanup or the guard object's lifetime ends. This prevents
reused file numbers from validating a replacement while permitting intentional
in-place copy edits. Windows identity handles allow read, write, and delete
sharing. Preparation failures close all pins after recording preservation
evidence; successful cleanup closes them before removing the run directory.
The real Windows fixture supplies the lease module's exclusive directory
creator, which sets the current user as owner and applies a protected
current-user/SYSTEM ACL only to new paths. Existing foreign paths are rejected.
This infrastructure is covered by portable and Windows API tests; AutoCAD
opening, saving, and shutdown behavior still require the opted-in real run.

The prepared opt-in command is documented in
[the Windows AutoCAD 2026 smoke guide](windows-testing-guide.md). Before any
real run, an operator must start full AutoCAD 2026 in the same interactive
session, close modal dialogs, choose an immutable source DWG, and use the
provided PowerShell runner. Without `--run-autocad`, every real-installation
test skips with the exact reason `requires explicit disposable-DWG
authorization`. A skip, collection-only result, or Linux result is not
AutoCAD verification.

## Core developer commands

The `Portable tests` GitHub workflow runs the frozen CPython 3.12 development
environment on both Ubuntu and Windows. It checks platform-marked COM package
availability, runs the test suite without opting into AutoCAD, and checks active
source lint/types, syntax, the manifest, and delayed COM imports. Actions and uv
are pinned; cache reuse is disabled so installation evidence comes from a clean
runner. A successful Windows job is dependency/Windows-API evidence, never a
real-AutoCAD result. Historical experimental source is syntax-checked but is not
included in the active Ruff/type gate.

For the current pure/core boundary, run:

```powershell
uv sync --frozen --group dev
uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
uv run ruff check src/autocad_mcp src/server.py tests/adapter tests/compatibility tests/contract tests/mcp tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/windows tests/conftest.py scripts
uv run python -m compileall -q src tests
uv run python -m json.tool mcp.json
```

Passing them is Linux pure/core MCP evidence only. It does not establish a
supported Windows setup or a real AutoCAD connection.

## Documentation checks

Documentation-only changes should at minimum verify:

```bash
python3 -m json.tool mcp.json
python3 -m compileall -q src tests
git diff --check main...HEAD -- . ':(exclude)docs/legacy/imported-2025/**'
```

The whitespace check excludes the imported legacy archive because those files intentionally preserve their original bytes, including historical line endings and trailing whitespace. Documentation changes should also check relative Markdown links, legacy-audit coverage, current repository URLs, and agreement between `mcp.json` and the selected server registrations.

## Reporting results

Use precise labels:

- `syntax checked`: Python parsing completed;
- `unit tested`: named pure Python suite passed;
- `MCP contract tested`: canonical server protocol tests passed with the named adapter;
- `AutoCAD verified`: named tests passed on the stated full AutoCAD release.

Do not use `working`, `supported`, or `production-ready` when the available evidence is narrower.
