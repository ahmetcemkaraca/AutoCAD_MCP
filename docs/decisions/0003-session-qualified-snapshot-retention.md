# 0003: Retain stable snapshot identities separately by document session

**Status:** Accepted implementation amendment; portable implementation and review pending.

**Date:** 2026-10-01

## Problem

EPIC-04 intentionally gives an unchanged saved drawing the same content digest
and snapshot ID after reopening, while its session UUID and ObjectIDs change.
An ID-only repository that always preserves the first record would return the
closed session after a fresh successful analysis. EPIC-06 would then correctly
reject every new preview until that old record expired. Replacing the first
record would instead break immutable historical paging.

## Decision

Retain each complete record under `(snapshot_id, session_id)`. Keep stable
fingerprint/snapshot-ID definitions and the existing `SnapshotRef` unchanged.
Expose `get_complete(snapshot_id, *, session_id=None)` and
`expires_at(snapshot_id, *, session_id=None)`. A qualified lookup resolves only
that pair. An unqualified lookup returns the sole live matching record; two or
more live sessions fail `SNAPSHOT_ID_COLLISION`, never pick an arbitrary session.
No live match returns `SNAPSHOT_EXPIRED` if a matching retained tombstone exists,
otherwise `SNAPSHOT_NOT_FOUND`. Invalid lookup types return not-found.

Insertion compares normalized identity facts with every live record sharing
the ID. Different facts still fail `SNAPSHOT_ID_COLLISION`, even across sessions.
Equal facts in the same pair preserve the original payload and expiry. Equal
facts in a new session create a separately bounded record and expiry. All
session records count toward the existing four-record/128 MiB limits; there is
no hidden session cache. Tombstones are also pair-qualified and share the
existing eight-entry limit and original-expiry-based retention.

Every consumer holding a `SnapshotRef` or snapshot cursor passes its session ID.
Historical pages therefore remain readable without opening AutoCAD while a
fresh analysis can return its new session's ObjectIDs. Future ID-only request
contracts gain an optional `source_session_id` when needed to disambiguate;
omission retains the unique-only rule. This additive input is a pre-release
contract amendment, not permission to silently replace caller identity with
the currently active document. Approval bindings still require the exact
session, document, content fingerprint and plan.

Within one session, idempotent insertion still preserves the first diagnostic
revision digest and timestamp. The digest proves the original complete read;
it is not a live authorization token. Freshness checks use fresh complete facts
and explicit expected state as already required by EPIC-06. Monotonic revision
tokens continue to guard each new multi-page read, including A-to-B-to-A edits.

## Alternatives and consequences

Adding session to the stable snapshot ID would violate the accepted reopen
identity invariant. Overwriting old payloads would invalidate historical
references. Waiting for expiry would make normal reopen workflows unusable.
The pair key preserves both guarantees with the same bounded dictionary.

The cost is an optional session argument at repository consumers and at later
ID-only request boundaries. Multiple retained sessions consume the existing
capacity faster. Required tests cover reopen with changed ObjectIDs, immutable
old-session paging, independent expiry, ambiguity, cross-session collisions,
capacity and pair-qualified tombstones. No real AutoCAD result is claimed.
