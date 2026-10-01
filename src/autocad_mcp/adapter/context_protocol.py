"""Immutable JSON-only additive context boundary; no Windows or COM dependencies."""

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, Protocol, cast, get_origin

from autocad_mcp.adapter.protocol import AutoCADAdapter
from autocad_mcp.context.models import Bounds3D, EntityQueryFilters, EntitySpace, Point3D
from autocad_mcp.context.serialization import record_to_json
from autocad_mcp.context.validation import (
    MAX_CURSOR_BYTES,
    MAX_ENTITY_BYTES,
    MAX_REQUEST_HANDLES,
    _field_bounds,
    convert_value,
    record_hints,
    require,
)
from autocad_mcp.core.models import JsonValue

CONTEXT_ADAPTER_SCHEMA_VERSION = "1.0"


def _charge_json(used: list[int], amount: int) -> None:
    used[0] += amount
    require(used[0] <= MAX_ENTITY_BYTES, "Raw JSON exceeds byte bound", code="PAYLOAD_LIMIT")


def _freeze_json(value: object, *, depth: int = 0, used: list[int] | None = None) -> Any:
    if used is None:
        used = [0]
    require(depth <= 16, "Raw JSON nesting exceeds bound", code="PAYLOAD_LIMIT")
    if isinstance(value, Mapping):
        require(len(value) <= 512, "Raw JSON object exceeds bound", code="PAYLOAD_LIMIT")
        _charge_json(used, 2)
        result = {}
        for index, (key, item) in enumerate(value.items()):
            convert_value(key, str)
            _charge_json(used, len(record_to_json(key).encode("utf-8")) + 1 + (index > 0))
            result[key] = _freeze_json(item, depth=depth + 1, used=used)
        return MappingProxyType(result)
    if type(value) in (tuple, list):
        sequence = cast(tuple[object, ...] | list[object], value)
        require(len(sequence) <= 10000, "Raw JSON array exceeds bound", code="PAYLOAD_LIMIT")
        _charge_json(used, 2)
        result_items = []
        for index, item in enumerate(sequence):
            _charge_json(used, int(index > 0))
            result_items.append(_freeze_json(item, depth=depth + 1, used=used))
        return tuple(result_items)
    require(type(value) in (str, int, float, bool, type(None)), "Raw fact is not a JSON value")
    converted = convert_value(value, type(value))
    _charge_json(used, len(record_to_json(converted).encode("utf-8")))
    return converted


def _bounded_text(value: str | None, limit: int, *, optional: bool = False) -> None:
    require(
        (optional and value is None)
        or (
            isinstance(value, str)
            and bool(value)
            and "\0" not in value
            and len(value.encode("utf-8")) <= limit
        ),
        "Raw text exceeds bound",
        code="PAYLOAD_LIMIT",
    )


def _bounds(value: tuple[float, float, float, float, float, float] | None) -> Bounds3D | None:
    if value is None:
        return None
    return Bounds3D(Point3D(*value[:3]), Point3D(*value[3:]))


class _RawRecord:
    __slots__ = ()

    def __post_init__(self) -> None:
        if hasattr(self, "schema_version"):
            require(
                self.schema_version == "1.0",
                "Unsupported context adapter schema",
                code="UNSUPPORTED_SCHEMA_VERSION",
            )
        for name, hint in record_hints(cast(Hashable, type(self))).items():
            value = getattr(self, name)
            # Raw JSON mappings are a proxy-isolation boundary, not mutable domain data.
            if get_origin(hint) is Mapping:
                require(isinstance(value, Mapping), "Expected raw JSON object")
                value = _freeze_json(value)
            elif (
                isinstance(self, AdapterEntityFacts)
                and name in ("block", "text", "dimension")
                and value is not None
            ):
                require(isinstance(value, Mapping), "Expected raw JSON object")
                value = _freeze_json(value)
            else:
                value = convert_value(value, hint)
            object.__setattr__(self, name, value)
        if not isinstance(self, ContextInclude):
            _field_bounds(self)
        _validate_raw(self)


@dataclass(frozen=True, slots=True)
class AdapterContextIssue(_RawRecord):
    code: str
    capability: str
    member: str | None
    entity_handle: str | None
    message: str


@dataclass(frozen=True, slots=True)
class AdapterDocumentIdentity(_RawRecord):
    display_name: str
    full_path: str | None
    database_fingerprint_guid: str | None
    session_document_id: str
    is_saved: bool
    is_read_only: bool


@dataclass(frozen=True, slots=True)
class AdapterDocumentContext(_RawRecord):
    schema_version: Literal["1.0"]
    identity: AdapterDocumentIdentity
    display_space: Literal["model", "paper", "model_in_paper_viewport"]
    active_layout_name: str
    viewport_object_id: int | None
    ucs: Mapping[str, JsonValue]
    view: Mapping[str, JsonValue]
    units: Mapping[str, JsonValue]
    issues: tuple[AdapterContextIssue, ...]


