"""Hand-authored source fixtures bind all nine reviewed template shapes."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest
from autocad_mcp.advanced.codegen.models import decode_recipe

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "codegen"
MANIFEST_SHA256 = "18db35b62f1d10b0524a8ad685cfbc355426b1bfec76114266d2b9fc1533e975"
PAIRS = json.loads((FIXTURES / "catalogue.json").read_text())["pairs"]


def renderer():
    try:
        return importlib.import_module("autocad_mcp.advanced.codegen.render").render_recipe
    except ModuleNotFoundError:
        pytest.fail("The literal-only renderer has not been implemented")


@pytest.mark.parametrize("pair", PAIRS, ids=lambda pair: f'{pair["target"]}-{pair["template_id"]}')
def test_fixed_pair_matches_frozen_hand_authored_golden(pair):
    render = renderer()
    manifest_bytes = (FIXTURES / "goldens.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA256
    golden = next(
        item
        for item in json.loads(manifest_bytes)["goldens"]
        if (item["target"], item["template_id"]) == (pair["target"], pair["template_id"])
    )
    source_bytes = (FIXTURES / golden["file"]).read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == golden["source_sha256"]
    source = render(decode_recipe(pair["example"]))
    assert source.encode("utf-8") == source_bytes
