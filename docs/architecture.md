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

Two additional server directions exist:

- `src/mcp_server.py` repeats the basic tool set with FastMCP.
- `src/mcp_integration/enhanced_mcp_server.py` combines many experimental inspection, execution, generation, testing, and enterprise-oriented components.

Neither is selected by the root MCP command. Consolidation must preserve observable basic behavior while removing this ambiguity.

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

### Windows AutoCAD adapter

Only this boundary imports `pythoncom`, `win32com`, or AutoCAD COM wrappers. It detects connected capabilities at runtime rather than assuming identical behavior across six releases. Pure data and MCP modules remain importable without COM.

### Structured drawing context

An explicit analysis request creates a `DrawingSnapshot` containing document identity, active space, UCS, view metadata, a change fingerprint, and entity facts. Persistent entity references use AutoCAD handles; `ObjectID` is session-local.

Semantic interpretations remain separate from CAD facts. An interpretation records its label, evidence, confidence, and whether it is confirmed, inferred, or unknown.

### On-demand drawing capture

`capture_drawing_view` is an explicit tool invocation. It does not run during startup, status checks, analysis, planning, editing, or every model turn. It can return a clean current-view, extents, or selection image and may optionally return a handle-labelled overlay generated outside the DWG.

The server produces the image and view metadata. Vision inference remains in the MCP client or model; the server does not embed a provider or require a vision API key.

### Constrained edit plans

The client submits declarative operations rather than executable Python, AutoLISP, VBA, shell commands, or unrestricted `SendCommand` input. A preview validates the snapshot, handles, prior values, and requested operations before issuing a short-lived approval token.

Application checks those preconditions again and groups supported changes in one AutoCAD Undo group. Initial support excludes deletion because an Undo mark does not provide database-transaction atomicity.

## Trust boundaries

- MCP input is untrusted and requires schema and semantic validation.
- Vision output is advisory and cannot override structured CAD facts without explicit confirmation.
- A stale drawing invalidates an edit plan.
- Drawing mutations require explicit approval and disposable test files during development.
- Historical code and documentation do not establish product guarantees.

## Architecture change policy

Each modernization stage must update this document only after its code and tests land. Future architecture stays labelled as target design until the corresponding [roadmap](roadmap.md) acceptance gate passes.
