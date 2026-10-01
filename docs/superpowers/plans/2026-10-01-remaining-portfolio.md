# Remaining Portfolio Execution

**User objective:** List and complete every remaining task the agent can perform. The user will execute real-application tests after implementation finishes.

**Current baseline:** `599e8a9` on `main`; PRs #1-3 and #5-8 are merged. This is a delivery ledger, not a claim of AutoCAD verification.

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
| EPIC-04 | Complete models, serialization, identities, fingerprints, cursors, immutable repository, native observer prerequisite, context adapters, builder, queries, relationships, MCP tools, fixtures, Windows runner | Models, identity, repository, owner frames and projection/cursors accepted; pure adapters in progress; native host/builder/tools pending |
| EPIC-05 | Explicit capture service/adapters, projection/overlay metadata, bounded image transport, restoration/failure tests and Windows runner | Pending |
| EPIC-06 | Preview, trusted non-MCP human approval broker, bounded mutation primitives, preflight, one-use approval, Undo/recovery, evidence and Windows runner | Pending |
| EPIC-07A | Evidence-based read-only architectural hypotheses, corpus/evaluation, MCP integration and Windows runner | Pending |
| EPIC-07B | Human-confirmed architectural edit compilation through accepted edit-plan pipeline | Pending |
| EPIC-08A | Domain-neutral topology, predicates/index/graph, closed-loop facts, MCP integration and Windows runner | Pending |
| EPIC-08B | Mechanical interpretations over accepted topology and evidence contracts, fixtures/evaluation and MCP integration | Pending |
| EPIC-09U | Validated numerical surface-unfolding delivery and constrained integration | Pure service and measured maximum case accepted; tool schema awaits review; MCP integration pending |
| EPIC-09C | Validated constrained code-generation delivery, security review and non-executing integration | All nine renderers and independent validator/service accepted; MCP integration in progress |
| EPIC-09P | Validated pattern-placement delivery using accepted topology | Pending |
| EPIC-09D | Validated dimension-proposal delivery using topology/mechanical context and approved edit path | Pending |
| Final integration | Full portable suite, import/schema/manifest agreement, independent reviews, focused PRs, current docs and a single ordered operator test guide | Pending |

## Operator-owned execution after implementation

- Clean Windows installation and full AutoCAD 2026 startup.
- Guarded base, context, capture, edits, semantic, topology, mechanical, and selected recovery-feature runs on disposable fixtures.
- Actual per-operation human approvals, including recovery decisions for preserved failed copies.
- Return redacted runner evidence. AutoCAD 2021-2025 stay targeted until separately tested.

The agent owns test code, fixtures that can be generated here, runner behavior, failure-injection checks, instructions, and evidence validation. It must not fabricate a successful real-device record or use missing hardware as a reason to leave implementable tasks unfinished.

## Current verified checkpoint

- Main remains `599e8a9`; PRs #1–3 and #5–8 are merged. A fresh GitHub readback
  finds only PR #4 open. It changes the pinned MCP major version and remains a
  separate migration review; it has not been merged into these feature branches.
- Baseline hosted evidence is Windows 233 passed/3 skipped and Linux 227 passed/
  9 skipped. This proves baseline dependency/portable/Windows-API behavior, not
  AutoCAD execution or the new unmerged feature branches.
- EPIC-04 source `d937fe7` now has independent contract/quality acceptance
  (plan checkpoint `380d805`): 49 changed tests, 249 context tests, 478 full tests,
  9 skips, plus independent marker/strict-roundtrip/cursor probes. Complete source
  identity survives response projection; projected records cannot become complete
  snapshots or fingerprints. Pure context records/fake/mapper are being built;
  their current uncommitted files are not accepted implementation evidence.
- EPIC-09U service `f3f6428` plus test correction `b82ff64` is independently
  accepted: 30 service tests and 456 full tests, 9 skips. The complete maximum
  fixture passes the unchanged shared work budget. Final immutable measurement
  `e296d80cc01c411dcf9722725f0cf20cbc91a1e60e367a6cb817c77ce5a6cd2b`
  records accepted 500/2,000/4,000-face runs in 1.332/5.645/11.531 seconds on the
  named Linux host, with cumulative process RSS and concurrent-load caveats.
  The earlier stage-local maximum failure remains in historical evidence and
  has been resolved; do not restart that repair. Tool-schema commit `208d311`
  passes 30 schema/84 affected core+stdio tests but awaits independent review.
  Handler, complete MCP body bound, registration and hosted feature CI remain.
- EPIC-09C source `cc0d959` is independently accepted at plan `58fcc0a`:
  84 focused tests and 464 full tests, 9 skips. All nine hand-reviewed goldens
  and 873 frozen malicious cases preserve their classification. Actual artifact
  bytes are bounded, with source never executed. MCP integration is active:
  closed schema, lazy default adapter composition, complete serialized result
  bound and core-only/no-execution tests. The first 19 red contract tests identify
  the missing integration; no registered-tool or hosted feature-CI claim yet.
- Native observer pure state/protocol `b2abd8a` is accepted: 90 native checks,
  69 focused Python/298 full tests, 9 skips, and three locked BCL builds. Actual
  SDK callback compile probes pass for the three pinned runtime profiles. Host
  events/authenticated Windows transport are still in progress. Client process
  incarnation and sampling-change races found during early review are assigned
  to that author. Windows pipe and real AutoCAD acceptance remain separate gates.

## Execution decisions

The accepted design and detailed epic specifications remain the full scope.
Runtime drawing approval is still separate from implementation authorization.
Real AutoCAD tests stay deferred to the user without relaxing drawing safety.
The cost of this scheduling choice is that compatibility remains unverified until
those runs occur; no production DWG is touched by implementation work here.

Shared server/runtime/catalogue/manifest integration is currently owned by
Track C. Track U and context may prepare isolated modules but must wait for that
window before editing the same integration surface. Completed pure foundations
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
