# Testing

AutoCAD MCP requires separate evidence for pure Python behavior, MCP protocol behavior, and real AutoCAD behavior. Evidence from one layer must not be reported as proof of another.

## Current baseline

The stewardship branch has run:

```bash
python3 -m compileall -q src tests
```

The command exited successfully with Python 3.14.4 in the current Linux development environment. This is a syntax check only.

The adopted pytest files are not a reliable runtime baseline: they import a Flask `app` that does not exist in the selected stdio server. Repairing the test boundary is part of the stable MCP core roadmap stage.

## Pure Python tests

Pure data models, validation, geometry processing, context relationships, edit-plan checks, and MCP result shaping should run without AutoCAD or Windows COM. These tests may run on Windows or Linux.

Passing them proves only the tested platform-independent behavior. Linux is not a supported AutoCAD runtime.

## MCP contract tests

Contract tests should start the canonical server with a focused fake AutoCAD adapter and verify:

- advertised tool, prompt, and resource schemas;
- valid and invalid input handling;
- structured success and error results;
- pagination and response limits;
- stdio output integrity;
- stale edit-plan and approval behavior.

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

## Intended developer commands after the development-baseline epic

After dependency metadata is migrated to PEP 621, a `uv.lock` is committed, and the stable-core test boundary is repaired, the expected workflow is:

```powershell
uv sync --frozen --group dev
uv run pytest
uv run ruff check src tests
```

These commands describe the target workflow; this stewardship pull request does not claim that they currently install the adopted dependencies or pass. The current repository has no supported setup command. When dependency and test repair lands, replace this note with fresh Windows results and supported command variants.

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
