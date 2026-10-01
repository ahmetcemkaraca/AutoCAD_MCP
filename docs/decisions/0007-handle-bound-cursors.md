# 0007: Bind continuation to a handle instead of copying layout names

**Status:** Accepted pre-release cursor amendment; implementation pending.

**Date:** 2026-10-01

A valid 255-character Unicode layout can make the old signed snapshot cursor
exceed its 2,048-byte ceiling because the whole layout sort key is embedded in
base64 JSON. A concrete cursor using a 255-emoji layout, normal UUID session,
valid IDs and a 16-digit handle fails INVALID_CURSOR. Larger case-folded names
and duplicated inner/outer live keys make this representation unsuitable for
otherwise valid drawing facts.

Replace the private PageCursor.last_sort_key field with
`last_handle: str | None`. A non-null value must already be normalized uppercase
hex under the existing handle bound. Preserve document/session, query/include
digest, page size, kind, revision/snapshot identity, issued/expiry and HMAC
bindings. Tokens remain opaque to clients; this has not been released, so no
old-token alias or compression layer is needed.

Snapshot continuation resolves the unique handle in the retained, session-bound
complete snapshot and resumes after that entity's actual canonical sort key.
Ordering still uses space, case-folded layout and numeric handle; it is never
replaced by handle-only sorting. Missing boundary handles reject INVALID_CURSOR.
Historical paging still needs no AutoCAD access.

An adapter cursor similarly binds a last handle to the unchanged document/session,
revision and request. The adapter resolves its current canonical key only after
revision validation. Public live cursors carry the compact adapter cursor and
can leave last_handle null. Never copy a long layout name into both layers.
With actual UUID sessions and maximum handles, both inner and outer production
tokens must fit the existing 2,048-byte ceiling. Generic aggregate oversize still
rejects; no limit is raised or stateful cursor cache added.

Tests cover maximum handles, Unicode/case-folded layouts, nested live bindings,
tampering/expiry and obsolete/invalid fields. Later service tests must prove
continuation across spaces/layouts with interleaved numeric handles, so resolving
a handle does not accidentally change global order. Non-default filters/include
options/page size must be repeated when continuing; their digest is a binding,
not storage of the original query settings.

Cost: a private pre-release constructor/test change and a bounded boundary lookup
in the retained snapshot or revision-checked adapter. No public tool schema,
drawing identity, fingerprint or retained payload is changed.
