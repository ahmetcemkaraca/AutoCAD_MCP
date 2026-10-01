"""Cross-language fixed metadata schema and bounded framing, without host or transport."""

import io
import json
import struct
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from autocad_mcp.adapter.native_revision import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    NativeRevisionError,
    RevisionWitness,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
    read_frame,
)

VECTORS = json.loads(
    (Path(__file__).parents[1] / "fixtures/native-context/vectors.json").read_text()
)
NONCE = "a" * 64
WITNESS = RevisionWitness(
    "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1, None
)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda row: row["name"])
def test_shared_vectors(vector):
    frame = bytes.fromhex(vector["frame_hex"])
    operation = (
        (lambda: decode_request(frame))
        if vector["kind"] == "request"
        else (lambda: decode_response(frame, expected_nonce=vector["nonce"]))
    )
    expected_error = vector.get("error")
    if not vector["valid"] or expected_error:
        with pytest.raises(NativeRevisionError) as error:
            operation()
        assert error.value.code == (expected_error or "INVALID_REQUEST")
        assert str(error.value) == error.value.code
    else:
        result = operation()
        assert result is not None
        if vector["kind"] == "request":
            encoded = encode_request(
                nonce=result.nonce, client_pid=result.client_pid, document_hwnd=result.document_hwnd
            )
            assert decode_request(encoded) == result
        else:
            assert encode_response(nonce=NONCE, witness=result) == frame


def test_witness_immutable_validated_and_token_is_bounded():
    expected = (
        "native-context-epochs-v1:11111111-1111-4111-8111-111111111111:"
        "22222222-2222-4222-8222-222222222222:1"
    )
    assert WITNESS.opaque_token == expected
    assert len(replace(WITNESS, epoch=2**64 - 1).opaque_token.encode()) < 512
    with pytest.raises(FrozenInstanceError):
        WITNESS.epoch = 2
    for changes in ({"epoch": True}, {"epoch": 0}, {"epoch": 2**64}, {"bridge_id": "private"}):
        with pytest.raises(NativeRevisionError):
            replace(WITNESS, **changes)


def test_fragmented_frame_reader_and_truncation_limits():
    class Fragmented(io.BytesIO):
        def read(self, length=-1):
            return super().read(min(length, 1))

    frame = encode_request(nonce=NONCE, client_pid=1, document_hwnd=1)
    assert read_frame(Fragmented(frame), limit=MAX_REQUEST_BYTES) == frame
    for broken in (frame[:2], frame[:-1], struct.pack("<I", 4097)):
        with pytest.raises(NativeRevisionError):
            read_frame(Fragmented(broken), limit=MAX_REQUEST_BYTES)
    payload = frame[4:]
    exact = payload + b" " * (MAX_REQUEST_BYTES - len(payload))
    assert decode_request(struct.pack("<I", len(exact)) + exact).client_pid == 1
    with pytest.raises(NativeRevisionError):
        decode_request(struct.pack("<I", len(exact) + 1) + exact + b" ")
    response = encode_response(nonce=NONCE, witness=WITNESS)
    exact = response[4:] + b" " * (MAX_RESPONSE_BYTES - len(response[4:]))
    assert decode_response(struct.pack("<I", len(exact)) + exact, expected_nonce=NONCE) == WITNESS


def test_old_response_does_not_match_fresh_connection_nonce():
    response = encode_response(nonce=NONCE, witness=WITNESS)
    with pytest.raises(NativeRevisionError) as error:
        decode_response(response, expected_nonce="b" * 64)
    assert error.value.code == "UNTRUSTED_PEER"
