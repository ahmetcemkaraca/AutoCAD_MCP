"""Strict JSON normalization enforces finite bounded pure-data requests."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from autocad_mcp.advanced.unfolding.models import (
    MeshValidationError,
    decode_request,
    normalize_request,
    request_json,
)

FIXTURES = Path(__file__).parents[3] / "fixtures" / "unfolding"


def payload() -> dict:
    return json.loads((FIXTURES / "cases/planar-grid.json").read_text())


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", ""),
        ("request_id", "r" * 129),
        ("request_id", "bad\ntext"),
        ("request_id", "bad\x7ftext"),
        ("request_id", 1),
        ("units_label", ""),
        ("units_label", "u" * 65),
        ("units_label", "bad\x85text"),
        ("root_face_id", True),
        ("root_face_id", -1),
        ("root_face_id", 2**53),
        ("root_face_id", 0.0),
        ("unknown_field", "ignored"),
    ],
)
def test_rejects_strict_request_fields(field: str, value: object) -> None:
    data = payload()
    data[field] = value
    with pytest.raises(MeshValidationError):
        decode_request(data)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("vertices", "vertex_id", True),
        ("vertices", "vertex_id", -1),
        ("vertices", "vertex_id", 2**53),
        ("vertices", "vertex_id", 0.0),
        ("vertices", "point", [0, 0]),
        ("vertices", "point", [0, True, 0]),
        ("vertices", "point", [0, "1", 0]),
        ("vertices", "point", [float("nan"), 0, 0]),
        ("vertices", "point", [0, float("inf"), 0]),
        ("vertices", "extra", 1),
        ("faces", "face_id", False),
        ("faces", "vertex_ids", [0, 1]),
        ("faces", "vertex_ids", [0, 1, False]),
        ("faces", "extra", 1),
    ],
)
def test_rejects_invalid_nested_types(target: str, field: str, value: object) -> None:
    data = payload()
    data[target][0][field] = value
    with pytest.raises(MeshValidationError):
        decode_request(data)


def test_normalization_is_canonical_and_preserves_oriented_face_identity() -> None:
    data = payload()
    data["request_id"] = "r" * 128
    data["units_label"] = "μ" * 64
    data["seam_edges"] = [[2, 0]]
    request = decode_request(data)
    shuffled = copy.deepcopy(data)
    shuffled["vertices"].reverse()
    shuffled["faces"].reverse()
    shuffled["seam_edges"] = [[0, 2]]
    assert request == decode_request(shuffled)
    assert request.faces[1].vertex_ids == (0, 2, 3)
    assert request.seam_edges == ((0, 2),)
    assert normalize_request(request) == request
    assert request_json(request) == request_json(decode_request(shuffled))
    assert request.vertices[0].point == (0.0, 0.0, 0.0)
    with pytest.raises(FrozenInstanceError):
        request.root_face_id = 1  # type: ignore[misc]


@pytest.mark.parametrize("field,collection", [("vertex_id", "vertices"), ("face_id", "faces")])
def test_duplicate_ids_reject(field: str, collection: str) -> None:
    data = payload()
    data[collection][1][field] = data[collection][0][field]
    with pytest.raises(MeshValidationError):
        decode_request(data)


@pytest.mark.parametrize("field,count", [("vertices", 2001), ("faces", 4001), ("seam_edges", 6001)])
def test_one_item_over_mesh_ceiling_rejects_before_normalization(field: str, count: int) -> None:
    data = payload()
    data[field] = [data[field][0] if data[field] else [0, 1]] * count
    with pytest.raises(MeshValidationError, match="limit"):
        decode_request(data)


def test_item_policy_counts_vertices_faces_and_seams() -> None:
    data = payload()
    data["policy"]["max_items"] = 6
    assert decode_request(data)
    data["policy"]["max_items"] = 5
    with pytest.raises(MeshValidationError, match="item"):
        decode_request(data)


def test_unknown_policy_fields_and_nonobject_data_reject() -> None:
    data = payload()
    data["policy"]["hidden"] = 1
    for invalid in (data, [], None, "mesh"):
        with pytest.raises(MeshValidationError):
            decode_request(invalid)


def test_actual_request_serialization_byte_limit_is_enforced() -> None:
    data = payload()
    # A valid bounded request ID with 128 astral code points remains accepted.
    data["request_id"] = "😀" * 128
    assert decode_request(data)
    data["padding"] = "x" * 1048576
    with pytest.raises(MeshValidationError):
        decode_request(data)


def test_frozen_corpus_and_exact_max_serialization_vectors() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    assert len(manifest["cases"]) >= 10
    for case in manifest["cases"] + [manifest["result_vector"]]:
        assert hashlib.sha256((FIXTURES / case["path"]).read_bytes()).hexdigest() == case["sha256"]
    maximum = decode_request(json.loads((FIXTURES / "cases/exact-max-torus.json").read_text()))
    assert len(maximum.vertices) == 2000
    assert len(maximum.faces) == 4000
    assert len(maximum.seam_edges) == 6000
    assert len(request_json(maximum).encode()) <= 1048576
    result = json.loads((FIXTURES / "worst-case-result.json").read_text())
    assert len(result["vertices_2d"]) == 12000
    assert len(result["faces_2d"]) == 4000
    assert (
        len(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
        <= 4194304
    )


def test_decode_and_normalize_can_share_cooperative_work_budget() -> None:
    from autocad_mcp.advanced.bounds import (
        BoundedExecutionInterrupted,
        BoundedExecutionPolicy,
        WorkBudget,
    )

    class Probe:
        calls = 0

        def is_cancelled(self) -> bool:
            self.calls += 1
            return self.calls >= 3

    budget = WorkBudget(BoundedExecutionPolicy(200000, 1000000, 30, 1, 0), cancellation=Probe())
    with pytest.raises(BoundedExecutionInterrupted):
        decode_request(payload(), budget=budget)


def test_deeply_nested_coordinate_returns_redacted_invalid_argument() -> None:
    data = payload()
    coordinate: object = "private-coordinate-value"
    for _ in range(2000):
        coordinate = [coordinate]
    data["vertices"][0]["point"][0] = coordinate

    with pytest.raises(MeshValidationError) as caught:
        decode_request(data)

    assert caught.value.code == "INVALID_ARGUMENT"
    assert "private-coordinate-value" not in str(caught.value)
