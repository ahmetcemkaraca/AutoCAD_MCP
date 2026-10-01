from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest
from autocad_mcp.adapter.capabilities import AdapterCapability, AdapterCapabilityIssueCode
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode, EntitySummary
from autocad_mcp.adapter.windows import WindowsAutoCADAdapter, detect_capabilities
from autocad_mcp.adapter.windows_session import AutoCADSession, ComModules, WindowsSessionManager

from tests.adapter.test_windows_session import StubClient, StubPythonCom


class Entity:
    def __init__(self, object_id: int = 7) -> None:
        self.ObjectID = object_id
        self.Handle = "A7"
        self.ObjectName = "AcDbLine"
        self.Layer = "Annotations"
        self.Color = 3
        self.Linetype = "Dashed"
        self.Length = 4.5
        self.Area = 2.0
        self.Volume = 1.0
        self.Radius = 0.5
        self.Center = (1.0, 2.0, 3.0)
        self.StartPoint = (0.0, 0.0, 0.0)
        self.EndPoint = (4.0, 0.0, 0.0)


def manager_for(application: object | Exception) -> tuple[WindowsSessionManager, StubPythonCom]:
    pythoncom = StubPythonCom()
    client = StubClient(application)
    return WindowsSessionManager(lambda: ComModules(pythoncom, client)), pythoncom


def connected_application(
    *, entities: tuple[object, ...] = (Entity(),), read_only: bool = True
) -> object:
    return SimpleNamespace(
        Name="AutoCAD",
        Version="24.3",
        ActiveDocument=SimpleNamespace(Name="drawing.dwg", ReadOnly=read_only, ModelSpace=entities),
    )


def test_adapter_uses_injected_manager_for_each_operation() -> None:
    """Reusing a stale application proxy would reduce the pair count to one."""
    manager, pythoncom = manager_for(connected_application())
    adapter = WindowsAutoCADAdapter(session_manager=manager)

    assert adapter.status().connected is True
    assert adapter.reconnect().connected is True

    assert vars(adapter) == {"_session_manager": manager}
    assert pythoncom.events == ["initialize", "uninitialize", "initialize", "uninitialize"]


def test_detect_capabilities_reflects_identity_members() -> None:
    """Dropping a required identity member must disable read operations."""
    entity = Entity()
    del entity.Handle
    session = AutoCADSession(
        ComModules(StubPythonCom(), StubClient(object())), object(), object(), (entity,)
    )

    report = detect_capabilities(session)

    assert report.supports(AdapterCapability.CONNECTION)
    assert report.supports(AdapterCapability.ACTIVE_DOCUMENT)
    assert not report.supports(AdapterCapability.LIST_ENTITIES)
    assert not report.supports(AdapterCapability.GET_ENTITY_INFO)
    assert report.issues[0].code is AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE
    assert report.issues[0].member == "Handle"


def test_detect_capabilities_records_member_access_failure() -> None:
    """A COM getter error must not be mistaken for an available member."""
    class BrokenEntity(Entity):
        def __init__(self) -> None:
            self.Handle = "A7"
            self.ObjectName = "AcDbLine"
            self.Layer = "Annotations"

        @property
        def ObjectID(self) -> int:  # noqa: N802
            raise RuntimeError("COM getter failed")

    session = AutoCADSession(
        ComModules(StubPythonCom(), StubClient(object())), object(), object(), (BrokenEntity(),)
    )

    report = detect_capabilities(session)

    assert not report.supports(AdapterCapability.LIST_ENTITIES)
    assert report.issues[0].code is AdapterCapabilityIssueCode.MEMBER_ACCESS_FAILED
    assert report.issues[0].message == "Required AutoCAD member could not be read"


def test_entity_conversion_uses_only_allowlisted_properties() -> None:
    """Adding arbitrary entity attributes must not expand public details."""
    entity = Entity()
    entity.Unsafe = "not exported"
    manager, _ = manager_for(connected_application(entities=(entity,)))

    detail = WindowsAutoCADAdapter(manager).get_entity_info(7)

    assert detail.object_id == 7
    assert detail.handle == "A7"
    assert detail.properties == {
        "color": 3,
        "linetype": "Dashed",
        "length": 4.5,
        "area": 2.0,
        "volume": 1.0,
        "radius": 0.5,
        "center": [1.0, 2.0, 3.0],
        "start_point": [0.0, 0.0, 0.0],
        "end_point": [4.0, 0.0, 0.0],
    }


def test_entity_conversion_omits_missing_optional_properties() -> None:
    """An unavailable optional COM property must not fail a read-only detail call."""
    entity = SimpleNamespace(ObjectID=7, Handle="A7", ObjectName="AcDbLine", Layer="0")
    manager, _ = manager_for(connected_application(entities=(entity,)))
    adapter = WindowsAutoCADAdapter(manager)

    assert adapter.get_entity_info(7).properties == {}
    assert vars(adapter) == {"_session_manager": manager}


