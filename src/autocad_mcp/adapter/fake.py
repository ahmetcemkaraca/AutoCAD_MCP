"""Deterministic adapter fake for portable contract tests."""

from autocad_mcp.adapter.capabilities import AdapterCapability, AdapterCapabilityReport
from autocad_mcp.adapter.protocol import (
    AdapterError,
    AdapterErrorCode,
    ConnectionInfo,
    EntityDetails,
    EntitySummary,
)


class FakeAutoCADAdapter:
    """Store contract values only; this is not an AutoCAD or COM emulator."""

    def __init__(
        self,
        *,
        connected: bool = True,
        document_name: str | None = "contract.dwg",
        entities: tuple[EntityDetails, ...] | None = None,
    ) -> None:
        self._connected = connected
        self._document_name = document_name
        self._entities = entities if entities is not None else (
            EntityDetails(1001, "10", "AcDbLine", "0", {"color": 256, "linetype": "ByLayer"}),
        )
        self._next_error: AdapterError | None = None
        self._calls: tuple[tuple[str, object], ...] = ()

    def fail_next(self, error: AdapterError) -> None:
        """Make the next adapter operation raise this public error once."""
        self._next_error = error

    @property
    def calls(self) -> tuple[tuple[str, object], ...]:
        """Return the immutable record of adapter operations."""
        return self._calls

    def _connection_info(self) -> ConnectionInfo:
        if not self._connected:
            return ConnectionInfo(False, None, None, None, None, None, AdapterCapabilityReport())
        if self._document_name is None:
            return ConnectionInfo(
                True,
                "AutoCAD",
                "contract",
                "contract",
                None,
                None,
                AdapterCapabilityReport(frozenset({AdapterCapability.CONNECTION})),
            )
        return ConnectionInfo(
            True,
            "AutoCAD",
            "contract",
            "contract",
            self._document_name,
            True,
            AdapterCapabilityReport(frozenset(AdapterCapability)),
        )

    def status(self) -> ConnectionInfo:
        self._calls += (("status", None),)
        error = self._next_error
        self._next_error = None
        if error is not None:
            raise error
        return self._connection_info()

    def reconnect(self) -> ConnectionInfo:
        self._calls += (("reconnect", None),)
        error = self._next_error
        self._next_error = None
        if error is not None:
            raise error
        self._connected = True
        return self._connection_info()

    def list_entities(self) -> tuple[EntitySummary, ...]:
        self._calls += (("list_entities", None),)
        error = self._next_error
        self._next_error = None
        if error is not None:
            raise error
        if not self._connected:
            raise AdapterError(
                AdapterErrorCode.AUTOCAD_UNAVAILABLE,
                "Full AutoCAD is unavailable",
                retryable=True,
            )
        if self._document_name is None:
            raise AdapterError(AdapterErrorCode.NO_ACTIVE_DOCUMENT, "No active document")
        return tuple(
            EntitySummary(entity.object_id, entity.handle, entity.object_name, entity.layer)
            for entity in self._entities
        )

    def get_entity_info(self, object_id: int) -> EntityDetails:
        self._calls += (("get_entity_info", object_id),)
        error = self._next_error
        self._next_error = None
        if error is not None:
            raise error
        if not self._connected:
            raise AdapterError(
                AdapterErrorCode.AUTOCAD_UNAVAILABLE,
                "Full AutoCAD is unavailable",
                retryable=True,
            )
        if self._document_name is None:
            raise AdapterError(AdapterErrorCode.NO_ACTIVE_DOCUMENT, "No active document")
        for entity in self._entities:
            if entity.object_id == object_id:
                return entity
        raise AdapterError(
            AdapterErrorCode.ENTITY_NOT_FOUND,
            "Entity was not found",
            details={"object_id": object_id},
        )
