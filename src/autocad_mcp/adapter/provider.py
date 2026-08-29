"""Composition seam for supplying a synchronous AutoCAD adapter."""

from collections.abc import Callable
from typing import Protocol

from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode, AutoCADAdapter


class AdapterProvider(Protocol):
    """Supplies an adapter for one service invocation."""

    def get(self) -> AutoCADAdapter: ...


class StaticAdapterProvider:
    """Return the adapter supplied at construction, primarily for tests."""

    def __init__(self, adapter: AutoCADAdapter) -> None:
        self._adapter = adapter

    def get(self) -> AutoCADAdapter:
        return self._adapter


class WindowsAdapterProvider:
    """Construct a Windows adapter without loading its implementation on import."""

    def __init__(self, factory: Callable[[], AutoCADAdapter] | None = None) -> None:
        self._factory = factory

    def get(self) -> AutoCADAdapter:
        if self._factory is not None:
            return self._factory()
        try:
            from autocad_mcp.adapter.windows import WindowsAutoCADAdapter
        except ModuleNotFoundError as error:
            if error.name != "autocad_mcp.adapter.windows":
                raise
            raise AdapterError(
                AdapterErrorCode.AUTOCAD_UNAVAILABLE,
                "Windows AutoCAD adapter is unavailable",
                retryable=True,
            ) from error

        return WindowsAutoCADAdapter()