def test_entity_conversion_omits_non_json_optional_values() -> None:
    """COM proxies and non-finite values must not escape in an otherwise valid detail."""
    entity = SimpleNamespace(
        ObjectID=7,
        Handle="A7",
        ObjectName="AcDbLine",
        Layer="0",
        Color=object(),
        Area=math.nan,
        Volume=math.inf,
        Center={"point": [1.0, 2.0, 3.0]},
    )
    manager, _ = manager_for(connected_application(entities=(entity,)))

    detail = WindowsAutoCADAdapter(manager).get_entity_info(7)

    assert detail.properties == {"center": {"point": [1.0, 2.0, 3.0]}}
    assert json.dumps(detail.properties, allow_nan=False) == (
        '{"center": {"point": [1.0, 2.0, 3.0]}}'
    )


def test_entity_conversion_rejects_scalar_and_mapping_key_subclasses() -> None:
    """Subclassed scalar/proxy values must not cross the immutable JSON boundary."""
    class ProxyInteger(int):
        pass

    class ProxyString(str):
        pass

    class ProxyFloat(float):
        pass

    entity = SimpleNamespace(
        ObjectID=7,
        Handle="A7",
        ObjectName="AcDbLine",
        Layer="0",
        Color=ProxyInteger(3),
        Linetype=ProxyString("Dashed"),
        Length=ProxyFloat(4.5),
        Center={ProxyString("point"): 1},
        Area=2,
        Radius=0.5,
        Volume="safe",
    )
    manager, _ = manager_for(connected_application(entities=(entity,)))

    detail = WindowsAutoCADAdapter(manager).get_entity_info(7)

    assert detail.properties == {"area": 2, "volume": "safe", "radius": 0.5}
    assert json.dumps(detail.properties, allow_nan=False) == (
        '{"area": 2, "volume": "safe", "radius": 0.5}'
    )


def test_detail_not_found_is_a_public_error() -> None:
    """An absent entity is a normal lookup result, not a COM exception leak."""
    manager, _ = manager_for(connected_application())

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).get_entity_info(99)

    assert raised.value.code is AdapterErrorCode.ENTITY_NOT_FOUND
    assert raised.value.details == {"object_id": 99}


def test_status_is_read_only_and_handles_no_document() -> None:
    """Status must attach only and report a connected application without a document."""
    application = SimpleNamespace(Name="AutoCAD", Version="24.3", ActiveDocument=None)
    manager, _ = manager_for(application)

    status = WindowsAutoCADAdapter(manager).status()

    assert status.connected is True
    assert status.active_document is None
    assert status.read_only is None
    assert status.release_hint == "24.3"
    assert status.capabilities.available == frozenset({AdapterCapability.CONNECTION})


def test_status_rejects_a_missing_active_document_member() -> None:
    """Absent ActiveDocument is an adapter error, not a false no-document state."""
    manager, _ = manager_for(SimpleNamespace(Name="AutoCAD", Version="24.3"))

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).status()

    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED


def test_document_without_model_space_has_only_document_capability() -> None:
    """A present document without ModelSpace is not the same as no active document."""
    application = SimpleNamespace(
        Name="AutoCAD",
        Version="24.3",
        ActiveDocument=SimpleNamespace(Name="drawing.dwg", ReadOnly=True, ModelSpace=None),
    )
    manager, _ = manager_for(application)
    adapter = WindowsAutoCADAdapter(manager)

    status = adapter.status()
    assert status.capabilities.available == frozenset(
        {AdapterCapability.CONNECTION, AdapterCapability.ACTIVE_DOCUMENT}
    )

    with pytest.raises(AdapterError) as listed:
        adapter.list_entities()
    with pytest.raises(AdapterError) as detailed:
        adapter.get_entity_info(7)

    assert listed.value.code is AdapterErrorCode.UNSUPPORTED_CAPABILITY
    assert listed.value.details == {"capability": "list_entities"}
    assert detailed.value.code is AdapterErrorCode.UNSUPPORTED_CAPABILITY
    assert detailed.value.details == {"capability": "get_entity_info"}


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (RuntimeError("server busy"), AdapterErrorCode.COM_BUSY),
        (RuntimeError("model space read failed"), AdapterErrorCode.AUTOCAD_OPERATION_FAILED),
    ],
)
def test_status_classifies_document_access_errors(
    document: Exception, expected: AdapterErrorCode
) -> None:
    """A COM access failure must not become a false no-document status."""
    if expected is AdapterErrorCode.COM_BUSY:
        application = SimpleNamespace(Name="AutoCAD", Version="24.3")

        class BusyApplication:
            Name = application.Name
            Version = application.Version

            @property
            def ActiveDocument(self) -> object:  # noqa: N802
                raise document

        application = BusyApplication()
    else:
        class BrokenDocument:
            Name = "drawing.dwg"
            ReadOnly = True

            @property
            def ModelSpace(self) -> object:  # noqa: N802
                raise document

        application = SimpleNamespace(
            Name="AutoCAD", Version="24.3", ActiveDocument=BrokenDocument()
        )
    manager, _ = manager_for(application)

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).status()

    assert raised.value.code is expected


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (RuntimeError("not running"), AdapterErrorCode.AUTOCAD_UNAVAILABLE),
        (RuntimeError("server busy"), AdapterErrorCode.COM_BUSY),
    ],
)
def test_connection_errors_are_classified(failure: Exception, expected: AdapterErrorCode) -> None:
    """Changing error classification would expose a false public recovery path."""
    manager, _ = manager_for(failure)

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).status()

    assert raised.value.code is expected


