"""Cooperative work bounds shared by isolated advanced candidates."""

import math
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol

MAX_ADVANCED_ITEMS: Final = 200_000
MAX_ADVANCED_ITERATIONS: Final = 1_000_000
MAX_ADVANCED_DEADLINE_SECONDS: Final = 30.0
MAX_CANCELLATION_CHECK_INTERVAL: Final = 1_024
MAX_ADVANCED_REQUEST_BYTES: Final = 1 * 1024 * 1024
MAX_ADVANCED_RESULT_BYTES: Final = 4 * 1024 * 1024
MAX_JSON_INTEGER: Final = 2**53 - 1


@dataclass(frozen=True)
class BoundedExecutionPolicy:
    max_items: int
    max_iterations: int
    deadline_seconds: float
    cancellation_check_interval: int
    deterministic_seed: int

    def __post_init__(self) -> None:
        for name, ceiling in (
            ("max_items", MAX_ADVANCED_ITEMS),
            ("max_iterations", MAX_ADVANCED_ITERATIONS),
            ("cancellation_check_interval", MAX_CANCELLATION_CHECK_INTERVAL),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} exceeds its positive limit")
        if (
            type(self.deadline_seconds) not in (int, float)
            or not 0 < self.deadline_seconds <= MAX_ADVANCED_DEADLINE_SECONDS
            or not math.isfinite(self.deadline_seconds)
        ):
            raise ValueError("deadline_seconds exceeds its finite positive limit")
        if (
            type(self.deterministic_seed) is not int
            or not 0 <= self.deterministic_seed <= MAX_JSON_INTEGER
        ):
            raise ValueError("deterministic_seed exceeds its integer limit")


class MonotonicClock(Protocol):
    def now(self) -> float: ...


class CancellationProbe(Protocol):
    def is_cancelled(self) -> bool: ...


class BoundedFailureCode(StrEnum):
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class BoundedExecutionFailure:
    code: BoundedFailureCode
    completed_iterations: int
    message: str


class BoundedExecutionInterrupted(Exception):  # noqa: N818 - interruption carries typed failure
    def __init__(self, failure: BoundedExecutionFailure) -> None:
        self.failure = failure
        super().__init__(failure.message)


class _SystemClock:
    def now(self) -> float:
        return time.monotonic()


class WorkBudget:
    """One mutable work counter shared across validation, solver, and verification."""

    def __init__(
        self,
        policy: BoundedExecutionPolicy,
        *,
        clock: MonotonicClock | None = None,
        cancellation: CancellationProbe | None = None,
    ) -> None:
        self.policy = policy
        self.clock = clock or _SystemClock()
        self.cancellation = cancellation
        self.completed_iterations = 0
        self.started_at = self.clock.now()
        self._since_check = 0
        self._check()

    def _check(self) -> None:
        if self.cancellation is not None and self.cancellation.is_cancelled():
            raise BoundedExecutionInterrupted(
                BoundedExecutionFailure(
                    BoundedFailureCode.CANCELLED, self.completed_iterations, "Work was cancelled"
                )
            )
        if self.clock.now() - self.started_at >= self.policy.deadline_seconds:
            raise BoundedExecutionInterrupted(
                BoundedExecutionFailure(
                    BoundedFailureCode.DEADLINE_EXCEEDED,
                    self.completed_iterations,
                    "Cooperative deadline exceeded",
                )
            )
        self._since_check = 0

    def checkpoint(self, work: int = 1) -> None:
        if type(work) is not int or work < 0:
            raise ValueError("Work must be a nonnegative integer")
        if work == 0:
            self._check()
            return
        if self.completed_iterations + work > self.policy.max_iterations:
            raise ValueError("Fixed iteration limit exceeded")
        # Bulk work must not skip a requested cancellation/deadline checkpoint.
        while work:
            step = min(work, self.policy.cancellation_check_interval - self._since_check)
            self.completed_iterations += step
            self._since_check += step
            work -= step
            if self._since_check == self.policy.cancellation_check_interval:
                self._check()


def check_serialized_size(payload: bytes, *, limit: int) -> None:
    if len(payload) > limit:
        raise ValueError("Serialized byte limit exceeded")
