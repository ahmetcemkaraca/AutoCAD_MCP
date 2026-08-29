"""Pure values and the four-method public AutoCAD adapter protocol."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from autocad_mcp.adapter.capabilities import AdapterCapabilityReport
from autocad_mcp.core.models import JsonValue


class AdapterErrorCode(StrEnum):
    AUTOCAD_UNAVAILABLE = "AUTOCAD_UNAVAILABLE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    COM_BUSY = "COM_BUSY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AUTOCAD_OPERATION_FAILED = "AUTOCAD_OPERATION_FAILED"


class AdapterError(Exception):
    """A stable, redacted error from an adapter operation."""

    code: AdapterErrorCode
    public_message: str
    retryable: bool
    details: Mapping[str, JsonValue]

    def __init__(
        self,
        code: AdapterErrorCode,
        public_message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, JsonValue] | None = None,
    ) -> None:
        super().__init__(public_message)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "public_message", public_message)
        object.__setattr__(self, "retryable", retryable)
        object.__setattr__(self, "details", MappingProxyType(dict(details or {})))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("AdapterError is immutable")
        object.__setattr__(self, name, value)


@dataclass(frozen=True)
class ConnectionInfo:
    connected: bool
    product: str | None
    version: str | None
    release_hint: str | None
    active_document: str | None
    read_only: bool | None
    capabilities: AdapterCapabilityReport


@dataclass(frozen=True)
class EntitySummary:
    object_id: int
    handle: str
    object_name: str
    layer: str


@dataclass(frozen=True)
class EntityDetails:
    object_id: int
    handle: str
    object_name: str
    layer: str
    properties: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))


class AutoCADAdapter(Protocol):
    """The complete public AutoCAD read-only/status boundary."""

    def status(self) -> ConnectionInfo: ...

    def reconnect(self) -> ConnectionInfo: ...

    def list_entities(self) -> tuple[EntitySummary, ...]: ...

    def get_entity_info(self, object_id: int) -> EntityDetails: ...
