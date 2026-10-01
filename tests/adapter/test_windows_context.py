"""Synthetic COM sessions test copying and guard logic; no AutoCAD host is exercised."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from autocad_mcp.adapter.context_protocol import ContextInclude
from autocad_mcp.adapter.native_revision import NativeRevisionError, RevisionWitness
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.adapter.windows_context import (
    WindowsContextAdapterProvider,
    WindowsContextAutoCADAdapter,
    _decode_mtext,
)
from autocad_mcp.adapter.windows_session import ComModules, WindowsSessionManager
from autocad_mcp.context.adapter_reader import map_document_context, map_entity_context
from autocad_mcp.context.serialization import record_to_payload
from autocad_mcp.context.validation import ContextValidationError

from tests.adapter.test_context_protocol import ALL, request
from tests.adapter.test_fake_context import CLOCK, SECRET
from tests.adapter.test_windows_session import StubClient, StubPythonCom

WITNESS = RevisionWitness(
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    1,
    "33333333-3333-4333-8333-333333333333",
)


class Collection:
    def __init__(self, items=()):
        self.items = items
        self.reads = []

    @property
    def Count(self):  # noqa: N802 - exact injected ActiveX member
        return len(self.items)

    def Item(self, index):  # noqa: N802 - exact injected ActiveX member
        self.reads.append(index)
        if isinstance(index, str):
            return next(item for item in self.items if getattr(item, "Name", None) == index)
        return self.items[index]


class Entity(SimpleNamespace):
    def GetBoundingBox(self, minimum, maximum):  # noqa: N802 - exact injected ActiveX member
        assert minimum.flags == maximum.flags == 0x6005
        minimum.value = (0.0, 0.0, 0.0)
        maximum.value = (5.0, 6.0, 0.0)

    def GetBulge(self, index):  # noqa: N802 - exact injected ActiveX member
        return (0.0, 0.5, 0.0)[index % 3]

    def GetAttributes(self):  # noqa: N802 - exact injected ActiveX member
        return (SimpleNamespace(TagString="EDITABLE", TextString="Synthetic"),)

    def GetConstantAttributes(self):  # noqa: N802 - exact injected ActiveX member
        return (SimpleNamespace(TagString="CONSTANT", TextString="Fixed"),)


def entity(handle="10", object_name="AcDbLine", **changes):
    fields = {
        "Handle": handle,
        "ObjectID": int(handle, 16),
        "OwnerID": 100,
        "ObjectName": object_name,
        "Layer": "Walls",
        "Color": 256,
        "TrueColor": SimpleNamespace(Red=1, Green=2, Blue=3),
        "Linetype": "ByLayer",
        "LinetypeScale": 1.0,
        "Lineweight": -1,
        "EntityTransparency": "ByLayer",
        "Visible": True,
        "StartPoint": (0.0, 0.0, 0.0),
        "EndPoint": (5.0, 6.0, 0.0),
        "Center": (1.0, 2.0, 3.0),
        "Normal": (0.0, 0.0, 1.0),
        "Radius": 2.0,
        "StartAngle": 0.0,
        "EndAngle": 1.0,
        "Coordinates": (0.0, 0.0, 2.0, 0.0, 2.0, 2.0),
        "Closed": True,
        "Elevation": 4.0,
        "Type": 0,
        "InsertionPoint": (1.0, 2.0, 0.0),
        "Rotation": 0.25,
        "XScaleFactor": 1.0,
        "YScaleFactor": 2.0,
        "ZScaleFactor": 1.0,
        "Name": "*U1",
        "EffectiveName": "SyntheticBlock",
        "IsDynamicBlock": True,
        "HasAttributes": True,
        "TextString": "Synthetic text",
        "Height": 2.0,
        "StyleName": "Standard",
        "Measurement": 5.0,
        "TextOverride": "<>",
        "TextPosition": (2.0, 3.0, 0.0),
    }
    return Entity(**(fields | changes))


def block(items, *, object_id=100, handle="A0", layout=None, is_xref=False):
    value = Collection(items)
    value.Handle = handle
    value.ObjectID = object_id
    value.Name = "*U1" if layout is None else layout
    value.IsLayout = layout is not None
    value.IsXRef = is_xref
    value.Layout = SimpleNamespace(ModelType=layout == "Observed Model", Name=layout)
    value.XRefDatabase = object()
    return value


class Utility:
    def __init__(self):
        self.calls = []

    def TranslateCoordinates(self, point, source, target, displacement, normal=None):  # noqa: N802 - exact injected ActiveX member
        point = point.value
        self.calls.append((point, source, target, displacement, normal.value if normal else None))
        if source == 1:  # rotated UCS with translated origin
            x, y, z = point
            return (-y + (0 if displacement else 10), x + (0 if displacement else 20), z)
        if source == 4:
            x, y, z = point
            return (x, z, -y) if normal.value == (0.0, 1.0, 0.0) else point
        return point


class Document:
    def __init__(self, entities=None):
        self.HWND = 111
        self.Name = "synthetic.dwg"
        self.FullName = r"C:\synthetic\test.dwg"
        self.ReadOnly = True
        self.ModelSpace = ()
        self.ActiveSpace = 1
        self.MSpace = False
        self.ActiveLayout = SimpleNamespace(Name="Observed Model")
        self.ActiveViewport = SimpleNamespace(ObjectID=900)
        self.ActivePViewport = SimpleNamespace(ObjectID=901)
        entities = tuple(entities) if entities is not None else (entity(),)
        self.Blocks = Collection(
            (block(entities, layout="Observed Model"), block((), object_id=200))
        )
        self.Layers = Collection(
            (SimpleNamespace(Name="Walls", LayerOn=True, Freeze=False, Lock=False),)
        )
        self.Utility = Utility()
        self.variables = {
            "UCSNAME": "Rotated",
            "UCSORG": (10.0, 20.0, 0.0),
            "VIEWCTR": (2.0, 3.0, 0.0),
            "TARGET": (1.0, 2.0, 3.0),
            "VIEWDIR": (0.0, 1.0, 2.0),
            "VIEWSIZE": 100.0,
            "SCREENSIZE": (1600.0, 800.0),
            "VIEWTWIST": 0.5,
            "PERSPECTIVE": 0,
            "VSCURRENT": "2D Wireframe",
            "INSUNITS": 4,
        }
        self.variable_reads = []

    def GetVariable(self, name):  # noqa: N802 - exact injected ActiveX member
        self.variable_reads.append(name)
        return self.variables[name]

    def HandleToObject(self, handle):  # noqa: N802 - exact injected ActiveX member
        return next(
            item for owner in self.Blocks.items for item in owner.items if item.Handle == handle
        )

    def ObjectIDToObject(self, object_id):  # noqa: N802 - exact injected ActiveX member
        return next(owner for owner in self.Blocks.items if owner.ObjectID == object_id)

    def SetVariable(self, *args):  # noqa: N802 - exact injected ActiveX member
        raise AssertionError("Mutation is forbidden")

    def SendCommand(self, *args):  # noqa: N802 - exact injected ActiveX member
        raise AssertionError("Execution is forbidden")

    def Save(self):  # noqa: N802 - exact injected ActiveX member
        raise AssertionError("Save is forbidden")


class Source:
    def __init__(self, values=None, hook=None):
        self.values = list(values or (WITNESS, WITNESS))
        self.calls = []
        self.hook = hook

    def witness(self, hwnd):
        self.calls.append(hwnd)
        if self.hook:
            self.hook(len(self.calls))
        value = self.values.pop(0) if len(self.values) > 1 else self.values[0]
        if isinstance(value, Exception):
            raise value
        return value


def setup(document=None, source=None):
    document = document or Document()
    application = SimpleNamespace(ActiveDocument=document)
    com = StubPythonCom()
    com.VT_BYREF = 0x4000
    com.VT_ARRAY = 0x2000
    com.VT_R8 = 5
    client = StubClient(application)
    client.VARIANT = lambda flags, value: SimpleNamespace(flags=flags, value=value)
    manager = WindowsSessionManager(lambda: ComModules(com, client))
    source = source or Source()
    adapter = WindowsContextAutoCADAdapter(
        manager, revision_source=source, cursor_secret=SECRET, clock=CLOCK
    )
    return adapter, document, application, com, source


def test_revision_context_units_and_guard_reacquisition_are_pure():
    adapter, doc, app, com, source = setup()
    token = adapter.read_document_revision()
    assert token.source == "native-context-epochs-v1" and token.opaque_value == WITNESS.opaque_token
    raw = adapter.read_document_context()
    active = map_document_context(raw)
    assert raw.identity.is_saved and raw.identity.session_document_id == WITNESS.session_id
    assert raw.identity.database_fingerprint_guid == WITNESS.database_guid
    assert raw.units["meters_per_unit"] == 0.001
    assert active.ucs.origin_wcs.x == 10 and active.ucs.x_axis_wcs.y == 1
    assert record_to_payload(active.view.target_wcs) == {"x": 8.0, "y": 21.0, "z": 3.0}
    assert record_to_payload(active.view.direction_wcs) == {"x": -1.0, "y": 0.0, "z": 2.0}
    assert active.view.width == 200 and active.view.height == 100
    assert com.events == ["initialize", "uninitialize"] * 2 and source.calls == [111] * 4
    assert "Saved" not in doc.variable_reads


@pytest.mark.parametrize(
    "name,expected",
    [
        ("AcDbLine", "line"),
        ("AcDbCircle", "circle"),
        ("AcDbArc", "arc"),
        ("AcDbPolyline", "lwpolyline"),
        ("AcDb2dPolyline", "polyline"),
        ("AcDb3dPolyline", "polyline"),
        ("AcDbPoint", "point"),
        ("AcDbBlockReference", "block_reference"),
        ("AcDbText", "unsupported"),
        ("AcDbMText", "unsupported"),
        ("AcDbAlignedDimension", "unsupported"),
        ("AcDbProxyEntity", "unsupported"),
    ],
)
def test_all_supported_complete_families_and_unknown_geometry(name, expected):
    coordinates = (
        (0.0, 0.0, 0.0, 1.0, 2.0, 3.0)
        if name in ("AcDb2dPolyline", "AcDb3dPolyline")
        else (0.0, 0.0, 2.0, 0.0, 2.0, 2.0)
    )
    if name == "AcDbPoint":
        coordinates = (1.0, 2.0, 3.0)
    adapter, doc, _, com, _ = setup(Document((entity(object_name=name, Coordinates=coordinates),)))
    facts = adapter.entity_facts_by_handles(("10",), ALL)[0]
    mapped = map_entity_context(facts)
    assert mapped.geometry.kind == expected and facts.dxf_name != "invented"
    if name == "AcDbBlockReference":
        assert mapped.block.definition_handle == doc.Blocks.items[1].Handle
        assert dict(mapped.block.attribute_values) == {"EDITABLE": "Synthetic", "CONSTANT": "Fixed"}
    if name in ("AcDbText", "AcDbMText"):
        assert mapped.text.plain_text == "Synthetic text"
    if "Dimension" in name:
        assert mapped.dimension.measurement == 5.0
    assert com.events == ["initialize", "uninitialize"]


@pytest.mark.parametrize(
    "change",
    [
        {"epoch": 2},
        {"session_id": "44444444-4444-4444-8444-444444444444"},
        {"bridge_id": "55555555-5555-4555-8555-555555555555"},
        {"database_guid": None},
    ],
)
def test_complete_witness_change_discards_output_and_balances_cleanup(change):
    adapter, _, _, com, _ = setup(source=Source((WITNESS, replace(WITNESS, **change))))
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(request())
    assert error.value.code == "SNAPSHOT_CHANGED_DURING_READ"
    assert com.events == ["initialize", "uninitialize"]


@pytest.mark.parametrize(
    "code,expected",
    [
        ("UNAVAILABLE", "REVISION_TOKEN_UNAVAILABLE"),
        ("UNTRUSTED_PEER", "REVISION_TOKEN_UNAVAILABLE"),
        ("TIMEOUT", "REVISION_TOKEN_UNAVAILABLE"),
        ("BUSY", "COM_BUSY"),
    ],
)
def test_native_failure_translation_has_no_private_details(code, expected):
    adapter, _, _, com, _ = setup(source=Source((NativeRevisionError(code),)))
    with pytest.raises((ContextValidationError, AdapterError)) as error:
        adapter.read_document_revision()
    assert str(error.value.code) == expected
    assert com.events == ["initialize", "uninitialize"]


def test_switch_in_first_witness_reacquires_active_document_before_facts():
    adapter, doc, app, com, source = setup()
    switched = Document()
    switched.HWND = 222
    source.hook = lambda count: setattr(app, "ActiveDocument", switched) if count == 1 else None
    with pytest.raises(ContextValidationError) as error:
        adapter.read_document_context()
    assert error.value.code == "SNAPSHOT_CHANGED_DURING_READ"
    assert not doc.variable_reads and not switched.variable_reads
    assert com.events == ["initialize", "uninitialize"]


def test_ocs_elevation_definition_frame_and_non_top_view_paper_context():
    raw = entity(object_name="AcDbPolyline", Normal=(0.0, 1.0, 0.0), OwnerID=200)
    doc = Document(())
    doc.Blocks.items[1].items = (raw,)
    doc.ActiveSpace = 0
    doc.MSpace = True
    doc.ActiveLayout.Name = "Paper α"
    adapter, _, _, _, _ = setup(doc)
    facts = adapter.entity_facts_by_handles(("10",), ALL)[0]
    mapped = map_entity_context(facts)
    assert mapped.space.kind == "block_definition" and mapped.space.owner_block_handle == "A0"
    assert mapped.geometry.vertices[0].y == 4 and mapped.geometry.vertices[0].z == 0
    context = map_document_context(adapter.read_document_context())
    assert context.space.display_space == "model_in_paper_viewport"
    assert context.space.viewport_object_id == 901


@pytest.mark.parametrize(
    "code,conversion",
    [
        (0, None),
        (1, 0.0254),
        (6, 1.0),
        (18, 149597870700.0),
        (19, None),
        (20, None),
        (21, 1200 / 3937),
        (22, 100 / 3937),
        (23, 3600 / 3937),
        (24, 6336000 / 3937),
    ],
)
def test_complete_unit_table_and_unrepresentable_conversions(code, conversion):
    doc = Document()
    doc.variables["INSUNITS"] = code
    adapter, _, _, _, _ = setup(doc)
    raw = adapter.read_document_context()
    assert raw.units["insunits_code"] == code and raw.units["meters_per_unit"] == conversion
    if code in (19, 20):
        assert any(issue.capability == "units" for issue in raw.issues)


@pytest.mark.parametrize(
    "raw,plain",
    [
        (r"{\C1;red} \Lunder\l\Pline", "red under\nline"),
        (r"\FArial|b0|i0;Hello\~world", "Hello\u00a0world"),
        (r"\U+00E9", "é"),
        (r"\{literal\} \\", "{literal} \\"),
    ],
)
def test_mtext_decoder_common_formatting_preserves_plain_content(raw, plain):
    assert _decode_mtext(raw) == plain


@pytest.mark.parametrize(
    "raw", [r"bad\qcode", r"\S1^2;", r"%<unsupported field>%", r"{missing", r"\U+D800"]
)
def test_unsupported_rich_text_is_required_read_refusal(raw):
    adapter, _, _, _, _ = setup(Document((entity(object_name="AcDbMText", TextString=raw),)))
    with pytest.raises(ContextValidationError) as error:
        adapter.entity_facts_by_handles(("10",), ALL)
    assert error.value.code == "UNSUPPORTED_CAPABILITY"


def test_optional_failures_preserve_scoped_issue_required_known_failures_refuse():
    raw = entity()
    del raw.Visible
    adapter, _, _, com, _ = setup(Document((raw,)))
    facts = adapter.entity_facts_by_handles(("10",), ALL)[0]
    assert facts.style["visible"] is None and any(
        issue.member == "Visible" for issue in facts.issues
    )
    del raw.StartPoint
    with pytest.raises(ContextValidationError):
        adapter.entity_facts_by_handles(("10",), ALL)
    assert com.events == ["initialize", "uninitialize"] * 2


def test_page_heap_filters_order_cursors_and_large_live_identity_scan():
    items = tuple(entity(handle=f"{index+1:X}") for index in range(10001))
    adapter, doc, _, _, _ = setup(Document(items))
    first = adapter.read_entity_page(request(page_size=1, handles=("1", "2711")))
    assert [item.handle for item in first.entities] == ["1"] and first.next_cursor
    second = adapter.read_entity_page(
        request(page_size=1, handles=("1", "2711"), cursor=first.next_cursor)
    )
    assert [item.handle for item in second.entities] == ["2711"] and second.next_cursor is None
    with pytest.raises(ContextValidationError):
        adapter.read_entity_page(
            request(page_size=2, handles=("1", "2711"), cursor=first.next_cursor)
        )


def test_lookup_bounds_duplicate_attributes_and_polyline_fit_refusal():
    adapter, _, _, _, _ = setup()
    for handles in ((), ("10", "10"), tuple(f"{i:X}" for i in range(257)), ("FF",)):
        with pytest.raises(ContextValidationError):
            adapter.entity_facts_by_handles(handles, ALL)
    for object_name in ("AcDb2dPolyline", "AcDb3dPolyline"):
        adapter, _, _, _, _ = setup(Document((entity(object_name=object_name, Type=1),)))
        with pytest.raises(ContextValidationError) as error:
            adapter.entity_facts_by_handles(("10",), ALL)
        assert error.value.code == "UNSUPPORTED_CAPABILITY"


def test_provider_construction_never_attaches_com():
    adapter, doc, app, com, source = setup()
    provider = WindowsContextAdapterProvider(
        adapter._session_manager, revision_source=source, cursor_secret=SECRET, clock=CLOCK
    )
    assert isinstance(provider.get(), WindowsContextAutoCADAdapter) and not com.events


def test_page_uses_actual_encoded_header_bytes_at_exact_boundary(monkeypatch):
    import autocad_mcp.adapter.windows_context as module
    from autocad_mcp.context.serialization import record_to_json

    adapter, _, _, _, _ = setup(Document((entity("1"), entity("2"), entity("3"))))
    before = adapter.read_entity_page(request(page_size=2))
    maximum = len(record_to_json(before).encode())
    monkeypatch.setattr(module, "MAX_RESULT_BYTES", maximum)
    exact = adapter.read_entity_page(request(page_size=2))
    assert exact == before and len(exact.entities) == 2
    monkeypatch.setattr(module, "MAX_RESULT_BYTES", maximum - 1)
    smaller = adapter.read_entity_page(request(page_size=2))
    assert len(smaller.entities) == 1 and smaller.next_cursor
    assert len(record_to_json(smaller).encode()) <= maximum - 1


def test_handle_lookup_checks_bytes_progressively_before_full_source_copy(monkeypatch):
    import autocad_mcp.adapter.windows_context as module
    from autocad_mcp.context.serialization import record_to_json

    seen = []

    class TrackedEntity(Entity):
        def __getattribute__(self, name):
            if name == "StartPoint":
                seen.append(super().__getattribute__("Handle"))
            return super().__getattribute__(name)

    items = tuple(TrackedEntity(**vars(entity(str(i)))) for i in (1, 2, 3))
    adapter, _, _, _, _ = setup(Document(items))
    one = adapter.entity_facts_by_handles(("1",), ALL)
    monkeypatch.setattr(module, "MAX_RESULT_BYTES", len(record_to_json(one).encode()))
    seen.clear()
    with pytest.raises(ContextValidationError) as error:
        adapter.entity_facts_by_handles(("1", "2", "3"), ALL)
    assert error.value.code == "PAYLOAD_LIMIT" and seen == ["1", "2"]


def test_saved_path_fallback_has_explicit_move_sensitive_issue_without_raw_path():
    adapter, doc, _, _, _ = setup(source=Source((replace(WITNESS, database_guid=None),)))
    raw = adapter.read_document_context()
    assert any(issue.code == "IDENTITY_PATH_FALLBACK" for issue in raw.issues)
    assert all(doc.FullName not in issue.message for issue in raw.issues)


def test_generated_typelib_bounds_binding_and_invalid_optional_bbox_are_explicit():
    class GeneratedEntity(Entity):
        __module__ = "win32com.gen_py.synthetic"

        def GetBoundingBox(self):  # noqa: N802 - exact injected ActiveX member
            return (1.0, 2.0, 3.0), (4.0, 5.0, 6.0)

    adapter, _, _, _, _ = setup(Document((GeneratedEntity(**vars(entity())),)))
    assert adapter.entity_facts_by_handles(("10",), ALL)[0].bounds == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

    class InvalidBounds(Entity):
        def GetBoundingBox(self, minimum, maximum):  # noqa: N802 - exact injected ActiveX member
            minimum.value = (True, 0.0, 0.0)

    adapter, _, _, _, _ = setup(Document((InvalidBounds(**vars(entity())),)))
    facts = adapter.entity_facts_by_handles(("10",), ALL)[0]
    assert facts.bounds is None and any(issue.member == "GetBoundingBox" for issue in facts.issues)


def test_partial_enumeration_busy_and_unloaded_xref_remain_explicit():
    class Failing(Collection):
        def Item(self, index):  # noqa: N802 - exact injected ActiveX member
            if index == 1:
                raise RuntimeError("private enumeration details")
            return super().Item(index)

    doc = Document()
    broken = Failing((entity("1"), entity("2")))
    owner = doc.Blocks.items[0]
    for name, value in vars(owner).items():
        if name != "items":
            setattr(broken, name, value)
    doc.Blocks.items = (broken,)
    adapter, _, _, com, _ = setup(doc)
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(request())
    assert error.value.code == "PARTIAL_READ" and "private" not in str(error.value)
    assert com.events == ["initialize", "uninitialize"]
    doc = Document()
    doc.Blocks.items[1].IsXRef = True
    doc.Blocks.items[1].XRefDatabase = None
    adapter, _, _, _, _ = setup(doc)
    page = adapter.read_entity_page(request())
    assert page.partial and any(issue.capability == "xref" for issue in page.issues)


@pytest.mark.parametrize(
    "member",
    [
        "Color",
        "TrueColor",
        "Linetype",
        "LinetypeScale",
        "Lineweight",
        "EntityTransparency",
        "Visible",
        "StyleName",
        "Height",
        "Rotation",
        "InsertionPoint",
    ],
)
def test_each_optional_property_missing_is_scoped_and_never_exports_proxy(member):
    raw = entity(object_name="AcDbText")
    delattr(raw, member)
    adapter, _, _, _, _ = setup(Document((raw,)))
    facts = adapter.entity_facts_by_handles(("10",), ALL)[0]
    assert any(issue.member == member and issue.entity_handle == "10" for issue in facts.issues)
    map_entity_context(facts)


@pytest.mark.parametrize("member", ["StartPoint", "EndPoint", "Layer"])
def test_known_required_getter_failure_is_redacted_and_cleanup_balanced(member):
    class Broken(Entity):
        def __getattribute__(self, name):
            if name == member:
                raise RuntimeError("private property details")
            return super().__getattribute__(name)

    adapter, _, _, com, _ = setup(Document((Broken(**vars(entity())),)))
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(request())
    assert "private" not in str(error.value) and com.events == ["initialize", "uninitialize"]


def test_layer_or_order_definition_wcs_and_cursor_staleness_before_full_facts():
    doc = Document((entity("F", Layer="Walls"),))
    paper = block(
        (entity("1", Layer="walls", OwnerID=300),), object_id=300, handle="B0", layout="Alpha"
    )
    definition = doc.Blocks.items[1]
    definition.items = (entity("2", OwnerID=200),)
    doc.Blocks.items = doc.Blocks.items + (paper,)
    doc.Layers.items = doc.Layers.items + (
        SimpleNamespace(Name="walls", LayerOn=True, Freeze=False, Lock=False),
    )
    adapter, _, _, _, source = setup(doc)
    initial = request(page_size=1, layer_names=("Walls",), layer_globs=("wal?s",))
    first = adapter.read_entity_page(initial)
    second = adapter.read_entity_page(replace(initial, cursor=first.next_cursor))
    assert [item.handle for item in first.entities + second.entities] == ["F", "1"]
    projected = adapter.read_entity_page(request(intersects_wcs=(0, 0, 0, 9, 9, 9)))
    assert "2" not in [item.handle for item in projected.entities] and projected.issues
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(
            request(spaces=("block_definition",), intersects_wcs=(0, 0, 0, 9, 9, 9))
        )
    assert error.value.code == "UNSUPPORTED_CAPABILITY"
    source.values = [replace(WITNESS, epoch=2)]
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(replace(initial, cursor=first.next_cursor))
    assert error.value.code == "STALE_CURSOR"


def test_bounded_heap_reads_complete_facts_for_selected_records_only(monkeypatch):
    import autocad_mcp.adapter.windows_context as module

    original = module.nsmallest
    limits = []
    copied = []

    def measured(size, source, *, key):
        limits.append(size)
        return original(size, source, key=key)

    monkeypatch.setattr(module, "nsmallest", measured)

    class Tracked(Entity):
        def __getattribute__(self, name):
            if name == "StartPoint":
                copied.append(super().__getattribute__("Handle"))
            return super().__getattribute__(name)

    items = tuple(Tracked(**vars(entity(f"{index+1:X}"))) for index in range(10001))
    adapter, _, _, _, _ = setup(Document(items))
    result = adapter.read_entity_page(request(page_size=2))
    assert limits == [3] and copied == ["1", "2"] and len(result.entities) == 2


def test_attribute_duplicates_and_private_required_com_busy_are_fixed():
    class Duplicate(Entity):
        def GetConstantAttributes(self):  # noqa: N802 - exact injected ActiveX member
            return (SimpleNamespace(TagString="EDITABLE", TextString="duplicate"),)

    adapter, _, _, _, _ = setup(
        Document((Duplicate(**vars(entity(object_name="AcDbBlockReference"))),))
    )
    with pytest.raises(ContextValidationError):
        adapter.entity_facts_by_handles(("10",), ALL)

    class Busy(Entity):
        @property
        def StartPoint(self):  # noqa: N802 - exact injected ActiveX member
            raise RuntimeError("private path; server busy")

    values = vars(entity())
    del values["StartPoint"]
    adapter, _, _, com, _ = setup(Document((Busy(**values),)))
    with pytest.raises(AdapterError) as error:
        adapter.entity_facts_by_handles(("10",), ALL)
    assert error.value.code == AdapterErrorCode.COM_BUSY and "private" not in str(error.value)
    assert com.events == ["initialize", "uninitialize"]


def test_no_attribute_block_skips_array_getters_and_xref_reads_constants_only():
    class NoAttributes(Entity):
        def GetAttributes(self):  # noqa: N802 - exact injected ActiveX member
            raise AssertionError("No-attributes getter must not run")

        def GetConstantAttributes(self):  # noqa: N802 - exact injected ActiveX member
            raise AssertionError("No-attributes getter must not run")

    values = vars(entity(object_name="AcDbBlockReference"))
    values["HasAttributes"] = False
    adapter, _, _, _, _ = setup(Document((NoAttributes(**values),)))
    assert dict(adapter.entity_facts_by_handles(("10",), ALL)[0].block["attribute_values"]) == {}

    class Xref(Entity):
        def GetAttributes(self):  # noqa: N802 - exact injected ActiveX member
            raise AssertionError("External reference supports constants only")

    values["HasAttributes"] = True
    doc = Document((Xref(**values),))
    doc.Blocks.items[1].IsXRef = True
    adapter, _, _, _, _ = setup(doc)
    assert dict(adapter.entity_facts_by_handles(("10",), ALL)[0].block["attribute_values"]) == {
        "CONSTANT": "Fixed"
    }


def test_attribute_provenance_truthfully_names_both_acquisition_methods():
    adapter, _, _, _, _ = setup(Document((entity(object_name="AcDbBlockReference"),)))
    mapped = map_entity_context(adapter.entity_facts_by_handles(("10",), ALL)[0])
    for item in mapped.fact_evidence:
        if item.fact_path.startswith("/block/attribute_values/"):
            assert item.member == "GetAttributes/GetConstantAttributes"


@pytest.mark.parametrize(
    "code,expected",
    [
        ("BUSY", "COM_BUSY"),
        ("UNAVAILABLE", "REVISION_TOKEN_UNAVAILABLE"),
        ("UNTRUSTED_PEER", "REVISION_TOKEN_UNAVAILABLE"),
        ("TIMEOUT", "REVISION_TOKEN_UNAVAILABLE"),
    ],
)
def test_final_witness_loss_returns_no_facts_and_cleanup_is_balanced(code, expected):
    adapter, _, _, com, _ = setup(source=Source((WITNESS, NativeRevisionError(code))))
    with pytest.raises((ContextValidationError, AdapterError)) as error:
        adapter.entity_facts_by_handles(("10",), ALL)
    assert str(error.value.code) == expected and com.events == ["initialize", "uninitialize"]


def test_rotation_uses_activex_owner_basis_not_current_ucs_and_raw_values_have_no_proxies():
    doc = Document((entity(object_name="AcDbMText"),))
    adapter, _, _, _, _ = setup(doc)
    first = adapter.entity_facts_by_handles(("10",), ALL)[0]
    doc.Utility.TranslateCoordinates = lambda *args: (_ for _ in ()).throw(
        AssertionError("Text rotation must not read UCS")
    )
    second = adapter.entity_facts_by_handles(
        ("10",), ContextInclude(False, False, False, False, False, False)
    )[0]
    assert first == second and first.text["rotation_radians"] == 0.25
    payload = record_to_payload(first)

    def primitives(value):
        if type(value) is dict:
            return all(type(key) is str and primitives(item) for key, item in value.items())
        if type(value) is list:
            return all(primitives(item) for item in value)
        return type(value) in (str, int, float, bool, type(None))

    assert primitives(payload)


def test_max_unicode_layout_handle_and_missing_cursor_boundary():
    items = (entity("E" * 128, ObjectID=1), entity("F" * 128, ObjectID=2))
    doc = Document(items)
    doc.Blocks.items[0].Layout.Name = "🙂" * 255
    adapter, _, _, _, _ = setup(doc)
    first = adapter.read_entity_page(request(page_size=1))
    assert len(first.next_cursor.encode()) <= 2048
    assert (
        adapter.read_entity_page(request(page_size=1, cursor=first.next_cursor)).entities[0].handle
        == "F" * 128
    )
    doc.Blocks.items[0].items = (items[1],)
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(request(page_size=1, cursor=first.next_cursor))
    assert error.value.code == "INVALID_CURSOR"
