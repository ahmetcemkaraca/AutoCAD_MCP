"""Solver resource and interruption failures never contain a partial chart."""

import json
import math
from dataclasses import asdict, replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from autocad_mcp.advanced.bounds import BoundedExecutionFailure, BoundedFailureCode, WorkBudget
from autocad_mcp.advanced.unfolding import solver
from autocad_mcp.advanced.unfolding.models import MeshValidationError, UnfoldingLayout
from autocad_mcp.advanced.unfolding.solver import solve_layout

from tests.unit.advanced.unfolding.test_solver import POLICY, mesh_from, square_mesh


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_interruption_mid_solve_keeps_original_shared_counter_and_only_failure(cause: str) -> None:
    mesh = square_mesh(cut=True)
    state = SimpleNamespace(calls=0, time=0.0)

    def cancelled() -> bool:
        state.calls += 1
        return cause == "cancelled" and state.calls >= 12

    def now() -> float:
        state.time += 0.01 if cause == "deadline" else 0.0
        return float(state.time)

    budget = WorkBudget(
        replace(POLICY, cancellation_check_interval=1, deadline_seconds=0.11),
        clock=SimpleNamespace(now=now),
        cancellation=SimpleNamespace(is_cancelled=cancelled),
    )
    budget.checkpoint(2)
    result = solve_layout(mesh, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
    assert result.completed_iterations > 2
    assert not hasattr(result, "vertices_2d") and not hasattr(result, "input_digest")


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_completion_checks_pending_interruption_even_below_check_interval(cause: str) -> None:
    mesh = square_mesh()
    state = SimpleNamespace(calls=0, time=0.0)

    def now() -> float:
        state.calls += 1
        if state.calls >= 3 and cause == "deadline":
            state.time = 31.0
        return float(state.time)

    def cancelled() -> bool:
        return cause == "cancelled" and state.calls >= 2

    budget = WorkBudget(
        POLICY, clock=SimpleNamespace(now=now), cancellation=SimpleNamespace(is_cancelled=cancelled)
    )
    result = solve_layout(mesh, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )


@pytest.mark.parametrize("limit", ["items", "work"])
def test_fixed_limits_raise_redacted_resource_failure(limit: str) -> None:
    mesh = square_mesh(cut=True)
    policy = replace(POLICY, max_items=1) if limit == "items" else replace(POLICY, max_iterations=2)
    with pytest.raises(MeshValidationError) as error:
        solve_layout(mesh, budget=WorkBudget(policy))
    assert error.value.code == "RESOURCE_LIMIT"
    assert "solver-check" not in str(error.value)


@pytest.mark.parametrize("shape", ["root-length", "strip-gap"])
def test_unrepresentable_geometry_fails_without_clamping(shape: str) -> None:
    mesh = (
        mesh_from(((-1e308, 0.0, 0.0), (1e308, 0.0, 0.0), (0.0, 1.0, 0.0)))
        if shape == "root-length"
        else square_mesh(cut=True, scale=math.ulp(0.0))
    )
    with pytest.raises(MeshValidationError) as error:
        solve_layout(mesh, budget=WorkBudget(POLICY))
    assert error.value.code == "NUMERICAL_FAILURE"
    assert "vertices" not in vars(error.value) and not hasattr(error.value, "input_digest")


def test_strip_translation_rejects_a_small_chart_collapsed_at_large_global_x() -> None:
    mesh = mesh_from(
        ((0.0, 0.0, 0.0), (1e300, 0.0, 0.0), (1e300, 1e-300, 0.0), (1e300, 0.0, 1e-300)),
        ((10, (0, 1, 2)), (20, (2, 1, 3))),
        seams=((1, 2),),
    )
    with pytest.raises(MeshValidationError) as error:
        solve_layout(mesh, budget=WorkBudget(POLICY))
    assert error.value.code == "NUMERICAL_FAILURE"


def test_exact_candidate_item_boundary_and_one_item_over() -> None:
    mesh = square_mesh(cut=True)
    assert not isinstance(
        solve_layout(mesh, budget=WorkBudget(replace(POLICY, max_items=9))), BoundedExecutionFailure
    )
    with pytest.raises(MeshValidationError) as error:
        solve_layout(mesh, budget=WorkBudget(replace(POLICY, max_items=8)))
    assert error.value.code == "RESOURCE_LIMIT"


def test_exact_candidate_byte_boundary_and_one_byte_over(monkeypatch: pytest.MonkeyPatch) -> None:
    mesh = square_mesh()
    candidate = solve_layout(mesh, budget=WorkBudget(POLICY))
    assert not isinstance(candidate, BoundedExecutionFailure)
    size = len(json.dumps(asdict(candidate), sort_keys=True, separators=(",", ":")).encode())
    monkeypatch.setattr(solver, "MAX_ADVANCED_RESULT_BYTES", size)
    assert solve_layout(mesh, budget=WorkBudget(POLICY)) == candidate
    monkeypatch.setattr(solver, "MAX_ADVANCED_RESULT_BYTES", size - 1)
    with pytest.raises(MeshValidationError) as error:
        solve_layout(mesh, budget=WorkBudget(POLICY))
    assert error.value.code == "RESOURCE_LIMIT"


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_pending_interruption_wins_over_early_byte_failure(
    monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    mesh = square_mesh()
    state = SimpleNamespace(cancelled=False, time=0.0)
    budget = WorkBudget(
        POLICY,
        clock=SimpleNamespace(now=lambda: state.time),
        cancellation=SimpleNamespace(is_cancelled=lambda: state.cancelled),
    )
    original = solver._bytes

    def interrupted_bytes(layout: UnfoldingLayout, shared_budget: WorkBudget) -> None:
        state.cancelled = cause == "cancelled"
        state.time = 31.0 if cause == "deadline" else 0.0
        original(layout, shared_budget)

    monkeypatch.setattr(solver, "MAX_ADVANCED_RESULT_BYTES", 64)
    monkeypatch.setattr(solver, "_bytes", interrupted_bytes)
    result = solve_layout(mesh, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )


def test_bounded_record_encoding_uses_small_shared_work_without_punctuation_charges() -> None:
    # Each bounded vertex/face/cut is one serialization work item; JSON punctuation
    # is part of the fixed-size native encoding of that item.
    candidate = solve_layout(square_mesh(), budget=WorkBudget(replace(POLICY, max_iterations=80)))
    assert isinstance(candidate, UnfoldingLayout)


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_pending_interruption_wins_over_a_real_unrepresentable_root(
    monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    mesh = mesh_from(((-1e308, 0.0, 0.0), (1e308, 0.0, 0.0), (0.0, 1.0, 0.0)))
    state = SimpleNamespace(cancelled=False, time=0.0)
    budget = WorkBudget(
        POLICY,
        clock=SimpleNamespace(now=lambda: state.time),
        cancellation=SimpleNamespace(is_cancelled=lambda: state.cancelled),
    )
    original = solver._frame

    def interrupted_frame(
        a: solver.SourcePoint, b: solver.SourcePoint, c: solver.SourcePoint
    ) -> tuple[Decimal, Decimal, Decimal]:
        frame = original(a, b, c)
        state.cancelled = cause == "cancelled"
        state.time = 31.0 if cause == "deadline" else 0.0
        return frame

    monkeypatch.setattr(solver, "_frame", interrupted_frame)
    result = solve_layout(mesh, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
