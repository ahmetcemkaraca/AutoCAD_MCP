"""Opt-in, real-device smoke for full AutoCAD 2026 and the canonical MCP server."""

from __future__ import annotations

import asyncio
import ctypes
import hashlib
import json
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryFile
from types import SimpleNamespace

import pytest
from autocad_harness import (
    ReadOnlyAutoCADHarness,
    ReadOnlyDrawingFingerprint,
    ReadOnlyFileFingerprint,
)
from autocad_mcp.adapter.capabilities import AdapterCapability, AdapterCapabilityReport
from autocad_mcp.adapter.protocol import (
    AutoCADAdapter,
    ConnectionInfo,
    EntityDetails,
    EntitySummary,
)
from autocad_mcp.adapter.windows import WindowsAutoCADAdapter
from drawing_copy_guard import DrawingCopyEvidence
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


@dataclass(frozen=True)
class _AttachedAutoCADIdentity:
    process_id: int
    executable: Path
    caption: str
    version: str


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


def _attached_application_identity(
    application: object,
    installation_path: Path,
    *,
    executable_for_window: Callable[[int], tuple[int, Path]] | None = None,
) -> _AttachedAutoCADIdentity:
    """Bind the generic AutoCAD ROT object to the exact leased 2026 executable."""
    resolver = executable_for_window or _process_executable_for_window
    try:
        hwnd = application.HWND  # type: ignore[attr-defined]
    except Exception as error:
        pytest.fail(f"could not read the running AutoCAD window handle: {type(error).__name__}")
    if isinstance(hwnd, bool) or not isinstance(hwnd, int) or hwnd <= 0:
        pytest.fail("the running AutoCAD window handle is invalid")
    process_id, process_executable = resolver(hwnd)
    expected = _resolved_acad_executable(installation_path)
    actual = _resolved_acad_executable(process_executable)
    if os.path.normcase(str(actual)) != os.path.normcase(str(expected)):
        pytest.fail("the attached AutoCAD process does not match the leased acad.exe")

    caption = _required_application_text(application, "Caption")
    name = _required_application_text(application, "Name")
    version = _required_application_text(application, "Version")
    product = f"{caption} {name}".casefold()
    if "autocad" not in product or "autocad lt" in product:
        pytest.fail("the attached application is not full AutoCAD")
    if "2026" not in caption.casefold():
        pytest.fail("the attached application is not AutoCAD 2026")
    return _AttachedAutoCADIdentity(process_id, actual, caption, version)


def _required_application_text(application: object, member: str) -> str:
    try:
        value = getattr(application, member)
    except Exception as error:
        pytest.fail(f"could not read AutoCAD {member}: {type(error).__name__}")
    if not isinstance(value, str) or not value.strip():
        pytest.fail(f"AutoCAD {member} is unavailable")
    return value.strip()


def _resolved_acad_executable(path: Path) -> Path:
    try:
        executable = Path(path).resolve(strict=True)
    except OSError as error:
        pytest.fail(f"AutoCAD executable cannot be resolved: {type(error).__name__}")
    if executable.name.casefold() != "acad.exe" or not executable.is_file():
        pytest.fail("AutoCAD executable must be a regular acad.exe file")
    return executable


def _process_executable_for_window(hwnd: int) -> tuple[int, Path]:
    """Return the owning process and executable for a real Windows AutoCAD HWND."""
    if sys.platform != "win32":
        pytest.fail("resolving an AutoCAD window executable requires Windows")
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    process_id = wintypes.DWORD()
    if not user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(process_id)):
        pytest.fail("could not identify the process that owns the AutoCAD window")
    process = kernel32.OpenProcess(0x1000, False, process_id)
    if not process:
        pytest.fail("could not inspect the process that owns the AutoCAD window")
    try:
        capacity = 32768
        buffer = ctypes.create_unicode_buffer(capacity)
        length = wintypes.DWORD(capacity)
        if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(length)):
            pytest.fail("could not read the AutoCAD process executable path")
        return int(process_id.value), Path(buffer.value)
    finally:
        kernel32.CloseHandle(process)