def test_list_rejects_a_missing_capability_with_its_exact_name() -> None:
    """A model space without stable identity cannot support listing."""
    manager, _ = manager_for(connected_application(entities=(SimpleNamespace(),)))

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).list_entities()

    assert raised.value.code is AdapterErrorCode.UNSUPPORTED_CAPABILITY
    assert raised.value.details == {"capability": "list_entities"}


def test_entity_read_failure_is_redacted_as_an_operation_error() -> None:
    """An entity getter that fails after capability detection must not leak COM details."""
    class FlakyEntity:
        def __init__(self) -> None:
            self.calls = 0
            self.Handle = "A7"
            self.ObjectName = "AcDbLine"
            self.Layer = "0"

        @property
        def ObjectID(self) -> int:  # noqa: N802
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("private COM detail")
            return 7

    manager, _ = manager_for(connected_application(entities=(FlakyEntity(),)))

    with pytest.raises(AdapterError) as raised:
        WindowsAutoCADAdapter(manager).list_entities()

    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED
    assert "private COM detail" not in raised.value.public_message


def test_one_shot_model_space_keeps_the_sampled_first_entity() -> None:
    """Capability probing must replay, not lose, the first one-shot entity."""
    entity = Entity()

    class Document:
        Name = "drawing.dwg"
        ReadOnly = True

        @property
        def ModelSpace(self) -> object:  # noqa: N802
            return iter((entity,))

    application = SimpleNamespace(Name="AutoCAD", Version="24.3", ActiveDocument=Document())
    manager, _ = manager_for(application)
    adapter = WindowsAutoCADAdapter(manager)

    assert adapter.list_entities() == (EntitySummary(7, "A7", "AcDbLine", "Annotations"),)
    assert adapter.get_entity_info(7).object_id == 7


def test_status_does_not_overclaim_for_a_one_shot_iterator_that_cannot_next() -> None:
    """Status must not inspect a one-shot iterator that only an operation can consume."""
    class FailingIterator:
        def __iter__(self) -> FailingIterator:
            return self

        def __next__(self) -> object:
            raise RuntimeError("iterator read failed")

    class Document:
        Name = "drawing.dwg"
        ReadOnly = True

        @property
        def ModelSpace(self) -> object:  # noqa: N802
            return FailingIterator()

    manager, _ = manager_for(
        SimpleNamespace(Name="AutoCAD", Version="24.3", ActiveDocument=Document())
    )
    adapter = WindowsAutoCADAdapter(manager)

    status = adapter.status()
    assert not status.capabilities.supports(AdapterCapability.LIST_ENTITIES)
    assert not status.capabilities.supports(AdapterCapability.GET_ENTITY_INFO)
    assert status.capabilities.issues[0].member == "ModelSpace"

    with pytest.raises(AdapterError) as raised:
        adapter.list_entities()
    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED


def test_one_shot_missing_identity_is_unsupported_only_during_operation() -> None:
    """Status must defer identity validation, while listing validates the sampled entity."""
    class Document:
        Name = "drawing.dwg"
        ReadOnly = True

        @property
        def ModelSpace(self) -> object:  # noqa: N802
            return iter((SimpleNamespace(),))

    manager, _ = manager_for(
        SimpleNamespace(Name="AutoCAD", Version="24.3", ActiveDocument=Document())
    )
    adapter = WindowsAutoCADAdapter(manager)

    status = adapter.status()
    assert not status.capabilities.supports(AdapterCapability.LIST_ENTITIES)
    assert not status.capabilities.supports(AdapterCapability.GET_ENTITY_INFO)

    with pytest.raises(AdapterError) as raised:
        adapter.get_entity_info(7)
    assert raised.value.code is AdapterErrorCode.UNSUPPORTED_CAPABILITY
    assert raised.value.details == {"capability": "get_entity_info"}


def test_empty_one_shot_model_space_supports_empty_list_and_not_found_detail() -> None:
    """Known-empty one-shot model space must not be downgraded to unsupported."""
    class Document:
        Name = "drawing.dwg"
        ReadOnly = True

        @property
        def ModelSpace(self) -> object:  # noqa: N802
            return iter(())

    manager, _ = manager_for(
        SimpleNamespace(Name="AutoCAD", Version="24.3", ActiveDocument=Document())
    )
    adapter = WindowsAutoCADAdapter(manager)

    assert adapter.list_entities() == ()
    with pytest.raises(AdapterError) as raised:
        adapter.get_entity_info(7)
    assert raised.value.code is AdapterErrorCode.ENTITY_NOT_FOUND
