# Pure Surface Unfolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the agent-owned EPIC-09U candidate, including independent numerical validation and bounded pure-data MCP integration.

**Architecture:** Validate a caller-supplied triangular mesh and explicit seams, unfold its acyclic face islands by rigid triangle propagation, and admit outputs only after an independently implemented verifier. Reuse the core envelopes; never acquire AutoCAD/context/capture/edit services.

**Tech Stack:** Python 3.12, standard library, existing locked NumPy/SciPy only if a measured numerical need justifies use, pytest, canonical MCP core.

**Spec:** `docs/epics/EPIC-09-validated-advanced-feature-recovery.md`, shared contracts and Track U. This implements an already-approved portfolio under the maintainer's 2026-10-01 instruction to finish agent work before application testing.

## Global Constraints

- No AutoCAD/context/capture/mutation, arbitrary execution, subprocess, new dependency, or filesystem staging in production code.
- Preserve the exact request/result/failure dataclasses in the epic. Unknown fields, non-finite values, invalid topology, and excessive policy/request/result bounds fail explicitly, never clamp.
- Shared bounds: 200,000 items, 1,000,000 iterations, 30-second cooperative deadline, at most 1,024 work items between cancellation checks, 1 MiB request, 4 MiB result.
- Mesh bounds: 3–2,000 vertices and 1–4,000 faces; connected orientable two-manifold; consistent winding; no duplicates, degeneracies, intersections, or non-manifold vertex links; seams leave an acyclic face-adjacency forest.
- Success is deterministic from canonical input/version/seed/fixed work. Deadline/cancellation produces only typed failure with no partial layout or digest.
- Numerical acceptance comes from an independent verifier: edge/area relative error and angle error at most 1e-9, no accepted overlaps, reversible edge lengths.
- Solver authors never edit verifier implementations, frozen expected results, or reference labels.
- Each implementer owns only its task files, writes a report, commits tested changes, and dispatches no agents. Shared server registration occurs only after controller authorization.

## Contract clarifications for review

- `faces_2d` is ordered by ascending caller `face_id`; each triple contains zero-based indices into `vertices_2d`. The indexed source vertex IDs must exactly match that source face's oriented `vertex_ids`. Thus caller face/vertex identity remains recoverable without another ambiguous index convention.
- A source vertex may occur more than once in the same island when cutting seams separates corners. Output vertex indices, not `(source_vertex_id, island_id)`, identify those separate corners.
- All islands share one global output coordinate frame. Build rigid island charts, then perform one deterministic initial horizontal-strip placement: the requested-root island first (preserving its root anchor), remaining islands by minimum source face ID. Place each subsequent island's minimum x after the previous maximum x using a positive scale-relative gap, and align its minimum y to zero. The independent verifier checks overlaps globally. Do not reposition or retry after a verifier rejection; in-island overlaps always reject. This is initial chart placement, not sheet nesting, layout optimization, or a reduced within-island overlap claim.
- For multiple islands, the gap is `1e-6 * max_span`, where `max_span` is the maximum x/y bounding-box span of any rigid chart before placement. Require a finite positive gap, finite translations/output, and a representably greater next minimum x than the preceding maximum x; otherwise return a structured numerical failure, never clamp. The single-island case needs no gap. Global face output order still follows source face ID, independently of chart placement order.
- Text bounds: `request_id` 1–128 Unicode code points and `units_label` 1–64, no control characters. IDs are non-Boolean nonnegative integers at most 2**53-1, unique within their collection. Root face must exist; seams are unique canonical undirected edges present in the mesh.

## Review Focus

1. Bow-tie vertices, duplicate/reversed faces and disconnected shells that pass simple edge-count checks must fail validation.
2. Adjacent triangles sharing a legitimate edge/vertex must not be misclassified as self-intersections; excess coplanar overlap must fail.
3. Tiny/large or nearly degenerate finite triangles must never yield non-finite output or a falsely accepted layout.
4. Seams can duplicate corners within one island; face/source identity must survive that duplication.
5. Cancellation/deadline during validation, solver or verification must not leak an incumbent success or a cacheable digest.

### Task 1: Shared cooperative bounds and strict mesh contract (E09-0/U01)

