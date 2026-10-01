"""JSON contracts reject malformed facts and retain complete immutable state."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

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
    assert json.loads(wire) == snapshot_payload()
    assert snapshot_from_json(wire) == original
    assert snapshot_to_json(snapshot_from_json(wire)) == wire
    offset = timezone(timedelta(hours=2))
    shifted = replace(
        original, captured_at=datetime(2026, 10, 1, 14, 34, 56, 789123, tzinfo=offset)
    )
    assert json.loads(snapshot_to_json(shifted))["captured_at"] == "2026-10-01T12:34:56.789Z"
    assert shifted.captured_at.tzinfo == UTC
    assert shifted.captured_at.microsecond == 789000


@pytest.mark.parametrize("version", ["2.0", "1.1", 1, None])
def test_unknown_version_rejected_with_structured_code(version):
    payload = snapshot_payload()
    payload["schema_version"] = version
    with pytest.raises(ContextValidationError) as error:
        snapshot_from_json(json.dumps(payload))
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
        snapshot_from_json(json.dumps(payload))


@pytest.mark.parametrize("stamp", ["2026-10-01T00:00:00", "not-a-date", 42])
def test_naive_and_invalid_datetimes_are_rejected(stamp):
    payload = snapshot_payload()
    payload["captured_at"] = stamp
    with pytest.raises(ContextValidationError):
        snapshot_from_json(json.dumps(payload))
    with pytest.raises(ContextValidationError):
        replace(snapshot(), captured_at=datetime(2026, 10, 1))


def test_nonfinite_json_duplicate_keys_and_wrong_primitives_are_rejected():
    raw = json.dumps(snapshot_payload())
    for broken in (
        raw.replace('"x": 0', '"x": NaN', 1),
        raw.replace('"is_saved": true', '"is_saved": 1'),
        raw.replace('"entity_count": 1', '"entity_count": true', 1),
        raw.replace('"schema_version": "1.0"', '"schema_version":"1.0","schema_version":"1.0"'),
    ):
        with pytest.raises(ContextValidationError):
            snapshot_from_json(broken)


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
    payload = json.loads(analyze_result_to_json(result))
    assert payload["entities"] == snapshot_payload()["entities"]
    assert payload["interpretations"] == []
    assert payload["source"]["snapshot_id"] == complete.snapshot_id
    assert "materialization" not in payload
    assert "interpretations" not in json.loads(snapshot_to_json(complete))


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
    decoded = snapshot_from_json(json.dumps(payload))
    assert decoded.entities[0].geometry.kind == kind
    assert json.loads(snapshot_to_json(decoded)) == payload


def test_snapshot_constructor_rejects_unknown_version():
    with pytest.raises(ContextValidationError) as error:
        replace(snapshot(), schema_version="2.0")
    assert error.value.code == "UNSUPPORTED_SCHEMA_VERSION"


def test_input_with_invalid_utf8_is_a_structured_failure():
    with pytest.raises(ContextValidationError):
        snapshot_from_json("\ud800")


def test_missing_fields_and_unknown_geometry_discriminator_fail():
    for operation in ("missing", "unknown_kind"):
        payload = snapshot_payload()
        if operation == "missing":
            del payload["entities"][0]["geometry"]["start_wcs"]
        else:
            payload["entities"][0]["geometry"]["kind"] = "made_up"
        with pytest.raises(ContextValidationError):
            snapshot_from_json(json.dumps(payload))


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