def _run_production_adapter_round(
    *,
    adapter: AutoCADAdapter,
    lease: object,
    application: object,
    guard: object,
    expected_version: str,
) -> _EntityIdentity:
    """Exercise the production adapter's four public operations around the guarded document."""
    status = _guarded_adapter_call(lease, application, guard, adapter.status)
    _assert_adapter_connection(status, guard, expected_version)
    reconnected = _guarded_adapter_call(lease, application, guard, adapter.reconnect)
    _assert_adapter_connection(reconnected, guard, expected_version)
    entities = _guarded_adapter_call(lease, application, guard, adapter.list_entities)
    if not isinstance(entities, tuple) or not entities:
        pytest.fail("the production adapter returned no queryable entities")
    first = _adapter_identity(entities[0])
    detail = _guarded_adapter_call(
        lease, application, guard, adapter.get_entity_info, first.entity_id
    )
    if _adapter_identity(detail) != first:
        pytest.fail("the production adapter detail does not match the listed entity")
    return first


def _guarded_adapter_call(
    lease: object,
    application: object,
    guard: object,
    operation: Callable[..., object],
    *arguments: object,
) -> object:
    _assert_active_guard(lease, application, guard)
    result = operation(*arguments)
    _assert_active_guard(lease, application, guard)
    return result


def _assert_active_guard(lease: object, application: object, guard: object) -> None:
    assert_owned = getattr(lease, "assert_owned", None)
    if not callable(assert_owned):
        pytest.fail("a trusted acquired AutoCAD lease is required")
    assert_owned()
    try:
        document = application.ActiveDocument  # type: ignore[attr-defined]
        full_name = document.FullName
        read_only = document.ReadOnly
    except Exception as error:
        pytest.fail(f"could not validate the active AutoCAD drawing: {type(error).__name__}")
    if not isinstance(full_name, str) or not full_name:
        pytest.fail("the active AutoCAD drawing has no full path")
    if read_only is not True:
        pytest.fail("the active AutoCAD drawing is not read-only")
    assert_active_full_name = getattr(guard, "assert_active_full_name", None)
    if not callable(assert_active_full_name):
        pytest.fail("a prepared disposable DWG guard is required")
    assert_active_full_name(full_name)


def _assert_adapter_connection(value: object, guard: object, expected_version: str) -> None:
    if not isinstance(value, ConnectionInfo):
        pytest.fail("the production adapter returned an invalid connection status")
    if value.connected is not True or value.active_document != guard.copy_path.name:  # type: ignore[attr-defined]
        pytest.fail("the production adapter is not attached to the guarded drawing")
    if value.read_only is not True:
        pytest.fail("the production adapter reported a writable drawing")
    if not isinstance(value.product, str) or "autocad" not in value.product.casefold():
        pytest.fail("the production adapter did not report full AutoCAD")
    if "autocad lt" in value.product.casefold():
        pytest.fail("the production adapter reported AutoCAD LT")
    if value.version != expected_version or not isinstance(value.release_hint, str):
        pytest.fail("the production adapter version does not match the attached AutoCAD")
    for capability in (
        AdapterCapability.CONNECTION,
        AdapterCapability.ACTIVE_DOCUMENT,
        AdapterCapability.LIST_ENTITIES,
        AdapterCapability.GET_ENTITY_INFO,
    ):
        if not value.capabilities.supports(capability):
            pytest.fail(f"the production adapter lacks required {capability.value} capability")


def _adapter_identity(value: object) -> _EntityIdentity:
    if not isinstance(value, EntitySummary | EntityDetails):
        pytest.fail("the production adapter returned an invalid entity")
    if isinstance(value.object_id, bool) or not isinstance(value.object_id, int):
        pytest.fail("the production adapter entity id is invalid")
    if not isinstance(value.handle, str) or not value.handle:
        pytest.fail("the production adapter entity handle is invalid")
    if not isinstance(value.object_name, str) or not value.object_name:
        pytest.fail("the production adapter entity type is invalid")
    if not isinstance(value.layer, str):
        pytest.fail("the production adapter entity layer is invalid")
    return _EntityIdentity(value.object_id, value.handle, value.object_name, value.layer)


