# Project Status

**Evidence date:** 2026-10-01

This document describes the current repository state. It deliberately separates
source-code presence, automated core evidence, and real AutoCAD verification.

## Observed in source

- `mcp.json` selects `uv run python -m autocad_mcp.server` as the canonical stdio command.
- `autocad_mcp.server` is the sole registration owner for `server_status`,
  `list_entities`, `get_entity_info`, and `generate_constrained_code`, one status resource, and one help prompt.
- `src.server` is a protocol-safe compatibility shim with no registrations.
- Default startup and code-generation requests import no adapter/context/capture/edit/COM module.
  The basic runtime retains its existing adapter service after the first validated basic call.
- Constrained code generation returns independently validated educational text
  from nine fixed target/template pairs; it has no execution or persistence path.
- The frozen four mutation schemas remain only in compatibility evidence.
- The active dependency source is `pyproject.toml` plus `uv.lock`. The inactive
  Poetry lock and unsupported root container files are retired after clean
  Windows/Linux frozen-install evidence and the maintainer's remaining-work authorization.
- Geometry, surface-unfolding, pattern-optimization, code-generation, inspection, mock, interactive, security, monitoring, and enterprise-oriented modules are present in the tree.
- `src/testing/mock_autocad.py` contains an extensive mock object model.

Source presence does not prove that a module is connected to the root server, functionally correct, safe, or compatible with a real AutoCAD release.

## Known inconsistencies

| Area | Evidence | Consequence |
| --- | --- | --- |
| Windows adapter | The delayed Windows COM adapter, fake contracts, lease, copy guard, and read-only harness are in the canonical runtime; no real adapter connection is recorded. | Execute the guarded AutoCAD 2026 smoke and review its evidence before making a real-AutoCAD claim. |
| Unconnected advanced server | `src/mcp_integration/enhanced_mcp_server.py` remains a large separate system not started by `mcp.json`. | It remains experimental and must not be advertised as root-server functionality. |

## Automated core evidence

The merged baseline `52448cb` passed a fresh frozen Linux installation and
`uv run --frozen pytest -q -ra`: **215 passed, 9 skipped**. The skipped checks
require Windows APIs or explicit disposable-DWG authorization. The merge also
fixed malformed MCP arguments returning unstructured SDK errors; both stdio
entry points now have regression coverage for the structured error contract.

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
- Surface unfolding, dimensioning, pattern optimization, legacy code-generation, or enterprise-oriented modules
- Full AutoCAD 2021, 2022, 2023, 2024, 2025, or 2026 compatibility

## Next validation gate

The current C integration branch adds portable output-only code generation.
Its [decision record](advanced/constrained-code-generation-decision.md) records
the separate static/core evidence, passed final review and pending hosted CI; no AutoCAD
or other advanced-track verification follows from it.

EPIC-03 must execute and document the prepared read-only smoke test on full
AutoCAD 2026 with an unchanged disposable drawing. Full AutoCAD 2021-2026
remains targeted, not verified. Stage 2 remains open until that evidence
exists; the current MCP evidence is not an EPIC completion claim.

On 2026-10-01 the maintainer requested completion of all agent-owned remaining
epic work before personally running application tests. Dependent implementation,
portable tests, fixtures, and Windows runners may proceed in dependency order.
This changes execution scheduling only: actual drawing edits still require
per-plan human approval, and no feature or AutoCAD release becomes verified
without its recorded real-device evidence.

## Repository governance status

- The imported history is preserved on the protected `archive` branch.
- [PR #1](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/1),
  [PR #2](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/2), and
  [PR #3](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/3) merged on 2026-10-01.
- `main` requires pull requests and linear history and prohibits force pushes
  and deletion. The single-maintainer policy requires zero approving GitHub
  reviews; the maintainer explicitly authorized the merges in the project chat.
- `archive` remains locked and prohibits force pushes and deletion.
- Roadmap Stage 1 is accepted; the [closure record](verification/stewardship-2026-10-01.md)
  records merged-state readback, documentation checks, and the review-policy limit.
