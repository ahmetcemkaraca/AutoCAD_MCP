# 0002: Freeze legacy mutation evidence before canonical server consolidation

**Status:** Proposed — compatibility record prepared; no EPIC gate is accepted by this record.

**Date:** 2026-08-29

## Context and evidence boundary

EPIC-01's selected entry point is currently `src.server`.  It is a low-level
`mcp.server.Server` stdio server that registers seven tools, one resource, and
one prompt.  Linux preparation for the safe, platform-independent core is
authorized while EPIC-01's Windows/AutoCAD evidence remains pending.  This
does not accept E01-G4, E02-G1, or any later EPIC gate; it only freezes the
observed compatibility evidence needed for review.

The adopted tool-list handler at baseline commit
`00207ed084e9ef81538b5283615e689d483632d1`, `src/server.py`, returned the
following tool order:

1. `draw_line`
2. `draw_circle`
3. `extrude_profile`
4. `revolve_profile`
5. `list_entities`
6. `get_entity_info`
7. `server_status`

The four mutating `inputSchema` dictionaries are copied verbatim (with no
tightening, normalization, or runtime reuse) to
`tests/fixtures/compatibility/legacy-mutating-tool-schemas.json`.  Its
SHA-256 is
`695ecf23340d9d804ac393c13e2421e47c038ecf8f5324647adabca23177c06b`.

## Current seven-tool behavior inventory

| Tool | Input properties; required properties | Valid observed-shaped example | Success payload fields |
| --- | --- | --- | --- |
| `draw_line` | `start_point`, `end_point`; both required | `{"start_point":[0,0,0],"end_point":[10,10,0]}` | `success`, `message`, `entity_id`, `start_point`, `end_point` |
| `draw_circle` | `center`, `radius`; both required; `radius` has `minimum: 0` | `{"center":[5,5,0],"radius":2.5}` | `success`, `message`, `entity_id`, `center`, `radius` |
| `extrude_profile` | `profile_points`, `extrude_height`; both required | `{"profile_points":[[0,0],[10,0],[10,10],[0,10]],"extrude_height":5}` | `success`, `message`, `entity_id`, `profile_points`, `extrude_height` |
| `revolve_profile` | `profile_points`, `axis_start`, `axis_end`, `angle`; all required | `{"profile_points":[[0,0],[10,0]],"axis_start":[0,0,0],"axis_end":[0,0,1],"angle":360}` | `success`, `message`, `entity_id`, `profile_points`, `axis_start`, `axis_end`, `angle` |
| `list_entities` | no properties; no required properties | `{}` | `success`, `count`, `entities` |
| `get_entity_info` | `entity_id`; required | `{"entity_id":1001}` | `success`, `entity` |
| `server_status` | no properties; no required properties | `{}` | `success`, `mcp_server`, `autocad_connected`, `active_document`, `tools_available`, `transport`, `message` |

Current failures are ad-hoc JSON and generally include `success`, `error`, and
`message`; `server_status` additionally preserves its MCP/connection fields.
The table records observed behavior, not a claim that any operation was
executed against AutoCAD.

`src/server.py` also advertises the resource
`autocad://server-status` (`AutoCAD MCP Server Status`, JSON) and the
`autocad-help` prompt, whose body lists all seven names and mutation examples.
`mcp.json` advertises the same seven tools, that resource, and that prompt and
launches `uv run python -m src.server`.

`src/mcp_server.py` is a separate FastMCP surface with the same seven basic
tool names, the same resource URI, and the same prompt name.  Its status and
resource payloads report `tools_available: 6` despite registering seven;
therefore it is evidence of drift, not an active-contract authority.  Its
module entry point also prints before starting stdio, which is incompatible
with a single protocol-owned stdout boundary.

`src/mcp_integration/enhanced_mcp_server.py` is **experimental and
unconnected**.  It is not launched by `mcp.json`, is not imported by the
selected server, is not evidence of active tools, and is not deleted here.

## Decisions frozen for EPIC-02 review

