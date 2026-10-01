# Project Status

**Evidence date:** 2026-08-28

This document describes the adopted repository state. It deliberately separates source-code presence from automated verification and real AutoCAD verification.

## Observed in source

- `mcp.json` selects `src/server.py` as its intended stdio entry point; successful startup has not been established.
- `src/server.py` registers seven tools: `draw_line`, `draw_circle`, `extrude_profile`, `revolve_profile`, `list_entities`, `get_entity_info`, and `server_status`.
- The same entry point exposes one status resource and one help prompt.
- AutoCAD access currently routes through helpers in `src/utils.py` using `pythoncom`, `win32com`, and `pyautocad`.
- Geometry, surface-unfolding, pattern-optimization, code-generation, inspection, mock, interactive, security, monitoring, and enterprise-oriented modules are present in the tree.
- `src/testing/mock_autocad.py` contains an extensive mock object model.

Source presence does not prove that a module is connected to the root server, functionally correct, safe, or compatible with a real AutoCAD release.

## Known inconsistencies

| Area | Evidence | Consequence |
| --- | --- | --- |
| Duplicate servers | `src/server.py` uses the low-level MCP `Server`; `src/mcp_server.py` defines a separate FastMCP server. | There is no single implementation surface for fixes and tests. |
| Unapproved mutation tools | The selected server registers line, circle, extrusion, and revolution tools that call mutation helpers directly, without preview, trusted human approval, stale-state checks, or verified Undo recovery. | The current mutation tools are not an accepted safe product surface and must not be carried into the canonical active catalog. |
| Tool-count mismatch | `src/mcp_server.py` contains seven decorated tools but reports `tools_available: 6`. | Metadata cannot be trusted without source comparison. |
| Unconnected advanced server | `src/mcp_integration/enhanced_mcp_server.py` defines a large separate system not started by `mcp.json`. | Advanced code must not be advertised as root-server functionality. |
| Platform import boundary | `src/utils.py` imports Windows COM packages at module import time. | The root server cannot currently be imported for platform-independent tests without those packages. |
| Test-entry mismatch | `tests/test_server.py` and `tests/unit/test_drawing_operations.py` import `src.server.app`, but `src/server.py` defines no Flask `app`. | The adopted tests do not exercise the current stdio entry point. |
| Configuration drift | The adopted metadata previously listed tools not registered by `src/server.py`. | Root metadata required correction before implementation work. |
| Launch-path mismatch | `mcp.json` sets `PYTHONPATH` to `src` while launching `python src/server.py`, whose code imports `src.utils`. | The configured path does not make the repository-root `src` package importable in the ordinary script-launch model. |
| Dependency-manager mismatch | Runtime and development dependencies are declared under Poetry tables, no `uv.lock` exists, and the root README previously prescribed `uv sync`. | A clean uv installation cannot be claimed until dependencies move to standard project tables and a lockfile is verified. |
| Version and target drift | Package and root metadata use version `0.1.0`, while `src/server.py` reports `1.0.0` and its help text names AutoCAD 2025 only. | Clients can observe inconsistent product versions and compatibility wording. |
| Stale deployment artifacts | `Dockerfile` expects absent requirements files and launches the unconnected enhanced server in Linux; `docker-compose.yml` expects HTTP, Redis, PostgreSQL, and Nginx services outside the selected stdio path. | The container files are not a supported deployment path and must be classified, repaired, or removed with evidence. |

## Verification performed for the stewardship baseline

```text
Python interpreter: 3.14.4
Command: python3 -m compileall -q src tests
Result: exit code 0
```

This result proves only that Python parsed the source and test files in that interpreter. It does not prove dependency compatibility, test correctness, MCP startup, COM connectivity, drawing operations, or AutoCAD release support.

## Not yet verified

- Dependency installation from `poetry.lock` or `pyproject.toml` on the target Windows environment
- Any reproducible setup using the current `uv`, Poetry, `mcp.json`, Docker, or Compose instructions
- Collection and execution of the existing pytest suite
- MCP initialization and tool calls through a real client
- AutoCAD COM connection lifecycle and reconnection
- Any drawing mutation against a disposable DWG
- Extrusion and revolution argument compatibility with AutoCAD COM
- Surface unfolding, dimensioning, pattern optimization, code generation, or enterprise-oriented modules
- Full AutoCAD 2021, 2022, 2023, 2024, 2025, or 2026 compatibility

## Next validation gate

The reproducible-development and stable-core deliveries must first repair dependency metadata, launch paths, version reporting, and stale deployment artifacts. They must then consolidate the server entry point, defer Windows-only imports, replace the mismatched Flask tests with MCP contract tests, and pass a documented smoke test on Windows with full AutoCAD 2026. Until those gates pass, treat the repository as a stabilization project and do not present a setup command as supported.

## Repository governance status

- The imported history is preserved on the protected `archive` branch.
- Draft pull request #1 contains the stewardship baseline and targets `main`.
- The `main` branch was not protected when read back on 2026-08-28.
- Roadmap Stage 1 remains in progress until review corrections are published, `main` protection is enabled, the pull request is approved and merged, and the merged state is read back.
