# Modernization Epic Portfolio

**Status:** Active implementation portfolio; real-application execution is deferred to the maintainer's final test phase.

**Documentation date:** 2026-10-01

This portfolio decomposes the approved AutoCAD MCP modernization design into independently reviewable implementation epics. The maintainer authorized all remaining agent-owned implementation on 2026-10-01 and will run real-application tests after implementation. Each delivery retains its own focused branch, execution plan, tests, review, and pull request. Real-device evidence is still required for full epic acceptance and compatibility claims.

## Portfolio outcomes

The portfolio delivers, in order:

1. closure of the stewardship baseline and protected workflow;
2. a reproducible Windows development and launch baseline;
3. one canonical, testable stdio MCP core;
4. a narrow Windows AutoCAD adapter with fake and real verification paths;
5. bounded, structured drawing facts;
6. explicitly requested visual capture;
7. human-approved and recoverable constrained edits;
8. evidence-based architectural semantics;
9. general and mechanical semantics; and
10. selective recovery of valuable historical research.

## Epic map

| Epic | Outcome | Depends on | Parallel execution |
| --- | --- | --- | --- |
| [EPIC-00](EPIC-00-stewardship-baseline-closure.md) | Close documentation review, branch protection, and pull request #1 | None | Documentation verification and protection configuration can run in parallel |
| [EPIC-01](EPIC-01-reproducible-windows-development-baseline.md) | Reproducible dependency, launch, version, and deployment baseline | Stewardship baseline | Starts first |
| [EPIC-02](EPIC-02-canonical-mcp-core.md) | One canonical stdio MCP server with three active read-only/status tools and structured contracts | EPIC-01 interface and launch decisions | Core schemas can begin after EPIC-01 metadata contract freezes |
| [EPIC-03](EPIC-03-windows-autocad-adapter-and-contract-tests.md) | Delayed read-only COM boundary, fake adapter, and AutoCAD 2026 smoke path | EPIC-01; adapter protocol agreed with EPIC-02 | Adapter and fake lanes run in parallel after protocol freeze |
| [EPIC-04](EPIC-04-structured-drawing-context.md) | Versioned, paginated drawing and entity facts | EPIC-02 and EPIC-03 | Data-model, extraction, and fixture lanes run in parallel after schema freeze |
| [EPIC-05](EPIC-05-on-demand-visual-capture.md) | Explicit current/extents/selection image capture | EPIC-02, EPIC-03, and EPIC-04 correlation metadata | Export, overlay, and MCP-result lanes run in parallel after capture contract freeze |
| [EPIC-06](EPIC-06-human-approved-safe-edit-plans.md) | Trusted human approval and recoverable constrained mutation | EPIC-02, EPIC-03, and EPIC-04 | Plan validation, human-broker integration, and mutation recovery lanes have separate ownership; human gates cannot be signed by agents |
| [EPIC-07](EPIC-07-architectural-semantics.md) | 07A read-only architectural hypotheses, followed by optional 07B human-confirmed edit compilation | EPIC-04 for 07A; EPIC-06 and accepted 07A for 07B; capture is optional | Detector lanes run in parallel; 07B cannot begin before its human-broker prerequisite |
| [EPIC-08 index](EPIC-08-general-and-mechanical-semantics.md) | Sequential split between domain-neutral topology and mechanical semantics | See EPIC-08A and EPIC-08B | The two sub-epics do not implement in parallel |
| [EPIC-08A](EPIC-08A-general-topology.md) | Domain-neutral topology and closed-loop facts | EPIC-04 | Predicate, index, and graph lanes run in parallel after contract/fixture freeze |
| [EPIC-08B](EPIC-08B-mechanical-semantics.md) | Evidence-based mechanical interpretations | Accepted EPIC-08A and EPIC-07A evidence contract | Mechanical detector lanes run in parallel against frozen topology/evidence vectors |
| [EPIC-09](EPIC-09-validated-advanced-feature-recovery.md) | Independently validated recovery of selected historical features | U: EPIC-02 only; C: EPIC-02 plus security review; P: EPIC-08A; D: EPIC-08A and EPIC-08B | Four candidate tracks run independently and merge separately after their exact gates |

## Dependency and delivery waves

