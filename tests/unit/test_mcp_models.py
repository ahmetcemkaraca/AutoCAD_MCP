"""Contract tests for pure, transport-independent MCP core models."""

from dataclasses import FrozenInstanceError
from typing import get_args

import pytest
from autocad_mcp.core.models import (
    BasicToolInput,
    ErrorCode,
    GetEntityInfoInput,
    JsonScalar,
    JsonValue,
    ListEntitiesInput,
    ServerStatusInput,
    ToolError,
    ToolFailure,
    ToolName,
    ToolResponse,
    ToolSuccess,
    response_json,
    response_payload,
)


def test_models_expose_the_three_immutable_request_types() -> None:
    """Changing a request type from frozen or its tool identity must fail here."""
    assert tuple(ToolName) == (
        ToolName.SERVER_STATUS,
        ToolName.LIST_ENTITIES,
        ToolName.GET_ENTITY_INFO,
    )
    assert ToolName.SERVER_STATUS.value == "server_status"
    assert ServerStatusInput.tool_name is ToolName.SERVER_STATUS
    assert ListEntitiesInput.tool_name is ToolName.LIST_ENTITIES
    assert GetEntityInfoInput(7).tool_name is ToolName.GET_ENTITY_INFO
    assert get_args(BasicToolInput) == (
        ServerStatusInput,
        ListEntitiesInput,
        GetEntityInfoInput,
    )
    assert get_args(ToolResponse) == (ToolSuccess, ToolFailure)
    assert JsonScalar is not None
    assert JsonValue is not None


@pytest.mark.parametrize(
    "tool_input", (ServerStatusInput(), ListEntitiesInput(), GetEntityInfoInput(7))
)
def test_requests_are_immutable(tool_input: BasicToolInput) -> None:
    """Removing frozen request models would let dispatch inputs change after validation."""
    with pytest.raises(FrozenInstanceError):
        tool_input.tool_name = ToolName.SERVER_STATUS  # type: ignore[misc]


def test_success_payload_merges_data_and_serializes_deterministically() -> None:
    """Dropping compatibility fields or JSON options changes the public wire response."""
    response = ToolSuccess({"entities": [{"id": 1001, "type": "AcDbLine"}], "count": 1})

    assert response_payload(response) == {
        "success": True,
        "entities": [{"id": 1001, "type": "AcDbLine"}],
        "count": 1,
    }
    assert response_json(response) == (
        '{"count":1,"entities":[{"id":1001,"type":"AcDbLine"}],"success":true}'
    )


def test_failure_payload_is_structured_and_contains_no_exception_field() -> None:
    """Adding raw exception details would expose internal implementation information."""
    response = ToolFailure(
        ToolError(
            code=ErrorCode.AUTOCAD_UNAVAILABLE,
            message="Full AutoCAD is unavailable",
            retryable=True,
        )
    )

    assert response_payload(response) == {
        "success": False,
        "error": {
            "code": "AUTOCAD_UNAVAILABLE",
            "message": "Full AutoCAD is unavailable",
            "retryable": True,
            "details": {},
        },
    }
    assert response_json(response) == (
        '{"error":{"code":"AUTOCAD_UNAVAILABLE","details":{},'
        '"message":"Full AutoCAD is unavailable","retryable":true},"success":false}'
    )


def test_success_payload_rejects_the_reserved_success_key() -> None:
    """Allowing data to overwrite success makes a successful result ambiguous."""
    with pytest.raises(ValueError, match="success"):
        response_payload(ToolSuccess({"success": False}))


def test_response_json_rejects_non_finite_values() -> None:
    """Permitting NaN would emit invalid JSON to MCP clients."""
    with pytest.raises(ValueError):
        response_json(ToolSuccess({"measurement": float("nan")}))


def test_error_codes_are_the_canonical_redacted_values() -> None:
    """Changing the error vocabulary breaks client-side structured error handling."""
    assert tuple(ErrorCode) == (
        ErrorCode.INVALID_ARGUMENT,
        ErrorCode.UNKNOWN_TOOL,
        ErrorCode.AUTOCAD_UNAVAILABLE,
        ErrorCode.NO_ACTIVE_DOCUMENT,
        ErrorCode.COM_BUSY,
        ErrorCode.UNSUPPORTED_CAPABILITY,
        ErrorCode.ENTITY_NOT_FOUND,
        ErrorCode.AUTOCAD_OPERATION_FAILED,
        ErrorCode.INTERNAL_ERROR,
    )