**Files:** `src/autocad_mcp/advanced/__init__.py`, `advanced/bounds.py`, `advanced/unfolding/__init__.py`, `advanced/unfolding/models.py`, `advanced/unfolding/validation.py`; `tests/unit/advanced/test_bounds.py`, `tests/unit/advanced/unfolding/test_models.py`, `test_validation.py`; `tests/fixtures/unfolding/**`.

**Interfaces:** Exact `BoundedExecutionPolicy`, `MonotonicClock`, `CancellationProbe`, `BoundedFailureCode`, `BoundedExecutionFailure` and immutable ceiling constants from the epic. Exact Track U dataclasses. Produce a strict request decoder/normalizer and mesh validator returning immutable canonical adjacency/edge records; publish helper signatures in the report before the next task.

- [x] Write failing tests for strict types/fields/text/ID bounds, finite points, all mesh support rules, request policy ceilings, cancellation/deadline using injected fake clocks, and exact request byte/item boundaries.
- [x] Independently freeze at least ten accepted/rejected fixtures spanning planar grids, cylinders/prisms, cones/frusta, branched strips, islands, reversed/non-manifold/degenerate/intersecting inputs, plus maximum-size serialization vectors. Expected classifications are mathematical input facts, not solver outputs.
- [x] Run the three focused files and record red evidence before source implementation.
- [x] Implement bounded contracts and validation only. Check resource budget within potentially large validation loops. Do not build the solver, metrics verifier, or alter core registrations.
- [x] Run focused/full portable tests, scoped Ruff/mypy, compile/import checks. Commit and return exact signatures, fixed fixture digest inventory, results, and any remaining ambiguities.

### Task 2: Independent numerical verifier (E09-U03 verifier portion)

**Files:** `advanced/unfolding/metrics.py`, additive candidate/verification value types in `advanced/unfolding/models.py`, `tests/unit/advanced/unfolding/test_metrics.py`, `test_verifier_adversarial.py`.

**Interfaces:** Consume the accepted public `ValidatedMesh` (including its normalized
original request and seam-island topology), plus an unverified layout. Recompute
metrics without importing solver internals or copying its future algorithm.

```python
@dataclass(frozen=True)
class UnfoldingLayout:
    solver_version: str
    vertices_2d: tuple[UnfoldedVertex, ...]
    faces_2d: tuple[tuple[int, int, int], ...]
    cut_edges: tuple[tuple[int, int], ...]

@dataclass(frozen=True)
class LayoutVerification:
    accepted: bool
    metrics: UnfoldingMetrics | None
    issues: tuple[UnfoldingIssue, ...]

VERIFIER_VERSION = "rigid-triangle-verifier-v1"
def verify_layout(
    mesh: ValidatedMesh, layout: UnfoldingLayout, *, budget: WorkBudget
) -> LayoutVerification | BoundedExecutionFailure: ...
```

Malformed/incomplete candidate data returns a redacted rejection without fake
zero-valued metrics. Only successful complete verification supplies accepted
metrics. A detected overlap may reject immediately with its explicit face pair
and `metrics=None`; do not report a partial pair count as an exact metric.
Unexpected diagnostic overflow fails structurally rather than truncating.
Deadline/cancellation returns the exact bounded failure with no candidate data.

Validate all points as finite non-Boolean numbers, output indices as bounded
non-Boolean integers, used-vertex completeness, exact source face order/oriented
corner identity, exact cut-edge set, and expected `island-{root_face_id}` labels.
Check corner connectivity through uncut edges: they share output corner indices;
separate corner equivalence classes must not be accidentally welded merely
because their source vertex IDs agree. Derive these classes independently from
public input topology, never from solver internals. Preserve the requested root
anchor and orientation; reject flipped triangles. Measure every source/output
edge, area, and angle with numerically stable scaling, including very small and
large inputs. All success metrics must be finite and within the epic's 1e-9
thresholds. Global overlap checks include distinct islands and allow legitimate
zero-area boundary contact, never positive-area overlap. Use bounded spatial
candidates and the shared budget; no unbounded all-pairs scan.

- [x] Freeze tests with manually constructed valid triangles/islands and stretched, flipped, overlapping (including distinct islands), incomplete, non-finite, misindexed, unused-vertex, split-uncut-edge, and incorrectly welded seam layouts. Add scale extremes, near-degenerate cases, fixed-budget exhaustion, exact threshold boundaries, cancellation and expiry during verification. These are independent expected geometries, not solver-generated expectations.
- [x] Implement independent numeric checks and bounded global overlap candidates, including overlapping distinct islands; test cancellation and byte limits.
- [x] Verify and commit before dispatching solver implementation. Review global-frame and canonical face-index mapping explicitly.

