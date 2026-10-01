# Architecture

This document distinguishes the implemented canonical MCP/Windows-adapter
boundary from future product targets. No real AutoCAD connection is claimed
until the corresponding roadmap acceptance evidence is recorded.

## Adopted canonical MCP core

```text
MCP client
    |
    | stdio
    v
autocad_mcp.server
    |-- closed schemas and structured errors
    |-- server_status / list_entities / get_entity_info
    |-- autocad://server-status resource and autocad-help prompt
    v
AdapterToolService -> delayed Windows adapter provider
    |-- transient COM only during an adapter operation
    v
Full AutoCAD when an operator has started it; structured unavailable otherwise

src.server -> protocol-safe compatibility shim -> autocad_mcp.server
```

`mcp.json` launches `uv run python -m autocad_mcp.server`. The canonical
server is the sole registration owner. Its pure schema, dispatch, adapter
contract, and stdio contracts are tested without COM on Linux; this does not
prove a connection to AutoCAD or support for Linux as an AutoCAD runtime.

The active catalog contains only `server_status`, `list_entities`, and
`get_entity_info`. The historical mutation schemas are retained as compatibility
evidence and are excluded from runtime, metadata, and help. EPIC-06 owns any
future constrained edits.

Two non-canonical directions remain outside the active server surface:

- `src/mcp_integration/enhanced_mcp_server.py` remains experimental and
  unconnected. It is neither launched nor advertised by the canonical core.
- The root Docker and Compose artifacts name an unsupported historical Linux
  HTTP direction. Their disposition is recorded in
  [decision 0001](decisions/0001-container-artifact-disposition.md); this
  document does not authorize their repair or removal.

The retired FastMCP duplicate and Flask-oriented tests are documented in
[decision 0002](decisions/0002-canonical-server-consolidation.md). Their
replacement evidence covers the selected MCP behavior, not HTTP routes or real
AutoCAD behavior.

## Approved target

```text
MCP client and vision-capable model
    |
    | constrained MCP tools and image results
    v
Canonical MCP server
    |-- structured schemas and errors
    |-- drawing snapshot and context analysis
    |-- on-demand drawing capture
    |-- edit-plan preview and approval
    v
Windows AutoCAD adapter
    |-- delayed COM imports
    |-- capability detection
    |-- connection and document lifecycle
    |-- constrained entity operations
    v
Full AutoCAD 2021-2026 on Windows
```

### Canonical MCP server

One entry point owns tool registration and transport. `autocad_mcp.server` is
adopted for the pure core; `src.server` remains only a tested compatibility
shim. Tool schemas, `mcp.json`, implementation names, tests, and documentation
must agree. Normal logging uses standard error so stdio protocol messages remain
valid.

The first stable-core catalog is deliberately read-only: `server_status`, `list_entities`, and `get_entity_info`. Historical mutation schemas remain recorded but unregistered until they can route through the human-approved edit-plan boundary. No canonical MCP tool may call a direct creation adapter method before that boundary is accepted.

### Windows AutoCAD adapter (implemented boundary; real verification pending)

Only this boundary imports `pythoncom`, `win32com`, or AutoCAD COM wrappers.
Its delayed-import, fake-adapter, MCP-contract, lease, copy-guard, and
read-only-harness behavior has platform-independent automated evidence. The
opt-in AutoCAD 2026 smoke procedure is prepared, but no real connection,
disposable-DWG, or release verification record exists. It detects connected
capabilities at runtime rather than assuming identical behavior across six
releases. Pure data and MCP modules remain importable without COM.

### Structured drawing context

An explicit analysis request creates a `DrawingSnapshot` containing document identity, active space, UCS, view metadata, a change fingerprint, and entity facts. Persistent entity references use AutoCAD handles; `ObjectID` is session-local.

Semantic interpretations remain separate from CAD facts. An interpretation records its label, evidence, confidence, and whether it is confirmed, inferred, or unknown.

### On-demand drawing capture

`capture_drawing_view` is an explicit tool invocation. It does not run during startup, status checks, analysis, planning, editing, or every model turn. It can return a clean current-view, extents, or selection image and may optionally return a handle-labelled overlay generated outside the DWG.

The server produces the image and view metadata. Vision inference remains in the MCP client or model; the server does not embed a provider or require a vision API key.

### Constrained edit plans

The client submits declarative operations rather than executable Python, AutoLISP, VBA, shell commands, or unrestricted `SendCommand` input. A preview validates the snapshot, handles, prior values, and requested operations, then returns a preview identifier and plan digest without mutation authority.

A trusted host-side approval broker, which is not exposed as a model-callable MCP tool, may issue a short-lived, single-use token after a human confirms that exact preview. The server binds the token to the document, AutoCAD session, snapshot, and plan digest. Application fails closed without that binding, checks the preconditions again, and groups supported changes in one AutoCAD Undo group. Initial support excludes deletion and semantic architectural edits.

If a later operation fails, application invalidates the token, requests Undo, rereads affected state, and reports either verified rollback or `rollback_failed` with per-operation outcomes. An Undo mark is treated as a recovery mechanism, not database-transaction atomicity.

## Trust boundaries

- MCP input is untrusted and requires schema and semantic validation.
- Vision output is advisory and cannot override structured CAD facts without explicit confirmation.
- A stale drawing invalidates an edit plan.
- Drawing mutations require explicit approval and disposable test files during development.
- Historical code and documentation do not establish product guarantees.

## Architecture change policy

Each modernization stage must update this document only after its code and tests land. Future architecture stays labelled as target design until the corresponding [roadmap](roadmap.md) acceptance gate passes.