1. The final active catalog is the exact ordered tuple
   `server_status`, `list_entities`, `get_entity_info`.  These are the only
   non-mutating tools to be registered, advertised, included in help, or
   retained in the final manifest.
2. `draw_line`, `draw_circle`, `extrude_profile`, and `revolve_profile` are
   an intentional safety reduction.  Their schemas are evidence-only in the
   fixture and this decision; they receive no core request model, parser,
   registration, executable compatibility shim, manifest entry, or help entry.
   EPIC-06 owns any later reviewed, authorized constrained edits.  Extrusion
   and revolution stay unregistered until a separately reviewed 3D
   edit-primitive extension exists.
3. `autocad_mcp.server` becomes the sole canonical stdio registration owner.
   EPIC-01's non-package mode is temporary; Hatchling will install
   `src/autocad_mcp`.  Low-level `mcp.server.Server` and stdio transport remain
   the selected transport.
4. `src.server` remains a protocol-safe, tested compatibility shim that
   delegates/re-exports `autocad_mcp.server` and owns no registration.  It
   emits no deprecation text to stdout.  It may be removed only in a later,
   focused pull request after `git grep` establishes that no active
   configuration, documentation, or caller uses `python -m src.server`, its
   compatibility tests are intentionally removed, and release notes describe
   the breaking change.
5. Every future tool failure uses `ToolError` in a structured envelope:
   `{"success":false,"error":{"code":...,"message":...,"retryable":...,"details":...}}`.
   The stable `ErrorCode` values are `INVALID_ARGUMENT`, `UNKNOWN_TOOL`,
   `AUTOCAD_UNAVAILABLE`, `NO_ACTIVE_DOCUMENT`, `COM_BUSY`,
   `UNSUPPORTED_CAPABILITY`, `ENTITY_NOT_FOUND`,
   `AUTOCAD_OPERATION_FAILED`, and `INTERNAL_ERROR`.  Unexpected exceptions
   are redacted from the tool result, correlated with an incident ID, and
   logged to stderr.
6. The canonical core receives a `BasicToolService` seam with
   `async invoke(request: BasicToolInput) -> ToolResponse`.  Its initial
   `UnavailableToolService` reports the honest unavailable state without a COM
   import; EPIC-03 later replaces only the runtime factory with the Windows
   adapter-backed service.
7. `src/mcp_server.py`, `tests/test_server.py`, and
   `tests/unit/test_drawing_operations.py` are not deleted by this record.
   Deletion is delayed until E02-G4 accepts replacement coverage: canonical
   schema/order/dispatch and stdio contracts for the three selected tools,
   explicit fixture/runtime/manifest/help exclusion coverage for the four
   mutations, and canonical status-resource/prompt contracts.  The Flask
   `/health` and imagined draw routes have no MCP replacement; they are
   removed only because they are not selected MCP behavior.  The Flask
   `/acad-status` claim is replaced by `server_status`, with connected
   verification still deferred to EPIC-03.

## Compatibility checks

`tests/compatibility/test_legacy_mutating_tool_schemas.py` first invokes the
currently selected `src.server.handle_list_tools()` handler and compares the
four observed `inputSchema` dictionaries to the fixture.  It also checks the
fixture's exact top-level fields and exact four-name tool key set.  That
integrity/equality check passes against the current temporary server.

The same test then requires the legacy set to be absent from the runtime
tool-list result, `mcp.json`, and the `autocad-help` prompt.  It deliberately
fails in the current state because each surface still advertises all four
mutations.  This red state is required evidence, not a failure to be hidden
by weakening the test or changing active source/metadata early.

## Consequences

The next implementation lanes have a stable evidence boundary and a required
safety outcome, but no claim that the canonical server, Windows adapter, or a
real AutoCAD session is working.  E02-G1 remains a reviewer decision after
the package migration, shim-retirement gate, three-tool matrix, digest and
exclusion policy, error codes, and `BasicToolService` boundary are reviewed.
