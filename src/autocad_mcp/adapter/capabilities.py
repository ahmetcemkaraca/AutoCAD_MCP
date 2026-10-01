"""Immutable capability values for the narrow AutoCAD adapter boundary."""

from dataclasses import dataclass, field
from enum import StrEnum


class AdapterCapability(StrEnum):
    """Read-only operations the adapter can support."""

    CONNECTION = "connection"
    ACTIVE_DOCUMENT = "active_document"
    LIST_ENTITIES = "list_entities"
    GET_ENTITY_INFO = "get_entity_info"


class AdapterCapabilityIssueCode(StrEnum):
    """Reasons a required AutoCAD member was not usable."""

    MEMBER_UNAVAILABLE = "MEMBER_UNAVAILABLE"
    MEMBER_ACCESS_FAILED = "MEMBER_ACCESS_FAILED"


@dataclass(frozen=True)
class AdapterCapabilityIssue:
    code: AdapterCapabilityIssueCode
    capability: AdapterCapability
    member: str
    message: str


@dataclass(frozen=True)
class AdapterCapabilityReport:
    available: frozenset[AdapterCapability] = field(default_factory=frozenset)
    issues: tuple[AdapterCapabilityIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "available", frozenset(self.available))
        object.__setattr__(self, "issues", tuple(self.issues))

    def supports(self, capability: AdapterCapability) -> bool:
        """Return whether the named read-only capability is available."""
        return capability in self.available
