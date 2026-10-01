"""Exact result bytes and one-budget acceptance at the frozen mesh maximum."""

import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedExecutionPolicy,
    BoundedFailureCode,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding import metrics
from autocad_mcp.advanced.unfolding.metrics import verify_layout
from autocad_mcp.advanced.unfolding.models import (
    UnfoldingIssue,
    UnfoldingLayout,
    UnfoldingMetrics,
    decode_request,
)
from autocad_mcp.advanced.unfolding.solver import solve_layout
from autocad_mcp.advanced.unfolding.validation import ValidatedMesh, validate_mesh

from tests.unit.advanced.unfolding.test_metrics import POLICY, square, triangle


def full_result_bytes(
    mesh: ValidatedMesh,
    layout: UnfoldingLayout,
    measured: UnfoldingMetrics | None = None,
    issues: tuple[UnfoldingIssue, ...] = (),
) -> int:
    """Independent whole-payload serialization, without verifier byte helpers."""
    payload = asdict(layout)
    payload.update(
        request_id=mesh.request.request_id,
        input_digest="0" * 64,
        units_label=mesh.request.units_label,
        verifier_version=metrics.VERIFIER_VERSION,
        metrics=None if measured is None else asdict(measured),
        warnings=(),
        issues=tuple(asdict(issue) for issue in issues),
    )
    return len(
        json.dumps(
            payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


@pytest.mark.parametrize("with_metrics", [False, True])
@pytest.mark.parametrize("with_issues", [False, True])
def test_record_byte_bound_matches_full_utf8_json_at_exact_boundary(
    monkeypatch: pytest.MonkeyPatch, with_metrics: bool, with_issues: bool
) -> None:
    mesh, layout = square(cut=True)
    mesh = replace(
        mesh, request=replace(mesh.request, request_id='réf "\\📐', units_label='µm "\\')
    )
    layout = replace(layout, solver_version='version-"\\é')
    measured = UnfoldingMetrics(1e-12, 2e-12, 3e-12, 0, 2) if with_metrics else None
    issues = (
        UnfoldingIssue("DISTORTION", (10, 20), 'Escaped "\\\n and Unicode é📐'),
        UnfoldingIssue("NUMERICAL_FAILURE", (20,), "Second diagnostic"),
    ) if with_issues else ()
    geometry_bytes = metrics._serialized_bound(mesh, layout, WorkBudget(POLICY))
    exact = full_result_bytes(mesh, layout, measured, issues)
    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", exact)
    assert metrics._serialized_bound(
        mesh, layout, WorkBudget(POLICY), measured, issues
    ) == geometry_bytes
    # Final metadata/metrics/diagnostics measurement must not rescan geometry.
    budget = WorkBudget(replace(POLICY, max_iterations=1 + len(issues)))
    assert metrics._serialized_bound(
        mesh, layout, budget, measured, issues, geometry_bytes=geometry_bytes
    ) == geometry_bytes
    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", exact - 1)
    with pytest.raises(metrics._LayoutRejectedError) as error:
        metrics._serialized_bound(
            mesh, layout, WorkBudget(POLICY), measured, issues, geometry_bytes=geometry_bytes
        )
    assert error.value.issue.code == "RESOURCE_LIMIT"


@pytest.mark.parametrize("distorted", [False, True])
def test_public_final_byte_bound_preserves_metrics_or_diagnostics(
    monkeypatch: pytest.MonkeyPatch, distorted: bool
) -> None:
    mesh, layout = triangle()
    if distorted:
        layout = replace(
            layout,
            vertices_2d=tuple(
                replace(
                    vertex, point_2d=(vertex.point_2d[0] * 1.01, vertex.point_2d[1] * 1.01)
                )
                for vertex in layout.vertices_2d
            ),
        )
    reference = verify_layout(mesh, layout, budget=WorkBudget(POLICY))
    assert not isinstance(reference, BoundedExecutionFailure)
    assert reference.accepted is not distorted
    exact = full_result_bytes(mesh, layout, reference.metrics, reference.issues)
    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", exact)
    assert verify_layout(mesh, layout, budget=WorkBudget(POLICY)) == reference
    monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", exact - 1)
    result = verify_layout(mesh, layout, budget=WorkBudget(POLICY))
    assert not isinstance(result, BoundedExecutionFailure)
    assert not result.accepted and result.metrics is None
    assert [issue.code for issue in result.issues] == ["RESOURCE_LIMIT"]


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
@pytest.mark.parametrize("byte_failure", [False, True])
def test_pending_interruption_wins_at_cached_final_serialization(
    monkeypatch: pytest.MonkeyPatch, cause: str, byte_failure: bool
) -> None:
    mesh, layout = triangle()
    state = SimpleNamespace(cancelled=False, time=0.0)
    budget = WorkBudget(
        POLICY,
        clock=SimpleNamespace(now=lambda: state.time),
        cancellation=SimpleNamespace(is_cancelled=lambda: state.cancelled),
    )
    original = metrics._serialized_bound

    def interrupted_final(
        source: ValidatedMesh,
        candidate: UnfoldingLayout,
        shared_budget: WorkBudget,
        measured: UnfoldingMetrics | None = None,
        issues: tuple[UnfoldingIssue, ...] = (),
        *,
        geometry_bytes: int | None = None,
    ) -> int:
        if measured is not None:
            state.cancelled = cause == "cancelled"
            state.time = 31.0 if cause == "deadline" else 0.0
            if byte_failure:
                monkeypatch.setattr(metrics, "MAX_ADVANCED_RESULT_BYTES", 1)
        return original(
            source, candidate, shared_budget, measured, issues, geometry_bytes=geometry_bytes
        )

    monkeypatch.setattr(metrics, "_serialized_bound", interrupted_final)
    result = verify_layout(mesh, layout, budget=budget)
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
    assert not hasattr(result, "metrics") and not hasattr(result, "vertices_2d")


def test_exact_max_public_pipeline_accepts_with_one_unchanged_budget() -> None:
    path = Path(__file__).parents[3] / "fixtures/unfolding/cases/exact-max-torus.json"
    payload = json.loads(path.read_text())
    policy = BoundedExecutionPolicy(**payload["policy"])
    # Isolate fixed work; real host deadline/performance evidence belongs to Task 4.
    budget = WorkBudget(policy, clock=SimpleNamespace(now=lambda: 0.0))
    request = decode_request(payload, budget=budget)
    decoded = budget.completed_iterations
    mesh = validate_mesh(request, budget=budget)
    assert isinstance(mesh, ValidatedMesh)
    validated = budget.completed_iterations
    layout = solve_layout(mesh, budget=budget)
    assert isinstance(layout, UnfoldingLayout)
    solved = budget.completed_iterations
    checked = verify_layout(mesh, layout, budget=budget)
    assert not isinstance(checked, BoundedExecutionFailure)
    assert checked.accepted, checked.issues
    assert checked.metrics is not None and not checked.issues
    assert checked.metrics.max_relative_edge_error <= 1e-9
    assert checked.metrics.max_relative_area_error <= 1e-9
    assert checked.metrics.max_angle_error_radians <= 1e-9
    assert checked.metrics.overlap_pair_count == 0 and checked.metrics.island_count == 4000
    assert 0 < decoded < validated < solved < budget.completed_iterations <= policy.max_iterations
    assert budget.policy is policy
