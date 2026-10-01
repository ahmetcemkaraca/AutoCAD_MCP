# Remaining Portfolio Execution

**User objective:** List and complete every remaining task the agent can perform. The user will execute real-application tests after implementation finishes.

**Current baseline:** `67f2adf` on `main`; PRs #1-9 are merged. This is a delivery ledger, not a claim of AutoCAD verification.

## Authority and completion boundary

The user's 2026-10-01 instruction authorizes implementing the existing modernization design and all remaining epic work. It changes the scheduling of real Windows/AutoCAD gates: prepare their runners and assertions now, and collect operator evidence after all implementation. Missing operator evidence does not block portable implementation or draft integration branches. It still prevents any feature/release being labelled AutoCAD-verified or any epic requiring such evidence being marked fully accepted.

Use the approved design and epic contracts; preserve their safety, validation, privacy, bounded-resource, and human-approval requirements. Runtime approval of individual drawing edits is never supplied by this implementation authorization. Deliver one focused PR per epic/sub-epic/candidate. Follow the existing dependency order; do not invent a reduced replacement objective.

## Agent-owned work

| Delivery | Remaining implementation and evidence | State |
| --- | --- | --- |
| EPIC-00 | Read back merged PR/protection state, validate canonical links/archive audit, update closure record | Done; PR #5 merged |
| EPIC-01 | Verify reproducible portable setup, add missing baseline CI, resolve documented historical artifact disposition, prepare clean Windows install witness | Done agent work; clean Windows/Linux evidence and PRs #6/#7 merged |
| EPIC-02 | Keep the accepted canonical core and its regression suite passing as tools are added; record merged evidence | Implemented; documentation pending |
| EPIC-03 | Preserve adapter contracts and guarded smoke, consolidate operator handoff and evidence collection | Implementation present; handoff audit pending |
| EPIC-04 | Complete models, serialization, identities, fingerprints, cursors, immutable repository, native observer prerequisite, context adapters, builder, queries, relationships, MCP tools, fixtures, Windows runner | Models, identity, repository, projection/cursors and both adapters accepted; builder/relationships active; native packaging, services and tools pending |
| EPIC-05 | Explicit capture service/adapters, projection/overlay metadata, bounded image transport, restoration/failure tests and Windows runner | Pending |
| EPIC-06 | Preview, trusted non-MCP human approval broker, bounded mutation primitives, preflight, one-use approval, Undo/recovery, evidence and Windows runner | Pending |
| EPIC-07A | Evidence-based read-only architectural hypotheses, corpus/evaluation, MCP integration and Windows runner | Pending |
| EPIC-07B | Human-confirmed architectural edit compilation through accepted edit-plan pipeline | Pending |
| EPIC-08A | Domain-neutral topology, predicates/index/graph, closed-loop facts, MCP integration and Windows runner | Pending |
| EPIC-08B | Mechanical interpretations over accepted topology and evidence contracts, fixtures/evaluation and MCP integration | Pending |
| EPIC-09U | Validated numerical surface-unfolding delivery and constrained integration | Pure service, MCP integration and independent final review passed; PR #10 awaits Windows CI repair and merge |
| EPIC-09C | Validated constrained code-generation delivery, security review and non-executing integration | Done; PR #9 merged after independent review and hosted Windows/Linux CI |
| EPIC-09P | Validated pattern-placement delivery using accepted topology | Pending |
| EPIC-09D | Read-only dimension proposals using accepted topology/mechanical facts; no dimension creation | Pending |
| Final integration | Full portable suite, import/schema/manifest agreement, independent reviews, focused PRs, current docs and a single ordered operator test guide | Pending |

## Operator-owned execution after implementation

- Clean Windows installation and full AutoCAD 2026 startup.
- Guarded base, context, capture, edits, semantic, topology, mechanical, and selected recovery-feature runs on disposable fixtures.
- Actual per-operation human approvals, including recovery decisions for preserved failed copies.
- Return redacted runner evidence. AutoCAD 2021-2025 stay targeted until separately tested.

The agent owns test code, fixtures that can be generated here, runner behavior, failure-injection checks, instructions, and evidence validation. It must not fabricate a successful real-device record or use missing hardware as a reason to leave implementable tasks unfinished.

## Current verified checkpoint

