"""Normalized input fixes source bytes independent of mapping insertion order."""

import hashlib

import pytest
from autocad_mcp.advanced.codegen.models import decode_recipe

from .test_goldens import PAIRS, renderer
from .test_literal_escaping import TARGETS, facts_request
from .test_models import request


@pytest.mark.parametrize("pair", PAIRS, ids=lambda pair: f'{pair["target"]}-{pair["template_id"]}')
def test_repeated_and_reordered_request_returns_same_source_and_digest(pair):
    render = renderer()
    recipe = decode_recipe(pair["example"])
    reordered = decode_recipe(dict(reversed(list(pair["example"].items()))))
    source = render(recipe)
    assert render(recipe) == render(reordered) == source
    assert (
        hashlib.sha256(render(recipe).encode()).digest() == hashlib.sha256(source.encode()).digest()
    )


@pytest.mark.parametrize("target", TARGETS)
def test_fact_property_order_does_not_change_source(target):
    render = renderer()
    first = facts_request(target, a=1, b=False)
    second = facts_request(target, b=False, a=1)
    assert render(decode_recipe(first)) == render(decode_recipe(second))


@pytest.mark.parametrize("target", TARGETS)
def test_normalized_handles_and_geometry_use_fixed_source(target):
    render = renderer()
    assert render(decode_recipe(request(target=target))) == render(
        decode_recipe(
            request(
                literals={"handles": ["ABC", "000F"]},
                target=target,
            )
        )
    )
    integer = request(
        "literal_geometry",
        {"lines": [{"start": [0, 1, 2], "end": [3, 4, 5]}], "circles": []},
        target=target,
    )
    floating = request(
        "literal_geometry",
        {"lines": [{"start": [-0.0, 1.0, 2.0], "end": [3.0, 4.0, 5.0]}], "circles": []},
        target=target,
    )
    assert render(decode_recipe(integer)) == render(decode_recipe(floating))
