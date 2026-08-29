# Stewardship Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace misleading imported documentation with a concise, evidence-based English documentation baseline while preserving every historical document under `docs/legacy/`.

**Architecture:** Keep the current runtime unchanged. Move the entire imported documentation corpus into a dated legacy archive, then create a small canonical documentation surface that distinguishes observed source code from verified runtime behavior. Align root metadata with the current repository and enforce contribution rules through `AGENTS.md`.

**Tech Stack:** Markdown, JSON, Git, Python standard library validation commands

**Spec:** `docs/superpowers/specs/2026-08-25-maintenance-and-modernization-design.md`

**Execution status (2026-08-28):** Tasks 1-3 are implemented on `docs/stewardship-baseline`. Task 4 verification, push, draft pull-request creation, and readback are complete. Final review remains open while documentation corrections are incorporated and the `main` branch-protection acceptance gate is pending.

## Global Constraints

- Product runtime support targets full AutoCAD 2021-2026 on Windows; AutoCAD LT and Linux-hosted AutoCAD are out of scope.
- AutoCAD 2026 is available for later real integration testing; no AutoCAD release is claimed as verified by this documentation-only pull request.
- The README maintenance handover is exactly one sentence and contains no detailed feature-status inventory.
- Every imported document is preserved with Git history under `docs/legacy/`.
- All new or revised project artifacts and Git history use English.
- Runtime source code is not changed in this pull request.
- Claims are limited to evidence visible in the repository or fresh verification output.

---

### Task 1: Archive and classify the imported documentation

**Files:**
- Move: existing `docs/*.md`, `docs/development/`, `docs/use-cases/`, and existing `docs/legacy/*.md` to `docs/legacy/imported-2025/docs/`
- Move: `docs_for_drafters/` to `docs/legacy/imported-2025/docs_for_drafters/`
- Move: `monitoring-tools/` to `docs/legacy/imported-2025/monitoring-tools/`
- Create: `docs/legacy/README.md`
- Create: `docs/legacy/document-audit.md`
- Preserve: `docs/superpowers/`

**Interfaces:**
- Consumes: the complete imported documentation inventory and source-code evidence collected during design
- Produces: a lossless historical archive plus a human-readable classification record used by canonical docs

- [x] **Step 1: Record the pre-move inventory**

Run:

```bash
find docs docs_for_drafters monitoring-tools -type f -print | sort
```

Expected: every imported document appears, including the duplicated drafter guides, planning documents, use cases, existing legacy integrations, and monitoring guide.

- [x] **Step 2: Move the imported corpus without rewriting its contents**

Use `git mv` so history remains traceable. Preserve the former top-level grouping below `docs/legacy/imported-2025/`; leave `docs/superpowers/` in place.

- [x] **Step 3: Write the legacy archive index**

Create `docs/legacy/README.md` with these sections and conclusions:

```markdown
# Legacy Documentation

This directory preserves documentation imported with the adopted codebase. It is historical evidence, not current product documentation.

## Why it was archived

- It documents HTTP/Flask endpoints that are absent from the current stdio MCP entry point.
- It contains duplicated guides and references to the unavailable upstream repository.
- It describes speculative or unverified features as complete, production-ready, or enterprise-ready.
- It references source and test paths that do not exist in the adopted tree.

## Using this archive

Use these files as research input only. Confirm every claim against current source code, automated tests, and a real supported AutoCAD installation before restoring it to canonical documentation.
```

Link to `document-audit.md` and the canonical `../README.md`.

- [x] **Step 4: Write the audit record**

Create `docs/legacy/document-audit.md` with one row for every original documentation file. Each row contains original path, archived path, classification, and evidence-based reason. Use the classifications `duplicate`, `obsolete`, `speculative`, `code-inconsistent`, `historical research`, and `unrelated tooling`. Record exact duplicate groups and representative missing endpoints or paths.

