from __future__ import annotations

from types import SimpleNamespace

import pytest
from autocad_mcp.adapter.capabilities import AdapterCapability, AdapterCapabilityIssueCode
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
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
    assert status.capabilities.available == frozenset({AdapterCapability.CONNECTION})


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
