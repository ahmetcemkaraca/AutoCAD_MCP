# EPIC-00: Stewardship Baseline Closure

**Status:** In progress

**Roadmap stage:** 1 — Stewardship baseline

## Outcome

Merge an evidence-based canonical documentation surface through a protected pull-request workflow while preserving the imported history and leaving runtime Python behavior unchanged.

## Current evidence

- The imported history exists on the protected `archive` branch.
- Draft pull request #1 targets `main` from `docs/stewardship-baseline`.
- Sixty-four imported documentation files are preserved and audited below `docs/legacy/imported-2025/`.
- Canonical project, architecture, roadmap, testing, compatibility, and epic documents exist.
- The `main` branch was not protected when checked on 2026-08-28.
- Review corrections are present locally and require final validation and publication.

## Scope

- Complete the canonical-document review corrections.
- Validate relative links, legacy-audit coverage, JSON syntax, Python syntax, and non-legacy whitespace.
- Update the draft pull-request description with fresh verification evidence.
- Configure `main` to require pull requests and prevent force pushes and deletion.
- Confirm `archive` protection remains enabled.
- Obtain final review and merge the documentation pull request.
- Read back the merged repository and record the Stage 1 acceptance evidence.

## Out of scope

- Runtime Python, dependency, MCP configuration, Docker, or test repair.
- Any AutoCAD operation or compatibility claim.
- Implementing EPIC-01 through EPIC-09.
- Rewriting historical files below `docs/legacy/imported-2025/`.

## Prerequisites and authority

- Repository-administrator authority is required to configure branch protection.
- A maintainer must approve and merge draft pull request #1.
- Documentation corrections must pass review before the pull request leaves draft state.

## Owned files and services

- Modify: `README.md`
- Modify: `AGENTS.md` only if review finds a policy defect
- Modify: `docs/README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/compatibility.md`
- Modify: `docs/project-status.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/testing.md`
- Modify: `docs/superpowers/specs/2026-08-25-maintenance-and-modernization-design.md`
- Modify: `docs/superpowers/plans/2026-08-25-stewardship-baseline.md`
- Modify: `docs/epics/**`
- External: GitHub branch-protection settings and draft pull request #1

No implementation lane may modify runtime or configuration files in this epic.

## Work packages

### STW-01: Documentation correction review

**Owner:** Documentation agent

1. Compare every canonical claim with current source and configuration evidence.
2. Confirm no document describes a setup command, AutoCAD release, deployment path, or feature as verified without reproducible evidence.
3. Confirm safe-edit documentation requires a trusted human approval broker and explicit rollback outcomes.
4. Run the relative-link and audit-coverage checks from STW-02.
5. Return changed paths and a finding-by-finding resolution table.

### STW-02: Repository verification

**Owner:** Verification agent; read-only ownership except generated command output

Run:

```bash
python3 -m json.tool mcp.json
python3 -m compileall -q src tests
git diff --check main...HEAD -- . ':(exclude)docs/legacy/imported-2025/**'
git status --short
```

Use a Python standard-library checker to resolve relative Markdown links in the root README, `AGENTS.md`, canonical docs, specs, plans, and epic files. Compare all files below `docs/legacy/imported-2025/` with the archived paths recorded in `docs/legacy/document-audit.md`. Expected results are zero missing links, zero unaudited archived files, zero missing archived targets, and no non-legacy whitespace errors.

### STW-03: Protection configuration

**Owner:** Repository administrator

1. Require pull requests before merging to `main`.
2. Require at least one approving review when repository policy permits it.
3. Block force pushes and branch deletion on `main`.
4. Confirm `archive` still blocks force pushes and deletion.
5. Read back both branch-protection resources and attach the results to pull request #1.

### STW-04: Pull-request closure

**Owner:** Maintainer

1. Update pull request #1 with the fresh STW-02 results and known limitations.
2. Confirm the pull request contains documentation and metadata stewardship changes only and no runtime Python modification.
3. Resolve review comments and rerun STW-02 after the final commit.
4. Mark the pull request ready, obtain approval, and merge without force pushing.
5. Read back `main`, confirm the merge and protections, then mark Roadmap Stage 1 complete with links to evidence.

## Parallel-agent lanes

- STW-01 and STW-02 may run in parallel after the correction commit is available because STW-02 is read-only.
- STW-03 may run in parallel with documentation review because it changes repository settings, not files.
- STW-04 is sequential and begins only after STW-01 through STW-03 pass.

## Acceptance criteria

- Every imported document remains present at its audited archived path.
- All canonical relative links resolve.
- Canonical documentation contains no unsupported working, compatibility, security, or production-readiness claim.
- Draft pull request #1 reports fresh, exact verification evidence and limitations.
- `main` and `archive` have the required protection settings.
- Pull request #1 is approved and merged through the protected workflow.
- Roadmap Stage 1 is marked complete only after merged-state readback.

## Rollback

If documentation review fails, keep the pull request in draft and revert only the defective correction commit. If protection settings block legitimate maintenance, restore the last recorded protection configuration through repository-administrator controls; never force push either protected branch. The imported archive must remain unchanged throughout rollback.

## Completion evidence

- Final commit hash and merged pull-request URL
- Branch-protection readback for `main` and `archive`
- Exact STW-02 command output
- Relative-link and archive-audit counts
- Final changed-file list proving runtime Python was untouched

## Handoff

After Stage 1 closes, dispatch EPIC-01. No later epic may use historical documentation as current guidance or bypass the protected pull-request workflow.
