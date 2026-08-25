# AutoCAD MCP Maintenance and Modernization Design

**Status:** Approved

**Date:** 2026-08-25

## Purpose

This design establishes a maintainable foundation for AutoCAD MCP after the original upstream repository became unavailable. The protected `archive` branch preserves the imported history. The rewritten `main` branch starts with a single adoption commit, and all subsequent work uses English-language feature branches and pull requests.

The product targets full AutoCAD releases 2021 through 2026 on Windows. AutoCAD LT and Linux-hosted AutoCAD operation are out of scope. Linux remains useful only for pure Python unit tests and MCP contract tests that do not import or operate Windows COM.

## Confirmed Product Decisions

- Full AutoCAD 2021-2026 on Windows is the target compatibility range.
- AutoCAD 2026 is the initially available real integration-test environment.
- AutoCAD 2021-2025 remain targeted, not verified, until tested on those releases.
- Vision runs in the MCP client or model. The server does not embed a vision provider or require a vision API key.
- Drawing capture is an explicit MCP tool. It never runs automatically during connection, inspection, planning, or editing.
- Editing uses preview, explicit approval, stale-state checks, and a single AutoCAD Undo group.
- Semantic support starts with architectural 2D drawings, expands to general CAD, and then expands to mechanical and manufacturing drawings.
- Existing unvalidated modules are classified as legacy or experimental instead of being advertised as production-ready.
- Code, identifiers, comments, docstrings, commits, pull requests, and project documentation use English.

## Repository Stewardship

The README will describe the maintenance handover in one sentence only. It will not contain a detailed inventory of working, experimental, legacy, and planned features. That inventory belongs in canonical project-status and roadmap documentation.

Every existing document must be reviewed. Documents that are obsolete, misleading, redundant, speculative, or inconsistent with the code will move under `docs/legacy/` while preserving their Git history. Current documentation will have a small canonical surface:

- `docs/README.md`: documentation entry point and audience routing
- `docs/project-status.md`: evidence-based implementation status
- `docs/architecture.md`: current architecture and boundaries
- `docs/roadmap.md`: ordered, acceptance-gated delivery roadmap
- `docs/testing.md`: platform-specific test strategy and commands
- `docs/compatibility.md`: supported, targeted, and verified versions

Research on surface unfolding, dimensioning, code generation, and related advanced ideas remains available as historical input. It will not be presented as working behavior until it has focused tests and real AutoCAD verification.

## Required Contributor Rules

The repository-root `AGENTS.md` is written in English for both maintainers and coding agents. It establishes these non-negotiable rules:

- All project artifacts and Git history use English.
- Development uses a feature branch and pull request; no routine development commits go directly to `main`.
- Behavior changes begin with a failing automated test.
- AutoCAD-independent code remains importable and testable without Windows COM.
- COM imports stay behind the Windows adapter boundary.
- Unverified functionality is never described as working or production-ready.
- Arbitrary Python, AutoLISP, or unrestricted `SendCommand` execution is not exposed through MCP.
- Destructive CAD mutations require preview, explicit approval, and Undo protection.
- New dependencies require a concrete need not met by the standard library or an existing dependency.
- Legacy code is not removed without a tested replacement or a documented removal justification.
- Documentation and roadmap status must match observable behavior.

## Target Architecture

The modernized codebase will expose one canonical MCP server. The existing server implementations and unconnected advanced components will be consolidated incrementally; historical variants will remain under a clear legacy boundary until their useful behavior is migrated or deliberately retired.

### AutoCAD adapter

A narrow Windows COM adapter owns connection management, capability detection, document access, and entity operations. It detects the connected AutoCAD release at runtime and reports capabilities instead of maintaining six speculative version-specific implementations. Pure data processing and MCP schema code do not import `pythoncom`, `win32com`, or `pyautocad`.

### Structured drawing context

An explicit analysis request produces a versioned `DrawingSnapshot`. The snapshot contains document identity, active space and layout, UCS and view data, a drawing fingerprint, and entity contexts.

An `EntityContext` uses the AutoCAD `Handle` as its stable drawing identity and treats `ObjectID` as session-local. It records entity type, layer, geometry, bounding box, visual properties, block membership, dimensions, and spatial relationships. Semantic interpretations remain separate from CAD facts and include evidence, confidence, and a `confirmed`, `inferred`, or `unknown` state.

### On-demand drawing capture