```text
Wave 0: Stewardship corrections and main protection
   |
   v
Wave 1: EPIC-01
   |
   +-------------------+
   v                   v
Wave 2: EPIC-02     EPIC-03
   |                   |
   +---------+---------+
             v
Wave 3:    EPIC-04
             |
             +----------------+----------------+----------------+
             v                v                v                v
Wave 4:   EPIC-05          EPIC-06          EPIC-07A         EPIC-08A
             \                |                |                /
              +---------------+----------------+---------------+
                              v
                    Serialized registration queue
                              |
                    +---------+---------+
                    v                   v
Wave 5:          EPIC-07B            EPIC-08B

EPIC-09 U and C may start after their core/security gates. P waits for EPIC-08A; D waits for EPIC-08B.
```

Dependency arrows require reviewed upstream interfaces. Under the maintainer's 2026-10-01 instruction, portable implementation and integration may proceed after those interfaces and automated contracts pass while real-device execution is deferred to the final operator phase. Missing real-device evidence remains an explicit acceptance limitation; it cannot be reported as a passed gate.

EPIC-05, EPIC-06, EPIC-07A, and EPIC-08A may develop exclusively owned pure/fake feature modules in parallel. Their real-AutoCAD runs are separately serialized by the verification lease below. EPIC-07B and EPIC-08B begin only after their named gates. No feature or candidate track may concurrently edit `src/autocad_mcp/core/models.py`, `src/autocad_mcp/runtime.py`, `src/autocad_mcp/server.py`, `mcp.json`, or canonical catalog/stdio contract tests. A controller-owned registration queue serializes those shared changes, rebases each next feature branch onto the prior integration commit, and reruns every active core, adapter, context, feature, catalog, and stdio contract suite before the newly integrated epic closes.

## Parallel AI-agent operating model

### Controller responsibilities

One controller agent owns the epic branch and coordinates work packages. It must:

- read `AGENTS.md`, the modernization design, this portfolio, and the selected epic before dispatch;
- freeze and record shared interfaces before parallel code lanes begin;
- assign exclusive path ownership to each implementation agent;
- keep at most one agent editing a shared registration, schema-export, or documentation index file;
- require each implementation lane to return exact test output and changed paths;
- run an integration review after every wave; and
- stop the epic when an acceptance gate requires real AutoCAD, human approval infrastructure, or maintainer authority that is unavailable.

### Implementation-agent responsibilities

Each implementation agent receives one bounded work package with explicit inputs, outputs, owned files, tests, and prohibited paths. An agent must not widen scope, modify another lane's files, create a new dependency, or claim AutoCAD verification from mocks or Linux checks.

### Review gates

Every work package has two independent reviews before integration:

1. **Contract review:** confirms the implementation matches the epic, interfaces, safety rules, and acceptance criteria.
2. **Quality review:** checks correctness, failure behavior, tests, documentation, and unnecessary complexity.

A failed review returns to the same implementation lane. The controller does not create a replacement interpretation of the work while the original lane can correct it.

Before dispatch, the controller creates `docs/verification/<epic-id>-work-package-review-matrix.md` with one row per work package. The identifier includes its suffix, such as `epic-07a`, `epic-07b`, `epic-08a`, or `epic-08b`:

| Work package | Implementer | Contract reviewer | Quality reviewer | Evidence artifact | Gate authority |
| --- | --- | --- | --- | --- | --- |
| Exact work-package ID | Assigned agent or human | Different reviewer | Different reviewer | Command output and review record path | Agent-reviewable, maintainer-only, repository-admin-only, security-owner-only, or human-operator-only |

No implementer may review its own package. “Reviewer gate: none” means no intermediate design stop; it does not waive the two completion reviews. Agent reviewers may sign only agent-reviewable gates. A controller or model must not sign maintainer approval, repository administration, human approval-broker authority, security-owner acceptance, or real-AutoCAD operator evidence.

## Shared interface freeze rules

The following artifacts are shared contracts and must be changed sequentially by the controller or a designated integration lane:

- canonical MCP tool registration and public schemas;
- adapter protocols and capability identifiers;
- `DrawingSnapshot`, `EntityContext`, and fingerprint schemas;
- edit-plan and approval-record schemas;
- package metadata and lockfiles;
- root documentation and compatibility status; and
- the epic portfolio index.

