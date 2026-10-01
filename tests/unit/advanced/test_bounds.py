"""Cooperative limits reject excess work without clamping or partial outputs."""

from dataclasses import FrozenInstanceError

import pytest
from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    BoundedExecutionPolicy,
    BoundedFailureCode,
    WorkBudget,
    check_serialized_size,
)


class Clock:
    value = 0.0

    def now(self) -> float:
        return self.value


class Cancellation:
    cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled


def policy(**changes: object) -> BoundedExecutionPolicy:
    return BoundedExecutionPolicy(
        **dict(
            max_items=200000,
            max_iterations=1000000,
            deadline_seconds=30.0,
            cancellation_check_interval=1024,
            deterministic_seed=9041,
            **changes,
        )
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_items", 0),
        ("max_items", 200001),
        ("max_items", True),
        ("max_iterations", 1000001),
        ("max_iterations", 1.0),
        ("deadline_seconds", 0),
        ("deadline_seconds", 30.001),
        ("deadline_seconds", float("nan")),
        ("deadline_seconds", True),
        ("cancellation_check_interval", 1025),
        ("cancellation_check_interval", 0),
        ("deterministic_seed", True),
        ("deterministic_seed", -1),
        ("deterministic_seed", 2**53),
    ],
)
def test_policy_rejects_invalid_values_without_clamping(field: str, value: object) -> None:
    values = {
        "max_items": 200000,
        "max_iterations": 1000000,
        "deadline_seconds": 30.0,
        "cancellation_check_interval": 1024,
        "deterministic_seed": 9041,
    }
    values[field] = value
    with pytest.raises(ValueError):
        BoundedExecutionPolicy(**values)


def test_exact_policy_ceiling_and_immutable_failure() -> None:
    request_policy = policy()
    with pytest.raises(FrozenInstanceError):
        request_policy.max_items = 1  # type: ignore[misc]
    failure = BoundedExecutionFailure(BoundedFailureCode.CANCELLED, 0, "Cancelled")
    with pytest.raises(FrozenInstanceError):
        failure.message = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("cause", ["deadline", "cancelled"])
def test_budget_checks_initial_state_and_requested_interval(cause: str) -> None:
    clock, cancellation = Clock(), Cancellation()
    request_policy = BoundedExecutionPolicy(10, 10, 1.0, 2, 0)
    budget = WorkBudget(request_policy, clock=clock, cancellation=cancellation)
    budget.checkpoint()
    if cause == "deadline":
        clock.value = 1.0
    else:
        cancellation.cancelled = True
    with pytest.raises(BoundedExecutionInterrupted) as caught:
        budget.checkpoint()
    assert caught.value.failure.completed_iterations == 2
    assert caught.value.failure.code == (
        BoundedFailureCode.DEADLINE_EXCEEDED
        if cause == "deadline"
        else BoundedFailureCode.CANCELLED
    )
    assert not hasattr(caught.value.failure, "vertices_2d")


def test_budget_stops_before_first_work_when_cancelled() -> None:
    cancellation = Cancellation()
    cancellation.cancelled = True
    with pytest.raises(BoundedExecutionInterrupted) as caught:
        WorkBudget(policy(), clock=Clock(), cancellation=cancellation)
    assert caught.value.failure.completed_iterations == 0


def test_fixed_iteration_exhaustion_is_distinct_from_clock_failure() -> None:
    budget = WorkBudget(BoundedExecutionPolicy(10, 2, 30, 1, 0), clock=Clock())
    budget.checkpoint()
    budget.checkpoint()
    with pytest.raises(ValueError, match="iteration"):
        budget.checkpoint()
    assert budget.completed_iterations == 2


@pytest.mark.parametrize("limit", [1048576, 4194304])
def test_exact_byte_boundary_and_one_byte_overflow(limit: int) -> None:
    check_serialized_size(b"x" * limit, limit=limit)
    with pytest.raises(ValueError, match="byte"):
        check_serialized_size(b"x" * (limit + 1), limit=limit)


def test_forced_checkpoint_detects_new_cancellation_without_more_work() -> None:
    cancellation = Cancellation()
    budget = WorkBudget(policy(), clock=Clock(), cancellation=cancellation)
    budget.checkpoint()
    cancellation.cancelled = True
    with pytest.raises(BoundedExecutionInterrupted):
        budget.checkpoint(0)
    assert budget.completed_iterations == 1


def test_extremely_large_integer_deadline_is_structurally_rejected() -> None:
    with pytest.raises(ValueError):
        BoundedExecutionPolicy(1, 1, 10**400, 1, 0)
