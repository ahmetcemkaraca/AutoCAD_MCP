"""Strict literal-only contracts; no rendering or execution capabilities."""

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast

from autocad_mcp.core.models import JsonValue

MAX_RECIPE_BYTES: Final = 16_384
MAX_ARTIFACT_BYTES: Final = 65_536
TEMPLATE_VERSION: Final = "1.0.0"
TEMPLATE_IDS: Final = frozenset({"literal_geometry", "serialize_entity_facts", "iterate_handles"})
HUMAN_REVIEW_WARNING: Final = "Generated text was not executed; review it outside AutoCAD MCP."
_ERROR_CODES: Final = frozenset(
    {
        "INVALID_ARGUMENT",
        "UNSUPPORTED_TARGET",
        "UNSUPPORTED_TEMPLATE",
        "UNSUPPORTED_TEMPLATE_VERSION",
        "PAYLOAD_LIMIT",
        "STATIC_VALIDATION_FAILED",
    }
)


class CodeGenerationError(ValueError):
    """Private stable failure vocabulary; never includes supplied data."""

    code: str

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "INVALID_ARGUMENT"
        super().__init__(self.code)


class CodeTarget(StrEnum):
    PYTHON = "python"
    AUTOLISP = "autolisp"
    VBA = "vba"


def _invalid() -> CodeGenerationError:
    return CodeGenerationError("INVALID_ARGUMENT")


def _object(value: object, keys: set[str] | None = None) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _invalid()
    if keys is not None and (len(value) != len(keys) or set(value) != keys):
        raise _invalid()
    if any(type(key) is not str for key in value):
        raise _invalid()
    return cast(Mapping[str, object], value)


def _items(value: object, maximum: int, minimum: int = 0) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise _invalid()
    return cast(list[object], value)


def _text(value: object, maximum: int, minimum: int = 0) -> str:
    if type(value) is not str or not minimum <= len(value) <= maximum:
        raise _invalid()
    if any(character == "\0" or 0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise _invalid()
    return value


def _number(value: object) -> float:
    if type(value) not in (int, float) or not -1e15 <= value <= 1e15:  # type: ignore[operator]
        raise _invalid()
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        raise _invalid()
    return number if number != 0 else 0.0


def _point(value: object) -> list[JsonValue]:
    return [_number(item) for item in _items(value, 3, 3)]


def _handle(value: object) -> str:
    handle = _text(value, 16, 1)
    if re.fullmatch(r"[0-9A-Fa-f]+", handle) is None:
        raise _invalid()
    return handle.upper()


def _scalar(value: object) -> JsonValue:
    if value is None or type(value) is bool:
        return cast(JsonValue, value)
    if type(value) is str:
        return _text(value, 1024)
    if type(value) is int:
        if abs(value) > 2**53 - 1:
            raise _invalid()
        return value
    return _number(value)


def _geometry(literals: Mapping[str, object]) -> dict[str, JsonValue]:
    _object(literals, {"lines", "circles"})
    lines: list[JsonValue] = []
    circles: list[JsonValue] = []
    for value in _items(literals["lines"], 64):
        line = _object(value, {"start", "end"})
        lines.append({"start": _point(line["start"]), "end": _point(line["end"])})
    for value in _items(literals["circles"], 64):
        circle = _object(value, {"center", "radius"})
        radius = _number(circle["radius"])
        if radius <= 0:
            raise _invalid()
        circles.append({"center": _point(circle["center"]), "radius": radius})
    if not lines and not circles:
        raise _invalid()
    return {"lines": lines, "circles": circles}


def _facts(literals: Mapping[str, object]) -> dict[str, JsonValue]:
    _object(literals, {"facts"})
    facts: list[JsonValue] = []
    handles: set[str] = set()
    for value in _items(literals["facts"], 64, 1):
        fact = _object(value, {"handle", "object_name", "layer", "properties"})
        handle = _handle(fact["handle"])
        if handle in handles:
            raise _invalid()
        handles.add(handle)
        properties = _object(fact["properties"])
        if len(properties) > 16:
            raise _invalid()
        facts.append(
            {
                "handle": handle,
                "object_name": _text(fact["object_name"], 255, 1),
                "layer": _text(fact["layer"], 255, 1),
                "properties": {
                    _text(key, 128, 1): _scalar(item) for key, item in properties.items()
                },
            }
        )
    return {"facts": facts}


def _normalize(template_id: str, value: object) -> dict[str, JsonValue]:
    literals = _object(value)
    if template_id == "literal_geometry":
        return _geometry(literals)
    if template_id == "serialize_entity_facts":
        return _facts(literals)
    _object(literals, {"handles"})
    handles = [_handle(item) for item in _items(literals["handles"], 256, 1)]
    if len(set(handles)) != len(handles):
        raise _invalid()
    return {"handles": cast(list[JsonValue], handles)}


def _freeze(value: JsonValue) -> JsonValue:
    # JsonValue is the wire type; immutable storage uses read-only mappings/tuples.
    if isinstance(value, dict):
        return cast(
            JsonValue, MappingProxyType({key: _freeze(item) for key, item in value.items()})
        )
    if isinstance(value, list):
        return cast(JsonValue, tuple(_freeze(item) for item in value))
    return value


def _thaw(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_thaw(item) for item in value]
    return cast(JsonValue, value)


def _json_bytes(payload: dict[str, JsonValue]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


@dataclass(frozen=True)
class CodeRecipe:
    schema_version: Literal["1"]
    template_id: str
    template_version: str
    target: CodeTarget
    literals: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != "1":
            raise _invalid()
        for value in (self.template_id, self.template_version):
            if type(value) is not str:
                raise _invalid()
        if not isinstance(self.target, str | CodeTarget):
            raise _invalid()
        try:
            target = CodeTarget(self.target)
        except ValueError:
            raise CodeGenerationError("UNSUPPORTED_TARGET") from None
        if self.template_id not in TEMPLATE_IDS:
            raise CodeGenerationError("UNSUPPORTED_TEMPLATE")
        if self.template_version != TEMPLATE_VERSION:
            raise CodeGenerationError("UNSUPPORTED_TEMPLATE_VERSION")
        normalized = _normalize(self.template_id, self.literals)
        # Check original JSON numbers/case/escaping, before normalization changes bytes.
        original: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "target": target.value,
            "literals": _thaw(self.literals),
        }
        if len(_json_bytes(original)) > MAX_RECIPE_BYTES:
            raise CodeGenerationError("PAYLOAD_LIMIT")
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "literals", _freeze(normalized))


