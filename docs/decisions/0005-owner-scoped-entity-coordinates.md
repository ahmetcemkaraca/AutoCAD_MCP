# 0005: Represent entity coordinates in their actual owner frame

**Status:** Accepted pre-release contract amendment; implementation pending.

**Date:** 2026-10-01

## Problem

EPIC-04 enumerates block definitions as well as model and paper layouts, but
names all entity coordinates as drawing WCS. A definition can be inserted more
than once with different transforms, or not inserted at all. Its own entity
coordinates therefore have no single insertion-expanded WCS value. Choosing
an arbitrary insertion would invent facts and produce false spatial relations.

## Decision

Use the existing `EntitySpace` discriminator as the explicit coordinate frame;
do not add a second redundant frame field. `kind="model"` means model WCS,
`kind="paper"` means the named layout's paper WCS, and
`kind="block_definition"` means the local frame of `owner_block_handle`.
Paper requires a nonempty layout name. Block definitions require an owner
handle and no layout name. Model layout name may be its observed bounded
display name or null; do not hard-code an English name to identify the model
space. Layout block owner handles may be retained as observed ownership metadata.

Rename the pre-release entity coordinate slots to frame-neutral names:

| Record | Old fields | New fields |
| --- | --- | --- |
| LineGeometry | start_wcs, end_wcs | start, end |
| CircleGeometry / ArcGeometry | center_wcs, normal_wcs | center, normal |
| PolylineGeometry | vertices_wcs | vertices |
| PointGeometry | position_wcs | position |
| BlockReferenceGeometry | insertion_wcs, normal_wcs | insertion, normal |
| TextFacts | insertion_wcs | insertion |
| DimensionFacts | text_position_wcs | text_position |
| EntityContext / EntitySummary / AdapterEntityFacts | bounding_box_wcs | bounds |

OCS conversion produces the containing owner's Cartesian frame, not an
arbitrary block-instance expansion. Geometry, text/dimension positions and
bounds in an entity record all use that same frame. Evidence JSON pointers
follow the renamed fields. `Bounds3D` itself is a frame-neutral geometric
value; document UCS/view fields retain their explicit WCS/ UCS names.
`EntityQueryFilters.intersects_wcs` remains explicitly WCS.

Spatial comparisons require equal owner frames: model with model, paper only
within the same layout, and definitions only within the same owner block.
Equal local coordinates in two different definitions do not establish a
touch/intersection. A WCS bounds filter never compares against local definition
coordinates. An explicit definition-space WCS-filter request fails unsupported;
an all-space live query reports an explicit definition-projection capability
issue while filtering the WCS spaces. Complete analysis uses no filters and
continues to include all bounded definition facts.

Capture/edit/semantic/topology consumers must establish the frame before any
WCS projection or comparison. Version 1 does not flatten every block instance
or invent transformed circle facts under nonuniform scale. Such projection
requires an explicit supported instance transform; otherwise return the
existing structured unsupported capability. Ordinary model/paper extraction
and full owner-local block facts remain implemented scope.

## Compatibility and checks

These fields have not been published or registered in MCP; this is a
pre-release correction to version 1.0, not a migration of a released schema.
Update models, strict codecs, fingerprints, fixtures, fact pointers and the
downstream epic examples together; reject obsolete keys rather than silently
aliasing them. Tests cover owner requirements, unchanged WCS document fields,
exact roundtrip, owner-dependent digest changes, cross-owner spatial isolation
and unsupported WCS projection. Existing bounded snapshot/paging/identity
requirements still apply.

Cost: internal fixture/import changes before EPIC-04 release. Keeping deceptive
WCS names or excluding all definition geometry was rejected because both would
weaken the promised facts.
