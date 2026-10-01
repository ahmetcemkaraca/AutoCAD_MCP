"""JSON contracts reject malformed facts and retain complete immutable state."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from types import MappingProxyType

import pytest
from autocad_mcp.context.models import AnalyzeDrawingResult, EntityQueryFilters, PageInfo
from autocad_mcp.context.serialization import (
    analyze_result_to_json,
    snapshot_from_json,
    snapshot_to_json,
)
from autocad_mcp.context.validation import ContextValidationError

from tests.unit.context.fixtures import CAPTURED_AT, snapshot, snapshot_payload


def test_exact_round_trip_and_utc_millisecond_wire_time():
    original = snapshot()
    assert original.captured_at == CAPTURED_AT
    wire = snapshot_to_json(original)
    assert isinstance(wire, dict)
    assert wire == snapshot_payload()
    assert snapshot_from_json(wire) == original
    assert snapshot_to_json(snapshot_from_json(wire)) == wire
    offset = timezone(timedelta(hours=2))
    shifted = replace(
        original, captured_at=datetime(2026, 10, 1, 14, 34, 56, 789123, tzinfo=offset)
    )
    assert snapshot_to_json(shifted)["captured_at"] == "2026-10-01T12:34:56.789Z"
    assert shifted.captured_at.tzinfo == UTC
    assert shifted.captured_at.microsecond == 789000


@pytest.mark.parametrize("version", ["2.0", "1.1", 1, None])
def test_unknown_version_rejected_with_structured_code(version):
    payload = snapshot_payload()
    payload["schema_version"] = version
    with pytest.raises(ContextValidationError) as error:
        snapshot_from_json(payload)
    assert error.value.code == "UNSUPPORTED_SCHEMA_VERSION"


@pytest.mark.parametrize(
    "location", [(), ("entities", 0), ("entities", 0, "geometry"), ("active_context", "view")]
)
def test_unknown_fields_cannot_disappear(location):
    payload = snapshot_payload()
    target = payload
    for field in location:
        target = target[field]
    target["misspelled_property"] = 1
    with pytest.raises(ContextValidationError):
        snapshot_from_json(payload)


@pytest.mark.parametrize("stamp", ["2026-10-01T00:00:00", "not-a-date", 42])
def test_naive_and_invalid_datetimes_are_rejected(stamp):
    payload = snapshot_payload()
    payload["captured_at"] = stamp
    with pytest.raises(ContextValidationError):
        snapshot_from_json(payload)
    with pytest.raises(ContextValidationError):
        replace(snapshot(), captured_at=datetime(2026, 10, 1))


def test_nonfinite_json_duplicate_keys_and_wrong_primitives_are_rejected():
    from autocad_mcp.context.serialization import snapshot_from_json_text

    raw = json.dumps(snapshot_payload())
    for broken in (
        raw.replace('"x": 0', '"x": NaN', 1),
        raw.replace('"is_saved": true', '"is_saved": 1'),
        raw.replace('"entity_count": 1', '"entity_count": true', 1),
        raw.replace('"schema_version": "1.0"', '"schema_version":"1.0","schema_version":"1.0"'),
    ):
        with pytest.raises(ContextValidationError):
            snapshot_from_json_text(broken)


def test_analyze_page_serialization_keeps_facts_and_interpretations_separate():
    complete = snapshot()
    result = AnalyzeDrawingResult(
        "1.0",
        complete.reference,
        complete.document,
        complete.fingerprint,
        EntityQueryFilters((), (), (), (), (), (), None),
        complete.entities,
        (),
        PageInfo(100, 1, False, None),
        "stored",
    )
    payload = analyze_result_to_json(result)
    assert isinstance(payload, dict)
    assert payload["entities"] == snapshot_payload()["entities"]
    assert payload["interpretations"] == []
    assert payload["source"]["snapshot_id"] == complete.snapshot_id
    assert "materialization" not in payload
    assert "interpretations" not in snapshot_to_json(complete)


@pytest.mark.parametrize(
    "kind, geometry",
    [
        (
            "circle",
            {
                "kind": "circle",
                "center_wcs": {"x": 1, "y": 2, "z": 0},
                "normal_wcs": {"x": 0, "y": 0, "z": 1},
                "radius": 3,
            },
        ),
        (
            "arc",
            {
                "kind": "arc",
                "center_wcs": {"x": 1, "y": 2, "z": 0},
                "normal_wcs": {"x": 0, "y": 0, "z": 1},
                "radius": 3,
                "start_angle_radians": 0,
                "end_angle_radians": 1.5,
            },
        ),
        (
            "lwpolyline",
            {
                "kind": "lwpolyline",
                "vertices_wcs": [{"x": 1, "y": 2, "z": 0}],
                "bulges": [0.5],
                "closed": True,
            },
        ),
        ("point", {"kind": "point", "position_wcs": {"x": 1, "y": 2, "z": 0}}),
        (
            "block_reference",
            {
                "kind": "block_reference",
                "insertion_wcs": {"x": 1, "y": 2, "z": 0},
                "normal_wcs": {"x": 0, "y": 0, "z": 1},
                "rotation_radians": 0.5,
                "scale_xyz": {"x": 1, "y": -1, "z": 1},
            },
        ),
        ("unsupported", {"kind": "unsupported", "object_name": "AcDbCustomEntity"}),
    ],
)
def test_geometry_variant_round_trip(kind, geometry):
    payload = snapshot_payload()
    payload["entities"][0]["geometry"] = geometry
    decoded = snapshot_from_json(payload)
    assert decoded.entities[0].geometry.kind == kind
    assert snapshot_to_json(decoded) == payload


def test_snapshot_constructor_rejects_unknown_version():
    with pytest.raises(ContextValidationError) as error:
        replace(snapshot(), schema_version="2.0")
    assert error.value.code == "UNSUPPORTED_SCHEMA_VERSION"


def test_input_with_invalid_utf8_is_a_structured_failure():
    from autocad_mcp.context.serialization import snapshot_from_json_text

    with pytest.raises(ContextValidationError):
        snapshot_from_json_text("\ud800")


def test_missing_fields_and_unknown_geometry_discriminator_fail():
    for operation in ("missing", "unknown_kind"):
        payload = snapshot_payload()
        if operation == "missing":
            del payload["entities"][0]["geometry"]["start_wcs"]
        else:
            payload["entities"][0]["geometry"]["kind"] = "made_up"
        with pytest.raises(ContextValidationError):
            snapshot_from_json(payload)


def test_complete_snapshot_and_mcp_result_have_distinct_entity_bounds():
    complete = snapshot()
    assert len(replace(complete, entities=complete.entities * 10000).entities) == 10000
    with pytest.raises(ContextValidationError):
        replace(complete, entities=complete.entities * 10001)
    with pytest.raises(ContextValidationError):
        AnalyzeDrawingResult(
            "1.0",
            complete.reference,
            complete.document,
            complete.fingerprint,
            EntityQueryFilters((), (), (), (), (), (), None),
            complete.entities * 501,
            (),
            PageInfo(500, 500, False, None),
            "stored",
        )


def test_mcp_result_serialized_byte_bound():
    from autocad_mcp.context.models import TextFacts

    complete = snapshot()
    entity = replace(
        complete.entities[0], text=TextFacts("x" * 65536, None, None, None, None, None)
    )
    result = AnalyzeDrawingResult(
        "1.0",
        complete.reference,
        complete.document,
        complete.fingerprint,
        EntityQueryFilters((), (), (), (), (), (), None),
        (entity,) * 64,
        (),
        PageInfo(100, 64, False, None),
        "stored",
    )
    with pytest.raises(ContextValidationError) as error:
        analyze_result_to_json(result)
    assert error.value.code == "PAYLOAD_LIMIT"


def test_read_only_mappings_decode_with_defensive_nested_copies():
    payload = snapshot_payload()
    entity = payload["entities"][0]
    entity["geometry"] = MappingProxyType(entity["geometry"])
    entity["block"] = MappingProxyType(entity["block"])
    payload["entities"][0] = MappingProxyType(entity)
    result = snapshot_from_json(MappingProxyType(payload))
    entity["block"]["attribute_values"]["KEY"] = "changed"
    payload["entities"].clear()
    assert len(result.entities) == 1
    assert result.entities[0].block.attribute_values["KEY"] == "VALUE"
    with pytest.raises(TypeError):
        result.entities[0].block.attribute_values["KEY"] = "changed"


def test_mapping_decoder_rejects_json_text():
    with pytest.raises(ContextValidationError) as error:
        snapshot_from_json(json.dumps(snapshot_payload()))
    assert error.value.code == "INVALID_ARGUMENT"


@pytest.mark.parametrize("stamp", ["0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"])
@pytest.mark.parametrize("decode", [False, True])
def test_utc_normalization_overflow_is_a_redacted_validation_error(stamp, decode):
    payload = snapshot_payload()
    payload["captured_at"] = stamp
    original = snapshot()
    with pytest.raises(ContextValidationError) as error:
        if decode:
            snapshot_from_json(payload)
        else:
            replace(original, captured_at=datetime.fromisoformat(stamp))
    assert error.value.code == "INVALID_ARGUMENT"
    assert "UTC" in str(error.value)
    assert stamp not in str(error.value)


def _record_at_byte_limit(make_record, limit):
    from autocad_mcp.context.models import TextFacts
    from autocad_mcp.context.serialization import record_to_json

    entity = snapshot().entities[0]
    empty = replace(entity, text=TextFacts("", "", None, None, None, None))
    full = replace(entity, text=replace(empty.text, plain_text="x" * 65536))
    base_bytes = len(record_to_json(make_record((empty,))).encode("utf-8"))
    entity_bytes = len(record_to_json(full).encode("utf-8"))
    count = (limit - base_bytes) // (entity_bytes + 1)
    entities = (full,) * count + (empty,)
    remaining = limit - len(record_to_json(make_record(entities)).encode("utf-8"))
    padded = replace(
        empty,
        text=replace(
            empty.text,
            plain_text="x" * min(remaining, 65536),
            raw_text="x" * max(remaining - 65536, 0),
        ),
    )
    return make_record(entities[:-1] + (padded,))


def _add_one_text_byte(record):
    last = record.entities[-1]
    last = replace(last, text=replace(last.text, raw_text=last.text.raw_text + "x"))
    return replace(record, entities=record.entities[:-1] + (last,))


def test_snapshot_mapping_input_and_output_accept_exact_byte_limit():
    from autocad_mcp.context.serialization import record_to_json, record_to_payload

    complete = snapshot()
    exact = _record_at_byte_limit(
        lambda entities: replace(complete, entities=entities), 32 * 1024**2
    )
    payload = snapshot_to_json(exact)
    assert isinstance(payload, dict)
    assert len(record_to_json(payload).encode("utf-8")) == 32 * 1024**2
    assert snapshot_from_json(MappingProxyType(payload)) == exact
    oversized = _add_one_text_byte(exact)
    assert len(record_to_json(oversized).encode("utf-8")) == 32 * 1024**2 + 1
    for operation in (
        lambda: snapshot_to_json(oversized),
        lambda: snapshot_from_json(record_to_payload(oversized)),
    ):
        with pytest.raises(ContextValidationError) as error:
            operation()
        assert error.value.code == "COMPLETE_SNAPSHOT_LIMIT"


def test_analysis_mapping_output_accepts_exact_byte_limit():
    from autocad_mcp.context.serialization import record_to_json

    complete = snapshot()

    def make_record(entities):
        return AnalyzeDrawingResult(
            "1.0", complete.reference, complete.document, complete.fingerprint,
            EntityQueryFilters((), (), (), (), (), (), None), entities,
            (), PageInfo(500, len(entities), False, None), "stored",
        )

    exact = _record_at_byte_limit(make_record, 4 * 1024**2)
    payload = analyze_result_to_json(exact)
    assert isinstance(payload, dict)
    assert len(record_to_json(payload).encode("utf-8")) == 4 * 1024**2
    oversized = _add_one_text_byte(exact)
    assert len(record_to_json(oversized).encode("utf-8")) == 4 * 1024**2 + 1
    with pytest.raises(ContextValidationError) as error:
        analyze_result_to_json(oversized)
    assert error.value.code == "PAYLOAD_LIMIT"