- Main is `67f2adf`; PRs #1–9 are merged. PR #4 initially broke server import
  with MCP 2.2 (`Server.list_tools` missing). The repaired dependency PR retains
  `mcp>=1,<2` (locked 1.30.0); independent review and hosted Windows 499/3 skips
  and Linux 493/9 skips passed before merge. Optional ML workloads were not run.
  PR #10 contains U; its Windows integration failure is under investigation.
- Baseline hosted evidence is Windows 233 passed/3 skipped and Linux 227 passed/
  9 skipped. This proves baseline dependency/portable/Windows-API behavior, not
  AutoCAD execution or the new unmerged feature branches.
- EPIC-04 source `d937fe7` now has independent contract/quality acceptance
  (plan checkpoint `380d805`): 49 changed tests, 249 context tests, 478 full tests,
  9 skips, plus independent marker/strict-roundtrip/cursor probes. Complete source
  identity survives response projection; projected records cannot become complete
  snapshots or fingerprints. Pure context records/fake/mapper are now accepted through `60e3c2c`: 48 focused/
  526 full tests plus 13 scoped mapper checks after an evidence-binding fix.
  Accepted native pure protocol was merged at `ea5ee70`; 120 combined tests passed.
  Windows extraction is accepted through `621b7d2`; after merging main,
  987 full tests and 5 fresh import checks passed. Builder, relationships and
  context services remain pending.
- EPIC-09U service `f3f6428` plus test correction `b82ff64` is independently
  accepted: 30 service tests and 456 full tests, 9 skips. The complete maximum
  fixture passes the unchanged shared work budget. Final immutable measurement
  `e296d80cc01c411dcf9722725f0cf20cbc91a1e60e367a6cb817c77ce5a6cd2b`
  records accepted 500/2,000/4,000-face runs in 1.332/5.645/11.531 seconds on the
  named Linux host, with cumulative process RSS and concurrent-load caveats.
  The earlier stage-local maximum failure remains in historical evidence and
  has been resolved; do not restart that repair. Tool-schema commit `208d311`
  passes 30 schema/84 affected core+stdio tests and now has independent
  contract/quality acceptance.
  Handler, complete MCP body bound and registration are implemented at `5c1ac9b`.
  Independent whole-U review passed with 248 focused and 742 full tests/9 skips.
  Main dependency merge `95c4e47` passed 742/9 again locally. Hosted Windows
  integration has a failure/stall and must pass before PR #10 merges.
- EPIC-09C is delivered through [PR #9](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/9),
  merged as `82b85a2`. All nine templates, independent static validation,
  default-server isolation and complete 65,536-byte SDK result bound passed
  independent final review. Hosted Windows: 499 passed/3 skipped; Linux:
  493 passed/9 skipped. Lint/types/syntax/import checks, CodeQL and GitGuardian
  passed. Windows CI's long pytest IDs were corrected without shrinking input
  cases. This track requires no AutoCAD execution; other tracks remain open.
- Native observer pure state/protocol `b2abd8a` is accepted: 90 native checks,
  69 focused Python/298 full tests, 9 skips, and three locked BCL builds. Actual
  SDK callback compile probes pass for the three pinned runtime profiles. Host
  events/authenticated transport are accepted at `f518e83`; harness correction
  `7cbaacc` has 39 native checks and 4 portable lifecycle checks. Real Windows
  pipe tests remain pending. Task3 packaging/CI/operator runner is active.
  Real AutoCAD acceptance remains an operator gate after implementation.

## Execution decisions

The accepted design and detailed epic specifications remain the full scope.
Runtime drawing approval is still separate from implementation authorization.
Real AutoCAD tests stay deferred to the user without relaxing drawing safety.
The cost of this scheduling choice is that compatibility remains unverified until
those runs occur; no production DWG is touched by implementation work here.

Shared server/runtime/catalogue/manifest integration is currently owned by
Track U after Track C merged. Context may prepare isolated modules but must wait
for that window before editing the same integration surface. Completed pure foundations
do not establish full epic completion.

## Recovery after interruption

Inspect this ledger, current worktrees/branch history, each active epic plan and
its ignored SDD ledger before dispatching work. Current files and live agent/tool
state override older summaries. Resume incomplete work; never duplicate a live
implementation after an observation timeout. Historical checkpoint details remain
in Git history and per-plan reports rather than competing with this current table.

Completion requires every delivery above to be implemented, independently
reviewed where required, tested at the appropriate portable/Windows boundary,
integrated through focused PRs, and included in one operator handoff. A successful
first epic, foundational module or mock test does not complete the objective.