The `capture_drawing_view` tool captures the current display, drawing extents, or a selected scope only when a user or model invokes it. A clean image is the default result. An optional annotated result maps entity handles to image-space labels without adding temporary entities to the DWG.

The implementation prefers AutoCAD plot or export capabilities over desktop-window screenshots. It returns enough view metadata to correlate the raster result with structured drawing context.

### Safe edit plans

The MCP client submits a constrained `EditPlan`; it cannot submit arbitrary executable code. The plan identifies the source snapshot, target handles, expected prior values, requested operations, and predicted effects.

`preview_edit_plan` validates the plan and returns a human-readable dry-run plus a short-lived, single-use approval token. `apply_edit_plan` checks the drawing fingerprint and entity preconditions again immediately before applying supported operations in one AutoCAD Undo group.

Initial operations cover creation, movement, rotation, scaling, geometry or property updates, layer changes, and architectural component edits. Deletion is initially disabled because an Undo mark is not an atomic database transaction. Destructive operations require a later checkpoint and recovery design.

Image capture is not part of the mandatory edit loop. A user or model may invoke it separately before or after an edit when visual evidence is useful.

## Initial MCP Tool Surface

- `server_status`: connection, AutoCAD release, and detected capabilities
- `query_entities`: filtered and paginated entity facts
- `get_entity_context`: detailed context for selected entities
- `analyze_drawing`: an explicitly requested structured drawing graph
- `capture_drawing_view`: an explicitly requested clean or annotated raster view
- `preview_edit_plan`: validation, impact summary, and approval-token creation
- `apply_edit_plan`: approved, preconditioned mutation in one Undo group
- Existing basic drawing tools retained through the canonical adapter for compatibility

## Error Handling

Structured errors distinguish AutoCAD unavailable, read-only drawing, COM busy, stale snapshot, missing handle, unsupported capability, rejected plan, expired approval, and partially completed application. Stdio protocol output is never polluted by normal logging; logs go to standard error or structured MCP results.

Retries are limited to transient connection or COM-busy conditions. Validation errors and unsupported capabilities fail immediately with actionable details.

## Testing Strategy

- Pure Python unit tests run on Windows and Linux.
- A focused fake AutoCAD backend verifies the adapter contract without pretending to reproduce the entire COM object model.
- MCP tests verify schemas, pagination, structured errors, and tool results.
- Real integration and smoke tests run only on Windows with full AutoCAD.
- AutoCAD 2026 is the first verified release.
- AutoCAD 2021-2025 are documented as targeted until each is exercised in a real installation.
- Integration tests use disposable drawing copies, avoid deletion by default, and group created test entities for Undo cleanup.

Linux is not a product runtime target. Passing Linux tests proves only that platform-independent components honor their boundary.

## Delivery Roadmap

Each stage is a separately reviewable pull request with observable acceptance criteria:

1. **Stewardship baseline:** honest README, contributor rules, complete documentation audit, canonical docs, status matrix, compatibility statement, and evidence-based roadmap.
2. **Stable MCP core:** one server, delayed Windows imports, structured errors, focused fake backend, and baseline CI.
3. **Structured drawing context:** snapshots, handle-based queries, geometry extraction, and relationship graph.
4. **On-demand visual capture:** clean and optional annotated output for current view, extents, and selection.
5. **Safe edit plans:** dry-run, stale-state protection, approval tokens, and Undo grouping.
6. **Architectural semantics:** walls, doors, windows, columns, rooms, dimensions, and text with evidence.
7. **General and mechanical semantics:** general relationships followed by parts, holes, axes, profiles, tolerances, and manufacturing context.
8. **Validated advanced features:** surface unfolding, automatic dimensioning, and selected legacy ideas promoted only after focused automated and real-AutoCAD verification.

Timelines are not treated as acceptance criteria. Documentation records evidence and compatibility honestly at every delivery stage.

## Stewardship Baseline Acceptance Criteria

- The README contains only a one-sentence maintenance-handover note and no detailed feature-status inventory.
- Every existing Markdown document is reviewed and classified.
- Obsolete, redundant, speculative, or code-inconsistent documents are moved under `docs/legacy/`.
- The canonical documentation set is concise, internally linked, and consistent with the repository.
- `AGENTS.md` contains the approved mandatory English and engineering rules.
- The roadmap derives from repository code and historical documents without presenting aspirations as completed work.
- Documentation links and repository references are validated.
- The work is committed on a feature branch and published as a draft pull request.
