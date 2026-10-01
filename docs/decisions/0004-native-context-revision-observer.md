# 0004: Observe native document lifetimes and covered changes

**Status:** Accepted implementation direction; host execution unverified.

**Date:** 2026-10-01

## Problem and evidence

EPIC-04 requires a fresh revision token after covered facts change, including
change-and-revert, and a new session UUID after closing/reopening a document.
Polling COM values or DBMOD cannot establish those guarantees: DBMOD is a
bitmask reset on save, and equal scanned facts hide intervening changes.
Proxy/ObjectID/window identity is also not a document-lifetime identity.
The old blanket exclusion of database-event subscriptions conflicts with the
required guarantee.

The official Autodesk-owned AutoCAD.NET.Core 25.1.0 reference package exposes
document lifetime, database mutation, command, view, quiescence and global lock
notifications, plus Database.FingerprintGuid and Document.Window.Handle.
A disposable probe built against these actual references using SDK 10.0.401
with zero warnings/errors. This is compile evidence only.

## Decision

Add a small, explicitly loaded managed AutoCAD observer. It keeps only native
document references needed to unsubscribe, per-open UUIDs, a bridge incarnation,
a monotonic change epoch, readiness, and optional database GUIDs. It does not
extract entity facts, mutate drawings or run commands. Python retains the
existing operation-scoped COM fact extraction and its `autocad_com` evidence.
The subscription exclusion is narrowed for this observer only; no in-memory
drawing replica or automatic analysis/capture is introduced.

Observe database writes (including open-for-modify), undo/redo-related object
events, system variables, view, commands, activation and lifecycle events.
Conservative extra epoch changes are permitted; missed changes are not. A
single bridge-wide counter is sufficient and deliberately invalidates reads
if another document changes. Counter exhaustion or lost observation disables
trusted witnesses instead of wrapping. Document UUIDs survive cancelled closes
and change after actual destruction/reopen. Safe UI-thread reconciliation of
the live document set establishes removal; a cancellable close event alone
does not retire identity.

Witness requests are sampled on the AutoCAD UI/idle thread. Readiness requires
the expected active document, quiescent editor, no command/modal/closing state,
and no global write/protected document lock. `Document.LockMode(true)` includes
all contexts; fiber-local `MyCurrentMode` is insufficient. Pipe workers never
read SDK objects. Every Python operation compares trusted before/after
witnesses; the builder still compares every page. Missing/lost/untrusted
observation fails `REVISION_TOKEN_UNAVAILABLE`, not a hash-based fallback.

Expose one bounded read-only local named-pipe operation. Authenticate the
kernel-reported server PID/creation time against the connected COM document's
process, and restrict clients to the current user and interactive Windows
session. Reject remote connections, oversized/unknown/duplicate fields,
replayed/mismatched nonces and deadlines. No endpoint accepts a member name,
source code, filename or mutation request. Diagnostics contain fixed codes
only. Package only this project's assembly, never Autodesk host binaries.

## Scope, alternatives and verification

A complete native extraction rewrite is deferred: the small observer supplies
the two missing guarantees while preserving the existing COM boundary. If
real-host tests show ordinary read-only COM getters invalidate every witness,
the acceptance gate requires a scoped native locked-read implementation; it
does not permit suppressing writer signals or claiming the thin path works.

First build profiles cover AutoCAD 2026 before/after its managed-runtime
update, using pinned real Autodesk references. Older releases remain targeted
and require matching compiled profiles and real-host acceptance; the product
support table is not promoted by this decision. No SDK stubs count as build
evidence. User-run tests cover unchanged reads, unseen change/revert, undo/redo,
modal/modeless writes, close cancellation, reopen/window reuse, process/plugin
restart/loss, and unchanged drawing bytes on disposable copies.

The cost is an explicitly loaded host component and build-time Autodesk
references. The alternative of weakening revision history would make stale
state checks unreliable and is rejected.

## Primary references

- [DBMOD semantics](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-E255E808-2D48-4BDE-A760-FFEA28E5A86F.htm)
- [Autodesk AutoCAD.NET.Core 25.1.0](https://www.nuget.org/packages/AutoCAD.NET.Core/25.1.0)
- [Database events](https://help.autodesk.com/cloudhelp/2026/ENU/OARX-DevGuide-Managed/files/GUID-E30279D1-E4B5-48A4-A3D8-9CEC83BD0967.htm)
- [Document locking](https://help.autodesk.com/cloudhelp/2026/ENU/OARX-DevGuide-Managed/files/GUID-A2CD7540-69C5-4085-BCE8-2A8ACE16BFDD.htm)
- [Managed runtime compatibility](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-A6C680F2-DE2E-418A-A182-E4884073338A.htm)
