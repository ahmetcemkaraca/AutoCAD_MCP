# EPIC-08: General and Mechanical Semantics Split Index

## Status

**Split into two sequential sub-epics.** This file is an index only and is not an implementation plan or completion claim.

## Delivery order

1. [EPIC-08A: General Topology](EPIC-08A-general-topology.md) delivers domain-neutral, read-only topology over the released EPIC-04 geometry contract.
2. [EPIC-08B: Mechanical Semantics](EPIC-08B-mechanical-semantics.md) begins only after EPIC-08A is accepted and consumes its frozen topology/closed-profile contract plus the accepted EPIC-07 evidence contract.

EPIC-08A and EPIC-08B have separate work packages, file ownership, fixtures, evaluators, MCP registration windows, Windows/AutoCAD runs, acceptance records, rollback procedures, and evidence labels. Passing EPIC-08A does not imply that mechanical semantics are implemented or evaluated.

## Boundary summary

EPIC-08A owns topology primitives, predicates, spatial indexing, graph/loop/component facts, complete `TopologySnapshot` materialization, paged `TopologyResultPage`, semantic-input-keyed repository, and `query_topology`. Its initial primitive contract is intentionally limited to EPIC-04 point, line, arc, circle, and polyline geometry; it does not add spline, hatch, mesh, or other context schema fields.

EPIC-08B injects both EPIC-04 snapshot and EPIC-08A complete-topology repositories, requires exact full source/fingerprint/spec agreement, and owns mechanical facts plus evidence-based part, hole, axis, profile, dimension, and tolerance interpretations through `analyze_mechanical_semantics`. Geometry/native annotation facts remain separate from manufacturing interpretations, and unknown/unsupported outcomes remain visible.

## Shared constraints

- Both sub-epics are read-only and introduce no edit, approval, code-generation, capture, or arbitrary-execution path.
- Pure modules import and test without Windows COM.
- Fixture labels/evaluators freeze before detector/algorithm lanes and have exclusive owners.
- Canonical registry/configuration changes use `tests/contract/test_stdio_server.py` and `tests/contract/test_server_tool_catalog.py` in serialized windows.
- Dependency setup uses `uv sync --frozen --group dev`.
- AutoCAD evidence distinguishes input extraction verified on a named full AutoCAD release from algorithms/detectors evaluated on AutoCAD-extracted fixtures.

Related constraints: [EPIC-07](EPIC-07-architectural-semantics.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing](../testing.md), and [compatibility](../compatibility.md).
