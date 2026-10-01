"""Strict constructor and JSON-boundary validation using standard-library types."""

from collections.abc import Hashable, Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from functools import cache
from math import isfinite
from re import fullmatch
from types import MappingProxyType, UnionType
from typing import Any, Literal, Union, cast, get_args, get_origin, get_type_hints

MAX_SCALAR_MAGNITUDE = 1e15
MAX_ENTITY_BYTES = 256 * 1024
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_RESULT_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_ENTITIES = 10000
MAX_COMPLETE_RELATIONSHIPS = 100000
MAX_PAGE_ENTITIES = 500
MAX_ENTITY_RELATIONSHIPS = 100
MAX_PAGE_RELATIONSHIPS = 10000
MAX_VERTICES = 10000
MAX_BLOCK_ATTRIBUTES = 512
MAX_TEXT_CHARACTERS = 65536
MAX_REQUEST_HANDLES = 256
MAX_FILTER_VALUES = 64
MAX_FILTER_CHARACTERS = 128
MAX_CURSOR_BYTES = 2048
MAX_SEMANTIC_HANDLES = 2000


class ContextValidationError(ValueError):
    """Redacted domain failure convertible to the core's structured tool error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INVALID_ARGUMENT",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = MappingProxyType(dict(details or {}))


def require(condition: bool, message: str, *, code: str = "INVALID_ARGUMENT") -> None:
    if not condition:
        raise ContextValidationError(message, code=code)


def normalize_handle(value: str) -> str:
    require(
        isinstance(value, str) and fullmatch(r"[0-9a-fA-F]{1,128}", value) is not None,
        "Handle must contain 1-128 hexadecimal characters without a prefix",
    )
    return value.upper()


@cache
def record_hints(record_type: Any) -> dict[str, Any]:
    return get_type_hints(record_type)


def _literal(value: Any, annotation: Any, decode: bool) -> Any:
    require(
        any(type(value) is type(item) and value == item for item in get_args(annotation)),
        "Value does not match the declared literal",
    )
    return value


def _sequence(value: Any, annotation: Any, decode: bool) -> tuple[Any, ...]:
    require(isinstance(value, tuple | list), "Expected an array")
    require(len(value) <= MAX_COMPLETE_RELATIONSHIPS, "Array exceeds bound", code="PAYLOAD_LIMIT")
    arguments = get_args(annotation)
    if len(arguments) == 2 and arguments[1] is Ellipsis:
        return tuple(convert_value(item, arguments[0], decode=decode) for item in value)
    require(len(value) == len(arguments), "Array has an incorrect length")
    return tuple(
        convert_value(item, hint, decode=decode)
        for item, hint in zip(value, arguments, strict=True)
    )


def _mapping(value: Any, annotation: Any, decode: bool) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), "Expected an object")
    require(len(value) <= MAX_BLOCK_ATTRIBUTES, "Too many block attributes", code="PAYLOAD_LIMIT")
    key_hint, value_hint = get_args(annotation)
    return MappingProxyType(
        {
            convert_value(key, key_hint, decode=decode): convert_value(
                item, value_hint, decode=decode
            )
            for key, item in value.items()
        }
    )


def _datetime(value: Any, decode: bool) -> datetime:
    if decode and isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise ContextValidationError("Invalid capture timestamp") from None
    require(
        isinstance(value, datetime) and value.utcoffset() is not None,
        "Capture timestamp must be timezone-aware",
    )
    try:
        value = value.astimezone(UTC)
    except OverflowError:
        raise ContextValidationError(
            "Capture timestamp is outside the UTC datetime range"
        ) from None
    result: datetime = value.replace(microsecond=value.microsecond // 1000 * 1000)
    return result


def _union(value: Any, annotation: Any, decode: bool) -> Any:
    errors = []
    for hint in get_args(annotation):
        try:
            return convert_value(value, hint, decode=decode)
        except ContextValidationError as error:
            errors.append(error)
    for failure in errors:
        if failure.code != "INVALID_ARGUMENT":
            raise failure
    raise ContextValidationError("Value does not match any declared variant")


def _primitive(value: Any, annotation: Any) -> Any:
    if annotation is float:
        require(type(value) in (int, float), "Expected a number, not a boolean")
        require(
            abs(value) <= MAX_SCALAR_MAGNITUDE and isfinite(value),
            "Number must be finite and within 1e15",
        )
    elif annotation is int:
        require(type(value) is int, "Expected an integer, not a boolean")
        require(abs(value) <= MAX_SCALAR_MAGNITUDE, "Integer exceeds 1e15")
    elif annotation is str:
        require(isinstance(value, str), "Expected a string")
        require(len(value) <= MAX_TEXT_CHARACTERS, "String exceeds bound", code="PAYLOAD_LIMIT")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ContextValidationError("String must be valid UTF-8") from None
    elif annotation is bool:
        require(type(value) is bool, "Expected a boolean")
    elif annotation is type(None):
        require(value is None, "Expected null")
    else:
        raise ContextValidationError("Unsupported value type")
    return value


def convert_value(value: Any, annotation: Any, *, decode: bool = False) -> Any:
    """Validate a typed value, copying containers without coercing primitives."""
    converters = {
        Literal: _literal,
        tuple: _sequence,
        Mapping: _mapping,
        UnionType: _union,
        Union: _union,
    }
    converter = converters.get(get_origin(annotation))
    if converter:
        return converter(value, annotation, decode)
    if annotation is datetime:
        return _datetime(value, decode)
    if isinstance(annotation, type) and is_dataclass(annotation):
        if decode:
            return record_from_payload(annotation, value)
        require(type(value) is annotation, "Expected a validated context record")
        return value
    return _primitive(value, annotation)


def record_from_payload(record_type: type[Any], payload: Any) -> Any:
    """Decode exactly the declared fields; reject unknown and missing keys."""
    require(isinstance(payload, Mapping), "Expected a record object")
    if "schema_version" in payload:
        require(
            payload["schema_version"] == "1.0",
            "Unsupported snapshot schema version",
            code="UNSUPPORTED_SCHEMA_VERSION",
        )
    hints = record_hints(cast(Hashable, record_type))
    require(payload.keys() == hints.keys(), "Record contains unknown or missing fields")
    return record_type(
        **{name: convert_value(payload[name], hint, decode=True) for name, hint in hints.items()}
    )


def _field_bounds(record: Any) -> None:
    for field in fields(record):
        name, value = field.name, getattr(record, field.name)
        if value is None:
            continue
        if name.endswith("handle"):
            object.__setattr__(record, name, normalize_handle(value))
        if name in ("handles", "subject_handles"):
            normalized = tuple(normalize_handle(handle) for handle in value)
            require(len(set(normalized)) == len(normalized), "Duplicate normalized handles")
            object.__setattr__(record, name, normalized)
        if name in (
            "display_name",
            "name",
            "layout_name",
            "active_layout_name",
            "style_name",
            "effective_name",
            "object_name",
            "dxf_name",
            "visual_style",
            "linetype",
        ):
            require(len(value) <= 255, "Name exceeds 255 code points", code="PAYLOAD_LIMIT")
        if name.endswith("count") or name in ("object_id", "viewport_object_id", "insunits_code"):
            require(value >= 0, "Count or session-local identifier must be nonnegative")


def _session_scopes(record: Any) -> None:
    for name in ("object_id", "viewport_object_id"):
        if hasattr(record, name):
            value, scope = getattr(record, name), getattr(record, name + "_scope")
            require((value is None) == (scope is None), "Session identifier requires session scope")


def _geometry(record: Any) -> None:
    if hasattr(record, "radius"):
        require(record.radius > 0, "Radius must be positive")
    if type(record).__name__ == "Bounds3D":
        require(
            all(
                getattr(record.minimum, axis) <= getattr(record.maximum, axis)
                for axis in ("x", "y", "z")
            ),
            "Inverted WCS bounds",
        )
    if type(record).__name__ == "PolylineGeometry":
        require(len(record.vertices_wcs) <= MAX_VERTICES, "Too many vertices", code="PAYLOAD_LIMIT")
        require(len(record.bulges) in (0, len(record.vertices_wcs)), "Bulges must match vertices")


def _filters(record: Any) -> None:
    for name in ("layout_names", "entity_types", "layer_names", "layer_globs"):
        values = getattr(record, name)
        require(len(values) <= MAX_FILTER_VALUES, "Too many filter values", code="PAYLOAD_LIMIT")
        require(
            all(len(item) <= MAX_FILTER_CHARACTERS for item in values),
            "Filter string exceeds 128 code points",
            code="PAYLOAD_LIMIT",
        )
    require(len(record.handles) <= MAX_REQUEST_HANDLES, "Too many handles", code="PAYLOAD_LIMIT")
    require(len(record.spaces) <= 3, "Too many space filters")


def _evidence(record: Any) -> None:
    if record.kind == "cad_fact":
        require(
            isinstance(record.fact_path, str)
            and fullmatch(r"/entities/[0-9A-F]+/(?:[^~]|~[01])+", record.fact_path) is not None,
            "CAD evidence requires a JSON Pointer rooted under /entities/{handle}",
        )
    else:
        require(record.fact_path is None, "Non-CAD evidence cannot claim a CAD fact pointer")


def _interpretation(record: Any) -> None:
    require(
        0 < len(record.subject_handles) <= MAX_SEMANTIC_HANDLES, "Invalid semantic handle scope"
    )
    if record.confidence is not None:
        require(0 <= record.confidence <= 1, "Confidence must be between 0 and 1")
    if record.state == "confirmed":
        require(
            any(item.kind == "user_confirmation" for item in record.evidence),
            "Confirmed interpretation requires user confirmation evidence",
        )
    elif record.state == "inferred":
        require(
            bool(record.evidence) and record.confidence is not None,
            "Inferred interpretation requires evidence and confidence",
        )
    else:
        require(record.confidence is None, "Unknown interpretation has no confidence")
    for item in record.evidence:
        if item.kind == "cad_fact":
            require(
                item.fact_path.split("/")[2] in record.subject_handles,
                "CAD evidence must reference an interpretation subject",
            )


def _page(record: Any) -> None:
    require(
        1 <= record.page_size <= MAX_PAGE_ENTITIES and 0 <= record.returned <= record.page_size,
        "Invalid page size or returned count",
    )
    require(record.has_more == (record.next_cursor is not None), "Cursor does not match has_more")
    if record.next_cursor is not None:
        require(
            0 < len(record.next_cursor.encode("utf-8")) <= MAX_CURSOR_BYTES,
            "Cursor exceeds byte bound",
            code="PAYLOAD_LIMIT",
        )


def _entity(record: Any) -> None:
    from .serialization import record_to_json

    if hasattr(record, "relationships"):
        require(
            len(record.relationships) <= MAX_ENTITY_RELATIONSHIPS,
            "Too many entity relationships",
            code="PAYLOAD_LIMIT",
        )
    measured = len(record_to_json(record).encode("utf-8"))
    if measured > MAX_ENTITY_BYTES:
        raise ContextValidationError(
            "Entity exceeds 256 KiB",
            code="PAYLOAD_LIMIT",
            details={"entity_handle": record.identity.handle, "measured_bytes": measured},
        )


def _collection(record: Any) -> None:
    name = type(record).__name__
    limit = MAX_SNAPSHOT_ENTITIES if name == "DrawingSnapshot" else MAX_PAGE_ENTITIES
    require(
        len(record.entities) <= limit,
        "Too many entities",
        code="COMPLETE_SNAPSHOT_LIMIT" if name == "DrawingSnapshot" else "PAYLOAD_LIMIT",
    )
    if name == "DrawingSnapshot":
        require(
            sum(len(entity.relationships) for entity in record.entities)
            <= MAX_COMPLETE_RELATIONSHIPS,
            "Too many complete relationships",
            code="COMPLETE_SNAPSHOT_LIMIT",
        )
    if name == "AnalyzeDrawingResult":
        require(record.page.returned == len(record.entities), "Page count does not match entities")
        require(
            sum(len(entity.relationships) for entity in record.entities) <= MAX_PAGE_RELATIONSHIPS,
            "Too many page relationships",
            code="PAYLOAD_LIMIT",
        )


def _additional(record: Any) -> None:
    name = type(record).__name__
    if name == "DrawingFingerprint":
        require(
            not record.incomplete_reasons, "Complete fingerprint cannot have incomplete reasons"
        )
    if name == "GeometryTolerance":
        require(record.linear > 0 and record.angular_radians > 0, "Tolerances must be positive")
    if name == "ViewContext":
        require(record.width > 0 and record.height > 0, "View dimensions must be positive")
    if name == "DrawingUnits" and record.meters_per_unit is not None:
        require(record.meters_per_unit > 0, "Meters per unit must be positive")
    if name == "StyleFacts" and record.true_color_rgb is not None:
        require(
            all(0 <= item <= 255 for item in record.true_color_rgb), "RGB channels must be 0-255"
        )


def validate_record(record: Any) -> None:
    """Validate and freeze a freshly constructed domain record."""
    for name, hint in record_hints(cast(Hashable, type(record))).items():
        if name == "schema_version":
            require(
                getattr(record, name) == "1.0",
                "Unsupported snapshot schema version",
                code="UNSUPPORTED_SCHEMA_VERSION",
            )
        object.__setattr__(record, name, convert_value(getattr(record, name), hint))
    _field_bounds(record)
    _session_scopes(record)
    _geometry(record)
    _additional(record)
    validators = {
        "EntityQueryFilters": _filters,
        "SemanticEvidenceRef": _evidence,
        "SemanticInterpretation": _interpretation,
        "PageInfo": _page,
        "EntityContext": _entity,
        "EntitySummary": _entity,
        "DrawingSnapshot": _collection,
        "AnalyzeDrawingResult": _collection,
        "EntityContextBatch": _collection,
    }
    validator = validators.get(type(record).__name__)
    if validator:
        validator(record)
