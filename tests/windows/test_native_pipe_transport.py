"""Real Windows local-pipe APIs against the BCL fake host; no AutoCAD/drawing access."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from autocad_mcp.adapter.native_revision import NativeRevisionError
from autocad_mcp.adapter.windows_native_revision import WindowsNativeRevisionSource

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="requires real Windows named-pipe APIs"
)
ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "native/context-observer/host-tests/ContextObserver.HostTests.csproj"


@pytest.fixture
def pipe_host(request):
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.fail("the native fake-host fixture requires the pinned .NET SDK")
    subprocess.run([dotnet, "build", str(PROJECT), "--verbosity", "quiet"], check=True, cwd=ROOT)  # noqa: S603 - fixed owned test project
    assembly = PROJECT.parent / "bin/Debug/net10.0/ContextObserver.HostTests.dll"
    arguments = [dotnet, str(assembly), "--pipe-host"]
    if getattr(request, "param", None) == "stall":
        arguments.append("--stall")
    process = subprocess.Popen(  # noqa: S603 - fixed owned fake-host executable
        arguments,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        metadata = json.loads(process.stdout.readline())
        yield metadata
    finally:
        if process.stdin is not None:
            process.stdin.write("stop\n")
            process.stdin.flush()
        _, error = process.communicate(timeout=10)
        assert process.returncode == 0, error


def test_kernel_authenticated_roundtrip_fresh_connections_and_protected_dacl(pipe_host):
    from autocad_mcp.adapter.windows_native_revision import _Win32

    source = WindowsNativeRevisionSource()
    first = source.witness(pipe_host["hwnd"])
    second = source.witness(pipe_host["hwnd"])
    assert first == second
    assert first.database_guid is None
    bindings = _Win32()
    expected = bindings.window_process(pipe_host["hwnd"])
    assert (
        pipe_host["pipe"]
        == f"autocad-mcp-context-v1-{expected.pid}-{expected.created_filetime:016x}"
    )
    import time

    import win32security

    handle = bindings.open_pipe(pipe_host["pipe"], time.monotonic() + 2)
    try:
        descriptor = win32security.GetSecurityInfo(
            handle, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION
        )
        control, _ = descriptor.GetSecurityDescriptorControl()
        assert control & win32security.SE_DACL_PROTECTED
        dacl = descriptor.GetSecurityDescriptorDacl()
        assert dacl.GetAceCount() == 1
        assert win32security.ConvertSidToStringSid(dacl.GetAce(0)[2]) == bindings.current().sid
    finally:
        bindings.close(handle)


@pytest.mark.parametrize("pipe_host", ["stall"], indirect=True)
def test_total_timeout_disconnects_and_never_dispatches_abandoned_request(pipe_host):
    import time

    began = time.monotonic()
    with pytest.raises(NativeRevisionError) as caught:
        WindowsNativeRevisionSource().witness(pipe_host["hwnd"])
    assert caught.value.code == "TIMEOUT"
    assert time.monotonic() - began < 2.5


def test_server_checks_kernel_client_pid_instead_of_request_claim(pipe_host):
    from dataclasses import replace

    from autocad_mcp.adapter.windows_native_revision import _Win32

    actual = _Win32()

    class WrongClaim:
        def __getattr__(self, name):
            return getattr(actual, name)

        def current(self):
            peer = actual.current()
            return replace(peer, pid=peer.pid + 1)

    with pytest.raises(NativeRevisionError) as caught:
        WindowsNativeRevisionSource(bindings=WrongClaim()).witness(pipe_host["hwnd"])
    assert caught.value.code == "UNTRUSTED_PEER"
