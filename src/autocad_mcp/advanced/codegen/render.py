"""Render immutable recipes as source data, without saving or executing it."""

import json
from typing import cast

from autocad_mcp.core.models import JsonValue

from .models import (
    MAX_ARTIFACT_BYTES,
    CodeGenerationError,
    CodeRecipe,
    CodeTarget,
    recipe_payload,
)
from .templates import TEMPLATES


def _quote(text: str, target: CodeTarget) -> str:
    # Inputs here are printable ASCII JSON or validated hexadecimal handles.
    if target == CodeTarget.VBA:
        return '"' + text.replace('"', '""') + '"'
    return json.dumps(text, ensure_ascii=True)


def _real(number: float, target: CodeTarget) -> str:
    mantissa, separator, exponent = repr(number).partition("e")
    if "." not in mantissa:
        mantissa += ".0"
    token = mantissa + ("E" + exponent if separator else "")
    return token + ("#" if target == CodeTarget.VBA else "")


def _record(parts: list[str], target: CodeTarget) -> str:
    if target == CodeTarget.AUTOLISP:
        return "(list " + " ".join(parts) + ")"
    if target == CodeTarget.VBA:
        return "Array(" + ", ".join(parts) + ")"
    return "(" + ", ".join(parts) + ")"


def _point(value: JsonValue, target: CodeTarget) -> str:
    return _record([_real(number, target) for number in cast(list[float], value)], target)


def _assign_records(name: str, records: list[str], target: CodeTarget) -> str:
    if target == CodeTarget.PYTHON:
        return (
            f"    {name} = [\n" + "".join(f"        {record},\n" for record in records) + "    ]\n"
        )
    if target == CodeTarget.AUTOLISP:
        return (
            f"  (setq {name} (list\n" + "".join(f"    {record}\n" for record in records) + "  ))\n"
        )
    if not records:
        return f"    {name} = Array()\n"
    return f"    ReDim {name}(0 To {len(records) - 1})\n" + "".join(
        f"    {name}({index}) = {record}\n" for index, record in enumerate(records)
    )


def _geometry(literals: dict[str, JsonValue], target: CodeTarget) -> dict[str, str]:
    lines = [
        _record([_point(line["start"], target), _point(line["end"], target)], target)
        for line in cast(list[dict[str, JsonValue]], literals["lines"])
    ]
    circles = [
        _record(
            [_point(circle["center"], target), _real(cast(float, circle["radius"]), target)], target
        )
        for circle in cast(list[dict[str, JsonValue]], literals["circles"])
    ]
    return {
        "lines": _assign_records("lines", lines, target),
        "circles": _assign_records("circles", circles, target),
    }


def _facts(value: JsonValue, target: CodeTarget) -> str:
    facts_json = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    statements = []
    # 256 raw ASCII characters escape to at most 512, below VBA's 1023-char line limit.
    for index in range(0, len(facts_json), 256):
        literal = _quote(facts_json[index : index + 256], target)
        if target == CodeTarget.PYTHON:
            statements.append(f"    facts_json = facts_json + {literal}\n")
        elif target == CodeTarget.AUTOLISP:
            statements.append(f"  (setq facts_json (strcat facts_json {literal}))\n")
        else:
            statements.append(f"    facts_json = facts_json & {literal}\n")
    return "".join(statements)


def render_recipe(recipe: CodeRecipe) -> str:
    """Return bounded source from a validated recipe; full-envelope sizing is later."""
    if not isinstance(recipe, CodeRecipe):
        raise CodeGenerationError("INVALID_ARGUMENT")
    literals = cast(dict[str, JsonValue], recipe_payload(recipe)["literals"])
    if recipe.template_id == "literal_geometry":
        substitutions = _geometry(literals, recipe.target)
    elif recipe.template_id == "serialize_entity_facts":
        substitutions = {"facts": _facts(literals["facts"], recipe.target)}
    else:
        handles = [_quote(handle, recipe.target) for handle in cast(list[str], literals["handles"])]
        substitutions = {"handles": _assign_records("handles", handles, recipe.target)}
    source = TEMPLATES[recipe.target, recipe.template_id].format(**substitutions)
    if len(source.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise CodeGenerationError("PAYLOAD_LIMIT")
    if recipe.target == CodeTarget.VBA and any(len(line) > 1023 for line in source.splitlines()):
        raise CodeGenerationError("STATIC_VALIDATION_FAILED")
    return source
