"""Frozen corpus evaluation and deterministic public end-to-end unfolding."""

import json
import random
from dataclasses import asdict
from decimal import localcontext
from pathlib import Path

import pytest
from autocad_mcp.advanced.bounds import BoundedExecutionFailure, BoundedExecutionPolicy, WorkBudget
from autocad_mcp.advanced.unfolding.metrics import verify_layout
from autocad_mcp.advanced.unfolding.models import UnfoldingLayout, decode_request
from autocad_mcp.advanced.unfolding.solver import solve_layout
from autocad_mcp.advanced.unfolding.validation import ValidatedMesh, validate_mesh

from tests.unit.advanced.unfolding.test_solver import accepted, solve

FIXTURES = Path(__file__).parents[3] / "fixtures" / "unfolding"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


@pytest.mark.parametrize(
    "case", [c for c in MANIFEST["cases"] if c["accepted"]], ids=lambda c: c["name"]
)
def test_every_accepted_source_corpus_passes_independent_verifier(case: dict) -> None:
    payload = json.loads((FIXTURES / case["path"]).read_text())
    mesh = validate_mesh(decode_request(payload))
    assert isinstance(mesh, ValidatedMesh)
    accepted(mesh, solve(mesh))


def test_decode_validate_solve_verify_uses_one_budget_without_reset() -> None:
    payload = json.loads((FIXTURES / "cases/branched-strip.json").read_text())
    policy = BoundedExecutionPolicy(**payload["policy"])
    budget = WorkBudget(policy)
    request = decode_request(payload, budget=budget)
    decoded_work = budget.completed_iterations
    mesh = validate_mesh(request, budget=budget)
    assert isinstance(mesh, ValidatedMesh)
    validated_work = budget.completed_iterations
    layout = solve_layout(mesh, budget=budget)
    assert isinstance(layout, UnfoldingLayout)
    solved_work = budget.completed_iterations
    checked = verify_layout(mesh, layout, budget=budget)
    assert not isinstance(checked, BoundedExecutionFailure) and checked.accepted
    assert 0 < decoded_work < validated_work < solved_work < budget.completed_iterations


def test_shuffled_input_and_repeated_runs_have_identical_layout_bytes() -> None:
    payload = json.loads((FIXTURES / "cases/cylinder-prism.json").read_text())
    canonical = validate_mesh(decode_request(payload))
    assert isinstance(canonical, ValidatedMesh)
    expected = json.dumps(asdict(solve(canonical)), sort_keys=True, separators=(",", ":"))
    randomizer = random.Random(9041)  # noqa: S311 - fixed seed for deterministic input shuffles
    for _ in range(5):
        for field in ("vertices", "faces", "seam_edges"):
            randomizer.shuffle(payload[field])
        mesh = validate_mesh(decode_request(payload))
        assert isinstance(mesh, ValidatedMesh)
        candidate = solve(mesh)
        assert json.dumps(asdict(candidate), sort_keys=True, separators=(",", ":")) == expected
        accepted(mesh, candidate)


def test_solver_arithmetic_does_not_depend_on_callers_decimal_context() -> None:
    payload = json.loads((FIXTURES / "cases/frustum.json").read_text())
    mesh = validate_mesh(decode_request(payload))
    assert isinstance(mesh, ValidatedMesh)
    original = solve(mesh)
    with localcontext() as context:
        context.prec = 5
        context.Emin, context.Emax = -10, 10
        assert solve(mesh) == original
