"""Registered C calls preserve recipe/artifact contracts and actual SDK size bounds."""

import asyncio
import json

import jsonschema
import mcp.types as types
import pytest
from autocad_mcp.advanced.codegen import service as codegen
from autocad_mcp.core.models import BasicToolInput, ToolResponse
from autocad_mcp.core.tools import TOOL_DEFINITIONS
from autocad_mcp.server import create_server

from tests.unit.advanced.codegen.test_validate import PAIRS

NAME = "generate_constrained_code"


class RejectBasicService:
    async def invoke(self, request: BasicToolInput) -> ToolResponse:
        raise AssertionError("Code generation reached basic service")


def call(payload: dict) -> types.CallToolResult:
    server = create_server(RejectBasicService())
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(name=NAME, arguments=payload)
    )
    return asyncio.run(server.request_handlers[types.CallToolRequest](request)).root


def body_size(result: types.CallToolResult) -> int:
    return len(result.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"))


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f'{p["target"]}-{p["template_id"]}')
def test_registered_handler_returns_exact_artifact_without_basic_service(pair: dict) -> None:
    result = call(pair["example"])
    assert json.loads(result.content[0].text) == {
        "success": True,
        "artifact": codegen.artifact_payload(codegen.generate_code(pair["example"])),
    }
    assert body_size(result) <= 65536


def test_schema_is_closed_disjoint_and_matches_literal_limits() -> None:
    tool = next(tool for tool in TOOL_DEFINITIONS if tool.name == NAME)
    schema = tool.inputSchema
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version",
        "template_id",
        "template_version",
        "target",
        "literals",
    }
    assert len(schema["oneOf"]) == 3
    for pair in PAIRS:
        jsonschema.validate(pair["example"], schema)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**pair["example"], "source": "private"}, schema)
    payload = PAIRS[0]["example"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"recipe": payload}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**payload, "literals": {"handles": ["A"] * 257}}, schema)
    geometry = next(p["example"] for p in PAIRS if p["template_id"] == "literal_geometry")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**geometry, "literals": {"lines": [], "circles": []}}, schema)


def test_handle_schema_rejects_trailing_newline() -> None:
    schema = next(tool.inputSchema for tool in TOOL_DEFINITIONS if tool.name == NAME)
    payload = {**PAIRS[0]["example"], "literals": {"handles": ["A\n"]}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


@pytest.mark.parametrize(
    "field,code",
    [
        ("source", "INVALID_ARGUMENT"),
        ("target", "UNSUPPORTED_TARGET"),
        ("template_id", "UNSUPPORTED_TEMPLATE"),
        ("template_version", "UNSUPPORTED_TEMPLATE_VERSION"),
    ],
)
def test_input_rejections_are_redacted_and_never_reach_basic_service(field: str, code: str) -> None:
    result = call({**PAIRS[0]["example"], field: "private-source-detail"})
    payload = json.loads(result.content[0].text)
    assert payload["success"] is False and payload["error"]["code"] == code
    assert "private-source-detail" not in result.content[0].text


def test_real_sdk_body_exact_boundary_and_one_byte_over(monkeypatch: pytest.MonkeyPatch) -> None:
    recipe = PAIRS[0]["example"]
    ordinary = codegen.generate_code(recipe)
    baseline = body_size(call(recipe))
    source = ordinary.source + " " * (65536 - baseline)
    monkeypatch.setattr(codegen, "render_recipe", lambda recipe: source)
    exact = call(recipe)
    assert json.loads(exact.content[0].text)["success"] is True
    assert body_size(exact) == 65536
    source += " "
    overflow = call(recipe)
    payload = json.loads(overflow.content[0].text)
    assert payload["success"] is False and payload["error"]["code"] == "PAYLOAD_LIMIT"
    assert "artifact" not in payload and body_size(overflow) < 65536


def test_real_quote_heavy_recipe_fits_artifact_but_not_nested_mcp_body() -> None:
    recipe = {
        "schema_version": "1",
        "template_id": "serialize_entity_facts",
        "template_version": "1.0.0",
        "target": "python",
        "literals": {
            "facts": [
                {
                    "handle": "A",
                    "object_name": "Entity",
                    "layer": "Layer",
                    "properties": {f"k{i}": '"' * 400 for i in range(16)},
                }
            ]
        },
    }
    artifact = codegen.generate_code(recipe)
    assert (
        len(
            json.dumps(
                codegen.artifact_payload(artifact), ensure_ascii=False, separators=(",", ":")
            ).encode()
        )
        < 65536
    )
    result = call(recipe)
    assert json.loads(result.content[0].text)["error"]["code"] == "PAYLOAD_LIMIT"
    assert artifact.source not in result.content[0].text


def test_unexpected_error_uses_incident_path_without_source_leak(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(recipe):
        raise RuntimeError("private-source-detail")

    monkeypatch.setattr(codegen, "render_recipe", fail)
    result = call(PAIRS[0]["example"])
    payload = json.loads(result.content[0].text)
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["details"]["incident_id"]
    assert "private-source-detail" not in result.content[0].text + caplog.text