def _emit_smoke_report(
    *,
    outcome: str,
    attached: _AttachedAutoCADIdentity | None,
    guard_evidence: DrawingCopyEvidence | None,
    initial_fingerprint: ReadOnlyDrawingFingerprint | None,
    final_fingerprint: ReadOnlyDrawingFingerprint | None,
    post_close_file_fingerprint: ReadOnlyFileFingerprint | None,
    lease_evidence: object | None,
) -> dict[str, object]:
    """Print a shareable report and a private pointer when a failed copy was preserved."""
    report: dict[str, object] = {
        "outcome": outcome,
        "application": _attached_report(attached),
        "drawing": _drawing_report(guard_evidence),
        "fingerprints": {
            "after_open": asdict(initial_fingerprint) if initial_fingerprint is not None else None,
            "pre_close": asdict(final_fingerprint) if final_fingerprint is not None else None,
            "post_close_file": (
                asdict(post_close_file_fingerprint)
                if post_close_file_fingerprint is not None
                else None
            ),
        },
        "lease": _lease_report(lease_evidence),
    }
    sys.stdout.write(f"AUTOCAD_MCP_SMOKE_EVIDENCE={json.dumps(report, sort_keys=True)}\n")
    if guard_evidence is not None and guard_evidence.preserved:
        sys.stdout.write(f"AUTOCAD_MCP_SMOKE_PRESERVED_COPY={guard_evidence.copy_path}\n")
    return report


def _attached_report(attached: _AttachedAutoCADIdentity | None) -> dict[str, object] | None:
    if attached is None:
        return None
    return {
        "process_id": attached.process_id,
        "executable": _redacted_path(str(attached.executable)),
        "caption": attached.caption,
        "version": attached.version,
    }


def _drawing_report(evidence: DrawingCopyEvidence | None) -> dict[str, object] | None:
    if evidence is None:
        return None
    return {
        "run_id": evidence.run_id,
        "source_path": _redacted_path(evidence.source_path),
        "copy_path": _redacted_path(evidence.copy_path),
        "active_document": _redacted_path(evidence.active_full_name),
        "source_sha256_before": evidence.source_sha256_before,
        "source_sha256_after": evidence.source_sha256_after,
        "copy_sha256_before": evidence.copy_sha256_before,
        "copy_sha256_after": evidence.copy_sha256_after,
        "close_without_save_attempted": evidence.close_without_save_attempted,
        "preserved": evidence.preserved,
        "preserve_reason_sha256": _redacted_text_digest(evidence.preserve_reason),
        "cleanup_succeeded": evidence.cleanup_succeeded,
    }


def _lease_report(evidence: object | None) -> dict[str, object] | None:
    if evidence is None:
        return None
    owner = getattr(evidence, "owner", None)
    if owner is None:
        return {"state": "unavailable"}
    return {
        "lease_key": getattr(owner, "lease_key", None),
        "owner_process_id": getattr(owner, "pid", None),
        "metadata_path": _redacted_path(getattr(evidence, "metadata_path", None)),
        "acquired_at_utc": getattr(evidence, "acquired_at_utc", None),
        "released_at_utc": getattr(evidence, "released_at_utc", None),
        "stale_owner_recovered": getattr(evidence, "stale_owner_recovered", None) is not None,
    }


def _redacted_path(path: str | None) -> dict[str, str] | None:
    if not path:
        return None
    return {
        "name": Path(path).name,
        "sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
    }


