"""Stateless cursor signatures, strict binding shape, time and encoded bounds."""

import base64
import hmac
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from autocad_mcp.context.models import EntityQueryFilters
from autocad_mcp.context.pagination import (
    CursorCodec,
    PageCursor,
    SystemClock,
    entity_sort_key,
    filter_digest,
    normalize_filters,
)
from autocad_mcp.context.validation import ContextValidationError

from tests.unit.context.fixtures import snapshot

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
SECRET = b"synthetic-test-secret-32-bytes-only"


def cursor(**changes):
    values = {
        "kind": "snapshot",
        "document_id": "dwg_" + "a" * 32,
        "session_id": "session-1",
        "filter_digest": "sha256:" + "b" * 64,
        "page_size": 100,
        "last_sort_key": (0, "model", 161, "A1"),
        "issued_at": NOW,
        "expires_at": NOW + timedelta(seconds=600),
        "snapshot_id": "ds1_" + "c" * 32,
    }
    values.update(changes)
    return PageCursor(**values)


def codec(now=NOW, secret=SECRET):
    return CursorCodec(clock=SimpleNamespace(now=lambda: now), secret=secret)


def signed_payload(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()

    def enc(value):
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    return enc(raw) + "." + enc(hmac.digest(SECRET, raw, "sha256"))


def test_snapshot_and_live_roundtrip_distinct_binding_and_clock():
    first = cursor(
        issued_at=NOW.replace(microsecond=123),
        expires_at=NOW + timedelta(seconds=1, microseconds=123),
    )
    live = cursor(
        kind="live_query",
        snapshot_id=None,
        revision_token_digest="sha256:" + "d" * 64,
        adapter_cursor="adapter-page",
        expires_at=NOW + timedelta(seconds=900),
    )
    for value in (first, live):
        wire = codec(NOW + timedelta(microseconds=123)).encode(value)
        assert len(wire.encode()) <= 2048
        assert codec(NOW + timedelta(microseconds=123)).decode(wire) == value
        assert codec(NOW + timedelta(microseconds=123)).encode(value) == wire
    assert SystemClock().now().tzinfo == UTC


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "other"},
        {"snapshot_id": None},
        {"revision_token_digest": "sha256:" + "d" * 64},
        {"adapter_cursor": "live"},
        {"kind": "live_query", "snapshot_id": None},
        {"page_size": True},
        {"page_size": 0},
        {"page_size": 501},
        {"last_sort_key": (0, "model", 1, "A1")},
        {"filter_digest": "bad"},
        {"expires_at": NOW},
        {"expires_at": NOW + timedelta(seconds=601)},
        {"issued_at": NOW.replace(tzinfo=None)},
        {"session_id": ""},
    ],
)
def test_cursor_shape_kind_mix_and_bounds(changes):
    with pytest.raises(ContextValidationError) as error:
        codec().encode(cursor(**changes))
    assert error.value.code == "INVALID_CURSOR"


def test_tampering_wrong_secret_invalid_encoding_future_time_and_exact_expiry():
    value = codec().encode(cursor())
    for broken in (
        value[:-1] + ("A" if value[-1] != "A" else "B"),
        "not-base64",
        value + "=",
        "." + value,
        "é" * 2049,
    ):
        with pytest.raises(ContextValidationError) as error:
            codec().decode(broken)
        assert error.value.code == "INVALID_CURSOR"
    with pytest.raises(ContextValidationError) as error:
        codec(secret=b"different-test-secret-32-bytes-only").decode(value)
    assert error.value.code == "INVALID_CURSOR"
    with pytest.raises(ContextValidationError) as error:
        codec(NOW - timedelta(microseconds=1)).decode(value)
    assert error.value.code == "INVALID_CURSOR"
    with pytest.raises(ContextValidationError) as error:
        codec(NOW + timedelta(seconds=600)).decode(value)
    assert error.value.code == "CURSOR_EXPIRED"
    assert codec(NOW + timedelta(seconds=600, microseconds=-1)).decode(value) == cursor()


def test_correctly_signed_unknown_fields_and_wrong_primitives_are_invalid():
    raw = codec().encode(cursor()).split(".")[0]
    payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    for key, value in (
        ("unknown", 1),
        ("page_size", True),
        ("version", 2),
        ("issued_at", "not-a-time"),
        ("last_sort_key", [True, "model", 161, "A1"]),
    ):
        altered = dict(payload, **{key: value})
        with pytest.raises(ContextValidationError) as error:
            codec().decode(signed_payload(altered))
        assert error.value.code == "INVALID_CURSOR"


def test_encoded_exact_2048_byte_boundary_and_secret_minimum():
    for length in range(800, 1600):
        live = cursor(
            kind="live_query",
            snapshot_id=None,
            revision_token_digest="sha256:" + "d" * 64,
            adapter_cursor="x" * length,
        )
        try:
            wire = codec().encode(live)
        except ContextValidationError:
            break
        if len(wire) == 2048:
            assert codec().decode(wire) == live
            with pytest.raises(ContextValidationError) as error:
                codec().encode(replace(live, adapter_cursor="x" * (length + 1)))
            assert error.value.code == "INVALID_CURSOR"
            break
    else:
        pytest.fail("no exact boundary cursor")
    assert len(wire) == 2048
    with pytest.raises(ContextValidationError):
        codec(secret=b"too short")


