"""Authentication and one total deadline use injected Windows metadata/pipe calls."""

import importlib
import struct
from dataclasses import replace

import pytest
from autocad_mcp.adapter.native_revision import (
    NativeRevisionError,
    RevisionWitness,
    decode_request,
    encode_response,
)


def api():
    try:
        return importlib.import_module("autocad_mcp.adapter.windows_native_revision")
    except ModuleNotFoundError:
        pytest.fail("Windows native witness transport is not implemented")


class Clock:
    value = 10.0

    def __call__(self):
        return self.value


class Bindings:
    def __init__(self, module, clock):
        self.clock = clock
        self.server = module.ProcessIdentity(42, 0x123456789ABCDEF0, "S-1-5-21-123", 2)
        self.client = module.ProcessIdentity(7, 100, self.server.sid, self.server.session_id)
        self.actual_pid = self.server.pid
        self.observed = self.server
        self.window_peer = self.server
        self.closed = []
        self.sent = bytearray()
        self.response = b""
        self.opened = []
        self.step = 0.0
        self.wrong_nonce = False
        self.header = None
        self.stalled = False

    def current(self):
        return self.client

    def window_process(self, hwnd):
        assert hwnd == 1234
        return self.window_peer

    def process(self, pid):
        assert pid == self.server.pid
        return self.observed

    def open_pipe(self, name, deadline):
        self.sent = bytearray()
        self.response = b""
        self.opened.append((name, deadline))
        self.clock.value += self.step
        return 99

    def server_pid(self, handle):
        assert handle == 99
        return self.actual_pid

    def write(self, handle, data):
        self.clock.value += self.step
        self.sent.extend(data[:1])
        if len(self.sent) >= 4 and len(self.sent) == struct.unpack("<I", self.sent[:4])[0] + 4:
            request = decode_request(bytes(self.sent))
            self.response = encode_response(
                nonce=("f" * 64 if self.wrong_nonce else request.nonce),
                witness=RevisionWitness(
                    "11111111-1111-4111-8111-111111111111",
                    "22222222-2222-4222-8222-222222222222",
                    5,
                    None,
                ),
            )
            if self.header is not None:
                self.response = self.header
        return 1

    def read(self, handle, size):
        self.clock.value += self.step
        if self.stalled:
            return b""
        result, self.response = self.response[:1], self.response[1:]
        return result

    def pause(self, remaining):
        self.clock.value += min(remaining, 0.005)

    def close(self, handle):
        self.closed.append(handle)


def setup_source():
    module = api()
    clock = Clock()
    bindings = Bindings(module, clock)
    source = module.WindowsNativeRevisionSource(bindings=bindings, clock=clock)
    return module, clock, bindings, source


def test_peer_derived_pipe_and_fragmented_roundtrip_close_handle():
    _, _, bindings, source = setup_source()
    witness = source.witness(1234)
    assert witness.epoch == 5
    assert bindings.opened == [("autocad-mcp-context-v1-42-123456789abcdef0", 12.0)]
    assert decode_request(bytes(bindings.sent)).client_pid == 7
    assert bindings.closed == [99]
    source.witness(1234)
    # A new nonce must be generated for every connection.
    assert bindings.closed == [99, 99]


@pytest.mark.parametrize(
    "field,value",
    [("pid", 43), ("created_filetime", 999), ("sid", "S-1-5-21-999"), ("session_id", 3)],
)
def test_connected_peer_identity_mismatch_fails_closed(field, value):
    _, _, bindings, source = setup_source()
    if field == "pid":
        bindings.actual_pid = value
    else:
        bindings.observed = replace(bindings.server, **{field: value})
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "UNTRUSTED_PEER"
    assert bindings.closed == [99]
    assert not bindings.sent


@pytest.mark.parametrize("field,value", [("sid", "S-1-5-21-999"), ("session_id", 3)])
def test_window_process_must_be_current_user_and_interactive_session(field, value):
    _, _, bindings, source = setup_source()
    bindings.client = replace(bindings.client, **{field: value})
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "UNTRUSTED_PEER"
    assert not bindings.opened


def test_response_nonce_mismatch_closes_handle():
    _, _, bindings, source = setup_source()
    bindings.wrong_nonce = True
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "UNTRUSTED_PEER"
    assert bindings.closed == [99]


@pytest.mark.parametrize("step,stalled", [(3.0, False), (0.02, False), (0.0, True)])
def test_connect_write_read_share_total_two_second_deadline(step, stalled):
    _, clock, bindings, source = setup_source()
    bindings.step, bindings.stalled = step, stalled
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "TIMEOUT"
    assert clock.value >= 12.0
    assert bindings.closed == [99]


@pytest.mark.parametrize("header", [struct.pack("<I", 8193), struct.pack("<I", 0)])
def test_oversized_or_zero_response_refuses_body_read(header):
    _, _, bindings, source = setup_source()
    bindings.header = header
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "INVALID_REQUEST"
    assert bindings.closed == [99]


def test_non_windows_binding_is_delayed_and_redacted(monkeypatch):
    module = api()
    monkeypatch.setattr(module.sys, "platform", "linux")
    source = module.WindowsNativeRevisionSource()
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert str(caught.value) == "UNAVAILABLE"


@pytest.mark.parametrize("hwnd", [None, 0, True, -1, 2**64])
def test_invalid_window_rejected_before_binding(hwnd):
    _, _, bindings, source = setup_source()
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(hwnd)
    assert caught.value.code == "INVALID_REQUEST"
    assert not bindings.opened


def test_peer_incarnation_rechecked_after_response_and_window_reuse_fails_closed():
    _, _, bindings, source = setup_source()
    original_read = bindings.read

    def changed(handle, size):
        data = original_read(handle, size)
        if len(bindings.response) == 0:
            bindings.window_peer = replace(bindings.server, created_filetime=999)
        return data

    bindings.read = changed
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "UNTRUSTED_PEER"
    assert bindings.closed == [99]


def test_binding_failure_is_redacted_and_closes_pipe():
    _, _, bindings, source = setup_source()

    def broken(handle, size):
        raise RuntimeError("synthetic private exception")

    bindings.read = broken
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert str(caught.value) == "UNAVAILABLE"
    assert bindings.closed == [99]


def test_session_zero_is_not_an_interactive_peer():
    _, _, bindings, source = setup_source()
    bindings.client = replace(bindings.client, session_id=0)
    bindings.server = replace(bindings.server, session_id=0)
    bindings.window_peer = bindings.server
    bindings.observed = bindings.server
    with pytest.raises(NativeRevisionError) as caught:
        source.witness(1234)
    assert caught.value.code == "UNTRUSTED_PEER"
    assert not bindings.opened
