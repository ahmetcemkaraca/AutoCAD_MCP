from __future__ import annotations

from types import SimpleNamespace

import pytest
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.adapter.windows_session import ComModules, WindowsSessionManager


class StubPythonCom:
    def __init__(self) -> None:
        self.events: list[str] = []

    def CoInitialize(self) -> None:  # noqa: N802
        self.events.append("initialize")

    def CoUninitialize(self) -> None:  # noqa: N802
        self.events.append("uninitialize")


class StubClient:
    def __init__(self, application: object | Exception) -> None:
        self.application = application
        self.progids: list[str] = []
        self.created = False

    def GetActiveObject(self, progid: str) -> object:  # noqa: N802
        self.progids.append(progid)
        if isinstance(self.application, Exception):
            raise self.application
        return self.application

    def Dispatch(self, progid: str) -> object:  # noqa: N802
        self.created = True
        raise AssertionError(f"creation attempted for {progid}")


def make_manager(
    application: object | Exception,
) -> tuple[WindowsSessionManager, StubPythonCom, StubClient]:
    pythoncom = StubPythonCom()
    client = StubClient(application)
    return WindowsSessionManager(lambda: ComModules(pythoncom, client)), pythoncom, client


def application(*, document: object | Exception | None = None) -> object:
    if isinstance(document, Exception):
        class BrokenApplication:
            @property
            def ActiveDocument(self) -> object:  # noqa: N802
                raise document

        return BrokenApplication()
    return SimpleNamespace(ActiveDocument=document)


def test_session_balances_com_on_success() -> None:
    """Removing the finally cleanup would leave an apartment initialized."""
    document = SimpleNamespace(ModelSpace=())
    manager, pythoncom, client = make_manager(application(document=document))

    with manager.session(require_document=True) as session:
        assert session.document is document
        assert session.model_space == ()

    assert pythoncom.events == ["initialize", "uninitialize"]
    assert client.progids == ["AutoCAD.Application"]
    assert client.created is False


def test_session_without_document_yields_only_the_application() -> None:
    """An optional document must not be read by an application-only operation."""
    app = application()
    manager, pythoncom, _ = make_manager(app)

    with manager.session(require_document=False) as session:
        assert session.application is app
        assert session.document is None
        assert session.model_space is None

    assert pythoncom.events == ["initialize", "uninitialize"]


def test_session_balances_com_on_consumer_error() -> None:
    """A caller exception must still balance the COM apartment."""
    manager, pythoncom, _ = make_manager(application())

    with pytest.raises(RuntimeError, match="consumer"):
        with manager.session(require_document=False):
            raise RuntimeError("consumer")

    assert pythoncom.events == ["initialize", "uninitialize"]


def test_session_balances_com_on_connection_error() -> None:
    """An attachment failure after initialization must be paired with cleanup."""
    manager, pythoncom, _ = make_manager(RuntimeError("not running"))

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=False):
            pass

    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert pythoncom.events == ["initialize", "uninitialize"]


def test_session_balances_com_on_document_error() -> None:
    """A failed active-document lookup must not leak a COM apartment."""
    manager, pythoncom, _ = make_manager(application(document=RuntimeError("no document")))

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=True):
            pass

    assert raised.value.code is AdapterErrorCode.NO_ACTIVE_DOCUMENT
    assert pythoncom.events == ["initialize", "uninitialize"]


def test_manager_does_not_retain_proxies_after_exit() -> None:
    """Keeping a yielded proxy on the manager would cross apartment boundaries."""
    model_space = object()
    document = SimpleNamespace(ModelSpace=model_space)
    app = application(document=document)
    manager, _, _ = make_manager(app)

    with manager.session(require_document=True):
        pass

    assert vars(manager) == {"_com_loader": vars(manager)["_com_loader"]}


def test_windows_extensions_share_manager_without_lifecycle_duplication() -> None:
    """Each Windows-only consumer opens its own short-lived manager context."""
    manager, pythoncom, _ = make_manager(application())

    class WindowsContextExtension:
        def read(self) -> bool:
            with manager.session(require_document=False) as session:
                return session.application is not None

    class WindowsCaptureExtension:
        def read(self) -> bool:
            with manager.session(require_document=False) as session:
                return session.application is not None

    assert WindowsContextExtension().read() is True
    assert WindowsCaptureExtension().read() is True
    assert pythoncom.events == ["initialize", "uninitialize", "initialize", "uninitialize"]
