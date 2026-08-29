"""Read-only production AutoCAD adapter using transient Windows COM sessions."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from autocad_mcp.adapter.capabilities import (
    AdapterCapability,
    AdapterCapabilityIssue,
    AdapterCapabilityIssueCode,
    AdapterCapabilityReport,
)
from autocad_mcp.adapter.protocol import (
    AdapterError,
    AdapterErrorCode,
    ConnectionInfo,
    EntityDetails,
    EntitySummary,
)
from autocad_mcp.adapter.windows_session import AutoCADSession, WindowsSessionManager, _com_error

_IDENTITY_MEMBERS = ("ObjectID", "Handle", "ObjectName", "Layer")
_OPTIONAL_PROPERTIES = (
    ("Color", "color"),
    ("Linetype", "linetype"),
    ("Length", "length"),
    ("Area", "area"),
    ("Volume", "volume"),
    ("Radius", "radius"),
    ("Center", "center"),
    ("StartPoint", "start_point"),
    ("EndPoint", "end_point"),
)
logger = logging.getLogger(__name__)


def _issue(
    code: AdapterCapabilityIssueCode, capability: AdapterCapability, member: str
) -> AdapterCapabilityIssue:
    return AdapterCapabilityIssue(
        code, capability, member, "Required AutoCAD member is unavailable"
    )


def _member(
    target: object, name: str, capability: AdapterCapability, issues: list[AdapterCapabilityIssue]
) -> object | None:
    try:
        return getattr(target, name)
    except AttributeError:
        issues.append(_issue(AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE, capability, name))
    except Exception:
        issues.append(_issue(AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED, capability, name))
    return None


def detect_capabilities(session: AutoCADSession) -> AdapterCapabilityReport:
    """Report supported operations from observed members, never product release text."""
    available: set[AdapterCapability] = set()
    issues: list[AdapterCapabilityIssue] = []
    if session.application is not None:
        available.add(AdapterCapability.CONNECTION)
    if session.document is None or session.model_space is None:
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    available.add(AdapterCapability.ACTIVE_DOCUMENT)
    try:
        entities = iter(session.model_space)
    except TypeError:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    except Exception:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    try:
        first = next(entities)
    except StopIteration:
        available.update({AdapterCapability.LIST_ENTITIES, AdapterCapability.GET_ENTITY_INFO})
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    except Exception:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    for member in _IDENTITY_MEMBERS:
        _member(first, member, AdapterCapability.LIST_ENTITIES, issues)
    if not issues:
        available.update({AdapterCapability.LIST_ENTITIES, AdapterCapability.GET_ENTITY_INFO})
    return AdapterCapabilityReport(frozenset(available), tuple(issues))


def _required(entity: object, name: str) -> object:
    try:
        return getattr(entity, name)
    except Exception as error:
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error


def _entity_summary(entity: object) -> EntitySummary:
    return EntitySummary(
        int(_required(entity, "ObjectID")),
        str(_required(entity, "Handle")),
        str(_required(entity, "ObjectName")),
        str(_required(entity, "Layer")),
    )


def _json_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _entity_details(entity: object) -> EntityDetails:
    summary = _entity_summary(entity)
    properties: dict[str, object] = {}
    for member, key in _OPTIONAL_PROPERTIES:
        try:
            properties[key] = _json_value(getattr(entity, member))
        except Exception as error:
            logger.debug("Optional AutoCAD property is unavailable", exc_info=error)
            continue
    return EntityDetails(
        summary.object_id, summary.handle, summary.object_name, summary.layer, properties
    )


def _unsupported(capability: AdapterCapability) -> AdapterError:
    return AdapterError(
        AdapterErrorCode.UNSUPPORTED_CAPABILITY,
        "AutoCAD capability is unavailable",
        details={"capability": capability.value},
    )


def _optional(target: object, name: str) -> object | None:
    try:
        return getattr(target, name)
    except Exception:
        return None


class WindowsAutoCADAdapter:
    """The complete read-only adapter contract; it retains only its session manager."""

    def __init__(self, session_manager: WindowsSessionManager | None = None) -> None:
        self._session_manager = session_manager or WindowsSessionManager()

    def status(self) -> ConnectionInfo:
        with self._session_manager.session(require_document=False) as connected:
            document = _optional(connected.application, "ActiveDocument")
            model_space = _optional(document, "ModelSpace") if document is not None else None
            session = AutoCADSession(connected.com, connected.application, document, model_space)
            product = _optional(connected.application, "Name")
            version = _optional(connected.application, "Version")
            document_name = _optional(document, "Name") if document is not None else None
            read_only = _optional(document, "ReadOnly") if document is not None else None
            return ConnectionInfo(
                True,
                str(product) if product is not None else None,
                str(version) if version is not None else None,
                str(product) if product is not None else None,
                str(document_name) if document_name is not None else None,
                bool(read_only) if read_only is not None else None,
                detect_capabilities(session),
            )

    def reconnect(self) -> ConnectionInfo:
        return self.status()

    def list_entities(self) -> tuple[EntitySummary, ...]:
        with self._session_manager.session(require_document=True) as session:
            report = detect_capabilities(session)
            if not report.supports(AdapterCapability.LIST_ENTITIES):
                raise _unsupported(AdapterCapability.LIST_ENTITIES)
            try:
                return tuple(_entity_summary(entity) for entity in session.model_space)  # type: ignore[union-attr]
            except AdapterError:
                raise
            except Exception as error:
                raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error

    def get_entity_info(self, object_id: int) -> EntityDetails:
        with self._session_manager.session(require_document=True) as session:
            report = detect_capabilities(session)
            if not report.supports(AdapterCapability.GET_ENTITY_INFO):
                raise _unsupported(AdapterCapability.GET_ENTITY_INFO)
            try:
                entities: Iterable[object] = session.model_space  # type: ignore[assignment]
                for entity in entities:
                    if int(_required(entity, "ObjectID")) == object_id:
                        return _entity_details(entity)
            except AdapterError:
                raise
            except Exception as error:
                raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error
            raise AdapterError(
                AdapterErrorCode.ENTITY_NOT_FOUND,
                "Entity was not found",
                details={"object_id": object_id},
            )
