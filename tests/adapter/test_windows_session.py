from __future__ import annotations

from types import SimpleNamespace

import pytest
from autocad_mcp.adapter import windows_session
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.adapter.windows_session import ComModules, WindowsSessionManager


class StubPythonCom:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.uninitialize_error: Exception | None = None

    def CoInitialize(self) -> None:  # noqa: N802
        self.events.append("initialize")

    def CoUninitialize(self) -> None:  # noqa: N802
        self.events.append("uninitialize")
        if self.uninitialize_error is not None:
            raise self.uninitialize_error


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


def test_cleanup_failure_does_not_mask_consumer_error(caplog: pytest.LogCaptureFixture) -> None:
    """A cleanup failure must not replace the exception the caller needs to handle."""
    manager, pythoncom, _ = make_manager(application())
    pythoncom.uninitialize_error = RuntimeError("private cleanup detail")

    with pytest.raises(RuntimeError, match="consumer"):
        with manager.session(require_document=False):
            raise RuntimeError("private consumer detail")

    assert pythoncom.events == ["initialize", "uninitialize"]
    assert "AutoCAD COM cleanup failed after a primary error" in caplog.text
    assert "private cleanup detail" not in caplog.text
    assert "private consumer detail" not in caplog.text


def test_cleanup_failure_is_classified_after_success() -> None:
    """A failed cleanup after normal work must still be visible as a public error."""
    manager, pythoncom, _ = make_manager(application())
    pythoncom.uninitialize_error = RuntimeError("cleanup failed")

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=False):
            pass

    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED
    assert pythoncom.events == ["initialize", "uninitialize"]


def test_session_balances_com_on_connection_error(caplog: pytest.LogCaptureFixture) -> None:
    """An attachment failure after initialization must be paired with cleanup."""
    manager, pythoncom, _ = make_manager(RuntimeError("private connection detail"))

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=False):
            pass

    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert pythoncom.events == ["initialize", "uninitialize"]
    assert "private connection detail" not in caplog.text


def test_loader_diagnostics_do_not_expose_import_exception_text(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_import(name: str) -> None:
        raise ImportError("private dependency path")

    monkeypatch.setattr(windows_session, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(windows_session, "importlib", SimpleNamespace(import_module=fail_import))
    with pytest.raises(AdapterError) as raised:
        windows_session.load_com_modules()
    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert caplog.records
    assert "private dependency path" not in caplog.text


def test_session_balances_com_on_document_error() -> None:
    """A failed active-document lookup must not leak a COM apartment."""
    manager, pythoncom, _ = make_manager(application(document=RuntimeError("no document")))

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=True):
            pass

    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED
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


def application_without_documents(failure: Exception, *, count: object = 0) -> object:
    """Model AutoCAD raising on ``ActiveDocument`` while ``Documents`` reports its size."""

    class EmptyApplication:
        Documents = SimpleNamespace(Count=count)

        @property
        def ActiveDocument(self) -> object:  # noqa: N802
            raise failure

    return EmptyApplication()


def test_empty_documents_collection_is_a_no_document_state(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AutoCAD raises on ActiveDocument with zero drawings; Documents.Count == 0 proves it."""
    manager, pythoncom, _ = make_manager(
        application_without_documents(RuntimeError("private: no document is active"))
    )

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=True):
            pass

    assert raised.value.code is AdapterErrorCode.NO_ACTIVE_DOCUMENT
    assert raised.value.retryable is False
    assert pythoncom.events == ["initialize", "uninitialize"]
    assert "private" not in caplog.text


@pytest.mark.parametrize("count", [2, "0", None, False])
def test_document_failure_stays_an_operation_failure_without_an_empty_count(
    count: object,
) -> None:
    """Only an explicit integer zero count may downgrade a COM failure to no-document."""
    manager, pythoncom, _ = make_manager(
        application_without_documents(RuntimeError("document read failed"), count=count)
    )

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=True):
            pass

    assert raised.value.code is AdapterErrorCode.AUTOCAD_OPERATION_FAILED
    assert pythoncom.events == ["initialize", "uninitialize"]


def test_busy_document_failure_is_not_masked_by_an_empty_count() -> None:
    """A busy server must stay retryable even when the Documents count reads zero."""
    manager, _, _ = make_manager(application_without_documents(RuntimeError("server busy")))

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=True):
            pass

    assert raised.value.code is AdapterErrorCode.COM_BUSY
    assert raised.value.retryable is True


def test_consumer_adapter_error_propagates_as_the_same_instance() -> None:
    """contextlib attaches a traceback to the propagated error; identity must survive."""
    manager, pythoncom, _ = make_manager(application())
    error = AdapterError(
        AdapterErrorCode.ENTITY_NOT_FOUND, "Entity was not found", details={"object_id": 1}
    )

    with pytest.raises(AdapterError) as raised:
        with manager.session(require_document=False):
            raise error

    assert raised.value is error
    assert raised.value.details == {"object_id": 1}
    assert pythoncom.events == ["initialize", "uninitialize"]
