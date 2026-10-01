"""Frozen classifications survive independent validation, with source kept as data."""

import json

import pytest
from autocad_mcp.advanced.codegen.models import CodeGenerationError, decode_recipe
from autocad_mcp.advanced.codegen.render import render_recipe
from autocad_mcp.advanced.codegen.service import generate_code
from autocad_mcp.advanced.codegen.validate import validate_source

from .test_models import request
from .test_validate import FIXTURES


def test_all_873_frozen_cases_keep_original_classification_and_literal_meaning() -> None:
    cases = json.loads((FIXTURES / "malicious-corpus.json").read_text())["cases"]
    accepted = rejected = 0
    for case in cases:
        if case["classification"] == "reject":
            with pytest.raises(CodeGenerationError) as caught:
                decode_recipe(case["payload"])
            assert caught.value.code == case["error"]
            with pytest.raises(CodeGenerationError) as service_error:
                generate_code(case["payload"])
            assert service_error.value.code == case["error"]
            rejected += 1
        else:
            recipe = decode_recipe(case["payload"])
            assert validate_source(recipe, render_recipe(recipe)) == (), case["id"]
            artifact = generate_code(case["payload"])
            assert artifact.source == render_recipe(recipe) and artifact.executed is False
            accepted += 1
    assert (accepted, rejected) == (576, 297)


@pytest.mark.parametrize("target", ["python", "autolisp", "vba"])
def test_maximum_geometry_handles_and_all_scalar_kinds_survive_independent_parser(
    target: str,
) -> None:
    payloads = [
        request(
            "literal_geometry",
            {
                "lines": [{"start": [i, -i, 5e-324], "end": [1e15, -1e15, 0.1]} for i in range(64)],
                "circles": [{"center": [i, 0, 1e-300], "radius": 5e-324} for i in range(64)],
            },
            target=target,
        ),
        request(literals={"handles": [f"{i:016X}" for i in range(256)]}, target=target),
        request(
            "serialize_entity_facts",
            {
                "facts": [
                    {
                        "handle": "A",
                        "object_name": "Entity",
                        "layer": "Layer",
                        "properties": {
                            "text": '"\\\n\u202e🙂' * 100,
                            "null": None,
                            "true": True,
                            "false": False,
                            "int": 2**53 - 1,
                            "float": -1e15,
                            "small": 5e-324,
                        },
                    }
                ]
            },
            target=target,
        ),
    ]
    for payload in payloads:
        recipe = decode_recipe(payload)
        assert validate_source(recipe, render_recipe(recipe)) == ()