def _redacted_text_digest(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
            pytest.fail("a real full AutoCAD application must already be started by the operator")
        if application is None:
            pytest.fail("a real full AutoCAD application must already be started by the operator")
        yield application
    finally:
        pythoncom.CoUninitialize()


def _open_guard_copy(application: object, guard: object, copy_path: str, read_only: bool) -> object:
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


async def _run_mcp_round(
    expected_document: Path, *, lease: object, application: object, guard: object
) -> _EntityIdentity:
    _assert_active_guard(lease, application, guard)
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
                _assert_active_guard(lease, application, guard)

                _status_data(
                    _call_json(await session.call_tool("server_status", {})), expected_document
                )
                _assert_active_guard(lease, application, guard)
                listed = _call_json(await session.call_tool("list_entities", {}))
                _assert_active_guard(lease, application, guard)
                list_data = listed.get("data")
                assert isinstance(list_data, dict)
                entities = list_data.get("entities")
                assert isinstance(entities, list) and entities
                first = _identity(entities[0])

                detailed = _call_json(
                    await session.call_tool("get_entity_info", {"entity_id": first.entity_id})
                )
                _assert_active_guard(lease, application, guard)
                detail_data = detailed.get("data")
                assert isinstance(detail_data, dict)
                assert _identity(detail_data.get("entity")) == first
        diagnostics.seek(0)
        assert diagnostics.read()
    _assert_active_guard(lease, application, guard)
    return first


@pytest.mark.autocad
def test_autocad_2026_read_only_mcp_smoke(autocad_smoke_session: object) -> None:
    """Verify two fresh canonical stdio sessions without changing the guarded DWG."""
    _require_2026_session(autocad_smoke_session)
    guard = autocad_smoke_session.guard  # type: ignore[attr-defined]
    lease = autocad_smoke_session.lease  # type: ignore[attr-defined]
    attached: _AttachedAutoCADIdentity | None = None
    harness: ReadOnlyAutoCADHarness | None = None
    initial_fingerprint: ReadOnlyDrawingFingerprint | None = None
    final_fingerprint: ReadOnlyDrawingFingerprint | None = None
    post_close_file_fingerprint: ReadOnlyFileFingerprint | None = None
    guard_evidence: DrawingCopyEvidence | None = None
    outcome = "failed"
    run_error: BaseException | None = None
    try:
        lease.assert_owned()
        with _operator_started_autocad() as application:
            harness = ReadOnlyAutoCADHarness(
                lease=lease,
                guard=guard,
                opener=lambda copy_path, read_only: _open_guard_copy(
                    application, guard, copy_path, read_only
                ),
            )
            try:
                attached = _attached_application_identity(
                    application,
                    autocad_smoke_session.installation_path,  # type: ignore[attr-defined]
                )
                harness.open()
                initial_fingerprint = harness.fingerprint
                adapter_identity = _run_production_adapter_round(
                    adapter=WindowsAutoCADAdapter(),
                    lease=lease,
                    application=application,
                    guard=guard,
                    expected_version=attached.version,
                )
                final_fingerprint = harness.assert_unchanged()

                first_identity = asyncio.run(
                    _run_mcp_round(
                        guard.copy_path, lease=lease, application=application, guard=guard
                    )
                )
                assert first_identity == adapter_identity
                final_fingerprint = harness.assert_unchanged()

                second_identity = asyncio.run(
                    _run_mcp_round(
                        guard.copy_path, lease=lease, application=application, guard=guard
                    )
                )
                assert second_identity == first_identity
                final_fingerprint = harness.assert_unchanged()
            except BaseException as error:
                run_error = error
                try:
                    guard_evidence = guard.finalize(
                        preserve=True, reason="read-only AutoCAD 2026 smoke failed"
                    )
                except BaseException as preserve_error:
                    error.add_note(f"guard preservation also failed: {preserve_error}")
                raise
            finally:
                if harness is not None and initial_fingerprint is not None:
                    try:
                        guard_evidence = harness.close()
                        post_close_file_fingerprint = harness.post_close_file_fingerprint
                    except BaseException as close_error:
                        if run_error is not None:
                            run_error.add_note(f"close without save also failed: {close_error}")
                        else:
                            raise
        outcome = "passed"
    except BaseException as error:
        if guard_evidence is None:
            try:
                guard_evidence = guard.finalize(
                    preserve=True, reason="read-only AutoCAD 2026 smoke failed"
                )
            except BaseException as preserve_error:
                error.add_note(f"guard preservation also failed: {preserve_error}")
        raise
    finally:
        _emit_smoke_report(
            outcome=outcome,
            attached=attached,
            guard_evidence=guard_evidence,
            initial_fingerprint=initial_fingerprint,
            final_fingerprint=final_fingerprint,
            post_close_file_fingerprint=post_close_file_fingerprint,
            lease_evidence=getattr(lease, "evidence", None),
        )


def test_autocad_2026_smoke_remains_opt_in_and_com_free_on_collection() -> None:
    """Prevent a collection-only regression from becoming a fake AutoCAD run."""
    marks = getattr(test_autocad_2026_read_only_mcp_smoke, "pytestmark", ())

    assert any(mark.name == "autocad" for mark in marks)
    assert {"pythoncom", "win32com", "win32com.client"}.isdisjoint(sys.modules)


def test_attached_application_identity_requires_the_leased_2026_executable(
    tmp_path: Path,
) -> None:
    """Rejecting the leased executable or marketing release must stop a mislabeled smoke."""
    executable = tmp_path / "AutoCAD 2026" / "acad.exe"
    executable.parent.mkdir()
    executable.touch()
    application = SimpleNamespace(
        HWND=101,
        Caption="Autodesk AutoCAD 2026",
        Name="AutoCAD",
        Version="25.1",
    )

    identity = _attached_application_identity(
        application,
        executable,
        executable_for_window=lambda hwnd: (4242, executable),
    )

    assert identity.process_id == 4242
    assert identity.executable == executable.resolve()
    assert identity.caption == "Autodesk AutoCAD 2026"
    assert identity.version == "25.1"


def test_attached_application_identity_rejects_another_installation_or_release(
    tmp_path: Path,
) -> None:
    """A generic ROT attachment must not pass when it is not the leased AutoCAD 2026."""
    expected = tmp_path / "AutoCAD 2026" / "acad.exe"
    actual = tmp_path / "AutoCAD 2025" / "acad.exe"
    expected.parent.mkdir()
    actual.parent.mkdir()
    expected.touch()
    actual.touch()
    application = SimpleNamespace(
        HWND=101,
        Caption="Autodesk AutoCAD 2025",
        Name="AutoCAD",
        Version="24.3",
    )

    with pytest.raises(pytest.fail.Exception, match="leased acad.exe"):
        _attached_application_identity(
            application,
            expected,
            executable_for_window=lambda hwnd: (4242, actual),
        )


def test_attached_application_identity_rejects_a_non_2026_caption(tmp_path: Path) -> None:
    """A matching executable alone must not turn an observed 2025 app into a 2026 result."""
    executable = tmp_path / "AutoCAD 2026" / "acad.exe"
    executable.parent.mkdir()
    executable.touch()
    application = SimpleNamespace(
        HWND=101,
        Caption="Autodesk AutoCAD 2025",
        Name="AutoCAD",
        Version="24.3",
    )

    with pytest.raises(pytest.fail.Exception, match="AutoCAD 2026"):
        _attached_application_identity(
            application,
            executable,
            executable_for_window=lambda hwnd: (4242, executable),
        )


def test_production_adapter_round_exercises_four_methods_under_the_guard(tmp_path: Path) -> None:
    """Dropping reconnect or allowing a switched full path must fail the real-device round."""
    copy_path = tmp_path / "guard" / "drawing-copy.dwg"
    document = SimpleNamespace(FullName=str(copy_path), ReadOnly=True)
    application = SimpleNamespace(ActiveDocument=document)
    capabilities = AdapterCapabilityReport(
        frozenset(
            {
                AdapterCapability.CONNECTION,
                AdapterCapability.ACTIVE_DOCUMENT,
                AdapterCapability.LIST_ENTITIES,
                AdapterCapability.GET_ENTITY_INFO,
            }
        )
    )
    connection = ConnectionInfo(
        True,
        "Autodesk AutoCAD 2026",
        "25.1",
        "25.1",
        "drawing-copy.dwg",
        True,
        capabilities,
    )

    class Lease:
        assertions = 0

        def assert_owned(self) -> None:
            self.assertions += 1

    class Guard:
        def __init__(self, path: Path) -> None:
            self.copy_path = path
            self.full_names: list[str] = []

        def assert_active_full_name(self, value: str) -> None:
            self.full_names.append(value)
            assert value == str(copy_path)

    class Adapter:
        calls: list[str] = []

        def status(self) -> ConnectionInfo:
            self.calls.append("status")
            return connection

        def reconnect(self) -> ConnectionInfo:
            self.calls.append("reconnect")
            return connection

        def list_entities(self) -> tuple[EntitySummary, ...]:
            self.calls.append("list_entities")
            return (EntitySummary(7, "A7", "AcDbLine", "0"),)

        def get_entity_info(self, object_id: int) -> EntityDetails:
            self.calls.append("get_entity_info")
            assert object_id == 7
            return EntityDetails(7, "A7", "AcDbLine", "0", {})

    lease = Lease()
    guard = Guard(copy_path)
    adapter = Adapter()

    identity = _run_production_adapter_round(
        adapter=adapter,
        lease=lease,
        application=application,
        guard=guard,
        expected_version="25.1",
    )

    assert identity == _EntityIdentity(7, "A7", "AcDbLine", "0")
    assert adapter.calls == ["status", "reconnect", "list_entities", "get_entity_info"]
    assert guard.full_names == [str(copy_path)] * 8
    assert lease.assertions == 8


def test_smoke_report_redacts_paths_but_preserves_a_local_failure_pointer(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A failed real smoke needs shareable evidence without exposing its drawing paths."""
    source_path = tmp_path / "private-source" / "fixture.dwg"
    copy_path = tmp_path / "private-guard" / "drawing-copy.dwg"
    fingerprint = ReadOnlyDrawingFingerprint("a" * 64, 12, 34, 0, 1, "b" * 64)
    post_close_file = ReadOnlyFileFingerprint("a" * 64, 12, 34)
    guard_evidence = DrawingCopyEvidence(
        run_id="run-123",
        source_path=str(source_path),
        copy_path=str(copy_path),
        source_sha256_before="a" * 64,
        source_sha256_after="a" * 64,
        copy_sha256_before="a" * 64,
        copy_sha256_after="a" * 64,
        active_full_name=str(copy_path),
        close_without_save_attempted=True,
        preserved=True,
        preserve_reason="test failure",
        cleanup_succeeded=False,
    )
    lease_evidence = SimpleNamespace(
        owner=SimpleNamespace(lease_key="c" * 64, pid=42),
        metadata_path=str(tmp_path / "private-lease" / "owner.json"),
        acquired_at_utc="2026-08-29T12:00:00.000000Z",
        released_at_utc=None,
        stale_owner_recovered=None,
    )

    report = _emit_smoke_report(
        outcome="failed",
        attached=_AttachedAutoCADIdentity(
            4242, tmp_path / "AutoCAD 2026" / "acad.exe", "AutoCAD 2026", "25.1"
        ),
        guard_evidence=guard_evidence,
        initial_fingerprint=fingerprint,
        final_fingerprint=fingerprint,
        post_close_file_fingerprint=post_close_file,
        lease_evidence=lease_evidence,
    )

    output = capsys.readouterr().out
    evidence_line = next(line for line in output.splitlines() if "_EVIDENCE=" in line)
    assert str(source_path) not in evidence_line
    assert str(copy_path) not in evidence_line
    assert report["drawing"]["source_path"]["name"] == "fixture.dwg"
    assert report["drawing"]["copy_path"]["name"] == "drawing-copy.dwg"
    assert report["fingerprints"]["after_open"] == asdict(fingerprint)
    assert report["fingerprints"]["pre_close"] == asdict(fingerprint)
    assert report["fingerprints"]["post_close_file"] == asdict(post_close_file)
    assert report["lease"]["released_at_utc"] is None
    assert f"AUTOCAD_MCP_SMOKE_PRESERVED_COPY={copy_path}" in output
    assert hashlib.sha256(str(source_path).encode("utf-8")).hexdigest() in evidence_line


def test_failed_smoke_preserves_the_copy_before_closing_the_document(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Latch preservation before harness cleanup can delete post-open failure evidence."""
    source_path = tmp_path / "source.dwg"
    copy_path = tmp_path / "drawing-copy.dwg"
    source_path.write_bytes(b"source")
    copy_path.write_bytes(b"copy")
    events: list[str] = []

    def evidence(*, preserved: bool) -> DrawingCopyEvidence:
        return DrawingCopyEvidence(
            run_id="run-123",
            source_path=str(source_path),
            copy_path=str(copy_path),
            source_sha256_before="a" * 64,
            source_sha256_after="a" * 64,
            copy_sha256_before="a" * 64,
            copy_sha256_after="a" * 64,
            active_full_name=str(copy_path),
            close_without_save_attempted=True,
            preserved=preserved,
            preserve_reason="adapter failed" if preserved else None,
            cleanup_succeeded=not preserved,
        )

    class Guard:
        def __init__(self, source: Path, copy: Path) -> None:
            self.source_path = source
            self.copy_path = copy

        @staticmethod
        def finalize(*, preserve: bool, reason: str) -> DrawingCopyEvidence:
            events.append("preserve" if preserve else "cleanup")
            return evidence(preserved=preserve)

    class Lease:
        @staticmethod
        def assert_owned() -> None:
            return None

    class Harness:
        fingerprint = ReadOnlyDrawingFingerprint("a" * 64, 4, 1, 0, 1, "b" * 64)

        def __init__(self, **kwargs: object) -> None:
            return None

        def open(self) -> object:
            return object()

        def assert_unchanged(self) -> ReadOnlyDrawingFingerprint:
            return self.fingerprint

        @staticmethod
        def close() -> DrawingCopyEvidence:
            events.append("close")
            return evidence(preserved=False)

    @contextmanager
    def operator() -> Iterator[object]:
        yield object()

    monkeypatch.setenv("AUTOCAD_MCP_SMOKE_RELEASE", "2026")
    monkeypatch.setattr(sys.modules[__name__], "_operator_started_autocad", operator)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_attached_application_identity",
        lambda application, installation_path: _AttachedAutoCADIdentity(
            42, tmp_path / "acad.exe", "AutoCAD 2026", "25.1"
        ),
    )
    monkeypatch.setattr(sys.modules[__name__], "ReadOnlyAutoCADHarness", Harness)
    monkeypatch.setattr(sys.modules[__name__], "WindowsAutoCADAdapter", object)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_run_production_adapter_round",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("adapter failed")),
    )
    session = SimpleNamespace(
        guard=Guard(source_path, copy_path),
        lease=Lease(),
        installation_path=tmp_path / "acad.exe",
    )

    with pytest.raises(RuntimeError, match="adapter failed"):
        test_autocad_2026_read_only_mcp_smoke(session)

    assert events[:2] == ["preserve", "close"]


