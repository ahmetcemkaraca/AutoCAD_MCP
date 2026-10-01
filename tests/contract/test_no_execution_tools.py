"""Fresh default startup and real stdio C requests have no drawing/execution effects."""

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import anyio
from autocad_mcp.core.tools import TOOL_DEFINITIONS
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from tests.unit.advanced.codegen.test_validate import PAIRS

ROOT = Path(__file__).parents[2]


def test_catalog_has_no_execution_or_mutation_companion() -> None:
    names = {tool.name for tool in TOOL_DEFINITIONS}
    assert names == {
        "server_status",
        "list_entities",
        "get_entity_info",
        "generate_constrained_code",
    }
    assert not {"exec", "execute", "run", "eval", "repl", "shell", "apply", "SendCommand"} & names


def test_metadata_module_can_be_the_first_project_import() -> None:
    result = subprocess.run(  # noqa: S603 - fixed Python metadata import probe
        [
            sys.executable,
            "-c",
            "from autocad_mcp.tools.constrained_code_generation "
            "import CONSTRAINED_CODE_GENERATION_TOOL; "
            "assert CONSTRAINED_CODE_GENERATION_TOOL.name == 'generate_constrained_code'",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def exercise_default_stdio() -> str:
    bootstrap = textwrap.dedent("""
        import ast, builtins, io, os, socket, subprocess, sys
        from unittest.mock import patch
        import autocad_mcp
        import mcp.types as types
        original_import = builtins.__import__
        blocked = ('autocad_mcp.adapter','autocad_mcp.context','autocad_mcp.capture',
                   'autocad_mcp.edit','pythoncom','win32com','pyautocad','comtypes')
        def guarded_import(name, *args, **kwargs):
            assert not any(name == p or name.startswith(p+'.') for p in blocked), name
            return original_import(name,*args,**kwargs)
        builtins.__import__ = guarded_import
        import autocad_mcp.server as canonical
        original_handler = canonical.server.request_handlers[types.CallToolRequest]
        original_compile = builtins.compile
        def forbidden(*args, **kwargs):
            raise AssertionError('Forbidden request effect')
        def ast_only(*args, **kwargs):
            flags=kwargs.get('flags', args[3] if len(args)>3 else 0)
            assert flags & ast.PyCF_ONLY_AST
            return original_compile(*args,**kwargs)
        async def guarded_handler(request):
            from contextlib import ExitStack
            with ExitStack() as stack:
                operations = ((builtins,'exec'),(builtins,'eval'),(builtins,'open'),
                              (io,'open'),(os,'open'),(os,'system'),(os,'getenv'),
                              (subprocess,'Popen'),(subprocess,'run'),(socket,'socket'),
                              (socket,'create_connection'))
                for owner, name in operations:
                    stack.enter_context(patch.object(owner,name,forbidden))
                stack.enter_context(patch.object(builtins,'compile',ast_only))
                return await original_handler(request)
        canonical.server.request_handlers[types.CallToolRequest] = guarded_handler
        import asyncio
        asyncio.run(canonical.main())
        assert not any(n == p or n.startswith(p+'.') for n in sys.modules for p in blocked)
        sys.stderr.write('Default core-only C stdio completed with zero forbidden effects\\n')
    """)
    parameters = StdioServerParameters(command=sys.executable, args=["-c", bootstrap], cwd=ROOT)
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as diagnostics:
        async with stdio_client(parameters, errlog=diagnostics) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 4
                for pair in PAIRS:
                    result = await session.call_tool("generate_constrained_code", pair["example"])
                    payload = json.loads(result.content[0].text)
                    assert payload["success"] is True and payload["artifact"]["executed"] is False
                    assert (
                        len(result.model_dump_json(by_alias=True, exclude_none=True).encode())
                        <= 65536
                    )
                for name, arguments in (
                    ("get_entity_info", {"entity_id": True}),
                    ("server_status", {"extra": "private"}),
                    ("unknown", {}),
                    ("generate_constrained_code", {"source": "private"}),
                ):
                    result = await session.call_tool(name, arguments)
                    assert json.loads(result.content[0].text)["success"] is False
                    assert "private" not in result.content[0].text
        diagnostics.seek(0)
        return diagnostics.read()


def test_fresh_default_server_all_nine_pairs_and_invalid_calls_are_core_only() -> None:
    diagnostics = anyio.run(exercise_default_stdio)
    assert "Default core-only C stdio completed with zero forbidden effects" in diagnostics
    assert "Forbidden request effect" not in diagnostics
