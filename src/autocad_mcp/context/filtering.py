"""Shared canonical context ordering and literal glob/filter semantics."""

from __future__ import annotations

from collections.abc import Mapping
from fnmatch import fnmatchcase
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast
from unicodedata import normalize

from autocad_mcp.context.models import EntityContext, EntityQueryFilters
from autocad_mcp.context.pagination import entity_sort_key

if TYPE_CHECKING:
    from autocad_mcp.adapter.context_protocol import AdapterEntityReadRequest
    from autocad_mcp.core.models import JsonValue


class FilterIdentity(Protocol):
    @property
    def space_kind(self) -> str: ...
    @property
    def layout_name(self) -> str | None: ...
    @property
    def handle(self) -> str: ...
    @property
    def object_name(self) -> str: ...
    @property
    def layer(self) -> Mapping[str, JsonValue]: ...
    @property
    def bounds(self) -> tuple[float, float, float, float, float, float] | None: ...


def entity_order(raw: FilterIdentity) -> tuple[int, str, int, str]:
    view = SimpleNamespace(
        space=SimpleNamespace(kind=raw.space_kind, layout_name=raw.layout_name),
        identity=SimpleNamespace(handle=raw.handle),
    )
    return entity_sort_key(cast(EntityContext, view))


def layer_glob_matches(pattern: str, value: str) -> bool:
    # Escape set syntax; stdlib star translation avoids exponential backtracking.
    return fnmatchcase(value, pattern.replace("[", "[[]"))


def matches_filters(
    item: FilterIdentity, request: AdapterEntityReadRequest, filters: EntityQueryFilters
) -> bool:
    def nfc(value: str) -> str:
        return normalize("NFC", value)

    for values, value in (
        (filters.spaces, item.space_kind),
        (filters.layout_names, item.layout_name or ""),
        (filters.entity_types, item.object_name),
        (filters.handles, item.handle),
    ):
        if values and nfc(value) not in values:
            return False
    layer = nfc(cast(str, item.layer.get("name", "")))
    if (filters.layer_names or filters.layer_globs) and not (
        layer in filters.layer_names
        or any(layer_glob_matches(pattern, layer) for pattern in filters.layer_globs)
    ):
        return False
    if request.intersects_wcs is not None:
        if item.space_kind == "block_definition" or item.bounds is None:
            return False
        query = request.intersects_wcs
        if any(
            item.bounds[axis] > query[axis + 3] or item.bounds[axis + 3] < query[axis]
            for axis in range(3)
        ):
            return False
    return True
