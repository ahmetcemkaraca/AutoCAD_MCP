"""Pure bounded unfolding orchestration; verified results are the only successful output."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, cast

from autocad_mcp.advanced.bounds import (
    MAX_ADVANCED_RESULT_BYTES,
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    CancellationProbe,
    MonotonicClock,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding.metrics import VERIFIER_VERSION, verify_layout
from autocad_mcp.advanced.unfolding.models import (
    MAX_ISSUE_CODE_CHARACTERS,
    MAX_ISSUE_FACE_IDS,
    MAX_ISSUE_MESSAGE_CHARACTERS,
    MAX_RESULT_ISSUES,
    MeshValidationError,
    UnfoldingIssue,
    UnfoldingRequest,
    UnfoldingResponse,
    UnfoldingResult,
    _integer,
    _payload,
    _text,
    decode_policy,
    decode_request,
)
from autocad_mcp.advanced.unfolding.solver import SOLVER_VERSION, solve_layout
from autocad_mcp.advanced.unfolding.validation import validate_mesh

if TYPE_CHECKING:
    from autocad_mcp.core.models import JsonValue


def _checkpoint(budget: WorkBudget | None) -> None:
    if budget is not None:
        try:
            budget.checkpoint()
        except ValueError:
            raise MeshValidationError(
                "RESOURCE_LIMIT", "Fixed service work limit exceeded"
            ) from None


def _json_value(value: object, budget: WorkBudget | None) -> JsonValue:
    _checkpoint(budget)
    if isinstance(value, Enum):
        return _json_value(value.value, budget)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name), budget) for field in fields(value)
        }
    if type(value) is tuple:
        return [_json_value(item, budget) for item in value]
    if value is None or type(value) in (str, bool, int):
        return cast("JsonValue", value)
    if type(value) is float and math.isfinite(value):
        return value
    raise MeshValidationError("INVALID_ARGUMENT", "Invalid unfolding result value")


def _result_payload(
    result: UnfoldingResponse, *, budget: WorkBudget | None = None
) -> dict[str, JsonValue]:
    if type(result) not in (UnfoldingResult, BoundedExecutionFailure):
        raise MeshValidationError("INVALID_ARGUMENT", "Invalid unfolding response")
    return cast("dict[str, JsonValue]", _json_value(result, budget))


def result_payload(result: UnfoldingResponse) -> dict[str, JsonValue]:
    """Copy a completed pure result/failure into fresh JSON primitives; no MCP envelope."""
    return _result_payload(result)


def _canonical_json(value: object, *, budget: WorkBudget) -> bytes:
    # Collection records are charged while shaping. Native JSON encoding is bounded
    # by admitted records; force checks around the native standard-library operation.
    budget.checkpoint(0)
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise MeshValidationError("INVALID_ARGUMENT", "Unfolding data is not finite JSON") from None
    budget.checkpoint(0)
    return encoded


def _digest(request: UnfoldingRequest, *, budget: WorkBudget) -> str:
    encoded = _canonical_json(_payload(request, budget), budget=budget)
    result = hashlib.sha256(encoded).hexdigest()
    budget.checkpoint(0)
    return result


def _issues(value: tuple[UnfoldingIssue, ...], budget: WorkBudget) -> tuple[UnfoldingIssue, ...]:
    if type(value) is not tuple or len(value) > MAX_RESULT_ISSUES:
        raise MeshValidationError("RESOURCE_LIMIT", "Diagnostic count bound exceeded")
    for issue in value:
        _checkpoint(budget)
        if type(issue) is not UnfoldingIssue or type(issue.face_ids) is not tuple:
            raise MeshValidationError("INVALID_ARGUMENT", "Invalid verification diagnostic")
        _text(issue.code, MAX_ISSUE_CODE_CHARACTERS, "issue code")
        _text(issue.message, MAX_ISSUE_MESSAGE_CHARACTERS, "issue message")
        if len(issue.face_ids) > MAX_ISSUE_FACE_IDS:
            raise MeshValidationError("RESOURCE_LIMIT", "Diagnostic face bound exceeded")
        for face_id in issue.face_ids:
            _integer(face_id, "issue face ID")
    return value


def unfold_surface(  # noqa: C901 - explicit bounded stage/failure sequencing
    payload: object,
    *,
    clock: MonotonicClock | None = None,
    cancellation: CancellationProbe | None = None,
) -> UnfoldingResponse:
    """Use one budget across strict decoding, validation, solve, verification and publication."""
    budget = None
    try:
        if type(payload) is not dict or "policy" not in payload:
            raise MeshValidationError("INVALID_ARGUMENT", "Request requires a bounded policy")
        policy = decode_policy(payload["policy"])
        budget = WorkBudget(policy, clock=clock, cancellation=cancellation)
        request = decode_request(payload, budget=budget)
        mesh = validate_mesh(request, budget=budget)
        if isinstance(mesh, BoundedExecutionFailure):
            return mesh
        layout = solve_layout(mesh, budget=budget)
        if isinstance(layout, BoundedExecutionFailure):
            return layout
        checked = verify_layout(mesh, layout, budget=budget)
        if isinstance(checked, BoundedExecutionFailure):
            return checked
        if not checked.accepted or checked.metrics is None:
            raise MeshValidationError(
                "VERIFICATION_FAILED",
                "Unfolding verification rejected candidate",
                issues=_issues(checked.issues, budget),
            )
        result = UnfoldingResult(
            request.request_id,
            _digest(mesh.request, budget=budget),
            request.units_label,
            SOLVER_VERSION,
            VERIFIER_VERSION,
            layout.vertices_2d,
            layout.faces_2d,
            layout.cut_edges,
            checked.metrics,
            (),
            (),
        )
        value = _result_payload(result, budget=budget)
        if len(_canonical_json(value, budget=budget)) > MAX_ADVANCED_RESULT_BYTES:
            raise MeshValidationError("RESOURCE_LIMIT", "Full unfolding result byte limit exceeded")
        budget.checkpoint(0)
        return result
    except BoundedExecutionInterrupted as error:
        return error.failure
    except MeshValidationError:
        if budget is not None:
            try:
                budget.checkpoint(0)
            except BoundedExecutionInterrupted as error:
                return error.failure
        raise
