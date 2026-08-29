# Project Status

**Evidence date:** 2026-08-29

This document describes the current repository state. It deliberately separates
source-code presence, automated core evidence, and real AutoCAD verification.

## Observed in source

- `mcp.json` selects `uv run python -m autocad_mcp.server` as the canonical stdio command.
- `autocad_mcp.server` is the sole registration owner for `server_status`,
  `list_entities`, and `get_entity_info`, one status resource, and one help prompt.
- `src.server` is a protocol-safe compatibility shim with no registrations.
- The core runtime composes a Windows adapter provider without importing COM
  packages until a Windows adapter operation begins.
- The frozen four mutation schemas remain only in compatibility evidence.
- Geometry, surface-unfolding, pattern-optimization, code-generation, inspection, mock, interactive, security, monitoring, and enterprise-oriented modules are present in the tree.
- `src/testing/mock_autocad.py` contains an extensive mock object model.

Source presence does not prove that a module is connected to the root server, functionally correct, safe, or compatible with a real AutoCAD release.

## Known inconsistencies

| Area | Evidence | Consequence |
| --- | --- | --- |
| Windows adapter | No real adapter connection is in the canonical core. | EPIC-03 must provide Windows-only COM behavior and real AutoCAD evidence. |
| Unconnected advanced server | `src/mcp_integration/enhanced_mcp_server.py` remains a large separate system not started by `mcp.json`. | It remains experimental and must not be advertised as root-server functionality. |
| Historical deployment artifacts | Docker and Compose describe a Linux HTTP direction that names the experimental enhanced server. | They are not a supported deployment; [decision 0001](decisions/0001-container-artifact-disposition.md) records their status without authorizing removal. |

## Automated core evidence

```text
The named model, tool/schema, dispatch, legacy-exclusion, and stdio suites are
the automated evidence for the pure MCP core. They include the canonical
entry point and the compatibility shim, the exact three-tool catalog, the
resource and prompt, structured unavailable results, and a fresh-process
COM-import boundary.
```

These Linux tests use unavailable or injected services. They do not prove
Windows installation, COM connectivity, drawing operations, unchanged DWG
state, or AutoCAD release support.

The repository also has a prepared opt-in AutoCAD 2026 smoke path: a trusted
lease, disposable-copy guard, read-only harness, and two-process canonical
stdio test. On Linux, the smoke is intentionally skipped with the exact reason
`requires explicit disposable-DWG authorization`; collection and non-AutoCAD
selection are not real-AutoCAD evidence.

## Not yet verified

- A real Windows installation and MCP startup with full AutoCAD
- AutoCAD COM connection lifecycle and reconnection
- Any drawing mutation against a disposable DWG
- Extrusion and revolution argument compatibility with AutoCAD COM
- Surface unfolding, dimensioning, pattern optimization, code generation, or enterprise-oriented modules
- Full AutoCAD 2021, 2022, 2023, 2024, 2025, or 2026 compatibility

## Next validation gate

EPIC-03 must execute and document the prepared read-only smoke test on full
AutoCAD 2026 with an unchanged disposable drawing. Full AutoCAD 2021-2026
remains targeted, not verified. Stage 2 remains open until that evidence
exists; the current MCP evidence is not an EPIC completion claim.

## Repository governance status

- The imported history is preserved on the protected `archive` branch.
- Draft pull request #1 contains the stewardship baseline and targets `main`.
- The `main` branch was not protected when read back on 2026-08-28.
- Roadmap Stage 1 remains in progress until review corrections are published, `main` protection is enabled, the pull request is approved and merged, and the merged state is read back.
