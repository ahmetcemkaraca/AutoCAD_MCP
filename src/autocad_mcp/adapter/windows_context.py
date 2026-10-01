"""Operation-scoped ActiveX facts guarded by an injected trusted native witness."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import asdict, dataclass
from datetime import timedelta
from heapq import nsmallest
from typing import Any, TypeVar, cast

from autocad_mcp.adapter.context_protocol import (
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterDocumentIdentity,
    AdapterDocumentRevisionToken,
    AdapterEntityFacts,
    AdapterEntityPage,
    AdapterEntityReadRequest,
    ContextInclude,
    request_filters,
)
from autocad_mcp.adapter.native_revision import (
    NativeRevisionError,
    NativeRevisionSource,
    RevisionWitness,
)
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.adapter.windows import WindowsAutoCADAdapter
from autocad_mcp.adapter.windows_session import AutoCADSession, WindowsSessionManager, _is_busy
from autocad_mcp.context.adapter_reader import map_document_context, map_entity_context
from autocad_mcp.context.filtering import entity_order, matches_filters
from autocad_mcp.context.identity import build_document_identity, normalize_handle
from autocad_mcp.context.models import DocumentIdentity, EntityQueryFilters
from autocad_mcp.context.pagination import (
    Clock,
    CursorCodec,
    PageCursor,
    SystemClock,
    filter_digest,
    normalize_filters,
)
from autocad_mcp.context.serialization import record_to_json
from autocad_mcp.context.validation import (
    MAX_ENTITY_BYTES,
    MAX_RESULT_BYTES,
    MAX_SCALAR_MAGNITUDE,
    ContextValidationError,
    convert_value,
    require,
)
from autocad_mcp.core.models import JsonValue

_T = TypeVar("_T")
_POINT = tuple[float, float, float]
_BOUNDS = tuple[float, float, float, float, float, float]
_DXF = {
    "AcDbLine": "LINE",
    "AcDbCircle": "CIRCLE",
    "AcDbArc": "ARC",
    "AcDbPolyline": "LWPOLYLINE",
    "AcDb2dPolyline": "POLYLINE",
    "AcDb3dPolyline": "POLYLINE",
    "AcDbPoint": "POINT",
    "AcDbBlockReference": "INSERT",
    "AcDbMInsertBlock": "INSERT",
    "AcDbText": "TEXT",
    "AcDbMText": "MTEXT",
    "AcDbAttribute": "ATTRIB",
    "AcDbAttributeDefinition": "ATTDEF",
}
_DIMENSIONS = frozenset(
    {
        "AcDbAlignedDimension",
        "AcDbRotatedDimension",
        "AcDb2LineAngularDimension",
        "AcDb3PointAngularDimension",
        "AcDbArcDimension",
        "AcDbDiametricDimension",
        "AcDbRadialDimension",
        "AcDbRadialDimensionLarge",
        "AcDbOrdinateDimension",
    }
)
_UNITS = (
    ("unspecified", None),
    ("inches", 0.0254),
    ("feet", 0.3048),
    ("miles", 1609.344),
    ("millimeters", 0.001),
    ("centimeters", 0.01),
    ("meters", 1.0),
    ("kilometers", 1000.0),
    ("microinches", 2.54e-8),
    ("mils", 2.54e-5),
    ("yards", 0.9144),
    ("angstroms", 1e-10),
    ("nanometers", 1e-9),
    ("microns", 1e-6),
    ("decimeters", 0.1),
    ("dekameters", 10.0),
    ("hectometers", 100.0),
    ("gigameters", 1e9),
    ("astronomical_units", 149597870700.0),
    ("light_years", 9460730472580800.0),
    ("parsecs", 3.0856775814913673e16),
    ("us_survey_feet", 1200 / 3937),
    ("us_survey_inches", 100 / 3937),
    ("us_survey_yards", 3600 / 3937),
    ("us_survey_miles", 6336000 / 3937),
)


def _required(target: object, member: str) -> Any:
    try:
        return getattr(target, member)
    except Exception as error:
        if _is_busy(error):
            raise AdapterError(
                AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
            ) from None
        raise ContextValidationError(
            "Required ActiveX member is unavailable", code="UNSUPPORTED_CAPABILITY"
        ) from None


def _scalar(value: object, kind: type[Any]) -> Any:
    require(
        type(value) is kind if kind is not float else type(value) in (int, float),
        "Invalid ActiveX scalar",
    )
    return convert_value(value, kind)


def _string(value: object, maximum: int = 255) -> str:
    result = cast(str, _scalar(value, str))
    require(len(result) <= maximum, "ActiveX string exceeds bound", code="PAYLOAD_LIMIT")
    return result


def _point(value: object) -> _POINT:
    require(type(value) in (tuple, list) and len(cast(Any, value)) == 3, "Invalid ActiveX point")
    return cast(_POINT, tuple(float(_scalar(item, float)) for item in cast(Any, value)))


def _point_payload(value: object) -> dict[str, float]:
    return dict(zip(("x", "y", "z"), _point(value), strict=True))


def _issue(
    capability: str, member: str | None, handle: str | None = None, code: str = "MEMBER_UNAVAILABLE"
) -> AdapterContextIssue:
    return AdapterContextIssue(
        code, capability, member, handle, "Requested ActiveX fact is unavailable"
    )


def _optional(
    target: object,
    member: str,
    converter: Callable[[Any], _T],
    issues: list[AdapterContextIssue],
    capability: str,
    handle: str | None = None,
) -> _T | None:
    try:
        return converter(getattr(target, member))
    except Exception as error:
        if _is_busy(error):
            raise AdapterError(
                AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
            ) from None
        issues.append(_issue(capability, member, handle))
        return None


def _variable(doc: object, name: str) -> Any:
    return _required(doc, "GetVariable")(name)


def _variant(session: AutoCADSession, value: object, *, byref: bool = False) -> Any:
    com = cast(Any, session.com.pythoncom)
    client = cast(Any, session.com.client)
    flags = com.VT_ARRAY | com.VT_R8 | (com.VT_BYREF if byref else 0)
    return client.VARIANT(flags, value)


def _translate(
    session: AutoCADSession,
    doc: object,
    value: object,
    source: int,
    *,
    displacement: bool = False,
    normal: object | None = None,
) -> _POINT:
    utility = _required(doc, "Utility")
    method = _required(utility, "TranslateCoordinates")
    args = (_variant(session, _point(value)), source, 0, displacement)
    translated = (
        method(*args) if normal is None else method(*args, _variant(session, _point(normal)))
    )
    return _point(translated)


def _bounds(session: AutoCADSession, entity: object) -> _BOUNDS:
    method = _required(entity, "GetBoundingBox")
    if type(entity).__module__.startswith("win32com.gen_py."):
        # Generated typelib wrappers convert the two [out] VARIANTs to a returned pair.
        minimum, maximum = method()
    else:
        # Dynamic dispatch requires explicit by-reference double-array VARIANTs.
        minimum = _variant(session, (0.0, 0.0, 0.0), byref=True)
        maximum = _variant(session, (0.0, 0.0, 0.0), byref=True)
        method(minimum, maximum)
        minimum, maximum = minimum.value, maximum.value
    a, b = _point(minimum), _point(maximum)
    require(all(a[i] <= b[i] for i in range(3)), "Invalid ActiveX bounding box")
    return cast(_BOUNDS, a + b)


def _items(collection: object) -> Iterator[object]:
    count = cast(int, _scalar(_required(collection, "Count"), int))
    require(count >= 0, "Invalid ActiveX collection count")
    for index in range(count):
        try:
            yield _required(collection, "Item")(index)
        except Exception as error:
            if isinstance(error, AdapterError):
                raise
            if _is_busy(error):
                raise AdapterError(
                    AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                ) from None
            raise ContextValidationError(
                "ActiveX enumeration is incomplete", code="PARTIAL_READ"
            ) from None


def _decode_text(value: str) -> str:
    require("%<" not in value, "Text field decoding is unsupported", code="UNSUPPORTED_CAPABILITY")

    def replace_code(match: re.Match[str]) -> str:
        codes = {"d": "°", "p": "±", "c": "⌀", "u": "", "o": "", "%": "%"}
        code = match.group(1).lower()
        require(code in codes, "Text code decoding is unsupported", code="UNSUPPORTED_CAPABILITY")
        return codes[code]

    return re.sub(r"%%(.)", replace_code, value)


def _unicode_escape(value: str, index: int) -> tuple[str, int]:
    require(
        value[index : index + 1] == "+"
        and re.fullmatch("[0-9a-fA-F]{4}", value[index + 1 : index + 5]) is not None,
        "Invalid MText Unicode escape",
        code="UNSUPPORTED_CAPABILITY",
    )
    number = int(value[index + 1 : index + 5], 16)
    index += 5
    if 0xD800 <= number <= 0xDBFF:
        require(
            value[index : index + 3] == "\\U+"
            and re.fullmatch("[0-9a-fA-F]{4}", value[index + 3 : index + 7]) is not None,
            "Invalid MText Unicode pair",
            code="UNSUPPORTED_CAPABILITY",
        )
        low = int(value[index + 3 : index + 7], 16)
        require(
            0xDC00 <= low <= 0xDFFF,
            "Invalid MText Unicode pair",
            code="UNSUPPORTED_CAPABILITY",
        )
        number = 0x10000 + ((number - 0xD800) << 10) + (low - 0xDC00)
        index += 7
    require(
        not 0xDC00 <= number <= 0xDFFF,
        "Invalid MText Unicode escape",
        code="UNSUPPORTED_CAPABILITY",
    )
    return chr(number), index


def _skip_mtext_format(value: str, index: int, code: str) -> int:
    end = value.find(";", index)
    require(end >= index, "Invalid MText format", code="UNSUPPORTED_CAPABILITY")
    argument = value[index:end]
    require(bool(argument), "Invalid MText format", code="UNSUPPORTED_CAPABILITY")
    if code != "F":
        require(
            re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)x?", argument) is not None,
            "Invalid MText numeric format",
            code="UNSUPPORTED_CAPABILITY",
        )
    return end + 1


def _decode_mtext(value: str) -> str:
    require(
        len(value) <= 65536 and "%<" not in value,
        "MText decoding is unsupported",
        code="UNSUPPORTED_CAPABILITY",
    )
    output = []
    index = 0
    depth = 0
    while index < len(value):
        char = value[index]
        index += 1
        if char == "{":
            depth += 1
            require(depth <= 16, "MText nesting exceeds bound", code="UNSUPPORTED_CAPABILITY")
        elif char == "}":
            depth -= 1
            require(depth >= 0, "Invalid MText grouping", code="UNSUPPORTED_CAPABILITY")
        elif char == "\\":
            require(index < len(value), "Invalid MText escape", code="UNSUPPORTED_CAPABILITY")
            code = value[index]
            index += 1
            if code in "\\{}":
                output.append(code)
            elif code in ("P", "~"):
                output.append("\n" if code == "P" else "\u00a0")
            elif code in "LlOoKk":
                pass
            elif code == "U":
                decoded, index = _unicode_escape(value, index)
                output.append(decoded)
            elif code in "ACcFHQTW":
                index = _skip_mtext_format(value, index, code)
            else:
                raise ContextValidationError(
                    "MText format decoding is unsupported", code="UNSUPPORTED_CAPABILITY"
                )
        else:
            output.append(char)
    require(depth == 0, "Invalid MText grouping", code="UNSUPPORTED_CAPABILITY")
    return _decode_text("".join(output))


@dataclass(frozen=True)
class _Owner:
    object_id: int
    space_kind: str
    layout_name: str | None
    handle: str


@dataclass(frozen=True)
class _Identity:
    handle: str
    object_id: int
    object_name: str
    space_kind: str
    layout_name: str | None
    owner_block_handle: str | None
    layer: Mapping[str, JsonValue]
    bounds: _BOUNDS | None


@dataclass
class _ScanState:
    issues: list[AdapterContextIssue]
    partial: bool = False


@dataclass(frozen=True)
class _Read:
    session: AutoCADSession
    document: Any
    hwnd: int
    witness: RevisionWitness


class WindowsContextAutoCADAdapter(WindowsAutoCADAdapter):
    def __init__(
        self,
        session_manager: WindowsSessionManager,
        *,
        revision_source: NativeRevisionSource,
        cursor_secret: bytes,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(session_manager)
        self._revision_source = revision_source
        self._clock = clock or SystemClock()
        self._codec = CursorCodec(clock=self._clock, secret=cursor_secret)

    def _witness(self, hwnd: int) -> RevisionWitness:
        try:
            value = self._revision_source.witness(hwnd)
            require(
                type(value) is RevisionWitness,
                "Revision witness is unavailable",
                code="REVISION_TOKEN_UNAVAILABLE",
            )
            return value
        except NativeRevisionError as error:
            if error.code == "BUSY":
                raise AdapterError(
                    AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                ) from None
            raise ContextValidationError(
                "Trusted native revision is unavailable", code="REVISION_TOKEN_UNAVAILABLE"
            ) from None
        except ContextValidationError:
            raise
        except Exception:
            raise ContextValidationError(
                "Trusted native revision is unavailable", code="REVISION_TOKEN_UNAVAILABLE"
            ) from None

    def _read(self, operation: Callable[[_Read], _T], *, continuation: bool = False) -> _T:
        changed = "STALE_CURSOR" if continuation else "SNAPSHOT_CHANGED_DURING_READ"
        with self._session_manager.session(require_document=True) as session:
            try:
                hwnd = cast(int, _scalar(_required(session.document, "HWND"), int))
                require(1 <= hwnd <= 2**64 - 1, "Invalid document window")
                witness = self._witness(hwnd)
                doc = _required(session.application, "ActiveDocument")
                require(
                    doc is not None and _required(doc, "HWND") == hwnd,
                    "Active document changed",
                    code=changed,
                )
                read = _Read(session, doc, hwnd, witness)
                try:
                    result = operation(read)
                finally:
                    current = _required(session.application, "ActiveDocument")
                    require(
                        current is not None and _required(current, "HWND") == hwnd,
                        "Active document changed",
                        code=changed,
                    )
                    require(
                        self._witness(hwnd) == witness, "Document revision changed", code=changed
                    )
                return result
            except (ContextValidationError, AdapterError):
                raise
            except Exception as error:
                if _is_busy(error):
                    raise AdapterError(
                        AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                    ) from None
                raise ContextValidationError(
                    "ActiveX context read failed", code="UNSUPPORTED_CAPABILITY"
                ) from None

    @staticmethod
    def _token(witness: RevisionWitness) -> AdapterDocumentRevisionToken:
        return AdapterDocumentRevisionToken(
            "1.0", witness.session_id, "native-context-epochs-v1", witness.opaque_token
        )

    def context_capabilities(self) -> tuple[str, ...]:
        return self._read(
            lambda read: ("document_context", "document_revision", "entity_facts", "entity_paging")
        )

    def read_document_revision(self) -> AdapterDocumentRevisionToken:
        return self._read(lambda read: self._token(read.witness))

    @staticmethod
    def _document_identity(read: _Read) -> AdapterDocumentIdentity:
        path = _string(_required(read.document, "FullName"), 65536)
        return AdapterDocumentIdentity(
            _string(_required(read.document, "Name")),
            path or None,
            read.witness.database_guid,
            read.witness.session_id,
            bool(path),
            _scalar(_required(read.document, "ReadOnly"), bool),
        )

    def read_document_context(self) -> AdapterDocumentContext:
        return self._read(self._document_context)

    def _document_context(self, read: _Read) -> AdapterDocumentContext:
        doc = read.document
        issues: list[AdapterContextIssue] = []
        active_space = _scalar(_required(doc, "ActiveSpace"), int)
        require(active_space in (0, 1), "Invalid active display space")
        model_in_paper = active_space == 0 and _scalar(_required(doc, "MSpace"), bool)
        display = (
            "model"
            if active_space == 1
            else "model_in_paper_viewport"
            if model_in_paper
            else "paper"
        )
        layout = _string(_required(_required(doc, "ActiveLayout"), "Name"))
        viewport = _optional(
            doc,
            "ActivePViewport" if active_space == 0 else "ActiveViewport",
            lambda value: _scalar(_required(value, "ObjectID"), int),
            issues,
            "viewport",
        )
        x = _translate(read.session, doc, (1.0, 0.0, 0.0), 1, displacement=True)
        y = _translate(read.session, doc, (0.0, 1.0, 0.0), 1, displacement=True)
        origin = _point(_variable(doc, "UCSORG"))
        ucs_name = _optional(
            doc, "GetVariable", lambda method: _string(method("UCSNAME")), issues, "ucs"
        )
        ucs: dict[str, Any] = {
            "name": ucs_name or None,
            "origin_wcs": _point_payload(origin),
            "x_axis_wcs": _point_payload(x),
            "y_axis_wcs": _point_payload(y),
            "is_orthonormal": all(abs(math.hypot(*axis) - 1) <= 1e-9 for axis in (x, y))
            and abs(sum(a * b for a, b in zip(x, y, strict=True))) <= 1e-9,
        }
        center = _variable(doc, "VIEWCTR")
        require(type(center) in (tuple, list) and len(center) in (2, 3), "Invalid view center")
        height = float(_scalar(_variable(doc, "VIEWSIZE"), float))
        screen = _variable(doc, "SCREENSIZE")
        require(type(screen) in (tuple, list) and len(screen) == 2, "Invalid screen size")
        pixels = tuple(float(_scalar(value, float)) for value in screen)
        require(height > 0 and all(value > 0 for value in pixels), "Invalid view dimensions")
        perspective = _scalar(_variable(doc, "PERSPECTIVE"), int)
        require(perspective in (0, 1), "Invalid projection")
        visual = _optional(
            doc, "GetVariable", lambda method: _string(method("VSCURRENT")), issues, "view"
        )
        view = {
            "center_ucs": {"x": _scalar(center[0], float), "y": _scalar(center[1], float)},
            "target_wcs": _point_payload(
                _translate(read.session, doc, _variable(doc, "TARGET"), 1)
            ),
            "direction_wcs": _point_payload(
                _translate(read.session, doc, _variable(doc, "VIEWDIR"), 1, displacement=True)
            ),
            "width": height * pixels[0] / pixels[1],
            "height": height,
            "twist_radians": _scalar(_variable(doc, "VIEWTWIST"), float),
            "projection": "perspective" if perspective else "parallel",
            "visual_style": visual,
        }
        unit_code = _scalar(_variable(doc, "INSUNITS"), int)
        require(
            0 <= unit_code < len(_UNITS), "Unsupported drawing units", code="UNSUPPORTED_CAPABILITY"
        )
        unit_name, conversion = _UNITS[unit_code]
        if conversion is not None and conversion > MAX_SCALAR_MAGNITUDE:
            conversion = None
            issues.append(_issue("units", "INSUNITS"))
        identity = self._document_identity(read)
        issues.extend(self._identity_issues(identity))
        raw = AdapterDocumentContext(
            "1.0",
            identity,
            cast(Any, display),
            layout,
            viewport,
            ucs,
            view,
            {"insunits_code": unit_code, "name": unit_name, "meters_per_unit": conversion},
            tuple(issues),
        )
        map_document_context(raw)
        return raw

    @staticmethod
    def _identity_issues(identity: AdapterDocumentIdentity) -> tuple[AdapterContextIssue, ...]:
        if identity.is_saved and identity.database_fingerprint_guid is None:
            return (
                AdapterContextIssue(
                    "IDENTITY_PATH_FALLBACK",
                    "document_identity",
                    None,
                    None,
                    "Saved drawing identity uses a move-sensitive path hash",
                ),
            )
        return ()

    @staticmethod
    def _owner(block: object) -> _Owner:
        is_layout = _scalar(_required(block, "IsLayout"), bool)
        object_id = _scalar(_required(block, "ObjectID"), int)
        handle = normalize_handle(_string(_required(block, "Handle")))
        if is_layout:
            layout = _required(block, "Layout")
            model = _scalar(_required(layout, "ModelType"), bool)
            return _Owner(
                object_id, "model" if model else "paper", _string(_required(layout, "Name")), handle
            )
        return _Owner(object_id, "block_definition", None, handle)

    def _identity(
        self, read: _Read, entity: object, owner: _Owner, *, bounds: bool = False
    ) -> _Identity:
        handle = normalize_handle(_string(_required(entity, "Handle")))
        require(
            _scalar(_required(entity, "OwnerID"), int) == owner.object_id,
            "Entity ownership changed",
            code="PARTIAL_READ",
        )
        value = _Identity(
            handle,
            _scalar(_required(entity, "ObjectID"), int),
            _string(_required(entity, "ObjectName")),
            owner.space_kind,
            owner.layout_name,
            owner.handle,
            {"name": _string(_required(entity, "Layer"))},
            _bounds(read.session, entity) if bounds else None,
        )
        return value

    def _geometry(
        self, read: _Read, entity: object, identity: _Identity, issues: list[AdapterContextIssue]
    ) -> dict[str, Any]:
        name = identity.object_name

        def point(member: str) -> dict[str, float]:
            return _point_payload(_required(entity, member))

        if name == "AcDbLine":
            return {"kind": "line", "start": point("StartPoint"), "end": point("EndPoint")}
        if name in ("AcDbCircle", "AcDbArc"):
            data = {
                "kind": "circle" if name == "AcDbCircle" else "arc",
                "center": point("Center"),
                "normal": point("Normal"),
                "radius": _scalar(_required(entity, "Radius"), float),
            }
            if name == "AcDbArc":
                data.update(
                    start_angle_radians=_scalar(_required(entity, "StartAngle"), float),
                    end_angle_radians=_scalar(_required(entity, "EndAngle"), float),
                )
            return data
        if name == "AcDbPoint":
            return {"kind": "point", "position": point("Coordinates")}
        if name in ("AcDbPolyline", "AcDb2dPolyline", "AcDb3dPolyline"):
            return self._polyline(read, entity, name)
        if name in ("AcDbBlockReference", "AcDbMInsertBlock"):
            return {
                "kind": "block_reference",
                "insertion": point("InsertionPoint"),
                "normal": point("Normal"),
                "rotation_radians": _scalar(_required(entity, "Rotation"), float),
                "scale_xyz": dict(
                    zip(
                        ("x", "y", "z"),
                        (
                            _scalar(_required(entity, key), float)
                            for key in ("XScaleFactor", "YScaleFactor", "ZScaleFactor")
                        ),
                        strict=True,
                    )
                ),
            }
        issues.append(_issue("geometry", None, identity.handle, "UNSUPPORTED_CAPABILITY"))
        return {"kind": "unsupported", "object_name": name}

    @staticmethod
    def _polyline(read: _Read, entity: object, name: str) -> dict[str, Any]:
        if name != "AcDbPolyline":
            require(
                _scalar(_required(entity, "Type"), int) == 0,
                "Fitted polyline representation is unsupported",
                code="UNSUPPORTED_CAPABILITY",
            )
        coordinates = _required(entity, "Coordinates")
        stride = 2 if name == "AcDbPolyline" else 3
        require(
            type(coordinates) in (tuple, list)
            and 0 < len(coordinates) <= stride * 10000
            and len(coordinates) % stride == 0,
            "Polyline coordinates exceed bound",
            code="PAYLOAD_LIMIT",
        )
        normal = None
        elevation = 0.0
        if name != "AcDb3dPolyline":
            normal = _point(_required(entity, "Normal"))
            elevation = float(_scalar(_required(entity, "Elevation"), float))
        vertices = []
        for index in range(0, len(coordinates), stride):
            source = (
                coordinates[index],
                coordinates[index + 1],
                coordinates[index + 2] if name == "AcDb3dPolyline" else elevation,
            )
            position = (
                _point(source)
                if name == "AcDb3dPolyline"
                else _translate(read.session, read.document, source, 4, normal=normal)
            )
            vertices.append(_point_payload(position))
        bulges = (
            []
            if name == "AcDb3dPolyline"
            else [
                _scalar(_required(entity, "GetBulge")(index), float)
                for index in range(len(vertices))
            ]
        )
        return {
            "kind": "lwpolyline" if name == "AcDbPolyline" else "polyline",
            "vertices": vertices,
            "bulges": bulges,
            "closed": _scalar(_required(entity, "Closed"), bool),
        }

    @staticmethod
    def _block_facts(
        read: _Read, entity: object, identity: _Identity, issues: list[AdapterContextIssue]
    ) -> dict[str, Any]:
        name = _string(_required(entity, "Name"))
        effective = _optional(entity, "EffectiveName", _string, issues, "block", identity.handle)
        definition = _required(read.document, "Blocks").Item(name)
        attributes: dict[str, str] = {}
        has_attributes = _scalar(_required(entity, "HasAttributes"), bool)
        is_xref = _scalar(_required(definition, "IsXRef"), bool)
        methods = (
            ()
            if not has_attributes
            else ("GetConstantAttributes",)
            if is_xref
            else ("GetAttributes", "GetConstantAttributes")
        )
        for method in methods:
            values = _required(entity, method)()
            require(type(values) in (tuple, list), "Invalid attribute array")
            require(
                len(values) + len(attributes) <= 512,
                "Block attributes exceed bound",
                code="PAYLOAD_LIMIT",
            )
            for attribute in values:
                tag = _string(_required(attribute, "TagString"), 65536)
                require(
                    tag not in attributes, "Duplicate attribute tag", code="UNSUPPORTED_CAPABILITY"
                )
                attributes[tag] = _string(_required(attribute, "TextString"), 65536)
        return {
            "effective_name": effective if effective is not None else name,
            "definition_handle": normalize_handle(_string(_required(definition, "Handle"))),
            "attribute_values": attributes,
            "is_dynamic": _optional(
                entity,
                "IsDynamicBlock",
                lambda value: _scalar(value, bool),
                issues,
                "block",
                identity.handle,
            ),
        }

    def _entity_facts(self, read: _Read, entity: object, identity: _Identity) -> AdapterEntityFacts:
        issues: list[AdapterContextIssue] = []
        layer_name = cast(str, identity.layer["name"])
        layer = _required(read.document, "Layers").Item(layer_name)
        layer_data = {
            "name": layer_name,
            "is_off": not _scalar(_required(layer, "LayerOn"), bool),
            "is_frozen": _scalar(_required(layer, "Freeze"), bool),
            "is_locked": _scalar(_required(layer, "Lock"), bool),
        }
        style = {}
        for key, member, kind in (
            ("color_index", "Color", int),
            ("linetype", "Linetype", str),
            ("linetype_scale", "LinetypeScale", float),
            ("lineweight", "Lineweight", int),
            ("transparency", "EntityTransparency", str),
            ("visible", "Visible", bool),
        ):

            def convert_scalar(value: Any, scalar_type: type[Any] = kind) -> Any:
                return _scalar(value, scalar_type)

            style[key] = _optional(
                entity,
                member,
                convert_scalar,
                issues,
                "visual_style",
                identity.handle,
            )
        style["true_color_rgb"] = _optional(
            entity,
            "TrueColor",
            lambda color: tuple(
                _scalar(_required(color, channel), int) for channel in ("Red", "Green", "Blue")
            ),
            issues,
            "visual_style",
            identity.handle,
        )
        geometry = self._geometry(read, entity, identity, issues)
        bounds = identity.bounds
        if bounds is None:
            try:
                bounds = _bounds(read.session, entity)
            except Exception as error:
                if isinstance(error, AdapterError):
                    raise
                if _is_busy(error):
                    raise AdapterError(
                        AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                    ) from None
                issues.append(_issue("bounding_box", "GetBoundingBox", identity.handle))
        block = None
        text: dict[str, Any] | None = None
        dimension = None
        if identity.object_name in ("AcDbBlockReference", "AcDbMInsertBlock"):
            block = self._block_facts(read, entity, identity, issues)
        if identity.object_name in (
            "AcDbText",
            "AcDbMText",
            "AcDbAttribute",
            "AcDbAttributeDefinition",
        ):
            raw_text = _string(_required(entity, "TextString"), 65536)
            plain = (
                _decode_mtext(raw_text)
                if identity.object_name == "AcDbMText"
                else _decode_text(raw_text)
            )
            text = {
                "plain_text": plain,
                "raw_text": raw_text,
                "style_name": _optional(
                    entity, "StyleName", _string, issues, "text", identity.handle
                ),
                "height": _optional(
                    entity,
                    "Height",
                    lambda value: _scalar(value, float),
                    issues,
                    "text",
                    identity.handle,
                ),
                "rotation_radians": _optional(
                    entity,
                    "Rotation",
                    lambda value: _scalar(value, float),
                    issues,
                    "text",
                    identity.handle,
                ),
                "insertion": _optional(
                    entity, "InsertionPoint", _point_payload, issues, "text", identity.handle
                ),
            }
        if identity.object_name in _DIMENSIONS:
            dimension = {
                key: _optional(entity, member, converter, issues, "dimension", identity.handle)
                for key, member, converter in (
                    ("measurement", "Measurement", lambda value: _scalar(value, float)),
                    ("dimension_text", "TextOverride", lambda value: _string(value, 65536)),
                    ("style_name", "StyleName", _string),
                    ("text_position", "TextPosition", _point_payload),
                )
            }
        raw = AdapterEntityFacts(
            "1.0",
            identity.handle,
            identity.object_id,
            identity.object_name,
            "DIMENSION" if identity.object_name in _DIMENSIONS else _DXF.get(identity.object_name),
            cast(Any, identity.space_kind),
            identity.layout_name,
            identity.owner_block_handle,
            layer_data,
            style,
            geometry,
            bounds,
            block,
            text,
            dimension,
            tuple(issues),
        )
        map_entity_context(raw)
        require(
            len(record_to_json(raw).encode("utf-8")) <= MAX_ENTITY_BYTES,
            "Entity byte limit exceeded",
            code="PAYLOAD_LIMIT",
        )
        return raw

    def entity_facts_by_handles(
        self, handles: tuple[str, ...], include: ContextInclude
    ) -> tuple[AdapterEntityFacts, ...]:
        require(type(handles) is tuple and 1 <= len(handles) <= 256, "Invalid handle count")
        normalized = tuple(normalize_handle(handle) for handle in handles)
        require(len(set(normalized)) == len(normalized), "Duplicate handle lookup")
        require(type(include) is ContextInclude, "Invalid include flags")

        def lookup(read: _Read) -> tuple[AdapterEntityFacts, ...]:
            output: list[AdapterEntityFacts] = []
            used = 2  # Exact outer array brackets; charge records before retaining them.
            for handle in normalized:
                try:
                    entity = read.document.HandleToObject(handle)
                except Exception as error:
                    if _is_busy(error):
                        raise AdapterError(
                            AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                        ) from None
                    raise ContextValidationError(
                        "Entity handle was not found", code="ENTITY_NOT_FOUND"
                    ) from None
                owner = self._owner(read.document.ObjectIDToObject(_required(entity, "OwnerID")))
                identity = self._identity(read, entity, owner)
                require(identity.handle == handle, "Entity handle changed", code="ENTITY_NOT_FOUND")
                raw = self._entity_facts(read, entity, identity)
                used += len(record_to_json(raw).encode("utf-8")) + bool(output)
                require(
                    used <= MAX_RESULT_BYTES, "Lookup byte limit exceeded", code="PAYLOAD_LIMIT"
                )
                output.append(raw)
            require(
                len(record_to_json(tuple(output)).encode("utf-8")) <= MAX_RESULT_BYTES,
                "Lookup byte limit exceeded",
                code="PAYLOAD_LIMIT",
            )
            return tuple(output)

        return self._read(lookup)

    def read_entity_page(self, request: AdapterEntityReadRequest) -> AdapterEntityPage:
        require(type(request) is AdapterEntityReadRequest, "Invalid entity read request")
        return self._read(
            lambda read: self._page(read, request), continuation=request.cursor is not None
        )

    def _cursor_boundary(
        self,
        read: _Read,
        request: AdapterEntityReadRequest,
        filters: EntityQueryFilters,
        document: DocumentIdentity,
        digest: str,
        revision: str,
    ) -> tuple[int, str, int, str] | None:
        if request.cursor is None:
            return None
        cursor = self._codec.decode(request.cursor)
        require(
            cursor.kind == "live_query"
            and cursor.document_id == document.document_id
            and cursor.session_id == document.session_document_id
            and cursor.revision_token_digest == revision,
            "Cursor document revision changed",
            code="STALE_CURSOR",
        )
        require(
            cursor.filter_digest == digest and cursor.page_size == request.page_size,
            "Cursor request changed",
            code="INVALID_CURSOR",
        )
        try:
            entity = read.document.HandleToObject(cursor.last_handle)
            owner = self._owner(read.document.ObjectIDToObject(_required(entity, "OwnerID")))
            identity = self._identity(
                read, entity, owner, bounds=request.intersects_wcs is not None
            )
            require(
                identity.handle == cursor.last_handle
                and matches_filters(identity, request, filters),
                "Cursor boundary is missing",
                code="INVALID_CURSOR",
            )
            return entity_order(identity)
        except AdapterError:
            raise
        except Exception as error:
            if _is_busy(error):
                raise AdapterError(
                    AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True
                ) from None
            raise ContextValidationError(
                "Cursor boundary is missing", code="INVALID_CURSOR"
            ) from None

    def _scan_candidates(
        self,
        read: _Read,
        request: AdapterEntityReadRequest,
        filters: EntityQueryFilters,
        boundary: tuple[int, str, int, str] | None,
        state: _ScanState,
    ) -> Iterator[tuple[_Identity, object]]:
        for block in _items(_required(read.document, "Blocks")):
            owner = self._owner(block)
            if request.intersects_wcs is not None and owner.space_kind == "block_definition":
                require(
                    "block_definition" not in filters.spaces,
                    "Definition has no WCS projection",
                    code="UNSUPPORTED_CAPABILITY",
                )
                if not filters.spaces and not any(
                    issue.capability == "definition_wcs_projection" for issue in state.issues
                ):
                    state.issues.append(
                        _issue("definition_wcs_projection", None, code="UNSUPPORTED_CAPABILITY")
                    )
                continue
            if _scalar(_required(block, "IsXRef"), bool):
                try:
                    require(
                        _required(block, "XRefDatabase") is not None, "Xref database unavailable"
                    )
                except AdapterError:
                    raise
                except Exception:
                    state.partial = True
                    if not any(issue.capability == "xref" for issue in state.issues):
                        state.issues.append(_issue("xref", "XRefDatabase"))
                    continue
            for entity in _items(block):
                identity = self._identity(
                    read, entity, owner, bounds=request.intersects_wcs is not None
                )
                if (boundary is None or entity_order(identity) > boundary) and matches_filters(
                    identity, request, filters
                ):
                    yield identity, entity

    def _continuation(
        self,
        document: DocumentIdentity,
        request: AdapterEntityReadRequest,
        digest: str,
        revision: str,
        last_handle: str,
    ) -> str:
        now = self._clock.now()
        return self._codec.encode(
            PageCursor(
                "live_query",
                document.document_id,
                document.session_document_id,
                digest,
                request.page_size,
                last_handle,
                now,
                now + timedelta(seconds=900),
                revision_token_digest=revision,
            )
        )

    def _page(self, read: _Read, request: AdapterEntityReadRequest) -> AdapterEntityPage:
        filters = normalize_filters(request_filters(request))
        raw_identity = self._document_identity(read)
        document = build_document_identity(raw_identity)
        revision = "sha256:" + hashlib.sha256(read.witness.opaque_token.encode()).hexdigest()
        digest = filter_digest(filters, asdict(request.include))
        boundary = self._cursor_boundary(read, request, filters, document, digest, revision)
        state = _ScanState(list(self._identity_issues(raw_identity)))
        selected = nsmallest(
            request.page_size + 1,
            self._scan_candidates(read, request, filters, boundary, state),
            key=lambda item: entity_order(item[0]),
        )
        require(
            len({item[0].handle for item in selected}) == len(selected),
            "Duplicate scanned handle",
            code="PARTIAL_READ",
        )
        token = self._token(read.witness)
        output: list[AdapterEntityFacts] = []
        used = 0
        cursor: str | None = None
        for identity, entity in selected[: request.page_size]:
            raw = self._entity_facts(read, entity, identity)
            size = len(record_to_json(raw).encode("utf-8"))
            candidate_cursor = (
                self._continuation(document, request, digest, revision, identity.handle)
                if len(selected) > len(output) + 1
                else None
            )
            # Exact encoded header, empty array replaced with admitted record bytes plus commas.
            header = AdapterEntityPage(
                "1.0", token, (), candidate_cursor, state.partial, tuple(state.issues)
            )
            actual = len(record_to_json(header).encode("utf-8")) + used + size + len(output)
            if actual > MAX_RESULT_BYTES:
                break
            output.append(raw)
            used += size
            cursor = candidate_cursor
        require(not selected or bool(output), "Page cannot fit one entity", code="PAYLOAD_LIMIT")
        result = AdapterEntityPage(
            "1.0", token, tuple(output), cursor, state.partial, tuple(state.issues)
        )
        require(
            len(record_to_json(result).encode("utf-8")) <= MAX_RESULT_BYTES,
            "Page byte limit exceeded",
            code="PAYLOAD_LIMIT",
        )
        return result


class WindowsContextAdapterProvider:
    def __init__(
        self,
        session_manager: WindowsSessionManager,
        *,
        revision_source: NativeRevisionSource,
        cursor_secret: bytes,
        clock: Clock | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._revision_source = revision_source
        self._cursor_secret = cursor_secret
        self._clock = clock

    def get(self) -> WindowsContextAutoCADAdapter:
        return WindowsContextAutoCADAdapter(
            self._session_manager,
            revision_source=self._revision_source,
            cursor_secret=self._cursor_secret,
            clock=self._clock,
        )
