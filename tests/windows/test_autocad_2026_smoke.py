"""Opt-in, real-device smoke for full AutoCAD 2026 and the canonical MCP server."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryFile

import pytest
from autocad_harness import ReadOnlyAutoCADHarness
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_PROJECT_ROOT = Path(__file__).parents[2]
_TOOL_NAMES = ("server_status", "list_entities", "get_entity_info")


@dataclass(frozen=True)
class _EntityIdentity:
    entity_id: int
    handle: str
    object_name: str
    layer: str


def _require_2026_session(autocad_smoke_session: object) -> None:
    if os.environ.get("AUTOCAD_MCP_SMOKE_RELEASE") != "2026":
        pytest.fail("AUTOCAD_MCP_SMOKE_RELEASE must be exactly 2026")
    lease = getattr(autocad_smoke_session, "lease", None)
    guard = getattr(autocad_smoke_session, "guard", None)
    assert_owned = getattr(lease, "assert_owned", None)
    if not callable(assert_owned):
        pytest.fail("a trusted acquired AutoCAD lease is required")
    if guard is None or not guard.copy_path.is_file() or guard.copy_path == guard.source_path:
        pytest.fail("a prepared disposable DWG guard is required")
    assert_owned()


@contextmanager
def _operator_started_autocad() -> Iterator[object]:
    """Attach only to a running AutoCAD application in this COM apartment."""
    if sys.platform != "win32":
        pytest.fail("requires Windows")
    import pythoncom
    from win32com import client

    pythoncom.CoInitialize()
    try:
        try:
            application = client.GetActiveObject("AutoCAD.Application")
        except Exception:
            pytest.fail(
                "a real full AutoCAD application must already be started by the operator"
            )
        if application is None:
            pytest.fail("a real full AutoCAD application must already be started by the operator")
        yield application
    finally:
        pythoncom.CoUninitialize()


def _open_guard_copy(
    application: object, guard: object, copy_path: str, read_only: bool
) -> object:
    if copy_path != str(guard.copy_path) or read_only is not True:  # type: ignore[attr-defined]
        raise RuntimeError("the smoke may open only a read-only disposable copy")
    return application.Documents.Open(str(guard.copy_path), True)  # type: ignore[attr-defined]


def _call_json(result: object) -> dict[str, object]:
    content = getattr(result, "content", ())
    assert len(content) == 1
    text = getattr(content[0], "text", None)
    assert isinstance(text, str)
    payload = json.loads(text)
    assert isinstance(payload, dict)
    assert payload.get("success") is True, payload
    return payload


def _status_data(payload: dict[str, object], expected_document: Path) -> None:
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data["autocad_connected"] is True
    assert data["active_document"] == expected_document.name
    assert data["read_only"] is True
    product = data["product"]
    assert isinstance(product, str) and "autocad" in product.lower() and "lt" not in product.lower()


def _identity(data: object) -> _EntityIdentity:
    assert isinstance(data, dict)
    entity_id = data.get("id")
    handle = data.get("handle")
    object_name = data.get("type")
    layer = data.get("layer")
    assert isinstance(entity_id, int) and not isinstance(entity_id, bool)
    assert isinstance(handle, str) and handle
    assert isinstance(object_name, str) and object_name
    assert isinstance(layer, str)
    return _EntityIdentity(entity_id, handle, object_name, layer)


async def _run_mcp_round(expected_document: Path) -> _EntityIdentity:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "autocad_mcp.server"],
        cwd=_PROJECT_ROOT,
    )
    with TemporaryFile(mode="w+", encoding="utf-8") as diagnostics:
        async with stdio_client(parameters, errlog=diagnostics) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert tuple(tool.name for tool in tools.tools) == _TOOL_NAMES

                _status_data(
                    _call_json(await session.call_tool("server_status", {})), expected_document
                )
                listed = _call_json(await session.call_tool("list_entities", {}))
                list_data = listed.get("data")
                assert isinstance(list_data, dict)
                entities = list_data.get("entities")
                assert isinstance(entities, list) and entities
                first = _identity(entities[0])

                detailed = _call_json(
                    await session.call_tool("get_entity_info", {"entity_id": first.entity_id})
                )
                detail_data = detailed.get("data")
                assert isinstance(detail_data, dict)
                assert _identity(detail_data.get("entity")) == first
        diagnostics.seek(0)
        assert diagnostics.read()
    return first


@pytest.mark.autocad
def test_autocad_2026_read_only_mcp_smoke(autocad_smoke_session: object) -> None:
    """Verify two fresh canonical stdio sessions without changing the guarded DWG."""
    _require_2026_session(autocad_smoke_session)
    guard = autocad_smoke_session.guard  # type: ignore[attr-defined]
    lease = autocad_smoke_session.lease  # type: ignore[attr-defined]

    with _operator_started_autocad() as application:
        harness = ReadOnlyAutoCADHarness(
            lease=lease,
            guard=guard,
            opener=lambda copy_path, read_only: _open_guard_copy(
                application, guard, copy_path, read_only
            ),
        )
        harness.open()
        initial_fingerprint = harness.fingerprint
        try:
            first_identity = asyncio.run(_run_mcp_round(guard.copy_path))
            assert harness.assert_unchanged() == initial_fingerprint

            second_identity = asyncio.run(_run_mcp_round(guard.copy_path))
            assert second_identity == first_identity
            assert harness.assert_unchanged() == initial_fingerprint
        except BaseException:
            guard.finalize(preserve=True, reason="read-only AutoCAD 2026 smoke failed")
            raise
        finally:
            harness.close()


def test_autocad_2026_smoke_remains_opt_in_and_com_free_on_collection() -> None:
    """Prevent a collection-only regression from becoming a fake AutoCAD run."""
    marks = getattr(test_autocad_2026_read_only_mcp_smoke, "pytestmark", ())

    assert any(mark.name == "autocad" for mark in marks)
    assert {"pythoncom", "win32com", "win32com.client"}.isdisjoint(sys.modules)
