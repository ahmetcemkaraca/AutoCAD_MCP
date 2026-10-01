# AutoCAD MCP

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D4.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

An experimental Model Context Protocol bridge for automating full AutoCAD on Windows.

> This repository is now independently maintained after the original upstream project became unavailable.

## Project direction

The canonical stdio server is `autocad_mcp.server`. Its active catalog is the
four non-mutating tools `server_status`, `list_entities`, `get_entity_info`, and
`generate_constrained_code`; `src.server` is a protocol-safe compatibility shim, not a
second implementation. The pure MCP contract has Linux automated evidence
with unavailable or injected services. It is not evidence of a Windows COM or
AutoCAD connection. See the [roadmap](docs/roadmap.md) for acceptance criteria
and delivery order.

`generate_constrained_code` returns reviewed Python, AutoLISP or VBA source from
bounded literal recipes. It never executes or saves that text and needs no
AutoCAD connection. The complete SDK `CallToolResult` body is limited to 65,536
UTF-8 bytes, including nested JSON text escaping. See the
[code-generation decision and usage](docs/advanced/constrained-code-generation-decision.md).

## Current limitations

The delayed Windows AutoCAD adapter and guarded AutoCAD 2026 smoke harness are
implemented, but no real Windows/AutoCAD run has been recorded. Full AutoCAD
2021-2026 is targeted, not verified. `src/mcp_integration/enhanced_mcp_server.py`
is experimental and unconnected; it is not launched or advertised by the
canonical server. Read the [Windows smoke guide](docs/windows-testing-guide.md)
and [project status](docs/project-status.md) before relying on the server with
production drawings.

## Requirements

- Windows
- Full AutoCAD 2021-2026; compatibility is targeted and tracked per release
- Python 3.12 or newer

The first guarded real-device smoke requires 64-bit CPython 3.12 exactly; the
package metadata remains `>=3.12` for ordinary development.

AutoCAD LT and AutoCAD hosted on Linux or macOS are outside the supported scope. See the [compatibility policy](docs/compatibility.md).

## Development setup

The manifest's canonical command is `uv run python -m autocad_mcp.server`.
The core MCP tests exercise that entry point and the `src.server` compatibility
shim on Linux without COM modules. They do not establish a supported Windows
installation or successful startup with a real AutoCAD session. See
[testing](docs/testing.md), [project status](docs/project-status.md), and the
[epic portfolio](docs/epics/README.md).

## Documentation

Start with the [documentation index](docs/README.md). Historical documents from the adopted repository are preserved in the [legacy archive](docs/legacy/README.md) and are not current product documentation.

## Contributing

Read [AGENTS.md](AGENTS.md) before making changes. Use an English-language feature branch, commit history, and pull request; routine development does not go directly to `main`.

## License

AutoCAD MCP is available under the [MIT License](LICENSE).
