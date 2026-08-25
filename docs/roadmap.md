# Roadmap

Roadmap stages are ordered by dependency and close only when their observable acceptance criteria pass. Dates and line counts are not evidence of completion.

## 1. Stewardship baseline

**Outcome:** Establish an honest, maintainable project surface.

**Acceptance criteria:**

- The imported Git history is preserved on the protected `archive` branch.
- `main` starts from the adoption baseline and is protected by a pull-request workflow.
- README maintenance context is one sentence and detailed status lives in canonical docs.
- `AGENTS.md` enforces English artifacts, tests, platform boundaries, and drawing safety.
- Every imported document is reviewed, classified, and preserved below `docs/legacy/`.
- Root metadata advertises only the tools registered by the selected entry point.

## 2. Stable MCP core

**Depends on:** Stage 1

**Outcome:** Provide one testable server and one AutoCAD connection boundary.

**Acceptance criteria:**

- One canonical MCP server owns all active tool registration.
- Platform-independent server and schema modules import without Windows COM installed.
- A focused fake adapter supports connection, document, line, circle, entity query, and failure contract tests.
- Existing Flask-oriented tests are replaced or archived with an explicit reason.
- MCP startup and basic tool contracts pass automated tests.
- A Windows smoke test connects to full AutoCAD 2026 using a disposable drawing.

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
- Approval tokens are short-lived and single-use.
- Stale snapshots, missing handles, read-only drawings, invalid values, and unsupported operations fail before mutation.
- Supported changes run in one AutoCAD Undo group and return structured results.
- Arbitrary executable code and deletion are not supported in the first delivery.

## 6. Architectural semantics

**Depends on:** Stages 3-5

**Outcome:** Interpret and safely develop 2D architectural plans.

**Acceptance criteria:**

- Wall, door, window, column, room, dimension, and text hypotheses include evidence and confidence.
- Deterministic CAD evidence and client-provided visual observations remain distinguishable.
- Ambiguous entities remain unknown or require confirmation; the system does not invent certainty.
- Fixture drawings cover common layer, block, opening, parallel-line, and enclosure patterns.
- Approved semantic edits use the constrained edit-plan path.

## 7. General and mechanical semantics

**Depends on:** A stable architectural semantic model

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
