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
| EPIC-04 | Complete models, serialization, identities, fingerprints, cursors, immutable repository, native observer prerequisite, context adapters, builder, queries, relationships, MCP tools, fixtures, Windows runner | In progress: models/identity accepted; repository session amendment and native observer underway |
| EPIC-05 | Explicit capture service/adapters, projection/overlay metadata, bounded image transport, restoration/failure tests and Windows runner | Pending |
| EPIC-06 | Preview, trusted non-MCP human approval broker, bounded mutation primitives, preflight, one-use approval, Undo/recovery, evidence and Windows runner | Pending |
| EPIC-07A | Evidence-based read-only architectural hypotheses, corpus/evaluation, MCP integration and Windows runner | Pending |
| EPIC-07B | Human-confirmed architectural edit compilation through accepted edit-plan pipeline | Pending |
| EPIC-08A | Domain-neutral topology, predicates/index/graph, closed-loop facts, MCP integration and Windows runner | Pending |
| EPIC-08B | Mechanical interpretations over accepted topology and evidence contracts, fixtures/evaluation and MCP integration | Pending |
| EPIC-09U | Validated numerical surface-unfolding delivery and constrained integration | Contracts/validation/corpus accepted; independent verifier implemented and under review |
| EPIC-09C | Validated constrained code-generation delivery, security review and non-executing integration | Pending |
| EPIC-09P | Validated pattern-placement delivery using accepted topology | Pending |
| EPIC-09D | Validated dimension-proposal delivery using topology/mechanical context and approved edit path | Pending |
| Final integration | Full portable suite, import/schema/manifest agreement, independent reviews, focused PRs, current docs and a single ordered operator test guide | Pending |

## Operator-owned execution after implementation

- Clean Windows installation and full AutoCAD 2026 startup.
- Guarded base, context, capture, edits, semantic, topology, mechanical, and selected recovery-feature runs on disposable fixtures.
- Actual per-operation human approvals, including recovery decisions for preserved failed copies.
- Return redacted runner evidence. AutoCAD 2021-2025 stay targeted until separately tested.

The agent owns test code, fixtures that can be generated here, runner behavior, failure-injection checks, instructions, and evidence validation. It must not fabricate a successful real-device record or use missing hardware as a reason to leave implementable tasks unfinished.

## Progress

- 2026-10-01: Revalidated clean `main`, merged baseline, and absence of open PRs. Started isolated EPIC-04 implementation from the accepted core.
- 2026-10-01: Ruling: Existing accepted design and detailed epic specifications are the implementation scope; the explicit request to do all tasks supplies execution authorization. Real-device acceptance remains deferred to the user, without relaxing drawing-safety rules. Cost if wrong: integration sequencing may need adjustment; no production DWG is touched.

## Recovery after interruption

Inspect this ledger, Git worktrees, branch history, each active epic plan, and that plan's SDD progress file before dispatching work. Resume the first incomplete task. A running agent must be polled or messaged, not duplicated. Completion requires checking every delivery above against code, portable test results, review records, and the operator handoff; a completed first epic is not completion of this objective.

## 2026-10-01 implementation checkpoint

- Main is `9d7ec0e`: PR #5 closes stewardship records; PR #6 adds clean Windows/Linux CI and repairs file identity, Windows ACL/process-liveness, exact fixture bytes and COM-free protocol tests; PR #7 retires the inactive Poetry lock and unsupported container files. Every PR had independent review and green applicable checks.
- Fresh foundation matrix: Windows 233 passed/3 expected skips; Linux 227 passed/9 expected skips. These are dependency/portable/Windows-API results, not AutoCAD execution.
- EPIC-04 Task 1 accepted after two review findings were fixed: exact dict/Mapping serializer interface and structured UTC overflow errors. Task 2 implementation `94e8a95` has 62 focused / 121 context / 336 full portable tests passing with 9 expected skips, and is awaiting independent reviews.
- EPIC-09U contracts, strict topology, cooperative bounds and 19 input fixtures are accepted after a structured-recursion-error fix. Main integrated into its separate worktree: 319 portable tests passed / 9 skipped. The verifier is being implemented independently before the solver. Global output overlap checks remain required; the initial proposal to check only per-island frames was explicitly rejected.
- All capture, edit approval/recovery, architectural/general/mechanical semantics, remaining recovery tracks, final catalog integration, and complete operator handoff remain in scope and unfinished. This checkpoint does not complete the goal.

## Latest checkpoint: session and native observer prerequisites

- Main `599e8a9` includes PR #8: private raw exception details removed from active
  core/adapter diagnostic logs, with regression and hosted Linux/Windows checks.
- EPIC-04 identity/cursors are accepted. Repository implementation `8166e57`
  passed 63 focused / 411 full portable tests with 9 expected skips. Decision
  0003 corrects pre-release ID-only retention to preserve old/new sessions under
  stable saved-drawing identity; amendment and independent review are pending.
- Decision 0005 corrects block-definition coordinate ownership before adapters:
  existing EntitySpace discriminates model/paper/owner-local frames. Domain field
  changes, adapter extraction and downstream projection checks remain pending.
- A separate native observer plan supplies trustworthy session/revision metadata
  to COM extraction. Real official Autodesk reference compilation is available;
  pure observer state/protocol implementation is underway. No native-host or
  AutoCAD acceptance is claimed. This prerequisite preserves the full requested
  context guarantee instead of substituting a state hash for change history.
- EPIC-09U verifier `6184181`: 50 focused / 142 advanced / 369 full tests passed,
  9 expected skips. Independent controller quality review passed; separate
  contract review is underway. Solver, combined-budget/performance evidence,
  service and MCP integration are still pending.
- PR #4 remains a separate major MCP SDK migration review. It is not merged
  into the frozen runtime stack and is not counted as portfolio completion.
- EPIC-05/06/07A/07B/08A/08B/09C/09P/09D, final integration and the ordered
  operator test handoff remain unfinished and authorized. Do not mark the goal
  complete after these prerequisites alone.
