"""The public mesh schema is closed and matches the accepted pure input contract."""

import copy
import json
from pathlib import Path

import pytest
from autocad_mcp.tools.surface_unfolding import SURFACE_UNFOLDING_TOOL
from jsonschema import Draft202012Validator

FIXTURES = Path(__file__).parents[1] / "fixtures" / "unfolding"
VALIDATOR = Draft202012Validator(SURFACE_UNFOLDING_TOOL.inputSchema)


def request():
    return json.loads((FIXTURES / "cases" / "planar-grid.json").read_text())


def test_schema_metadata_and_all_admissible_frozen_inputs():
    Draft202012Validator.check_schema(SURFACE_UNFOLDING_TOOL.inputSchema)
    assert SURFACE_UNFOLDING_TOOL.name == "unfold_surface"
    assert SURFACE_UNFOLDING_TOOL.annotations.readOnlyHint is True
    assert SURFACE_UNFOLDING_TOOL.annotations.openWorldHint is False
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    for case in manifest["cases"]:
        if case["accepted"]:
            VALIDATOR.validate(json.loads((FIXTURES / case["path"]).read_text()))
    assert json.loads(SURFACE_UNFOLDING_TOOL.model_dump_json())["inputSchema"] == (
        SURFACE_UNFOLDING_TOOL.inputSchema
    )


@pytest.mark.parametrize("where", [(), ("policy",), ("vertices", 0), ("faces", 0)])
def test_every_object_rejects_unknown_and_missing_fields(where):
    data = request()
    target = data
    for key in where:
        target = target[key]
    first = next(iter(target))
    saved = target[first]
    del target[first]
    assert not VALIDATOR.is_valid(data)
    target[first] = saved
    target["private_extra"] = "private_text"
    assert not VALIDATOR.is_valid(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", ""), ("request_id", "a" * 129),
        ("units_label", "a" * 65), ("units_label", "private\x00text"),
        ("units_label", "private\x85text"), ("units_label", "private\n"), ("units_label", "\ud800"),
        ("root_face_id", True), ("root_face_id", -1), ("root_face_id", 2**53),
        ("vertices", []), ("faces", []), ("seam_edges", [[0, 1, 2]]),
    ],
)
def test_root_types_text_and_dimensions_are_closed(field, value):
    assert not VALIDATOR.is_valid(request() | {field: value})


@pytest.mark.parametrize(
    "field,maximum", [("vertices", 2000), ("faces", 4000), ("seam_edges", 6000)]
)
def test_collection_exact_count_ceiling_and_one_over(field, maximum):
    data = request()
    item = data[field][0] if data[field] else [0, 1]
    data[field] = [copy.deepcopy(item) for _ in range(maximum)]
    # Unique identities and mesh topology are enforced by the strict decoder, not this schema.
    assert VALIDATOR.is_valid(data)
    data[field].append(copy.deepcopy(item))
    assert not VALIDATOR.is_valid(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_items", 200001), ("max_iterations", 1000001),
        ("cancellation_check_interval", 1025), ("deadline_seconds", 30.001),
        ("deadline_seconds", 0), ("deterministic_seed", 2**53),
        ("max_iterations", True), ("deterministic_seed", -1),
    ],
)
def test_policy_ceilings_and_scalar_types(field, value):
    data = request()
    data["policy"][field] = value
    assert not VALIDATOR.is_valid(data)


def test_points_and_face_ids_have_exact_arity_and_numeric_types():
    for field, key, value in (
        ("vertices", "point", [0, 0]),
        ("vertices", "point", [0, True, 0]),
        ("faces", "vertex_ids", [0, 1, 2, 3]),
        ("faces", "vertex_ids", [0, "1", 2]),
    ):
        data = request()
        data[field][0][key] = value
        assert not VALIDATOR.is_valid(data)
