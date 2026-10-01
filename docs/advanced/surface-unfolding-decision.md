# Surface unfolding decision

Status: **integration_candidate**; pure service implementation and named-host
numerical measurements accepted. `unfold_surface` is registered in the current
integration branch. Portable MCP checks pass; independent final review and
hosted Windows/Linux CI remain pending before PR/merge.

The contract is [EPIC-09 Track U](../epics/EPIC-09-validated-advanced-feature-recovery.md#track-u-surface-unfolding).
The implementation plan is [surface unfolding](../superpowers/plans/2026-10-01-surface-unfolding.md).

## Supported input and output

Version one accepts a caller-supplied connected, oriented, embedded triangular
two-manifold mesh, with 3–2,000 vertices, 1–4,000 faces and explicit seams that
leave acyclic face-adjacency islands. Coordinates must be finite. The request
includes units, a root face and a bounded deterministic policy. Request/result
ceilings are 1 MiB/4 MiB; work is at most 1,000,000 iterations and 30 seconds with
cooperative cancellation checks. These are refusal limits, not hard process
isolation or memory enforcement.

Rigid propagation preserves source-oriented corners. All islands share one 2D
frame with the documented deterministic initial strip placement. The independent
verifier checks global overlap, orientation, edge/area/angle error and source
corner correspondence before success. Numerical thresholds are 1e-9. It never
repositions rejected charts to hide overlap. Failure returns no partial layout.

Unsupported inputs include NURBS, arbitrary AutoCAD surfaces, thick solids,
uncut adjacency cycles and self-intersecting/non-manifold meshes. No automatic
seam optimization, manufacturing allowances or manufacturing guarantee is
provided. The service reads no drawing, repository, file or process and mutates
nothing. AutoCAD is not a prerequisite for this track.

## Accepted evidence

| Evidence | What it establishes |
| --- | --- |
| [Frozen input manifest](../../tests/fixtures/unfolding/manifest.json) | 19 independently classified inputs, 10 admissible; SHA-256 `3f1c9c71931285cd48676c193d135b319e30068d928bd8f1cb9575e27b75c13c` |
| [Solver-stage evidence](evidence/unfolding/solver/2af14504aa57b7a36cdce3fafacb570e5966e38416b3b2a2d5eda2dcc1853bee.json) | All 10 admissible fixtures passed numerical verification with stage-local budgets; it also honestly records the former complete maximum-budget failure |
| Verifier repair `bb063fd`, service `f3f6428`, test correction `b82ff64` | Complete maximum fixture passes one unchanged budget; final service tests cover interruption, exact output bytes and no partial results |
| [Final named-host measurements](evidence/unfolding/performance/e296d80cc01c411dcf9722725f0cf20cbc91a1e60e367a6cb817c77ce5a6cd2b.json) | Complete service accepts 500/2,000/4,000-face torus bands using seed 9041; all overlap counts zero; actual result bytes 150,634/608,434/1,237,131 |

Final measurement host label is `linux-x64-reference-host`, Linux x86_64,
Python 3.12.14. Observed times were 1.332/5.645/11.531 seconds. Process-lifetime
cumulative peak RSS was 30,535,680/42,790,912/55,836,672 bytes. Regression tests
ran concurrently on this shared host; these observations are not cross-host
latency guarantees or per-case allocations. The earlier measurement remains
immutable; product digests are unchanged after removing an unnecessary runtime
type import. Both evidence filenames equal the SHA-256 of their exact bytes.

The final service change passed 30 focused tests and 456 full-suite tests with 9
skipped, plus Ruff, source mypy and syntax/import checks. Independent controller
review accepted the service; a subsequent one-string test correction passed its
focused import check. Solver and verifier implementations had different authors
and independent reviews. No AutoCAD runtime verification is inferred.

Reproduce the final service checks and measurements from this worktree:

```bash
uv run pytest tests/unit/advanced/unfolding/test_service.py -q
uv run python tests/performance/measure_unfolding.py --host-label linux-x64-reference-host --output-dir docs/advanced/evidence/unfolding/performance
```

Use an explicit nonpersonal host label for another environment. The harness
always derives the first 500/2,000/4,000 canonical faces of the frozen maximum
torus, retains referenced vertices, cuts all actual edges and fixes seed 9041.
It creates new content-addressed evidence and never overwrites prior outcomes.

## MCP integration evidence and remaining gates

The public `unfold_surface` tool accepts the direct seven-field request and
returns successful JSON with sibling `success: true` and `result` fields. The
result is the exact accepted payload: bare 64-hex input digest, request ID,
units, solver/verifier versions, geometry, metrics, warnings and issues. There
are no elapsed-time/RSS fields. Fixed mesh/resource/verification failures use
structured core codes and bounded diagnostics; deadline/cancellation failures
preserve their code/completed work without geometry, metrics or digest.

One stdlib `asyncio.to_thread` call invokes the accepted service. A
`threading.Event`-backed probe connects transport cancellation to its existing
cooperative budget. Cancelling the awaiting MCP call signals the worker and
prevents late result publication; it does not hard-kill a thread or promise a
domain response after the SDK cancels the request. A real stdio cancellation
notification stopped a controlled worker while a concurrent C request remained
responsive. Request-scoped effect guards permit standard thread dispatch and
AST-only C parsing, and reject file/process/network/environment/execution calls.

The actual serialized SDK `CallToolResult` body is bounded to 4,194,304 UTF-8
bytes, including nested JSON TextContent escaping and isError. Client JSON-RPC
IDs are transport metadata outside that body. Exact/one-over controlled guard
vectors accept 4,194,304 and reject 4,194,305; these are serialization checks,
not admitted physical results. The actual maximum service result occupies
1,333,254 bytes. The frozen worst-case vector occupies 3,417,137 bytes and is
explicitly serialization-only. Overflow yields fixed PAYLOAD_LIMIT without a
result. C retains its exact 65,536-byte body bound, refusal text/206-byte heavy
quote error and all nine accepted body digests.

[Immutable MCP evidence](evidence/unfolding/mcp/1bc9da8768f1b482842dcdcd815e2536104f64f96129ea51ad591d6ac35934a5.json)
has SHA-256 `1bc9da8768f1b482842dcdcd815e2536104f64f96129ea51ad591d6ac35934a5`.
It records four actual service cases through the default registered handler,
body/input hashes and metrics, the five-tool snapshot, shared size/cancellation
contracts and unchanged C evidence. It stores no drawing/source geometry.

The current catalog is exactly three basic tools plus C and U. Basic service
injection and lazy adapter composition are preserved; both pure calls bypass
the basic port, and invalid/unknown calls do not initialize it. Default server
imports remain free of adapter/context/capture/edit/COM modules. No execute,
apply, shell, interpreter, custom executor or task registry was added.

Fresh Linux integration checks passed **155 focused U/C/core/stdio tests in
27.23s** and one full run passed **742 tests, 9 skipped, in 82.06s**. Scoped Ruff,
mypy (nine source files), syntax and Bandit passed. The skip/platform limits
remain unchanged. These results are not Windows/AutoCAD evidence. Accepted
solver/verifier/models/service/bounds and frozen numerical inputs/measurement
records were not edited during integration.

Complete independent whole-U review, hosted Windows/Linux CI and a focused PR
before merge. Existing C has its own accepted release/CI record; U does not
promote its AutoCAD compatibility or complete another advanced track.

### Reproducible integration gate

Expose only the exact caller-supplied mesh schema. Test the real MCP result-body
byte limit including nested text escaping, structured failure mapping, default
server import isolation, stdout integrity and absence of drawing/file/process
calls. Preserve the existing catalogue and other accepted tracks. Then complete
independent final review, hosted Windows/Linux CI and a focused pull request.
The serialized integration window builds on Track C's merged core; its wire
contract and effect guards remain covered.
