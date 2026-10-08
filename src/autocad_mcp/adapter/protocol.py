"""Pure values and the four-method public AutoCAD adapter protocol."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import NoReturn, Protocol, Self, SupportsIndex, overload

from autocad_mcp.adapter.capabilities import AdapterCapabilityReport
from autocad_mcp.core.models import JsonValue


class _FrozenJsonDict(dict[str, JsonValue]):
    """A JSON-serializable mapping that rejects all mutation."""

    def __init__(self, values: Mapping[str, JsonValue]) -> None:
        super().__init__((key, _freeze_json_value(value)) for key, value in values.items())

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("JSON value is immutable")

    def __setitem__(self, key: str, value: JsonValue) -> None:
        self._immutable()

    def __delitem__(self, key: str) -> None:
        self._immutable()

    def __ior__(self, value: object) -> Self:  # type: ignore[misc,override]
        self._immutable()

    def clear(self) -> NoReturn:
        self._immutable()

    def pop(self, key: str, default: object = None) -> NoReturn:
        self._immutable()

    def popitem(self) -> NoReturn:
        self._immutable()

    def setdefault(self, key: str, default: JsonValue = None) -> NoReturn:
        self._immutable()

    def update(self, *args: object, **kwargs: JsonValue) -> NoReturn:
        self._immutable()


class _FrozenJsonList(list[JsonValue]):
    """A JSON-serializable sequence that rejects all mutation."""

    def __init__(self, values: list[JsonValue]) -> None:
        super().__init__(_freeze_json_value(value) for value in values)

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("JSON value is immutable")

    @overload
    def __setitem__(self, index: SupportsIndex, value: JsonValue, /) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[JsonValue], /) -> None: ...

    def __setitem__(
        self, index: SupportsIndex | slice, value: JsonValue | Iterable[JsonValue], /
    ) -> None:
        self._immutable()

    def __delitem__(self, index: SupportsIndex | slice, /) -> None:
        self._immutable()

    def __iadd__(self, value: Iterable[JsonValue], /) -> Self:  # type: ignore[misc,override]
        self._immutable()

    def __imul__(self, value: SupportsIndex, /) -> Self:
        self._immutable()

    def append(self, value: JsonValue, /) -> None:
        self._immutable()

    def clear(self) -> None:
        self._immutable()

    def extend(self, values: Iterable[JsonValue], /) -> None:
        self._immutable()

    def insert(self, index: SupportsIndex, value: JsonValue, /) -> None:
        self._immutable()

    def pop(self, index: SupportsIndex = -1, /) -> JsonValue:
        self._immutable()

    def remove(self, value: JsonValue, /) -> None:
        self._immutable()

    def reverse(self) -> None:
        self._immutable()

    def sort(self, *, key: object = None, reverse: bool = False) -> None:
        self._immutable()


def _freeze_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return _FrozenJsonDict(value)
    if isinstance(value, list):
        return _FrozenJsonList(value)
    return value


class AdapterErrorCode(StrEnum):
    AUTOCAD_UNAVAILABLE = "AUTOCAD_UNAVAILABLE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    COM_BUSY = "COM_BUSY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AUTOCAD_OPERATION_FAILED = "AUTOCAD_OPERATION_FAILED"


_EXCEPTION_BOOKKEEPING = frozenset(
    {"__traceback__", "__cause__", "__context__", "__suppress_context__", "__notes__"}
)


class AdapterError(Exception):
    """A stable, redacted error from an adapter operation.

    The public fields are sealed after construction; the interpreter's own exception
    bookkeeping (traceback, chaining, notes) stays writable so ``contextlib``,
    ``add_note`` and test frameworks can handle the instance normally.
    """

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
        object.__setattr__(self, "details", _FrozenJsonDict(details or {}))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if name not in _EXCEPTION_BOOKKEEPING and getattr(self, "_sealed", False):
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
        object.__setattr__(self, "properties", _FrozenJsonDict(self.properties))


class AutoCADAdapter(Protocol):
    """The complete public AutoCAD read-only/status boundary."""

    def status(self) -> ConnectionInfo: ...

    def reconnect(self) -> ConnectionInfo: ...

    def list_entities(self) -> tuple[EntitySummary, ...]: ...

    def get_entity_info(self, object_id: int) -> EntityDetails: ...
