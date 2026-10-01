"""U calls use the accepted pure service and bounded SDK bodies, preserving C."""

import asyncio
import hashlib
import json
import threading
from dataclasses import replace
from pathlib import Path

import mcp.types as types
import pytest
from autocad_mcp.advanced.bounds import (
    BoundedExecutionFailure,
    BoundedExecutionInterrupted,
    BoundedFailureCode,
    WorkBudget,
)
from autocad_mcp.advanced.unfolding import service
from autocad_mcp.advanced.unfolding.models import (
    LayoutVerification,
    UnfoldingIssue,
    UnfoldingResult,
    decode_policy,
)
from autocad_mcp.core.models import BasicToolInput, ToolResponse
from autocad_mcp.server import create_server

from tests.contract.test_surface_unfolding_tool import FIXTURES, request
from tests.unit.advanced.codegen.test_validate import PAIRS

LIMIT = 4 * 1024 * 1024


class NoBasicService:
    async def invoke(self, value: BasicToolInput) -> ToolResponse:
        raise AssertionError("Pure unfolding reached basic backend")


def call(payload: dict, name: str = "unfold_surface") -> types.CallToolResult:
    server = create_server(NoBasicService())
    request_ = types.CallToolRequest(
        params=types.CallToolRequestParams(name=name, arguments=payload)
    )
    return asyncio.run(server.request_handlers[types.CallToolRequest](request_)).root


def size(result: types.CallToolResult) -> int:
    return len(result.model_dump_json(by_alias=True, exclude_none=True).encode())


def test_registered_result_is_exact_service_payload_and_canonical() -> None:
    payload = request()
    result = call(payload)
    expected = service.result_payload(service.unfold_surface(payload))
    assert json.loads(result.content[0].text) == {"success": True, "result": expected}
    assert len(expected["input_digest"]) == 64
    assert expected["metrics"]["overlap_pair_count"] == 0
    assert size(result) <= LIMIT
    reordered = {**payload, "vertices": payload["vertices"][::-1], "faces": payload["faces"][::-1]}
    assert call(reordered).model_dump_json() == result.model_dump_json()


@pytest.mark.parametrize("change", ["unknown", "policy", "face", "nonfinite"])
def test_invalid_before_solver_is_structured_and_redacted(monkeypatch, change: str) -> None:
    payload = request()
    if change == "unknown":
        payload["private"] = "private literal"
    elif change == "policy":
        payload["policy"]["max_iterations"] = True
    elif change == "face":
        payload["faces"][0]["vertex_ids"] = [0, 0, 0]
    else:
        payload["vertices"][0]["point"][0] = float("nan")
    calls = []
    monkeypatch.setattr(service, "solve_layout", lambda *args, **kwargs: calls.append(1))
    response = json.loads(call(payload).content[0].text)
    assert response["success"] is False and response["error"]["code"] in {
        "INVALID_ARGUMENT",
        "INVALID_FACE",
        "RESOURCE_LIMIT",
    }
    assert not calls and "private" not in json.dumps(response)


def test_verifier_rejection_never_releases_geometry(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "verify_layout",
        lambda *args, **kwargs: LayoutVerification(
            False, None, (UnfoldingIssue("OVERLAP", (0, 1), "Output triangles overlap"),)
        ),
    )
    response = json.loads(call(request()).content[0].text)
    assert response["error"]["code"] == "VERIFICATION_FAILED"
    assert response["error"]["details"]["issues"][0]["face_ids"] == [0, 1]
    assert not {"result", "vertices_2d", "metrics", "input_digest"} & response.keys()


@pytest.mark.parametrize(
    "code", [BoundedFailureCode.CANCELLED, BoundedFailureCode.DEADLINE_EXCEEDED]
)
def test_domain_interruption_preserves_work_without_partial_data(monkeypatch, code) -> None:
    calls = []

    def interrupted(*args, **kwargs):
        calls.append(1)
        return BoundedExecutionFailure(code, 17, "private interruption detail")

    monkeypatch.setattr(service, "unfold_surface", interrupted)
    response = json.loads(call(request()).content[0].text)
    assert response["error"]["code"] == code.value
    assert response["error"]["details"] == {"completed_iterations": 17}
    assert calls == [1] and "private" not in json.dumps(response)
    assert "result" not in response