@dataclass(frozen=True)
class StaticFinding:
    rule_id: str
    severity: Literal["error", "warning"]
    location: str
    message: str


@dataclass(frozen=True)
class GeneratedCodeArtifact:
    target: CodeTarget
    template_id: str
    template_version: str
    source: str
    digest: str
    findings: tuple[StaticFinding, ...]
    executed: Literal[False]
    warning: Literal["Generated text was not executed; review it outside AutoCAD MCP."]

    def __post_init__(self) -> None:
        if self.executed is not False or self.warning != HUMAN_REVIEW_WARNING:
            raise _invalid()
        object.__setattr__(self, "findings", tuple(self.findings))


def decode_recipe(payload: object) -> CodeRecipe:
    """Decode a closed JSON-compatible mapping; all rejection text is redacted."""
    values = _object(
        payload,
        {
            "schema_version",
            "template_id",
            "template_version",
            "target",
            "literals",
        },
    )
    return CodeRecipe(
        cast(Literal["1"], values["schema_version"]),
        cast(str, values["template_id"]),
        cast(str, values["template_version"]),
        cast(CodeTarget, values["target"]),
        cast(Mapping[str, JsonValue], values["literals"]),
    )


def recipe_payload(recipe: CodeRecipe) -> dict[str, JsonValue]:
    """Return a fresh mutable wire payload detached from the immutable recipe."""
    return {
        "schema_version": recipe.schema_version,
        "template_id": recipe.template_id,
        "template_version": recipe.template_version,
        "target": recipe.target.value,
        "literals": _thaw(recipe.literals),
    }


def canonical_recipe_bytes(recipe: CodeRecipe) -> bytes:
    """Return deterministic normalized compact JSON for digest provenance."""
    return _json_bytes(recipe_payload(recipe))