Parallel agents consume a tagged commit or recorded commit hash containing the frozen contract. Interface changes after dispatch require all affected lanes to stop, rebase, and rerun their focused tests.

## Guarded real-AutoCAD fixture policy

Every real-AutoCAD lane reuses EPIC-03's neutral drawing-copy guard instead of accepting a caller-prepared mutable drawing. The guard resolves an immutable source fixture, creates a unique GUID-named copy below an OS-generated temporary directory, proves source/copy path inequality and matching initial hashes, verifies the active document `FullName`, closes without saving, and rechecks the source hash. EPIC-03 wraps it with a forced-read-only policy; EPIC-06 owns a separate writable-copy policy for approved mutation cases. Mutation matrices use a fresh copy per case. A copy involved in induced `rollback_failed` or uncertain cleanup is preserved for named human diagnosis; successful read-only copies are removed after evidence capture.

## Exclusive real-AutoCAD verification lease

Parallel planning, pure tests, fake-adapter tests, and implementation lanes do not authorize concurrent attachment to one real AutoCAD process. Before any real-AutoCAD command, the controller and runner acquire the EPIC-03 verification lease keyed by AutoCAD installation/build and Windows interactive-session ID. The lease records owner process, epic/work-package, fixture, acquisition time, and release outcome; acquisition fails closed while a live owner exists. Stale-owner recovery requires proof that the recorded process is dead and is recorded as evidence.

Only one real verification lane may run against an AutoCAD instance/session at a time because active-document changes, plot variables, and application state are shared. Parallel real runs require isolated VMs or distinct interactive sessions with different lease keys. Every AutoCAD evidence record includes lease acquisition and release output; an unleased run cannot satisfy an acceptance gate.

## Branch and pull-request policy

- Use one `codex/<epic-id>-<short-name>` integration branch per independently accepted delivery unit.
- Use short-lived work-package branches or isolated worktrees beneath the epic branch.
- Merge work packages into the epic branch only after both review gates pass.
- Open one pull request and one completion record per delivery unit. EPIC-07A, EPIC-07B, EPIC-08A, and EPIC-08B each have separate branches, review matrices, registration windows, acceptance records, and pull requests. EPIC-09 uses one pull request per candidate feature.
- Do not combine unrelated epics in one pull request.
- The epic pull request must report exact verification commands, Windows and AutoCAD versions, fixture revisions, limitations, documentation impact, and rollback instructions.

## Global completion rules

An epic is complete only when:

- every acceptance criterion has reproducible evidence;
- required automated suites pass from a clean environment;
- required full-AutoCAD checks pass on the named release and disposable fixture;
- unsupported releases remain labelled `targeted`, not `verified`;
- tool metadata, schemas, implementation, tests, and documentation agree;
- drawing mutation safety requirements pass failure-injection tests;
- current documentation is updated in the same pull request; and
- deferred work is linked to another named epic rather than hidden in prose.

Code presence, mock behavior, syntax checks, line counts, elapsed time, or an AI-agent completion message are not completion evidence.

## Portfolio-level risks

| Risk | Control |
| --- | --- |
| Parallel agents edit the same contracts | Freeze interfaces first and enforce exclusive path ownership. |
| Mocks diverge from AutoCAD COM | Keep the fake contract narrow and require named real-AutoCAD gates. |
| A model approves its own mutation | Keep the approval broker outside model-callable MCP tools and fail closed without trusted human confirmation. |
| An Undo group is mistaken for a transaction | Require failure injection, state reread, fingerprint checks, and explicit rollback outcomes. |
| Historical modules regain unsupported claims | Recover each candidate through EPIC-09 with an independent evidence gate. |
| Documentation drifts after implementation | Make documentation agreement an epic merge criterion. |

## Canonical references

- [Modernization design](../superpowers/specs/2026-08-25-maintenance-and-modernization-design.md)
- [Architecture](../architecture.md)
- [Project status](../project-status.md)
- [Roadmap](../roadmap.md)
- [Testing policy](../testing.md)
- [Compatibility policy](../compatibility.md)
- [Contributor and agent rules](../../AGENTS.md)
