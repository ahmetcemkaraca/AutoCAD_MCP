"""Recipe boundaries protect callers from mutation and noncanonical input."""

import importlib
import json
from dataclasses import FrozenInstanceError, fields

import pytest


def api():
    try:
        return importlib.import_module("autocad_mcp.advanced.codegen.models")
    except ModuleNotFoundError:
        pytest.fail("The constrained recipe contract has not been implemented")


def request(template="iterate_handles", literals=None, **changes):
    return {
        "schema_version": "1",
        "template_id": template,
        "template_version": "1.0.0",
        "target": "python",
        "literals": {"handles": ["abc", "000f"]} if literals is None else literals,
        **changes,
    }


def test_normalized_recipe_is_detached_and_deeply_immutable():
    models = api()
    payload = request(
        "literal_geometry", {"lines": [{"start": [0, -0.0, 1], "end": [2, 3, 4]}], "circles": []}
    )
    recipe = models.decode_recipe(payload)
    assert models.recipe_payload(recipe)["literals"] == {
        "lines": [{"start": [0.0, 0.0, 1.0], "end": [2.0, 3.0, 4.0]}],
        "circles": [],
    }
    payload["literals"]["lines"][0]["start"][0] = 99
    assert recipe.literals["lines"][0]["start"][0] == 0.0
    with pytest.raises(TypeError):
        recipe.literals["lines"][0]["start"][0] = 99
    with pytest.raises(TypeError):
        recipe.literals["lines"][0]["start"] = ()
    with pytest.raises(FrozenInstanceError):
        recipe.target = models.CodeTarget.VBA
    exported = models.recipe_payload(recipe)
    exported["literals"]["lines"][0]["start"][0] = 100
    assert recipe.literals["lines"][0]["start"][0] == 0.0


def test_recipe_bytes_are_canonical_and_handles_normalize():
    models = api()
    recipe = models.decode_recipe(request())
    assert models.canonical_recipe_bytes(recipe) == (
        b'{"literals":{"handles":["ABC","000F"]},"schema_version":"1",'
        b'"target":"python","template_id":"iterate_handles","template_version":"1.0.0"}'
    )
    assert models.canonical_recipe_bytes(
        models.decode_recipe(dict(reversed(list(request().items()))))
    ) == models.canonical_recipe_bytes(recipe)


def test_exact_epic_dataclass_fields_and_constructor_validation():
    models = api()
    for name, expected in {
        "CodeRecipe": ["schema_version", "template_id", "template_version", "target", "literals"],
        "StaticFinding": ["rule_id", "severity", "location", "message"],
        "GeneratedCodeArtifact": [
            "target",
            "template_id",
            "template_version",
            "source",
            "digest",
            "findings",
            "executed",
            "warning",
        ],
    }.items():
        assert [field.name for field in fields(getattr(models, name))] == expected
    with pytest.raises(models.CodeGenerationError):
        models.CodeRecipe(
            "1", "iterate_handles", "1.0.0", models.CodeTarget.PYTHON, {"handles": []}
        )
    finding = models.StaticFinding("rule", "warning", "1", "Review")
    warning = "Generated text was not executed; review it outside AutoCAD MCP."
    with pytest.raises(models.CodeGenerationError):
        models.GeneratedCodeArtifact(
            models.CodeTarget.PYTHON, "iterate_handles", "1.0.0", "", "", (finding,), True, warning
        )


def test_request_bound_measures_original_utf8_json_at_exact_boundary():
    models = api()
    facts = [
        {
            "handle": "a",
            "object_name": "x",
            "layer": "x",
            "properties": {f"k{i}": "x" * 1000 for i in range(16)},
        }
    ]
    payload = request("serialize_entity_facts", {"facts": facts})

    def compact(value):
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()

    remaining = 16384 - len(compact(payload))
    assert 0 < remaining < 254
    facts[0]["layer"] += "x" * remaining
    assert len(compact(payload)) == 16384
    models.decode_recipe(payload)
    facts[0]["layer"] += "x"
    with pytest.raises(models.CodeGenerationError) as caught:
        models.decode_recipe(payload)
    assert caught.value.code == "PAYLOAD_LIMIT"


def test_all_literal_maxima_and_json_scalars_are_accepted():
    models = api()
    models.decode_recipe(request("iterate_handles", {"handles": [f"{i:X}" for i in range(256)]}))
    models.decode_recipe(
        request(
            "literal_geometry",
            {
                "lines": [{"start": [-1e15, 0, 1e15], "end": [0, 0, 0]}] * 64,
                "circles": [{"center": [0, 0, 0], "radius": 1e15}] * 64,
            },
        )
    )
    facts = [
        {"handle": f"{i:X}", "object_name": "x", "layer": "y", "properties": {}} for i in range(64)
    ]
    models.decode_recipe(request("serialize_entity_facts", {"facts": facts}))
    fact = {
        "handle": "FFFFFFFFFFFFFFFF",
        "object_name": "x" * 255,
        "layer": "y" * 255,
        "properties": {
            "k" * 128: "🙂" * 1024,
            "null": None,
            "bool": True,
            "positive_int": 2**53 - 1,
            "negative_int": -(2**53 - 1),
            "positive_float": 1e15,
            "negative_float": -1e15,
        },
    }
    recipe = models.decode_recipe(request("serialize_entity_facts", {"facts": [fact]}))
    assert models.recipe_payload(recipe)["literals"]["facts"][0] == fact


def test_deeply_nested_and_cyclic_nonjson_input_is_rejected_without_recursion():
    models = api()
    cycle = []
    cycle.append(cycle)
    for value in (cycle, {"x": cycle}):
        with pytest.raises(models.CodeGenerationError) as caught:
            models.decode_recipe(
                request(
                    "serialize_entity_facts",
                    {
                        "facts": [
                            {
                                "handle": "a",
                                "object_name": "x",
                                "layer": "y",
                                "properties": {"x": value},
                            }
                        ]
                    },
                )
            )
        assert caught.value.code == "INVALID_ARGUMENT"