def test_filters_are_set_normalized_without_changing_layer_case_or_literal_globs():
    first = EntityQueryFilters(
        ("paper", "model"),
        ("Layout", "Layout"),
        ("AcDbLine",),
        ("café", "Walls"),
        ("wall[1]*",),
        ("10", "a1"),
        None,
    )
    second = EntityQueryFilters(
        ("model", "paper"),
        ("Layout",),
        ("AcDbLine",),
        ("Walls", "cafe\u0301"),
        ("wall[1]*",),
        ("A1", "10"),
        None,
    )
    assert normalize_filters(first) == normalize_filters(second)
    assert filter_digest(first, {"text": True, "geometry": False}) == filter_digest(
        second, {"geometry": False, "text": True}
    )
    assert filter_digest(first, {"text": True}) != filter_digest(first, {"text": False})
    assert filter_digest(first, {}) != filter_digest(replace(first, layer_names=("walls",)), {})
    with pytest.raises(ContextValidationError):
        filter_digest(first, {"text": 1})
    entity = snapshot().entities[0]
    assert entity_sort_key(entity) == (0, "model", 161, "A1")
    assert entity_sort_key(replace(entity, identity=replace(entity.identity, handle="10"))) < (
        entity_sort_key(entity)
    )


def test_opaque_unicode_bindings_preserve_exact_bytes_and_normalization_distinction():
    live = cursor(
        kind="live_query",
        snapshot_id=None,
        revision_token_digest="sha256:" + "d" * 64,
        session_id="session-cafe\u0301",
        adapter_cursor="opaque-cafe\u0301",
    )
    assert codec().decode(codec().encode(live)) == live
    equivalent_text = replace(live, adapter_cursor="opaque-café")
    assert codec().encode(live) != codec().encode(equivalent_text)


@pytest.mark.parametrize("layout", ["\x00", "\ud800"])
def test_invalid_sort_key_text_is_a_structured_cursor_failure(layout):
    with pytest.raises(ContextValidationError) as error:
        codec().encode(cursor(last_sort_key=(0, layout, 161, "A1")))
    assert error.value.code == "INVALID_CURSOR"


@pytest.mark.parametrize(
    "changes",
    [
        {"document_id": "dwg_" + "e" * 32},
        {"session_id": "session-2"},
        {"filter_digest": "sha256:" + "e" * 64},
        {"page_size": 101},
        {"last_sort_key": (0, "model", 162, "A2")},
        {"snapshot_id": "ds1_" + "e" * 32},
    ],
)
def test_signature_binds_every_snapshot_continuation_field(changes):
    original = cursor()
    changed = replace(original, **changes)
    assert codec().encode(changed) != codec().encode(original)
    assert codec().decode(codec().encode(changed)) == changed
    raw, signature = codec().encode(original).split(".")
    changed_raw = codec().encode(changed).split(".")[0]
    with pytest.raises(ContextValidationError) as error:
        codec().decode(changed_raw + "." + signature)
    assert error.value.code == "INVALID_CURSOR"


def test_live_revision_and_adapter_bindings_and_maximum_lifetime():
    live = cursor(
        kind="live_query",
        snapshot_id=None,
        revision_token_digest="sha256:" + "d" * 64,
        adapter_cursor="page-1",
        expires_at=NOW + timedelta(seconds=900),
    )
    for changed in (
        replace(live, revision_token_digest="sha256:" + "e" * 64),
        replace(live, adapter_cursor="page-2"),
    ):
        assert codec().encode(changed) != codec().encode(live)
        assert codec().decode(codec().encode(changed)) == changed
    with pytest.raises(ContextValidationError) as error:
        replace(live, expires_at=NOW + timedelta(seconds=900, microseconds=1))
    assert error.value.code == "INVALID_CURSOR"
    with pytest.raises(ContextValidationError) as error:
        codec(NOW + timedelta(seconds=900)).decode(codec().encode(live))
    assert error.value.code == "CURSOR_EXPIRED"


def test_signed_duplicate_json_keys_are_not_accepted():
    raw, _ = codec().encode(cursor()).split(".")
    payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    payload = payload.replace(b'"version":1', b'"version":1,"version":1')
    wire = (
        base64.urlsafe_b64encode(payload).decode().rstrip("=")
        + "."
        + base64.urlsafe_b64encode(hmac.digest(SECRET, payload, "sha256")).decode().rstrip("=")
    )
    with pytest.raises(ContextValidationError) as error:
        codec().decode(wire)
    assert error.value.code == "INVALID_CURSOR"


def test_casefold_expansion_of_valid_layout_name_remains_a_valid_sort_key():
    entity = snapshot().entities[0]
    entity = replace(entity, space=replace(entity.space, layout_name="ß" * 130))
    key = entity_sort_key(entity)
    assert len(key[1]) == 260
    value = cursor(last_sort_key=key)
    assert codec().decode(codec().encode(value)) == value
