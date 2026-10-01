"""Default stdio U service stays pure and cooperatively observes transport cancellation."""

import asyncio
import json
import sys
import tempfile
import textwrap
from pathlib import Path

import anyio
import mcp.types as types
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import McpError

from tests.contract.test_surface_unfolding_tool import request
from tests.unit.advanced.codegen.test_validate import PAIRS

ROOT = Path(__file__).parents[2]


async def exercise_stdio() -> str:
    bootstrap = textwrap.dedent("""
        import ast, asyncio, builtins, concurrent.futures.thread, io, os
        import socket, subprocess, sys, threading
        from contextlib import ExitStack
        from unittest.mock import patch
        import autocad_mcp
        import mcp.types as types
        original_import=builtins.__import__
        blocked=('autocad_mcp.adapter','autocad_mcp.context','autocad_mcp.capture',
                 'autocad_mcp.edit','pythoncom','win32com','pyautocad','comtypes')
        def guarded_import(name,*args,**kwargs):
            assert not any(name==p or name.startswith(p+'.') for p in blocked),name
            return original_import(name,*args,**kwargs)
        builtins.__import__=guarded_import
        import autocad_mcp.server as canonical
        from autocad_mcp.advanced.unfolding import service
        from autocad_mcp.advanced.bounds import WorkBudget,BoundedExecutionInterrupted
        from autocad_mcp.advanced.unfolding.models import decode_policy
        original_service=service.unfold_surface
        def controlled(payload,*,cancellation):
            if payload.get('request_id')!='controlled-cancel':
                return original_service(payload,cancellation=cancellation)
            budget=WorkBudget(decode_policy(payload['policy']),cancellation=cancellation)
            sys.stderr.write('Controlled U worker started\\n');sys.stderr.flush()
            try:
                pause=threading.Event()
                while True:
                    budget.checkpoint()
                    pause.wait(.001)
            except BoundedExecutionInterrupted as error:
                assert cancellation.is_cancelled()
                return error.failure
            finally:
                sys.stderr.write('Controlled U worker stopped\\n');sys.stderr.flush()
        service.unfold_surface=controlled
        original_handler=canonical.server.request_handlers[types.CallToolRequest]
        original_compile=builtins.compile
        def forbidden(*args,**kwargs):
            raise AssertionError('Forbidden U request effect')
        def ast_only(*args,**kwargs):
            flags=kwargs.get('flags',args[3] if len(args)>3 else 0)
            assert flags & ast.PyCF_ONLY_AST
            return original_compile(*args,**kwargs)
        async def guarded_handler(req):
            with ExitStack() as guard:
                effects=((builtins,'exec'),(builtins,'eval'),(builtins,'open'),
                         (io,'open'),(os,'open'),(os,'system'),(os,'getenv'),
                         (subprocess,'Popen'),(subprocess,'run'),(socket,'socket'),
                         (socket,'create_connection'))
                for owner,name in effects:
                    guard.enter_context(patch.object(owner,name,forbidden))
                guard.enter_context(patch.object(builtins,'compile',ast_only))
                return await original_handler(req)
        canonical.server.request_handlers[types.CallToolRequest]=guarded_handler
        asyncio.run(canonical.main())
        assert not any(n==p or n.startswith(p+'.') for n in sys.modules for p in blocked)
        sys.stderr.write('Default U stdio pure boundary passed\\n')
    """)
    parameters = StdioServerParameters(command=sys.executable, args=["-c", bootstrap], cwd=ROOT)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "diagnostics.txt"
        with path.open("w+", encoding="utf-8") as log:
            async with stdio_client(parameters, errlog=log) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    assert len((await session.list_tools()).tools) == 5
                    success = await session.call_tool("unfold_surface", request())
                    assert json.loads(success.content[0].text)["success"] is True
                    invalid = {**request(), "private": "private-data"}
                    rejection = await session.call_tool("unfold_surface", invalid)
                    assert (
                        json.loads(rejection.content[0].text)["error"]["code"] == "INVALID_ARGUMENT"
                    )
                    assert "private-data" not in rejection.content[0].text
                    payload = request()
                    payload["request_id"] = "controlled-cancel"
                    payload["policy"]["cancellation_check_interval"] = 1
                    request_id = session._request_id
                    pending = asyncio.create_task(session.call_tool("unfold_surface", payload))
                    with anyio.fail_after(5):
                        while "Controlled U worker started" not in path.read_text():
                            await asyncio.sleep(0.01)
                    # The loop serves C while U numerical work remains active.
                    c = await asyncio.wait_for(
                        session.call_tool("generate_constrained_code", PAIRS[0]["example"]), 2
                    )
                    assert json.loads(c.content[0].text)["success"] is True
                    await session.send_notification(
                        types.ClientNotification(
                            types.CancelledNotification(
                                params=types.CancelledNotificationParams(
                                    requestId=request_id, reason="Controlled transport cancellation"
                                )
                            )
                        )
                    )
                    with anyio.fail_after(5):
                        while "Controlled U worker stopped" not in path.read_text():
                            await asyncio.sleep(0.01)
                    with pytest.raises(McpError) as cancellation:
                        await asyncio.wait_for(pending, 2)
                    assert cancellation.value.error.message == "Request cancelled"
                    assert cancellation.value.error.data is None
        return path.read_text()


def test_default_stdio_purity_concurrent_request_and_worker_cancellation() -> None:
    diagnostics = anyio.run(exercise_stdio)
    assert "Default U stdio pure boundary passed" in diagnostics
    assert "Controlled U worker stopped" in diagnostics
    assert "Forbidden U request effect" not in diagnostics
