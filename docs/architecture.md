# Architecture

This document distinguishes the architecture adopted from the historical repository from the approved modernization target. Target components are not current functionality until their roadmap acceptance gates pass.

## Adopted architecture

```text
MCP client
    |
    | stdio
    v
src/server.py
    |
    v
src/utils.py
    |
    | pythoncom / win32com / pyautocad
    v
Full AutoCAD on Windows
```

`mcp.json` selects `src/server.py`, which manually declares MCP tools, resources, prompts, and handlers. AutoCAD operations call shared helpers that currently import Windows COM dependencies eagerly.

Four selected-server tools can mutate a drawing directly. They do not currently pass through preview, trusted human approval, stale-state validation, or verified Undo recovery. Their presence is an adopted risk, not an approved target behavior; the stable-core delivery removes them from active registration until the safe edit-plan boundary exists.

Two additional server directions exist:

- `src/mcp_server.py` repeats the basic tool set with FastMCP.
- `src/mcp_integration/enhanced_mcp_server.py` combines many experimental inspection, execution, generation, testing, and enterprise-oriented components.

Neither is selected by the root MCP command. Consolidation preserves observable read-only/status behavior while removing this ambiguity. Historical mutation schemas are retained as compatibility evidence, not as active behavior, until the approved edit-plan safety boundary exists.

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

One entry point owns tool registration and transport. Tool schemas, `mcp.json`, implementation names, tests, and documentation must agree. Normal logging uses standard error so stdio protocol messages remain valid.

The first stable-core catalog is deliberately read-only: `server_status`, `list_entities`, and `get_entity_info`. Historical mutation schemas remain recorded but unregistered until they can route through the human-approved edit-plan boundary. No canonical MCP tool may call a direct creation adapter method before that boundary is accepted.

### Windows AutoCAD adapter

Only this boundary imports `pythoncom`, `win32com`, or AutoCAD COM wrappers. It detects connected capabilities at runtime rather than assuming identical behavior across six releases. Pure data and MCP modules remain importable without COM.

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
