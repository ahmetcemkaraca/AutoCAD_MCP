"""Pure orchestration never releases unverified/partial data or resets its work budget."""

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from autocad_mcp.advanced.bounds import BoundedExecutionFailure, BoundedFailureCode
from autocad_mcp.advanced.unfolding import service
from autocad_mcp.advanced.unfolding.models import (
    LayoutVerification,
    MeshValidationError,
    UnfoldingIssue,
    UnfoldingResult,
    decode_request,
    request_json,
)

FIXTURES = Path(__file__).parents[3] / "fixtures/unfolding/cases"


def test_service_import_adds_no_host_transport_or_process_dependencies():
    script = """
import sys
import autocad_mcp
before = set(sys.modules)
import autocad_mcp.advanced.unfolding.service
added = set(sys.modules) - before
forbidden = ('mcp', 'autocad_mcp.core', 'autocad_mcp.context',
             'autocad_mcp.adapters', 'pythoncom', 'win32com', 'pyautocad',
             'subprocess', 'socket')
assert not {name for name in added
            if any(name == prefix or name.startswith(prefix + '.')
                   for prefix in forbidden)}, sorted(added)
"""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and literal import probe
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def payload(name="planar-grid"):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def test_deterministic_complete_result_and_exact_canonical_input_hash():
    data = payload()
    result = service.unfold_surface(data)
    assert isinstance(result, UnfoldingResult)
    assert (
        result.input_digest
        == hashlib.sha256(request_json(decode_request(data)).encode()).hexdigest()
    )
    assert result.warnings == result.issues == ()
    assert result.solver_version == "rigid-triangle-unfolding-v1"
    assert result.verifier_version == "rigid-triangle-verifier-v1"
    again = service.unfold_surface(data)
    assert service.result_payload(result) == service.result_payload(again)
    assert json.loads(json.dumps(service.result_payload(result))) == service.result_payload(result)
    assert "elapsed" not in repr(service.result_payload(result))
    reordered = dict(data, vertices=data["vertices"][::-1], faces=data["faces"][::-1])
    assert service.result_payload(service.unfold_surface(reordered)) == service.result_payload(
        result
    )


@pytest.mark.parametrize("change", ["unknown", "bad-policy", "invalid-face", "missing-policy"])
def test_invalid_input_fails_before_solver_without_private_message(monkeypatch, change):
    data = payload()
    if change == "unknown":
        data["private-drawing-facts"] = "private-data"
    elif change == "bad-policy":
        data["policy"]["max_iterations"] = True
    elif change == "invalid-face":
        data["faces"][0]["vertex_ids"] = [0, 0, 0]
    else:
        del data["policy"]
    calls = []
    monkeypatch.setattr(service, "solve_layout", lambda *args, **kwargs: calls.append(1))
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(data)
    assert not calls and "private" not in str(error.value)


def test_single_shared_budget_through_every_stage(monkeypatch):
    seen = []
    for name in (
        "decode_request",
        "validate_mesh",
        "solve_layout",
        "verify_layout",
        "_digest",
        "_result_payload",
    ):
        original = getattr(service, name)

        def wrapped(*args, _original=original, _name=name, **kwargs):
            budget = kwargs.get("budget")
            if budget is not None:
                seen.append((_name, budget, budget.completed_iterations))
            return _original(*args, **kwargs)

        monkeypatch.setattr(service, name, wrapped)
    assert isinstance(service.unfold_surface(payload()), UnfoldingResult)
    assert len({id(budget) for _, budget, _ in seen}) == 1
    assert {name for name, _, _ in seen} == {
        "decode_request",
        "validate_mesh",
        "solve_layout",
        "verify_layout",
        "_digest",
        "_result_payload",
    }
    assert [work for _, _, work in seen] == sorted(work for _, _, work in seen)


def test_verifier_rejection_is_bounded_error_with_no_candidate_or_digest(monkeypatch):
    issue = UnfoldingIssue("OVERLAP", (0, 1), "Output triangles overlap")
    monkeypatch.setattr(
        service, "verify_layout", lambda *args, **kwargs: LayoutVerification(False, None, (issue,))
    )
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(payload())
    assert error.value.code == "VERIFICATION_FAILED" and error.value.issues == (issue,)
    assert not hasattr(error.value, "vertices_2d") and not hasattr(error.value, "input_digest")
    with pytest.raises(MeshValidationError):
        service.unfold_surface(
            payload("branched-strip") | {"policy": dict(payload()["policy"], max_iterations=2)}
        )


