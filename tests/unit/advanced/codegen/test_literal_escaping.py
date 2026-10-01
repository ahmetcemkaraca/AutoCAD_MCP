"""Read literal tokens and JSON as data; never execute generated functions."""

import ast
import json
import re

import pytest
from autocad_mcp.advanced.codegen.models import (
    CodeGenerationError,
    decode_recipe,
    recipe_payload,
)

from .test_goldens import FIXTURES, renderer
from .test_models import request

TARGETS = ["python", "autolisp", "vba"]


def facts_request(target, text="synthetic", **properties):
    return request(
        "serialize_entity_facts",
        {
            "facts": [
                {
                    "handle": "a",
                    "object_name": "Entity",
                    "layer": "Layer",
                    "properties": {"text": text, **properties},
                }
            ]
        },
        target=target,
    )


def read_facts_string(source, target):
    """Decode only the exact assignment frames and quoted tokens used for facts."""
    assert all(character == "\n" or 32 <= ord(character) <= 126 for character in source)
    assert len(source.encode("utf-8")) <= 65536
    if target == "python":
        module = ast.parse(source)
        assert len(module.body) == 1
        function = module.body[0]
        assert isinstance(function, ast.FunctionDef)
        assert function.name == "codegen_facts" and not function.decorator_list
        assert not function.args.args and not function.args.defaults
        assert (
            ast.dump(function.body[0], include_attributes=False)
            == "Assign(targets=[Name(id='facts_json', ctx=Store())], value=Constant(value=''))"
        )
        assert (
            ast.dump(function.body[-1], include_attributes=False)
            == "Return(value=Name(id='facts_json', ctx=Load()))"
        )
        chunks = []
        for statement in function.body[1:-1]:
            assert isinstance(statement, ast.Assign) and len(statement.targets) == 1
            assert isinstance(statement.targets[0], ast.Name)
            assert statement.targets[0].id == "facts_json"
            value = statement.value
            assert isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)
            assert isinstance(value.left, ast.Name) and value.left.id == "facts_json"
            assert isinstance(value.right, ast.Constant) and type(value.right.value) is str
            chunks.append(value.right.value)
        return "".join(chunks)
    lines = source.splitlines()
    if target == "autolisp":
        assert lines[:2] == ["(defun codegen_facts (/ facts_json)", '  (setq facts_json "")']
        assert lines[-2:] == ["  facts_json", ")"]
        chunks = []
        for line in lines[2:-2]:
            prefix = "  (setq facts_json (strcat facts_json "
            assert line.startswith(prefix) and line.endswith("))")
            token = line[len(prefix) : -2]
            assert re.fullmatch(r'"(?:\\["\\]|[^"\\])*"', token)
            chunks.append(json.loads(token))
        return "".join(chunks)
    assert max(map(len, lines)) <= 1023
    assert lines[:6] == [
        "Option Explicit",
        "Option Base 0",
        "",
        "Public Function CodegenFacts() As String",
        "    Dim facts_json As String",
        '    facts_json = ""',
    ]
    assert lines[-2:] == ["    CodegenFacts = facts_json", "End Function"]
    chunks = []
    for line in lines[6:-2]:
        prefix = "    facts_json = facts_json & "
        assert line.startswith(prefix)
        token = line[len(prefix) :]
        assert re.fullmatch(r'"(?:[^"\r\n]|"")*"', token)
        chunks.append(token[1:-1].replace('""', '"'))
    return "".join(chunks)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "text",
    [
        "\"\\'` ; # /* */ () [] {} : _\n\r\t\b\f",
        "".join(chr(number) for number in range(1, 32)) + chr(127) + chr(128) + chr(159),
        "é漢字🙂\u2028\u2029\u202e\u2066\u2069\uff02\uff07\ud7ff\ue000\uffff\U00010000\U0010ffff",
        '\\u0022\\n\\\\"; eval("synthetic"); import os #',
        '"' * 1024,
        "\\" * 1024,
        "🙂" * 1024,
        "",
    ],
)
def test_quoted_fact_data_roundtrips_without_extra_executable_structure(target, text):
    render = renderer()
    recipe = decode_recipe(facts_request(target, text))
    source = render(recipe)
    decoded_json = read_facts_string(source, target)
    assert json.loads(decoded_json) == recipe_payload(recipe)["literals"]["facts"]
    assert decoded_json.isascii()
    assert decoded_json == json.dumps(
        recipe_payload(recipe)["literals"]["facts"],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@pytest.mark.parametrize("target", TARGETS)
def test_all_property_scalar_kinds_survive_json_serialization(target):
    render = renderer()
    recipe = decode_recipe(
        facts_request(
            target,
            null=None,
            true=True,
            false=False,
            minimum=-(2**53 - 1),
            maximum=2**53 - 1,
            small=5e-324,
            negative=-1e15,
            positive=1e15,
            zero=-0.0,
        )
    )
    assert (
        json.loads(read_facts_string(render(recipe), target))
        == recipe_payload(recipe)["literals"]["facts"]
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "value",
    [
        0.0,
        -0.0,
        1e15,
        -1e15,
        1e-100,
        -1.2345678901234567e-100,
        5e-324,
        -5e-324,
        2.2250738585072014e-308,
        0.1,
        1.0000000000000002,
    ],
)
def test_geometry_real_tokens_preserve_binary_float_values(target, value):
    render = renderer()
    recipe = decode_recipe(
        request(
            "literal_geometry",
            {
                "lines": [{"start": [value, 0, 0], "end": [0, 0, 0]}],
                "circles": [{"center": [0, 0, 0], "radius": 5e-324}],
            },
            target=target,
        )
    )
    source = render(recipe)
    if target == "python":
        ast.parse(source)
    tokens = re.findall(r"-?\d+\.\d+(?:[eE][+-]?\d+)?#?", source)
    assert len(tokens) == 10
    assert float(tokens[0].rstrip("#")).hex() == (0.0 if value == 0 else value).hex()
    assert float(tokens[-1].rstrip("#")).hex() == (5e-324).hex()
    if target == "vba":
        assert all(token.endswith("#") for token in tokens)
        assert max(map(len, source.splitlines())) <= 1023


def test_all_frozen_malicious_classifications_survive_rendering():
    render = renderer()
    corpus = json.loads((FIXTURES / "malicious-corpus.json").read_bytes())
    accepted = rejected = 0
    for case in corpus["cases"]:
        if case["classification"] == "reject":
            with pytest.raises(CodeGenerationError) as caught:
                decode_recipe(case["payload"])
            assert caught.value.code == case["error"], case["id"]
            rejected += 1
        else:
            recipe = decode_recipe(case["payload"])
            source = render(recipe)
            result = json.loads(read_facts_string(source, case["payload"]["target"]))
            assert result == recipe_payload(recipe)["literals"]["facts"], case["id"]
            accepted += 1
    assert (accepted, rejected) == (576, 297)


@pytest.mark.parametrize("target", TARGETS)
def test_source_overflow_rejects_expanding_valid_literals_without_truncation(target):
    render = renderer()
    payload = facts_request(target)
    payload["literals"]["facts"][0]["properties"] = {f"k{i}": chr(127) * 1000 for i in range(16)}
    recipe = decode_recipe(payload)
    with pytest.raises(CodeGenerationError) as caught:
        render(recipe)
    assert caught.value.code == "PAYLOAD_LIMIT"
    assert str(caught.value) == "PAYLOAD_LIMIT"


@pytest.mark.parametrize(
    "target,control_count,padding",
    [
        ("python", 7079, 51),
        ("autolisp", 6784, 48),
        ("vba", 8316, 52),
    ],
)
def test_exact_source_byte_ceiling_and_one_byte_overflow(target, control_count, padding):
    render = renderer()
    payload = facts_request(target)
    fact = payload["literals"]["facts"][0]
    fact["object_name"] = "Entity" + "x" * padding
    fact["properties"] = {}
    for index in range(16):
        controls = max(0, min(1000, control_count - index * 1000))
        fact["properties"][f"k{index}"] = chr(127) * controls + "x" * (1000 - controls)
    recipe = decode_recipe(payload)
    source = render(recipe)
    assert len(source.encode("utf-8")) == 65536
    assert (
        json.loads(read_facts_string(source, target)) == recipe_payload(recipe)["literals"]["facts"]
    )
    fact["object_name"] += "x"
    over_limit = decode_recipe(payload)
    with pytest.raises(CodeGenerationError) as caught:
        render(over_limit)
    assert caught.value.code == "PAYLOAD_LIMIT"


@pytest.mark.parametrize("target", TARGETS)
def test_maximum_geometry_records_preserve_all_coordinate_and_radius_order(target):
    render = renderer()
    lines = [
        {"start": [index, -index, 0.25], "end": [index + 1, index + 2, 0.5]} for index in range(64)
    ]
    circles = [{"center": [index, index + 1, 0.75], "radius": index + 1} for index in range(64)]
    recipe = decode_recipe(
        request("literal_geometry", {"lines": lines, "circles": circles}, target=target)
    )
    source = render(recipe)
    tokens = re.findall(r"-?\d+\.\d+(?:[eE][+-]?\d+)?#?", source)
    expected = [
        number for line in lines for point in (line["start"], line["end"]) for number in point
    ]
    expected += [number for circle in circles for number in (*circle["center"], circle["radius"])]
    assert [float(token.rstrip("#")) for token in tokens] == expected
    if target == "python":
        ast.parse(source)
    if target == "vba":
        assert max(map(len, source.splitlines())) <= 1023


@pytest.mark.parametrize("target", TARGETS)
def test_maximum_handles_remain_quoted_literals_in_supplied_order(target):
    render = renderer()
    handles = [f"{index:016X}" for index in range(256)]
    recipe = decode_recipe(request(literals={"handles": handles}, target=target))
    source = render(recipe)
    tokens = re.findall(r'"[0-9A-F]*"', source)
    assert [token[1:-1] for token in tokens] == handles + [""]
    if target == "python":
        module = ast.parse(source)
        assert len(module.body) == 1 and isinstance(module.body[0], ast.FunctionDef)
        assert module.body[0].name == "codegen_iterate_handles"
    if target == "vba":
        assert max(map(len, source.splitlines())) <= 1023


@pytest.mark.parametrize("value", [None, {}, "source"])
def test_renderer_requires_a_validated_recipe_object(value):
    render = renderer()
    with pytest.raises(CodeGenerationError) as caught:
        render(value)
    assert caught.value.code == "INVALID_ARGUMENT"