def test_transport_cancel_is_observed_by_one_cooperative_worker(monkeypatch) -> None:
    started, stopped = threading.Event(), threading.Event()
    seen = []

    def controlled(payload, *, cancellation):
        seen.append(cancellation)
        budget = WorkBudget(decode_policy(payload["policy"]), cancellation=cancellation)
        started.set()
        try:
            while True:
                budget.checkpoint()
        except BoundedExecutionInterrupted as error:
            return error.failure
        finally:
            stopped.set()

    monkeypatch.setattr(service, "unfold_surface", controlled)

    async def exercise():
        payload = request()
        payload["policy"]["cancellation_check_interval"] = 1
        server = create_server(NoBasicService())
        req = types.CallToolRequest(
            params=types.CallToolRequestParams(name="unfold_surface", arguments=payload)
        )
        task = asyncio.create_task(server.request_handlers[types.CallToolRequest](req))
        assert await asyncio.to_thread(started.wait, 2)
        # A second pure request must remain responsive while numerical work runs.
        c = types.CallToolRequest(
            params=types.CallToolRequestParams(
                name="generate_constrained_code", arguments=PAIRS[0]["example"]
            )
        )
        checked = await asyncio.wait_for(server.request_handlers[types.CallToolRequest](c), 2)
        assert json.loads(checked.root.content[0].text)["success"] is True
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await asyncio.to_thread(stopped.wait, 2)
        assert len(seen) == 1 and seen[0].is_cancelled()

    asyncio.run(exercise())


def test_actual_body_boundary_with_controlled_serialization_output(monkeypatch) -> None:
    ordinary = service.unfold_surface(request())
    assert isinstance(ordinary, UnfoldingResult)
    baseline = size(call(request()))
    # This is a serialization guard vector, not a numerically admitted mesh result.
    output = replace(ordinary, request_id=ordinary.request_id + "p" * (LIMIT - baseline))
    monkeypatch.setattr(service, "unfold_surface", lambda *args, **kwargs: output)
    exact = call(request())
    assert json.loads(exact.content[0].text)["success"] is True and size(exact) == LIMIT
    output = replace(output, request_id=output.request_id + "p")
    rejected = json.loads(call(request()).content[0].text)
    assert rejected["error"]["code"] == "PAYLOAD_LIMIT" and "result" not in rejected


def test_maximum_service_result_fits_real_sdk_body() -> None:
    payload = json.loads((FIXTURES / "cases/exact-max-torus.json").read_text())
    result = call(payload)
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert len(response["result"]["faces_2d"]) == 4000 and size(result) <= LIMIT


def test_frozen_worst_case_vector_is_measured_as_serialization_only(monkeypatch) -> None:
    ordinary = service.unfold_surface(request())
    vector = json.loads((FIXTURES / "worst-case-result.json").read_text())
    monkeypatch.setattr(service, "unfold_surface", lambda *args, **kwargs: ordinary)
    monkeypatch.setattr(service, "result_payload", lambda value: vector)
    result = call(request())
    assert json.loads(result.content[0].text)["result"] == vector
    assert size(result) == 3417137


def test_existing_c_body_bytes_and_digests_are_unchanged() -> None:
    evidence = (
        Path(__file__).parents[2]
        / "docs/advanced/evidence/codegen"
        / "077ad74ae8dedfcba3260cf6253a38e1ed89afca5cecb9fe9eeb4951b76b5a55.json"
    )
    rows = json.loads(evidence.read_text())["request_pairs"]
    for pair, row in zip(PAIRS, rows, strict=True):
        result = call(pair["example"], name="generate_constrained_code")
        body = result.model_dump_json(by_alias=True, exclude_none=True).encode()
        assert (
            len(body) == row["body_bytes"]
            and hashlib.sha256(body).hexdigest() == row["body_sha256"]
        )
