"""Map full raw coverage into strict owner-frame facts before hashing; no COM reads."""

from collections.abc import Hashable, Mapping
from dataclasses import replace
from typing import Any, cast, get_args

from autocad_mcp.adapter.context_protocol import (
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterEntityFacts,
    _bounds,
)
from autocad_mcp.context.fingerprint import entity_state_digest
from autocad_mcp.context.models import (
    ActiveDrawingContext,
    ArcGeometry,
    BlockFacts,
    BlockReferenceGeometry,
    CadFactEvidence,
    CapabilityIssue,
    CircleGeometry,
    DimensionFacts,
    DrawingUnits,
    EntityContext,
    EntityIdentity,
    EntitySpace,
    LayerFacts,
    LineGeometry,
    PointGeometry,
    PolylineGeometry,
    SpaceContext,
    StyleFacts,
    TextFacts,
    UcsContext,
    UnsupportedGeometry,
    ViewContext,
)
from autocad_mcp.context.validation import record_from_payload, record_hints, require

_MEMBERS = {
    "name": "Layer",
    "is_off": "LayerOn",
    "is_frozen": "Freeze",
    "is_locked": "Lock",
    "color_index": "Color",
    "true_color_rgb": "TrueColor",
    "linetype": "Linetype",
    "linetype_scale": "LinetypeScale",
    "lineweight": "Lineweight",
    "transparency": "EntityTransparency",
    "visible": "Visible",
    "start": "StartPoint",
    "end": "EndPoint",
    "center": "Center",
    "normal": "Normal",
    "radius": "Radius",
    "start_angle_radians": "StartAngle",
    "end_angle_radians": "EndAngle",
    "vertices": "Coordinates",
    "bulges": "GetBulge",
    "closed": "Closed",
    "position": "Coordinates",
    "insertion": "InsertionPoint",
    "rotation_radians": "Rotation",
    "scale_xyz": "XScaleFactor/YScaleFactor/ZScaleFactor",
    "effective_name": "EffectiveName",
    "definition_handle": "Blocks.Item(Name).Handle",
    "attribute_values": "GetAttributes/GetConstantAttributes",
    "is_dynamic": "IsDynamicBlock",
    "plain_text": "TextString",
    "raw_text": "TextString",
    "style_name": "StyleName",
    "height": "Height",
    "measurement": "Measurement",
    "dimension_text": "TextOverride",
    "text_position": "TextPosition",
    "object_name": "ObjectName",
    "kind": "ObjectName",
}
_GEOMETRY = {
    "line": LineGeometry,
    "circle": CircleGeometry,
    "arc": ArcGeometry,
    "lwpolyline": PolylineGeometry,
    "polyline": PolylineGeometry,
    "point": PointGeometry,
    "block_reference": BlockReferenceGeometry,
    "unsupported": UnsupportedGeometry,
}


def _complete(issues: tuple[AdapterContextIssue, ...]) -> None:
    require(
        not any(issue.code == "NOT_REQUESTED" for issue in issues),
        "Full raw coverage is required",
        code="SNAPSHOT_INCOMPLETE",
    )


def _facts(
    kind: type[Any],
    values: Mapping[str, Any],
    issues: tuple[AdapterContextIssue, ...],
    capability: str,
    handle: str,
) -> Any:
    payload = dict(values)
    for field, hint in record_hints(cast(Hashable, kind)).items():
        if field not in payload:
            require(
                type(None) in get_args(hint)
                and any(
                    issue.capability == capability
                    and issue.member == _MEMBERS.get(field)
                    and issue.entity_handle in (None, handle)
                    for issue in issues
                ),
                "Required raw fact is unavailable",
                code="UNSUPPORTED_CAPABILITY",
            )
            payload[field] = None
    return record_from_payload(kind, payload)


def _evidence(
    values: object,
    path: str,
    member: str,
    capability: str,
    unavailable: set[tuple[str, str | None]],
) -> tuple[CadFactEvidence, ...]:
    if isinstance(values, Mapping):
        return tuple(
            item
            for key, value in values.items()
            for item in _evidence(
                value,
                path + "/" + str(key).replace("~", "~0").replace("/", "~1"),
                f"{key.upper()}ScaleFactor"
                if path == "/geometry/scale_xyz"
                else _MEMBERS.get(key, member)
                if path.count("/") == 1
                else member,
                capability,
                unavailable,
            )
        )
    if isinstance(values, tuple):
        return tuple(
            item
            for index, value in enumerate(values)
            for item in _evidence(value, path + "/" + str(index), member, capability, unavailable)
        )
    return (
        CadFactEvidence(
            path,
            "autocad_com",
            member,
            "unavailable"
            if (capability, member) in unavailable or (capability, None) in unavailable
            else "observed",
        ),
    )


