"""Mathematical support rules and immutable adjacency precede any solving."""

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedExecutionPolicy,
    BoundedFailureCode,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding.models import MeshValidationError, decode_request
from autocad_mcp.advanced.unfolding.validation import validate_mesh

FIXTURES = Path(__file__).parents[3] / "fixtures" / "unfolding"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


@pytest.mark.parametrize(
    "case",
    [c for c in MANIFEST["cases"] if c["name"] != "exact-max-torus"],
    ids=lambda c: c["name"],
)
def test_frozen_mathematical_classifications(case: dict) -> None:
    data = json.loads((FIXTURES / case["path"]).read_text())
    if case["accepted"]:
        assert not isinstance(validate_mesh(decode_request(data)), BoundedExecutionFailure)
    else:
        with pytest.raises(MeshValidationError):
            validate_mesh(decode_request(data))


def test_canonical_immutable_edges_adjacency_and_islands() -> None:
    request = decode_request(json.loads((FIXTURES / "cases/planar-grid.json").read_text()))
    mesh = validate_mesh(request)
    assert not isinstance(mesh, BoundedExecutionFailure)
    assert mesh.adjacency == ((0, (1,)), (1, (0,)))
    assert mesh.islands == ((0, 1),)
    assert [(edge.vertex_ids, edge.face_ids) for edge in mesh.edges] == [
        ((0, 1), (0,)),
        ((0, 2), (0, 1)),
        ((0, 3), (1,)),
        ((1, 2), (0,)),
        ((2, 3), (1,)),
    ]
    with pytest.raises(FrozenInstanceError):
        mesh.edges = ()  # type: ignore[misc]
    cut = validate_mesh(replace(request, seam_edges=((0, 2),)))
    assert not isinstance(cut, BoundedExecutionFailure)
    assert cut.adjacency == ((0, ()), (1, ()))
    assert cut.islands == ((0,), (1,))


@pytest.mark.parametrize(
    "change",
    [
        "unknown-vertex",
        "root",
        "unknown-seam",
        "duplicate-seam",
        "repeated-corner",
        "unused-vertex",
    ],
)
def test_bad_incidence_rejects(change: str) -> None:
    data = json.loads((FIXTURES / "cases/planar-grid.json").read_text())
    if change == "unknown-vertex":
        data["faces"][0]["vertex_ids"][0] = 99
    elif change == "root":
        data["root_face_id"] = 99
    elif change == "unknown-seam":
        data["seam_edges"] = [[1, 3]]
    elif change == "duplicate-seam":
        data["seam_edges"] = [[0, 2], [2, 0]]
    elif change == "repeated-corner":
        data["faces"][0]["vertex_ids"] = [0, 0, 2]
    else:
        data["vertices"].append({"vertex_id": 9, "point": [9, 9, 9]})
    with pytest.raises(MeshValidationError):
        validate_mesh(decode_request(data))


class AdvancingClock:
    value = 0.0

    def now(self) -> float:
        self.value += 0.01
        return self.value


class CancellingProbe:
    calls = 0

    def is_cancelled(self) -> bool:
        self.calls += 1
        return self.calls >= 4


@pytest.mark.parametrize("cause", ["deadline", "cancelled"])
def test_interrupting_validation_returns_only_typed_failure(cause: str) -> None:
    request = decode_request(json.loads((FIXTURES / "cases/exact-max-torus.json").read_text()))
    request = replace(request, policy=BoundedExecutionPolicy(200000, 1000000, 0.1, 2, 9041))
    budget = WorkBudget(
        request.policy,
        clock=AdvancingClock(),
        cancellation=CancellingProbe() if cause == "cancelled" else None,
    )
    result = validate_mesh(request, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
    assert result.completed_iterations > 0
    assert not hasattr(result, "input_digest")


def test_non_coplanar_triangle_crossing_is_rejected() -> None:
    data = json.loads((FIXTURES / "cases/planar-grid.json").read_text())
    data["vertices"] = [
        {"vertex_id": i, "point": point}
        for i, point in enumerate([[-1, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, -1], [0, 0, 1]])
    ]
    data["faces"] = [
        {"face_id": i, "vertex_ids": ids} for i, ids in enumerate([[0, 1, 2], [1, 0, 3], [3, 0, 4]])
    ]
    with pytest.raises(MeshValidationError) as caught:
        validate_mesh(decode_request(data))
    assert caught.value.code == "SELF_INTERSECTION"


def test_vertex_only_contact_on_folded_manifold_is_legitimate() -> None:
    data = json.loads((FIXTURES / "cases/planar-grid.json").read_text())
    data["vertices"] = [
        {"vertex_id": i, "point": point}
        for i, point in enumerate([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 1], [-1, 1, 1]])
    ]
    data["faces"] = [
        {"face_id": i, "vertex_ids": ids} for i, ids in enumerate([[0, 1, 2], [0, 2, 3], [0, 3, 4]])
    ]
    assert not isinstance(validate_mesh(decode_request(data)), BoundedExecutionFailure)


def test_exact_max_mesh_passes_with_a_shared_fixed_budget() -> None:
    request = decode_request(json.loads((FIXTURES / "cases/exact-max-torus.json").read_text()))
    budget = WorkBudget(request.policy)
    result = validate_mesh(request, budget=budget)
    assert not isinstance(result, BoundedExecutionFailure)
    assert len(result.islands) == 4000
    assert budget.completed_iterations < 500000
