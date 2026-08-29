# Task 11 report: retire duplicate paths and align canonical documentation

## Scope and deletion precondition

Only the Task 11 documentation and tool-test paths changed. The three deleted
files are `src/mcp_server.py`, `tests/test_server.py`, and
`tests/unit/test_drawing_operations.py`. The experimental
`src/mcp_integration/enhanced_mcp_server.py`, all Docker artifacts, the
canonical server, compatibility shim, manifest, package metadata, lockfile,
and adapter paths were not modified. The untracked release plan
`docs/superpowers/plans/2026-08-29-first-safe-local-autocad-release.md` was
preserved.

Before deletion, the active-configuration search returned no
`src.mcp_server` or `src/mcp_server.py` reference:

```text
rg -n --glob 'mcp.json' --glob 'pyproject.toml' --glob '*.toml' --glob '*.json' --glob 'Dockerfile' --glob 'docker-compose*.yml' 'src\\.mcp_server|src/mcp_server\\.py' .
Result: exit code 1 (no matches)
```

`mcp.json` was parsed by `uv run python -m json.tool mcp.json` after the
change (exit code 0). The Dockerfile reference to
`src.mcp_integration.enhanced_mcp_server` was not a selected MCP configuration;
it remains the unsupported historical Linux HTTP direction classified by
`docs/decisions/0001-container-artifact-disposition.md`.

## Replacement evidence

The legacy Flask suites were run before deletion:

```text
/root/.codex/agent-tools/uv/uv run pytest tests/test_server.py tests/unit/test_drawing_operations.py -q
Result: 2 collection errors
tests/test_server.py: ImportError: cannot import name 'app' from 'src.server'
tests/unit/test_drawing_operations.py: ImportError: cannot import name 'app' from 'src.server'
```

This is the required red evidence that the Flask tests did not exercise the
canonical stdio surface. `docs/decisions/0002-canonical-server-consolidation.md`
now records the replacement matrix: canonical schema/order/dispatch/stdio
contracts for the three active tools; the fixture, digest, and explicit
exclusion evidence for all four legacy mutation schemas; canonical resource
and prompt contracts; no MCP replacement for Flask `/health` or draw routes;
and structured `server_status` only for `/acad-status`, with real connection
work deferred to EPIC-03.

The new manifest agreement and fresh-process COM-import-boundary tests were
then run directly against the already-canonical Task 10 implementation:

```text
/root/.codex/agent-tools/uv/uv run pytest tests/unit/test_mcp_tools.py -q
Result: 25 passed in 1.97s
```

They are green because the manifest was already canonical; Task 11 made no
production or metadata change. The import probe removes `PYTHONPATH` and uses
a fresh subprocess to verify that importing the pure core does not load
`pythoncom`, `win32com`, `win32com.client`, `pyautocad`, or `comtypes`.

## Post-deletion verification

```text
/root/.codex/agent-tools/uv/uv run pytest tests/unit/test_project_metadata.py tests/unit/test_package_entrypoints.py tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q
Result: 68 passed in 4.45s

/root/.codex/agent-tools/uv/uv run ruff check src/autocad_mcp src/server.py tests/unit/test_project_metadata.py tests/unit/test_package_entrypoints.py tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py
Result: all checks passed (with Ruff's existing top-level-settings deprecation warning)

/root/.codex/agent-tools/uv/uv run python -m compileall -q src tests
Result: exit code 0

/root/.codex/agent-tools/uv/uv run python -m json.tool mcp.json >/dev/null
Result: exit code 0

git diff --check
Result: exit code 0
```

Historical Flask tests were not run after deletion.

## Documentation scope and limits

`README.md`, `docs/architecture.md`, `docs/project-status.md`, `docs/testing.md`,
and `docs/roadmap.md` now name the canonical pure/core MCP contract, its three
non-mutating tools, the `src.server` compatibility shim, and the experimental
enhanced module. They retain the Windows adapter as an EPIC-03 target, Stage 2
as open, and full AutoCAD 2021-2026 as targeted rather than verified. Docker
is linked only to its existing disposition decision; no Docker artifact was
removed or repaired.

The automated evidence is Linux pure/core MCP coverage with unavailable or
injected services. It is not a claim that any E02 or E03 gate is complete, that
the Windows adapter works, that a real AutoCAD connection was made, or that an
AutoCAD release or DWG behavior was verified.

## Self-review

`git diff --name-status -- src/mcp_server.py tests/test_server.py
tests/unit/test_drawing_operations.py docs/decisions/0002-canonical-server-consolidation.md`
showed only the intended decision update and the three intended deletions.
`git status --short` showed only the Task 11 files plus the preserved untracked
release plan. The deletion and test changes are limited to the task-authorized
paths; the report is the explicitly required handoff artifact.
