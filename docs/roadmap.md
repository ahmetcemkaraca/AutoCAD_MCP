# Roadmap

Roadmap stages are ordered by dependency and close only when their observable acceptance criteria pass. Dates and line counts are not evidence of completion.

## 1. Stewardship baseline

**Outcome:** Establish an honest, maintainable project surface.

**Status:** Accepted on 2026-10-01 after maintainer-authorized PR #1 integration,
merged-state readback, protection verification, and documentation checks. See
the [closure evidence](verification/stewardship-2026-10-01.md).

**Acceptance criteria:**

- The imported Git history is preserved on the protected `archive` branch.
- `main` starts from the adoption baseline and is protected by a pull-request workflow.
- README maintenance context is one sentence and detailed status lives in canonical docs.
- `AGENTS.md` enforces English artifacts, tests, platform boundaries, and drawing safety.
- Every imported document is reviewed, classified, and preserved below `docs/legacy/`.
- Root metadata advertises only the tools registered by the selected entry point.

## 2. Stable MCP core

**Depends on:** Stage 1

**Outcome:** Provide one testable canonical MCP core and prepare the AutoCAD
connection boundary.

**Status:** Open. The pure/core MCP contract has local Linux evidence, but
EPIC-03's real-AutoCAD acceptance criterion below remains pending.

**Acceptance criteria:**

- One canonical MCP server owns all active tool registration.
- PEP 621 dependency metadata, a committed `uv.lock`, and Windows-only COM markers produce a reproducible clean installation.
- The documented launch command starts the installed `autocad_mcp.server` module and matches `mcp.json`; `src.server` remains only a tested temporary compatibility shim.
- Package, initialization, and metadata versions agree.
- Docker and Compose artifacts are either proven against the supported
  architecture or removed with a documented justification.
  [Decision 0001](decisions/0001-container-artifact-disposition.md) records
  removal of the unsupported historical artifacts on 2026-10-01.
- Platform-independent server and schema modules import without Windows COM installed.
- A focused fake adapter supports connection, document discovery, entity query, and failure contract tests without a mutation capability.
- Invalid Flask-oriented tests and the duplicate FastMCP server are retired
  only with the replacement matrix in
  [decision 0002](decisions/0002-canonical-server-consolidation.md).
- MCP startup and the active `server_status`, `list_entities`, and `get_entity_info` contracts pass automated tests.
- Historical mutation schemas are preserved as compatibility records but are absent from active registration and metadata.
- A read-only Windows smoke test connects to full AutoCAD 2026 using a disposable drawing and proves unchanged drawing state.

**Recorded partial evidence:** The canonical command, three non-mutating tools,
structured unavailable status, resource and prompt, compatibility shim,
legacy-schema exclusion, and stdio contract have Linux pure/core MCP coverage.
This is not a Stage 2 completion claim: the prepared Windows adapter and
unchanged-DWG full AutoCAD 2026 smoke must still be executed and recorded on a
real installation. AutoCAD 2021-2026 remains targeted, not verified.

## 3. Structured drawing context

**Depends on:** Stage 2

**Outcome:** Give users and models reliable, queryable CAD facts.

**Acceptance criteria:**

- Snapshots include document identity, change fingerprint, active space, UCS, view metadata, and pagination.
- Entity contexts use handles for drawing identity and clearly label session-local IDs.
- Geometry, layer, style, block, text, dimension, bounding-box, and supported relationship extraction have focused tests.
- Large drawings use filters and bounded page sizes rather than unbounded payloads.
- Unsupported entity properties return structured capability information instead of silent omission.

## 4. On-demand visual capture

**Depends on:** Stages 2 and 3

**Outcome:** Let a user or model request a drawing image only when visual context is useful.

**Acceptance criteria:**

- `capture_drawing_view` supports current display, extents, and selected scope.
- No connection, status, analysis, plan, edit, or model turn invokes capture automatically.
- The tool returns image data plus view and bounds metadata.
- Clean output is the default; annotated handle overlays are opt-in and do not modify the DWG.
- Real AutoCAD 2026 tests cover output creation, failure cleanup, and unchanged drawing content.

## 5. Safe edit plans

**Depends on:** Stage 3

**Outcome:** Preview and apply constrained drawing changes with explicit authorization.

**Acceptance criteria:**

- Plans identify their source snapshot, target handles, expected prior state, and requested operations.
- Dry-run produces an impact summary without changing the drawing.
- Preview returns an immutable identifier and plan digest but no mutation authority.
- A trusted, non-model-callable host approval broker issues short-lived, single-use tokens only after human confirmation.
- Approval records are bound server-side to the active document, AutoCAD session, snapshot fingerprint, plan digest, and expiration; application fails closed without a valid binding.
- Stale snapshots, missing handles, read-only drawings, invalid values, and unsupported operations fail before mutation.
- Supported changes run in one AutoCAD Undo group and return structured per-operation results.
- Mid-plan failure triggers token invalidation, Undo, state reread, fingerprint verification, and an explicit `rolled_back` or `rollback_failed` outcome.
- Arbitrary executable code, deletion, and architectural semantic edits are not supported in the first delivery.

## 6. Architectural semantics

**Depends on:** Stage 3 for read-only architectural analysis. The optional confirmed-edit bridge additionally depends on Stage 5. Stage 4 capture is an optional evidence input, not a delivery gate.

**Outcome:** Interpret and safely develop 2D architectural plans.

**Acceptance criteria:**

- Wall, door, window, column, room, dimension, and text hypotheses include evidence and confidence.
- Deterministic CAD evidence and client-provided visual observations remain distinguishable.
- Ambiguous entities remain unknown or require confirmation; the system does not invent certainty.
- Fixture drawings cover common layer, block, opening, parallel-line, and enclosure patterns.
- Approved semantic edits use the constrained edit-plan path.

## 7. General and mechanical semantics

**Depends on:** General topology depends on Stage 3. Mechanical semantics additionally depends on the accepted general-topology contract and the evidence/confidence contract from Stage 6 read-only analysis.

**Outcome:** Extend context beyond architectural plans without weakening evidence rules.

**Acceptance criteria:**

- General topology and relationship extraction works independently of domain labels.
- Mechanical support identifies parts, holes, axes, profiles, dimensions, and tolerances with explicit evidence.
- Manufacturing interpretations remain separate from geometry facts.
- Domain-specific fixtures and real drawing evaluations report precision, ambiguity, and unsupported cases.

## 8. Validated advanced features

**Depends on:** Stable core and feature-specific evidence

**Outcome:** Recover valuable historical research selectively.

**Candidate areas:** surface unfolding, automatic dimensioning, pattern optimization, and constrained code generation.

**Acceptance criteria for each candidate:**

- The feature has a focused design consistent with the current safety boundary.
- Historical claims are replaced by measurable requirements.
- Unit, numerical, MCP contract, and relevant real-AutoCAD tests pass.
- Failure modes, approximation limits, performance data, and supported entities are documented.
- The feature is integrated into the canonical server before being described as available.

## Status updates

A roadmap stage may be marked complete only in the pull request that provides its acceptance evidence. Partially implemented code remains in progress or experimental regardless of size.

Detailed future work, dependencies, file ownership, parallel-agent lanes, tests, and evidence gates are defined in the [modernization epic portfolio](epics/README.md).
