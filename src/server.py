"""Compatibility shim for the historical ``python -m src.server`` command."""

import asyncio

from autocad_mcp.server import create_server, main, server

__all__ = ["create_server", "main", "server"]


if __name__ == "__main__":
    asyncio.run(main())