def test_smoke_report_redacts_paths_embedded_in_a_preservation_reason(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """An exception-derived preservation reason must not leak a private drawing path."""
    copy_path = tmp_path / "private-guard" / "drawing-copy.dwg"
    reason = f"file fingerprint changed: {copy_path}"
    guard_evidence = DrawingCopyEvidence(
        run_id="run-123",
        source_path=str(tmp_path / "private-source" / "fixture.dwg"),
        copy_path=str(copy_path),
        source_sha256_before="a" * 64,
        source_sha256_after="a" * 64,
        copy_sha256_before="a" * 64,
        copy_sha256_after="a" * 64,
        active_full_name=str(copy_path),
        close_without_save_attempted=True,
        preserved=True,
        preserve_reason=reason,
        cleanup_succeeded=False,
    )

    report = _emit_smoke_report(
        outcome="failed",
        attached=None,
        guard_evidence=guard_evidence,
        initial_fingerprint=None,
        final_fingerprint=None,
        post_close_file_fingerprint=None,
        lease_evidence=None,
    )

    output = capsys.readouterr().out
    assert str(copy_path) not in output.split("AUTOCAD_MCP_SMOKE_PRESERVED_COPY=", maxsplit=1)[0]
    assert report["drawing"]["preserve_reason_sha256"] == hashlib.sha256(
        reason.encode("utf-8")
    ).hexdigest()