def map_document_context(raw: AdapterDocumentContext) -> ActiveDrawingContext:
    _complete(raw.issues)
    # Units are complete acquisition facts even though this helper returns active context only.
    record_from_payload(DrawingUnits, raw.units)
    return ActiveDrawingContext(
        SpaceContext(
            raw.display_space,
            raw.active_layout_name,
            raw.viewport_object_id,
            "session" if raw.viewport_object_id is not None else None,
        ),
        record_from_payload(UcsContext, raw.ucs),
        record_from_payload(ViewContext, raw.view),
    )


def map_entity_context(raw: AdapterEntityFacts) -> EntityContext:
    _complete(raw.issues)
    geometry_kind = raw.geometry.get("kind")
    require(isinstance(geometry_kind, str), "Invalid raw geometry kind")
    geometry_type = _GEOMETRY.get(cast(str, geometry_kind))
    require(
        geometry_type is not None,
        "Unknown raw geometry requires explicit unsupported facts",
        code="UNSUPPORTED_CAPABILITY",
    )
    if geometry_type is UnsupportedGeometry:
        require(
            raw.object_name
            not in {
                "AcDbLine",
                "AcDbCircle",
                "AcDbArc",
                "AcDbPolyline",
                "AcDb2dPolyline",
                "AcDb3dPolyline",
                "AcDbPoint",
                "AcDbBlockReference",
            },
            "Supported geometry facts are unavailable",
            code="UNSUPPORTED_CAPABILITY",
        )
        require(
            any(
                issue.capability == "geometry" and issue.entity_handle in (None, raw.handle)
                for issue in raw.issues
            ),
            "Unsupported geometry requires capability evidence",
            code="UNSUPPORTED_CAPABILITY",
        )
    geometry = _facts(
        cast(type[Any], geometry_type), raw.geometry, raw.issues, "geometry", raw.handle
    )
    layer = _facts(LayerFacts, raw.layer, raw.issues, "layer", raw.handle)
    style = _facts(StyleFacts, raw.style, raw.issues, "visual_style", raw.handle)
    block = (
        None
        if raw.block is None
        else _facts(BlockFacts, raw.block, raw.issues, "block", raw.handle)
    )
    text = None if raw.text is None else _facts(TextFacts, raw.text, raw.issues, "text", raw.handle)
    dimension = (
        None
        if raw.dimension is None
        else _facts(DimensionFacts, raw.dimension, raw.issues, "dimension", raw.handle)
    )
    issues = tuple(
        CapabilityIssue(
            issue.code, issue.capability, issue.entity_handle, issue.member, issue.message, False
        )
        for issue in raw.issues
    )
    from autocad_mcp.context.serialization import record_to_payload

    unavailable = {
        (issue.capability, issue.member)
        for issue in raw.issues
        if issue.entity_handle in (None, raw.handle)
    }
    evidence = tuple(
        item
        for name, value in (
            ("layer", layer),
            ("style", style),
            ("geometry", geometry),
            ("bounds", _bounds(raw.bounds)),
            ("block", block),
            ("text", text),
            ("dimension", dimension),
        )
        if value is not None
        for item in _evidence(
            record_to_payload(value),
            "/" + name,
            "GetBoundingBox" if name == "bounds" else name,
            {"style": "visual_style", "bounds": "bounding_box"}.get(name, name),
            unavailable,
        )
    )
    entity = EntityContext(
        EntityIdentity(
            raw.handle,
            raw.object_id,
            "session" if raw.object_id is not None else None,
            raw.object_name,
            raw.dxf_name,
        ),
        EntitySpace(raw.space_kind, raw.layout_name, raw.owner_block_handle),
        layer,
        style,
        geometry,
        _bounds(raw.bounds),
        block,
        text,
        dimension,
        (),
        evidence,
        issues,
        "sha256:" + "0" * 64,
    )
    return replace(entity, state_digest=entity_state_digest(entity))