- [x] **Step 5: Verify lossless coverage**

Compare the audit rows and archived files to the pre-move inventory. Confirm no imported document was deleted and no historical document remains in the canonical docs root.

- [x] **Step 6: Commit the archive**

```bash
git add docs docs_for_drafters monitoring-tools
git commit -m "docs: archive imported documentation"
```

---

### Task 2: Establish repository-wide contributor rules and honest root metadata

**Files:**
- Create: `AGENTS.md`
- Modify: `README.md`
- Modify: `mcp.json`

**Interfaces:**
- Consumes: approved contributor rules and observed current MCP entry-point behavior
- Produces: enforceable repository guidance and root metadata that no longer advertises unavailable endpoints or the removed upstream owner

- [x] **Step 1: Write `AGENTS.md`**

Include scope, platform boundary, workflow, testing, documentation, security, and legacy-code sections. State these mandatory rules using `MUST` or `MUST NOT`:

```markdown
- Code, identifiers, comments, docstrings, commit messages, pull-request text, and project documentation MUST be written in English.
- Routine development MUST use a feature branch and pull request; agents MUST NOT commit directly to `main`.
- Behavior changes MUST begin with a failing automated test.
- AutoCAD-independent modules MUST remain importable without Windows COM.
- Arbitrary Python, AutoLISP, VBA, or unrestricted `SendCommand` execution MUST NOT be exposed through MCP.
- Destructive drawing changes MUST require preview, explicit approval, stale-state validation, and Undo protection.
- Unverified functionality MUST NOT be described as working or production-ready.
```

Also require focused changes, existing-dependency reuse, evidence-based docs, preservation of unrelated user changes, and explicit real-AutoCAD verification labels.

- [x] **Step 2: Replace the README**

Keep it concise and use these sections:

```markdown
# AutoCAD MCP

[badges]

An experimental Model Context Protocol bridge for automating full AutoCAD on Windows.

> This repository is now independently maintained after the original upstream project became unavailable.

## Project direction
## Current limitations
## Requirements
## Development setup
## Documentation
## Contributing
## License
```

Do not list feature classifications in the README. Link `Current limitations` to `docs/project-status.md`, and state that setup and live AutoCAD behavior are being revalidated before wider use.

- [x] **Step 3: Correct `mcp.json` metadata**

Set version `0.1.0`, the current GitHub owner and URLs, an experimental description, Windows/full AutoCAD 2021-2026 target wording, and Python `>=3.12`. Retain only the seven tools registered by `src/server.py`: `draw_line`, `draw_circle`, `extrude_profile`, `revolve_profile`, `list_entities`, `get_entity_info`, and `server_status`. Do not advertise surface unfolding, Boolean, dimensioning, batch, or pattern tools as registered MCP tools.

- [x] **Step 4: Validate root claims**

Run searches proving that `README.md`, `AGENTS.md`, and `mcp.json` contain no old owner URL, no `production-ready` claim, no AutoCAD LT support, and no advanced tool registration absent from `src/server.py`.

- [x] **Step 5: Commit root stewardship files**

```bash
git add AGENTS.md README.md mcp.json
git commit -m "docs: establish project stewardship rules"
```

---

### Task 3: Create the canonical documentation set

**Files:**
- Create: `docs/README.md`
- Create: `docs/project-status.md`
- Create: `docs/architecture.md`
- Create: `docs/roadmap.md`
- Create: `docs/testing.md`
- Create: `docs/compatibility.md`

**Interfaces:**
- Consumes: legacy audit, current source tree, approved modernization design
- Produces: the only canonical documentation linked from the root README

- [x] **Step 1: Write the documentation index**

Route maintainers and contributors to each canonical document, the approved design, the delivery plan, and the legacy archive. State that only files linked by this index are current documentation.

- [x] **Step 2: Write the evidence-based project status**

Record these observed facts:

