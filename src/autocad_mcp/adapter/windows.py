"""Read-only production AutoCAD adapter using transient Windows COM sessions."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from itertools import chain
from typing import cast

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
from autocad_mcp.core.models import JsonValue

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
_NO_SAMPLE = object()
_EMPTY_MODEL_SPACE = object()
_JSON_SCALAR_TYPES = frozenset({bool, int, str})


def _issue(
    code: AdapterCapabilityIssueCode, capability: AdapterCapability, member: str
) -> AdapterCapabilityIssue:
    message = (
        "Required AutoCAD member could not be read"
        if code is AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED
        else "Required AutoCAD member is unavailable"
    )
    return AdapterCapabilityIssue(
        code, capability, member, message
    )


def _member(
    target: object, name: str, capability: AdapterCapability, issues: list[AdapterCapabilityIssue]
) -> object | None:
    try:
        return cast(object, getattr(target, name))
    except AttributeError:
        issues.append(_issue(AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE, capability, name))
    except Exception:
        issues.append(_issue(AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED, capability, name))
    return None


def _model_space_sample(
    model_space: object, issues: list[AdapterCapabilityIssue]
) -> object:
    try:
        entities = iter(cast(Iterable[object], model_space))
    except TypeError:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return _NO_SAMPLE
    except Exception:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return _NO_SAMPLE
    if entities is model_space:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return _NO_SAMPLE
    try:
        return next(entities)
    except StopIteration:
        return _EMPTY_MODEL_SPACE
    except Exception:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return _NO_SAMPLE


def detect_capabilities(
    session: AutoCADSession, sample: object = _NO_SAMPLE
) -> AdapterCapabilityReport:
    """Report supported operations from observed members, never product release text."""
    available: set[AdapterCapability] = set()
    issues: list[AdapterCapabilityIssue] = []
    if session.application is not None:
        available.add(AdapterCapability.CONNECTION)
    if session.document is None:
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    available.add(AdapterCapability.ACTIVE_DOCUMENT)
    if session.model_space is None:
        issues.append(
            _issue(
                AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE,
                AdapterCapability.LIST_ENTITIES,
                "ModelSpace",
            )
        )
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    if sample is _NO_SAMPLE:
        sample = _model_space_sample(session.model_space, issues)
    if issues:
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    if sample is _NO_SAMPLE or sample is _EMPTY_MODEL_SPACE:
        available.update({AdapterCapability.LIST_ENTITIES, AdapterCapability.GET_ENTITY_INFO})
        return AdapterCapabilityReport(frozenset(available), tuple(issues))
    for member in _IDENTITY_MEMBERS:
        _member(sample, member, AdapterCapability.LIST_ENTITIES, issues)
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
        int(cast(str, _required(entity, "ObjectID"))),
        str(_required(entity, "Handle")),
        str(_required(entity, "ObjectName")),
        str(_required(entity, "Layer")),
    )


def _json_value(value: object) -> JsonValue:
    if value is None:
        return None
    if type(value) in _JSON_SCALAR_TYPES:
        return cast(JsonValue, value)
    if type(value) is float:
        if math.isfinite(value):
            return float(value)
        raise ValueError("Non-finite values are not JSON-safe")
    if isinstance(value, bool | int | float | str):
        raise TypeError("Optional AutoCAD scalar subclass is not JSON-safe")
    if isinstance(value, Mapping):
        if not all(type(key) is str for key in value):
            raise TypeError("JSON object keys must be strings")
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [_json_value(item) for item in value]
    raise TypeError("Optional AutoCAD value is not JSON-safe")


def _entity_details(entity: object) -> EntityDetails:
    summary = _entity_summary(entity)
    properties: dict[str, JsonValue] = {}
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


def _status_member(target: object, name: str, *, required: bool = False) -> object | None:
    try:
        return cast(object, getattr(target, name))
    except AttributeError as error:
        if required:
            raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error
        return None
    except Exception as error:
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error


def _probed_entities(
    session: AutoCADSession,
) -> tuple[AdapterCapabilityReport, Iterable[object]]:
    if session.model_space is None:
        return detect_capabilities(session), ()
    try:
        entities = iter(cast(Iterable[object], session.model_space))
    except TypeError:
        return detect_capabilities(session), ()
    except Exception as error:
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error
    try:
        first = next(entities)
    except StopIteration:
        return detect_capabilities(session, _EMPTY_MODEL_SPACE), ()
    except Exception as error:
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error
    return detect_capabilities(session, first), chain((first,), entities)


class WindowsAutoCADAdapter:
    """The complete read-only adapter contract; it retains only its session manager."""

    def __init__(self, session_manager: WindowsSessionManager | None = None) -> None:
        self._session_manager = session_manager or WindowsSessionManager()

    def status(self) -> ConnectionInfo:
        with self._session_manager.session(require_document=False) as connected:
            document = _status_member(connected.application, "ActiveDocument", required=True)
            model_space = _status_member(document, "ModelSpace") if document is not None else None
            session = AutoCADSession(connected.com, connected.application, document, model_space)
            product = _status_member(connected.application, "Name")
            version = _status_member(connected.application, "Version")
            release = _status_member(connected.application, "Release")
            release_hint = release if release is not None else version
            document_name = _status_member(document, "Name") if document is not None else None
            read_only = _status_member(document, "ReadOnly") if document is not None else None
            return ConnectionInfo(
                True,
                str(product) if product is not None else None,
                str(version) if version is not None else None,
                str(release_hint) if release_hint is not None else None,
                str(document_name) if document_name is not None else None,
                bool(read_only) if read_only is not None else None,
                detect_capabilities(session),
            )

    def reconnect(self) -> ConnectionInfo:
        return self.status()

    def list_entities(self) -> tuple[EntitySummary, ...]:
        with self._session_manager.session(require_document=True) as session:
            report, entities = _probed_entities(session)
            if not report.supports(AdapterCapability.LIST_ENTITIES):
                raise _unsupported(AdapterCapability.LIST_ENTITIES)
            try:
                return tuple(_entity_summary(entity) for entity in entities)
            except AdapterError:
                raise
            except Exception as error:
                raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error

    def get_entity_info(self, object_id: int) -> EntityDetails:
        with self._session_manager.session(require_document=True) as session:
            report, entities = _probed_entities(session)
            if not report.supports(AdapterCapability.GET_ENTITY_INFO):
                raise _unsupported(AdapterCapability.GET_ENTITY_INFO)
            try:
                for entity in entities:
                    if int(cast(str, _required(entity, "ObjectID"))) == object_id:
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