### Task 3: Rigid unfolding solver (E09-U02)

**Files:** `advanced/unfolding/solver.py`, solver/golden/property/bounds tests only.

**Interfaces:** Consume normalized request/adjacency and frozen cooperative bounds. Produce an immutable candidate layout, not self-approved metrics. Preserve root face, winding and corner/source incidence.

```python
SOLVER_VERSION = "rigid-triangle-unfolding-v1"
def solve_layout(
    mesh: ValidatedMesh, *, budget: WorkBudget
) -> UnfoldingLayout | BoundedExecutionFailure: ...
```

Consume the already validated public topology; do not parse or revalidate the
request, construct another budget, or import verifier/validation private helpers.
Use deterministic face-ID-sorted traversal of each acyclic island; the requested
root owns its island and every other root is the minimum face ID. Root placement
uses the original oriented source corner order: first `(0, 0)`, second positive
x with y zero, third positive y. Propagation preserves oriented corners and
shares output indices only through the uncut edge; seam-separated corners may
repeat source IDs even within an island. Final faces follow global source-ID
order independently of traversal/strip order. Emit normalized requested cuts.

Only cancellation/deadline return `BoundedExecutionFailure`, preserving its exact
carrier. Unrepresentable/nonfinite/collapsed numerical output raises existing
`MeshValidationError("NUMERICAL_FAILURE", fixed_message)`; fixed item/work/result
limits raise `MeshValidationError("RESOURCE_LIMIT", fixed_message)`. No partial
candidate, metric, digest, raw value or source content accompanies these errors.
Check pending interruption before returning success or a numerical/resource
rejection, so an early limit does not hide cancellation. Every stage consumes
the supplied budget; the later service owns its final full result serialization.

Verify hand-computable goldens plus every mathematically accepted input fixture
with the independent public verifier. Report any numerical rejection honestly
and investigate it; never change frozen classifications or expected outputs.
Test tiny/large/thin triangles, a non-minimum requested root, within-island seam
corner duplication, shuffled input, deterministic repeated layout bytes, global
strip order/gap and unrepresentable separation, cancellation/deadline mid-solve
and pre-return, fixed-work/item bounds. Include one decode/validate/solve/verify
run sharing a single budget, rather than only stage-local fresh budgets.

- [x] Add failing rigid edge-preserving goldens, shuffled input determinism, branched/seamed cases and fixed-work/deadline/cancellation tests.
- [x] Implement canonical root placement, deterministic adjacency traversal, and the declared one-pass strip placement; no distortion minimizer, seam optimizer, overlap-driven repositioning, or hidden layout search.
- [x] Run independent verifier against fixtures. Do not edit verifier or frozen expectations to make results pass. Commit with evidence.

### Task 4A: Complete maximum-mesh verification within the shared work ceiling

**Files:** `advanced/unfolding/metrics.py`, additive focused byte/accounting
tests and a full public-pipeline regression. Independent verifier ownership;
the solver author must not implement or approve this repair.

The accepted solver's maximum fixture passes numerical verification in separate
stages, but one shared budget needs 1,123,782 work: decode114,049,
validation325,628, solver81,996, verifier602,109. The immutable ceiling is
1,000,000. This is an integration gap, not an accepted maximum-case refusal.

- [x] First add a failing exact-max public decode/validate/solve/verify test
  using one unchanged WorkBudget and the frozen torus fixture. A fixed injected
  clock isolates fixed-work accounting; real host timing remains Task4.
- [x] Replace duplicate/per-token verifier serialization work with exact,
  bounded per-record size accounting using standard-library encoding. Preserve
  every shape/connectivity/numerical/global-overlap check, actual UTF-8 bytes,
  diagnostic bounds, envelope reservations and interruption priority. All
  explicit potentially long loops must honor the caller's checkpoint interval;
  bounded native record encoding is not an unaccounted whole-layout scan.
- [x] Do not reset/increase budgets, change policy, skip verification, modify
  solver/validation/frozen corpus, add xfails or relabel accepted input. Reject
  genuine resource overflow without partial metrics/candidate/digest.