@pytest.mark.parametrize(
    "stage",
    [
        "decode_request",
        "validate_mesh",
        "solve_layout",
        "verify_layout",
        "_digest",
        "_result_payload",
    ],
)
@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_interruptions_at_every_stage_release_only_failure(monkeypatch, stage, cause):
    state = SimpleNamespace(cancelled=False, now=0.0)
    original = getattr(service, stage)

    def interrupt(*args, **kwargs):
        state.cancelled = cause == "cancelled"
        state.now = 31.0 if cause == "deadline" else 0.0
        return original(*args, **kwargs)

    monkeypatch.setattr(service, stage, interrupt)
    result = service.unfold_surface(
        payload(),
        clock=SimpleNamespace(now=lambda: state.now),
        cancellation=SimpleNamespace(is_cancelled=lambda: state.cancelled),
    )
    assert isinstance(result, BoundedExecutionFailure)
    assert result.code == (
        BoundedFailureCode.CANCELLED
        if cause == "cancelled"
        else BoundedFailureCode.DEADLINE_EXCEEDED
    )
    assert set(service.result_payload(result)) == {"code", "completed_iterations", "message"}
    assert not hasattr(result, "input_digest") and not hasattr(result, "vertices_2d")


def test_actual_full_result_exact_utf8_size_and_one_byte_over(monkeypatch):
    data = payload()
    data["units_label"] = "μm"
    result = service.unfold_surface(data)
    measured = len(
        json.dumps(
            asdict(result),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode()
    )
    monkeypatch.setattr(service, "MAX_ADVANCED_RESULT_BYTES", measured)
    assert service.unfold_surface(data) == result
    monkeypatch.setattr(service, "MAX_ADVANCED_RESULT_BYTES", measured - 1)
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(data)
    assert error.value.code == "RESOURCE_LIMIT"


def test_saddle_candidate_rejection_is_not_a_success():
    from tests.unit.advanced.unfolding.test_metrics import seam_fan

    mesh, _ = seam_fan(saddle=True)
    data = json.loads(request_json(mesh.request))
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(data)
    assert error.value.code == "VERIFICATION_FAILED"
    assert any(issue.code == "OVERLAP" for issue in error.value.issues)


def test_maximum_mesh_complete_service_under_same_unchanged_budget(monkeypatch):
    totals = []
    original = service.WorkBudget

    def record_budget(*args, **kwargs):
        budget = original(*args, **kwargs)
        totals.append(budget)
        return budget

    monkeypatch.setattr(service, "WorkBudget", record_budget)
    result = service.unfold_surface(
        payload("exact-max-torus"), clock=SimpleNamespace(now=lambda: 0.0)
    )
    assert isinstance(result, UnfoldingResult)
    assert len(totals) == 1 and totals[0].policy.max_iterations == 1000000
    assert totals[0].completed_iterations < 1000000
    assert len(result.faces_2d) == 4000 and result.metrics.island_count == 4000
    assert result.metrics.overlap_pair_count == 0
    assert result.metrics.max_relative_edge_error <= 1e-9
    assert result.metrics.max_relative_area_error <= 1e-9
    assert result.metrics.max_angle_error_radians <= 1e-9
    assert (
        len(json.dumps(service.result_payload(result), ensure_ascii=False).encode()) <= 4 * 1024**2
    )


@pytest.mark.parametrize("cause", ["cancelled", "deadline"])
def test_interruption_when_initializing_budget_has_no_partial_work(cause):
    times = iter((0.0, 31.0))
    result = service.unfold_surface(
        payload(),
        clock=SimpleNamespace(now=(lambda: next(times)) if cause == "deadline" else lambda: 0.0),
        cancellation=SimpleNamespace(is_cancelled=lambda: cause == "cancelled"),
    )
    assert isinstance(result, BoundedExecutionFailure)
    assert result.completed_iterations == 0
    assert not hasattr(result, "input_digest")


@pytest.mark.parametrize(
    "issues",
    [
        tuple(UnfoldingIssue("FAIL", (), "fixed") for _ in range(1001)),
        (UnfoldingIssue("FAIL", (0, 1, 2), "fixed"),),
        (UnfoldingIssue("FAIL", (), "private\x00text"),),
    ],
)
def test_rejection_diagnostics_are_bounded_and_redacted(monkeypatch, issues):
    monkeypatch.setattr(
        service, "verify_layout", lambda *args, **kwargs: LayoutVerification(False, None, issues)
    )
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(payload())
    assert error.value.code in ("RESOURCE_LIMIT", "INVALID_ARGUMENT")
    assert "private" not in str(error.value)
    assert not error.value.issues


def test_payload_copies_and_no_success_without_metrics(monkeypatch):
    result = service.unfold_surface(payload())
    mutable = service.result_payload(result)
    mutable["vertices_2d"].clear()
    assert result.vertices_2d and service.result_payload(result)["vertices_2d"]
    monkeypatch.setattr(
        service, "verify_layout", lambda *args, **kwargs: LayoutVerification(True, None, ())
    )
    with pytest.raises(MeshValidationError) as error:
        service.unfold_surface(payload())
    assert error.value.code == "VERIFICATION_FAILED"


def test_policy_helper_and_error_issue_count_bounds():
    from autocad_mcp.advanced.unfolding.models import decode_policy

    assert asdict(decode_policy(payload()["policy"])) == payload()["policy"]
    with pytest.raises(MeshValidationError):
        decode_policy(dict(payload()["policy"], extra=1))
    with pytest.raises(MeshValidationError):
        MeshValidationError(
            "FAIL", "fixed", issues=tuple(UnfoldingIssue("FAIL", (), "fixed") for _ in range(1001))
        )