@dataclass(frozen=True, slots=True)
class ContextInclude(_RawRecord):
    geometry: bool
    bounding_box: bool
    visual_style: bool
    block: bool
    text: bool
    dimension: bool


@dataclass(frozen=True, slots=True)
class AdapterDocumentRevisionToken(_RawRecord):
    schema_version: Literal["1.0"]
    session_document_id: str
    source: str
    opaque_value: str


@dataclass(frozen=True, slots=True)
class AdapterEntityReadRequest(_RawRecord):
    spaces: tuple[str, ...]
    layout_names: tuple[str, ...]
    entity_types: tuple[str, ...]
    layer_names: tuple[str, ...]
    layer_globs: tuple[str, ...]
    handles: tuple[str, ...]
    intersects_wcs: tuple[float, float, float, float, float, float] | None
    include: ContextInclude
    page_size: int
    cursor: str | None


@dataclass(frozen=True, slots=True)
class AdapterEntityFacts(_RawRecord):
    schema_version: Literal["1.0"]
    handle: str
    object_id: int | None
    object_name: str
    dxf_name: str | None
    space_kind: Literal["model", "paper", "block_definition"]
    layout_name: str | None
    owner_block_handle: str | None
    layer: Mapping[str, JsonValue]
    style: Mapping[str, JsonValue]
    geometry: Mapping[str, JsonValue]
    bounds: tuple[float, float, float, float, float, float] | None
    block: Mapping[str, JsonValue] | None
    text: Mapping[str, JsonValue] | None
    dimension: Mapping[str, JsonValue] | None
    issues: tuple[AdapterContextIssue, ...]


@dataclass(frozen=True, slots=True)
class AdapterEntityPage(_RawRecord):
    schema_version: Literal["1.0"]
    revision_token: AdapterDocumentRevisionToken
    entities: tuple[AdapterEntityFacts, ...]
    next_cursor: str | None
    partial: bool
    issues: tuple[AdapterContextIssue, ...]


def request_filters(request: AdapterEntityReadRequest) -> EntityQueryFilters:
    """Adapt the exact raw filter fields to the existing validated query contract."""
    return EntityQueryFilters(
        cast(Any, request.spaces),
        request.layout_names,
        request.entity_types,
        request.layer_names,
        request.layer_globs,
        request.handles,
        _bounds(request.intersects_wcs),
    )


def _validate_raw(record: _RawRecord) -> None:
    if isinstance(record, AdapterEntityFacts):
        EntitySpace(record.space_kind, record.layout_name, record.owner_block_handle)
        _bounds(record.bounds)
        require(
            len(record_to_json(record).encode("utf-8")) <= MAX_ENTITY_BYTES,
            "Raw entity exceeds byte bound",
            code="PAYLOAD_LIMIT",
        )
    if isinstance(record, AdapterEntityReadRequest):
        filters = request_filters(record)
        object.__setattr__(record, "handles", filters.handles)
        require(1 <= record.page_size <= 500, "Invalid raw page size")
        _bounded_text(record.cursor, MAX_CURSOR_BYTES, optional=True)
    if isinstance(record, AdapterEntityPage):
        require(len(record.entities) <= 500, "Raw page count exceeds bound", code="PAYLOAD_LIMIT")
        _bounded_text(record.next_cursor, MAX_CURSOR_BYTES, optional=True)
    if isinstance(record, AdapterDocumentRevisionToken):
        _bounded_text(record.opaque_value, 512)
        _bounded_text(record.source, 255)
        _bounded_text(record.session_document_id, 255)
    if isinstance(record, AdapterDocumentIdentity):
        # Shared field validation already enforces the domain's codepoint bound.
        require(
            bool(record.display_name) and "\0" not in record.display_name,
            "Invalid document display name",
        )
        _bounded_text(record.session_document_id, 255)
    if hasattr(record, "issues"):
        require(
            len(record.issues) <= MAX_REQUEST_HANDLES,
            "Raw issue count exceeds bound",
            code="PAYLOAD_LIMIT",
        )


class ContextAutoCADAdapter(AutoCADAdapter, Protocol):
    def context_capabilities(self) -> tuple[str, ...]: ...
    def read_document_context(self) -> AdapterDocumentContext: ...
    def read_document_revision(self) -> AdapterDocumentRevisionToken: ...
    def read_entity_page(self, request: AdapterEntityReadRequest) -> AdapterEntityPage: ...
    def entity_facts_by_handles(
        self, handles: tuple[str, ...], include: ContextInclude
    ) -> tuple[AdapterEntityFacts, ...]: ...


class ContextAdapterProvider(Protocol):
    def get(self) -> ContextAutoCADAdapter: ...
