"""Frozen malicious cases bind the input contract before source rendering exists."""

import hashlib
import json
from pathlib import Path

import pytest

from .test_models import api, request

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "codegen"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("target", "shell", "UNSUPPORTED_TARGET"),
        ("template_id", "caller_source", "UNSUPPORTED_TEMPLATE"),
        ("template_version", "2.0.0", "UNSUPPORTED_TEMPLATE_VERSION"),
        ("schema_version", 1, "INVALID_ARGUMENT"),
        ("target", [], "INVALID_ARGUMENT"),
        ("template_id", None, "INVALID_ARGUMENT"),
        ("template_version", False, "INVALID_ARGUMENT"),
    ],
)
def test_closed_selection_has_distinct_redacted_errors(field, value, code):
    models = api()
    with pytest.raises(models.CodeGenerationError) as caught:
        models.decode_recipe(request(**{field: value}))
    assert caught.value.code == code
    assert str(caught.value) == code


@pytest.mark.parametrize(
    "value", [True, None, "1", float("nan"), float("inf"), -float("inf"), 1e15 + 1, 10**400]
)
def test_geometry_numbers_reject_nonfinite_boolean_and_unbounded_values(value):
    models = api()
    with pytest.raises(models.CodeGenerationError) as caught:
        models.decode_recipe(
            request(
                "literal_geometry",
                {"lines": [{"start": [value, 0, 0], "end": [0, 0, 0]}], "circles": []},
            )
        )
    assert caught.value.code == "INVALID_ARGUMENT"


@pytest.mark.parametrize("value", ["\x00", "\ud800", "\udfff"])
def test_strings_reject_nul_and_surrogates_in_names_keys_and_values(value):
    models = api()
    for field in ("object_name", "layer", "property_key", "property_value"):
        fact = {"handle": "a", "object_name": "x", "layer": "x", "properties": {"x": "x"}}
        if field == "property_key":
            fact["properties"] = {value: "x"}
        elif field == "property_value":
            fact["properties"] = {"x": value}
        else:
            fact[field] = value
        with pytest.raises(models.CodeGenerationError) as caught:
            models.decode_recipe(request("serialize_entity_facts", {"facts": [fact]}))
        assert caught.value.code == "INVALID_ARGUMENT"


def test_frozen_catalogue_and_corpus_are_unique_content_addressed_contracts():
    models = api()
    catalogue_bytes = (FIXTURES / "catalogue.json").read_bytes()
    corpus_bytes = (FIXTURES / "malicious-corpus.json").read_bytes()
    catalogue = json.loads(catalogue_bytes)
    corpus = json.loads(corpus_bytes)
    assert hashlib.sha256(catalogue_bytes).hexdigest() == CATALOGUE_SHA256
    assert hashlib.sha256(corpus_bytes).hexdigest() == CORPUS_SHA256
    assert len(catalogue["pairs"]) == 9
    cases = corpus["cases"]
    assert len(cases) >= 500
    assert len({case["id"] for case in cases}) == len(cases)
    assert len({json.dumps(case["payload"], sort_keys=True) for case in cases}) == len(cases)
    assert {
        case["payload"]["target"]
        for case in cases
        if isinstance(case["payload"], dict) and isinstance(case["payload"].get("target"), str)
    } >= {"python", "autolisp", "vba"}
    for pair in catalogue["pairs"]:
        models.decode_recipe(pair["example"])
    for case in cases:
        if case["classification"] == "reject":
            with pytest.raises(models.CodeGenerationError) as caught:
                models.decode_recipe(case["payload"])
            assert caught.value.code == case["error"], case["id"]
            assert str(caught.value) == case["error"]
        else:
            recipe = models.decode_recipe(case["payload"])
            exported = models.recipe_payload(recipe)
            assert exported["literals"] == case["payload"]["literals"], case["id"]
            canonical = models.canonical_recipe_bytes(recipe)
            assert len(canonical) <= 16384, case["id"]
            assert models.canonical_recipe_bytes(models.decode_recipe(exported)) == canonical
            assert case["classification"] == "literal-data"


CATALOGUE_SHA256 = "c87a5206c1791162d6f2ca76bafcb57a1e010f31981eca104bc3dd05c824a9a5"
CORPUS_SHA256 = "99f7622181d35afa382a2ea005dea0caa0034ec50fc2432fa2e6c8ff14d977ef"
