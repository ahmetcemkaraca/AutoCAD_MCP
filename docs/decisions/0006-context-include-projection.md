# 0006: Project responses without changing their complete source identity

**Status:** Accepted pre-release clarification; implementation pending in CTX-03/04.

**Date:** 2026-10-01

## Problem

The three context tools accept include flags, but EntityContext currently has
mandatory geometry and a digest over complete entity facts. Removing geometry
cannot produce the declared record. Computing a digest from a projected subset
would also make it unsuitable for the complete expected-state checks in EPIC-06.

## Decision

Include flags control response projection. Canonical services acquire the full
version-1 entity fact coverage first, using all-true ContextInclude at the raw
adapter boundary. They calculate complete entity state digests before projecting
responses. This applies to live entity reads as well as retained analysis pages;
a live read still does not construct a whole-drawing fingerprint or repository
record. Include flags do not promise that unreturned properties are never read.
Default flags are all true.

Allow `EntityContext.geometry: GeometryFacts | None` for projected responses.
When a group is excluded, return null for geometry/bounds/block/text/dimension;
visual_style projection uses StyleFacts with all optional fields null. Keep
identity, owner space and layer facts. Add an informational CapabilityIssue with
code `NOT_REQUESTED`, the excluded group's capability name, the entity handle,
member null and required false. Geometry null requires that explicit geometry
projection marker. It is not an UnsupportedGeometry claim about the CAD engine.
Remove evidence pointers for excluded fields; do not mutate the retained source.

Preserve the source's complete `state_digest` in a projected entity. Consumers
cannot recompute that digest from the partial response alone. The public
`entity_state_digest` helper refuses projected records (null geometry or any
NOT_REQUESTED marker) with SNAPSHOT_INCOMPLETE. Complete drawing fingerprint
construction, DrawingSnapshot validation and repository admission also refuse
such records. UnsupportedGeometry remains valid for genuinely unsupported
entity families, with their existing explicit capability evidence.

EntitySummary continues to expose the actual geometry kind derived from the
complete source, even though it contains no geometry coordinates. Its bounds
may be omitted by projection; its state digest still refers to the complete
entity read. AnalyzeDrawingResult references the original complete snapshot;
include options never alter its snapshot ID, complete fingerprint or retained
payload. Projected response entities never enter SnapshotRepository.

Raw adapters may honor smaller internal include sets, but must mark omitted
groups explicitly. `map_entity_context` requires full coverage before producing
the complete state digest; it cannot promote a partial raw record. Canonical
services request the full set, so public include combinations remain supported.
Optional unavailable properties continue to produce their normal capability
issues; projection is not a way to bypass required fact or snapshot limits.

## Consequences and checks

This adds no new record family, tool or cache. Nullable response geometry and
strict complete-source guards correct an unreleased version-1 contract. The
cost is reading complete entity facts even for a small response. A future cheap
metadata-only API would need a different explicit identity contract rather than
silently reusing a partial digest for edits.

Tests must prove every include flag and all-false projection preserve source
digests/reference/retained bytes, omit only the requested groups and evidence,
and still produce strict valid response records. Null geometry without its
marker is invalid; projected records fail complete model/fingerprint/repository
boundaries. Live and analysis handlers acquire full adapter coverage, and none
of these reads triggers capture or mutation. Real AutoCAD verification remains
operator-owned after implementation.
