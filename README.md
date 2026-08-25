# AutoCAD MCP

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D4.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

An experimental Model Context Protocol bridge for automating full AutoCAD on Windows.

> This repository is now independently maintained after the original upstream project became unavailable.

## Project direction

The project is being stabilized around one MCP server, a testable Windows COM boundary, structured drawing context, on-demand drawing capture, and approval-gated CAD edits. See the [roadmap](docs/roadmap.md) for acceptance criteria and delivery order.

## Current limitations

The adopted runtime and installation flow are being revalidated before wider use. Read the [project status](docs/project-status.md) before relying on the server with production drawings.

## Requirements

- Windows
- Full AutoCAD 2021-2026; compatibility is targeted and tracked per release
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) or Poetry for dependency management

AutoCAD LT and AutoCAD hosted on Linux or macOS are outside the supported scope. See the [compatibility policy](docs/compatibility.md).

## Development setup

```powershell
git clone https://github.com/ahmetcemkaraca/AutoCAD_MCP.git
cd AutoCAD_MCP
uv sync
uv run python src/server.py
```

The command above starts the stdio MCP entry point configured by `mcp.json`. Live AutoCAD behavior must be validated on a disposable drawing while the stabilization work is in progress.

## Documentation

Start with the [documentation index](docs/README.md). Historical documents from the adopted repository are preserved in the [legacy archive](docs/legacy/README.md) and are not current product documentation.

## Contributing

Read [AGENTS.md](AGENTS.md) before making changes. Use an English-language feature branch, commit history, and pull request; routine development does not go directly to `main`.

## License

AutoCAD MCP is available under the [MIT License](LICENSE).