- [x] Prove measured bytes against independent full JSON serialization at exact
  boundaries, with Unicode/escapes, metrics and diagnostics. Keep the existing
  true4MiB overflow and late cancellation regressions. Verify exact-max shared
  acceptance plus focused/full regression, publish final stage counters, and
  obtain independent scoped review before Task4 integration.

### Task 4B: Pure orchestration and named-host evidence

**Files:** `advanced/unfolding/service.py`, focused service tests,
`tests/performance/measure_unfolding.py`, content-addressed evidence. Models may
only extract a reusable `decode_policy(value) -> BoundedExecutionPolicy` helper
and add optional bounded `issues` to MeshValidationError for rejection details.
No solver/verifier/bounds/registration or frozen-corpus changes.

```python
def unfold_surface(
    payload: object, *, clock: MonotonicClock | None = None,
    cancellation: CancellationProbe | None = None,
) -> UnfoldingResponse: ...
def result_payload(result: UnfoldingResponse) -> dict[str, JsonValue]: ...
```

Validate the small policy shape before constructing one WorkBudget; all mesh
decode, validation, solve, verification and result/digest work shares it. Do not
decode the full mesh once without a budget just to discover its policy. Reuse
the accepted normalized-request payload helper with checkpoints for canonical
hashing, rather than needlessly revalidating a trusted ValidatedMesh request.
Input digest is the lowercase64-character SHA-256 of the same canonical UTF-8
bytes defined by request_json; no elapsed/host data enters it. Do not call the
unbudgeted request_json path over a large request inside orchestration.

The service returns only an exact bounded failure on deadline/cancellation,
including during digest/result shaping. Other validation/numerical/resource
failures raise the accepted fixed MeshValidationError. A verifier rejection
raises VERIFICATION_FAILED with its bounded issues and no candidate/metrics/
digest. Success copies accepted candidate/metrics and fixed versions into the
exact UnfoldingResult, with no unsolicited warnings. Independently enforce actual
full result UTF-8 bytes including warnings/issues, not just candidate estimates.
The later MCP owner also checks its full serialized envelope. No classes,
factory framework, persistence or new dependency is needed for the pure service.

- [x] Write red service tests for validate-before-solve, verifier-before-success,
  every failure/interrupt stage, no partial result/digest, deterministic bytes,
  exact final size and the maximum fixture through this complete service under
  one unchanged budget. Test seams with function spies, not execution backdoors.
- [x] Implement the bounded service and pure payload helper; preserve all current
  algorithms, thresholds and corpus labels. All potentially long explicit loops
  need cooperative checks. Keep imports free of context/COM/capture/edit/files/
  processes. Invalid structured input must not leak exception text.
- [x] Measure real-clock service runs at500/2000/4000 faces with seed9041. Derive
  connected bands from the frozen maximum torus's firstN faces, retain referenced
  vertices and all actual edges as seams; record this deterministic construction
  and input hashes. Do not relabel/write the frozen source corpus.
- [x] Record explicit nonpersonal host label, OS/architecture/Python, policy,
  wall time, process peak RSS (state its cumulative semantics), input/result
  digests, versions, metrics and outcomes in new content-addressed immutable
  evidence. Measurement code may use filesystem/OS APIs; production may not.
  No subprocess or hard-kill claim, and no elapsed/RSS in product results.
- [x] Run focused/full checks, lint/types and import/no-effect checks. Obtain
  independent review before the serialized registration window below.

### Task 4: Serialized MCP integration and final acceptance (E09-U04)

**Files:** `tests/performance/measure_unfolding.py`, immutable numerical evidence, `advanced/unfolding/service.py`, `tools/surface_unfolding.py`, MCP tests; controller-owned server/runtime/catalog/manifest/docs during an exclusive integration window.

- [ ] Measure 500/2,000/4,000-face cases in-process with seed 9041, recording host/wall time/RSS outside results/digests. Publish rejected numerical cases honestly.
- [ ] Test that malformed/over-budget input never reaches solver, verifier rejection never reaches success, interrupted work returns no geometry, and result ceilings are enforced.
- [ ] Prove zero context/COM/capture/edit/file/process access and strict schema/envelope/stdout behavior.
- [ ] Record an independent per-track contract/pure/environment/registration decision. Integrate only this passing track, preserving other tools through the serial catalog owner.
- [ ] Run full portable regression, active lint/types/syntax/import/manifest checks, independent review, and focused PR. Update portfolio ledger without claiming completion of other tracks.
