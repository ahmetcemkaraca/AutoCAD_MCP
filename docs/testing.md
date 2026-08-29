# Testing

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

Contract tests start the canonical server with unavailable or focused injected
services and verify:

- advertised tool, prompt, and resource schemas;
- valid and invalid input handling;
- structured success and error results;
- stdio output integrity;
- the status resource and help prompt;
- exclusion of the four historical mutation names.

The fake adapter should implement only the contract needed by active tools. It should not attempt to emulate the complete AutoCAD object model.

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

## Core developer commands

For the current pure/core boundary, run:

```powershell
uv sync --frozen --group dev
uv run pytest tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
uv run ruff check src tests
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