- `src/server.py` registers seven stdio MCP tools.
- `src/mcp_server.py` is a second FastMCP implementation and reports six tools despite exposing seven decorated tool functions.
- `src/mcp_integration/enhanced_mcp_server.py` is a large, separate experimental integration not used by the root MCP command.
- `src/utils.py` imports Windows COM modules at module import time.
- Existing tests import a missing `src.server.app` Flask object and therefore do not match the current entry point.
- `python3 -m compileall -q src tests` passes in the current environment, but runtime dependencies and AutoCAD behavior have not been validated in this pull request.

Separate `Observed in source`, `Not yet verified`, `Known inconsistencies`, and `Next validation gate`. Do not use a production-readiness label.

- [x] **Step 3: Write current and target architecture**

Describe the current duplicate server paths and direct COM boundary. Then summarize the approved target: one canonical server, delayed Windows adapter imports, structured drawing snapshots, explicitly invoked capture, constrained edit plans, and client-side vision. Keep future architecture visibly labeled as target design.

- [x] **Step 4: Write the roadmap**

Create the eight approved stages: stewardship baseline, stable MCP core, structured drawing context, on-demand visual capture, safe edit plans, architectural semantics, general/mechanical semantics, and validated advanced features. Give each stage concrete acceptance criteria and dependencies. Avoid calendar promises.

- [x] **Step 5: Write testing guidance**

Distinguish pure Python checks from Windows/AutoCAD integration checks. Document the currently available syntax command:

```bash
python -m compileall -q src tests
```

Label Poetry dependency installation and pytest as intended commands pending baseline repair. State that Linux is only a test host for platform-independent components.

- [x] **Step 6: Write compatibility guidance**

Use a table with `Targeted`, `Verified`, and `Out of scope` columns. Full AutoCAD 2021-2026 on Windows is targeted; no release is marked verified in this pull request; AutoCAD LT, macOS, and Linux-hosted AutoCAD are out of scope. Explain that AutoCAD 2026 is the first planned real validation environment.

- [x] **Step 7: Validate canonical links and claims**

Use a Python standard-library Markdown-link check for relative links in `README.md`, `AGENTS.md`, and canonical docs. Run `git diff --check main...HEAD -- . ':(exclude)docs/legacy/imported-2025/**'` and search for old owner references outside `docs/legacy/`. The archive exclusion preserves historical files byte-for-byte instead of rewriting their original whitespace.

- [x] **Step 8: Commit canonical documentation**

```bash
git add docs
git commit -m "docs: add canonical project documentation"
```

---

### Task 4: Verify and publish the draft pull request

**Files:**
- Verify: all changed files on `docs/stewardship-baseline`
- Publish: draft pull request against `main`

**Interfaces:**
- Consumes: all prior task deliverables
- Produces: a reviewable remote branch and draft pull request

- [x] **Step 1: Run repository checks**

```bash
python3 -m compileall -q src tests
git diff --check main...HEAD -- . ':(exclude)docs/legacy/imported-2025/**'
git status --short
```

Run the relative Markdown-link checker, JSON-parse `mcp.json`, verify every audit entry resolves to an archived file, and confirm the canonical docs contain no removed-upstream URL.

- [ ] **Step 2: Review the complete diff**

Confirm the README has one maintenance-handover sentence, no detailed status inventory, and no unsupported feature claim. Confirm every imported document is archived, contributor rules use mandatory language, and roadmap/status statements match source evidence.

- [x] **Step 3: Push the feature branch**

```bash
git push --set-upstream origin docs/stewardship-baseline
```

- [x] **Step 4: Open the draft pull request**

Use title `docs: establish stewardship baseline` and an English body with summary, evidence, test commands, limitations, and the note that runtime behavior is unchanged. Open it as a draft against `main`.

- [x] **Step 5: Read back the pull request**

Verify the PR is draft, targets `main`, uses the feature branch, contains only intended commits, and reports the actual verification results.
