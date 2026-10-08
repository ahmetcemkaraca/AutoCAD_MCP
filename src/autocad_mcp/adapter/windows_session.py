"""Delayed, short-lived COM sessions for Windows-only adapter implementations."""

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType
from typing import Any, cast

from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComModules:
    """The COM modules loaded only when a Windows operation starts."""

    pythoncom: ModuleType
    client: ModuleType


@dataclass(frozen=True)
class AutoCADSession:
    """COM proxies valid only while a manager session context is open."""

    com: ComModules
    application: object
    document: object | None
    model_space: object | None


def load_com_modules() -> ComModules:
    """Load Windows COM dependencies without making portable imports depend on them."""
    if sys.platform != "win32":
        raise AdapterError(
            AdapterErrorCode.AUTOCAD_UNAVAILABLE,
            "Windows AutoCAD automation is unavailable on this platform",
            retryable=True,
        )
    try:
        return ComModules(
            importlib.import_module("pythoncom"),
            importlib.import_module("win32com.client"),
        )
    except (ImportError, ModuleNotFoundError) as error:
        logger.error(
            "Windows COM dependencies could not be loaded; error_type=%s", type(error).__name__
        )
        raise AdapterError(
            AdapterErrorCode.AUTOCAD_UNAVAILABLE,
            "Windows AutoCAD automation dependencies are unavailable",
            retryable=True,
        ) from error


def _is_busy(error: Exception) -> bool:
    hresult = getattr(error, "hresult", None)
    return hresult in {-2147418111, -2147417846} or any(
        phrase in str(error).lower()
        for phrase in ("busy", "call was rejected", "retry later", "rpc_e_call_rejected")
    )


def _com_error(error: Exception, code: AdapterErrorCode) -> AdapterError:
    if isinstance(error, AdapterError):
        return error
    logger.error("AutoCAD COM operation failed; error_type=%s", type(error).__name__)
    if _is_busy(error):
        return AdapterError(AdapterErrorCode.COM_BUSY, "AutoCAD is busy", retryable=True)
    messages = {
        AdapterErrorCode.AUTOCAD_UNAVAILABLE: ("Full AutoCAD is unavailable", True),
        AdapterErrorCode.NO_ACTIVE_DOCUMENT: ("No active document", False),
        AdapterErrorCode.AUTOCAD_OPERATION_FAILED: ("AutoCAD operation failed", False),
    }
    message, retryable = messages[code]
    return AdapterError(code, message, retryable=retryable)


def _no_open_documents(application: object) -> bool:
    """Return True only when the ``Documents`` collection explicitly reports zero drawings."""
    try:
        count = cast(Any, application).Documents.Count
    except Exception:
        return False
    return type(count) is int and count == 0


def active_document(application: object) -> object | None:
    """Read ``ActiveDocument``; an explicitly empty ``Documents`` collection yields None.

    AutoCAD raises from ``ActiveDocument`` while no drawing is open. That state is only
    reported as no-document when ``Documents.Count`` is the integer zero; any other
    failure keeps its public classification so a COM fault is never hidden.
    """
    try:
        return cast(object, cast(Any, application).ActiveDocument)
    except AdapterError:
        raise
    except Exception as error:
        if not _is_busy(error) and _no_open_documents(application):
            return None
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error


def _document_and_model_space(application: object) -> tuple[object, object | None]:
    document = active_document(application)
    if document is None:
        raise AdapterError(AdapterErrorCode.NO_ACTIVE_DOCUMENT, "No active document")
    try:
        return document, cast(object, cast(Any, document).ModelSpace)
    except AttributeError:
        return document, None
    except Exception as error:
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error


def _uninitialize(com: ComModules, primary_error: BaseException | None) -> None:
    try:
        com.pythoncom.CoUninitialize()
    except Exception as error:
        if primary_error is not None:
            logger.error(
                "AutoCAD COM cleanup failed after a primary error; error_type=%s",
                type(error).__name__,
            )
            return
        raise _com_error(error, AdapterErrorCode.AUTOCAD_OPERATION_FAILED) from error


class WindowsSessionManager:
    """Own one COM apartment and running-AutoCAD attachment per operation."""

    def __init__(self, com_loader: Callable[[], ComModules] = load_com_modules) -> None:
        self._com_loader = com_loader

    @contextmanager
    def session(self, require_document: bool) -> Iterator[AutoCADSession]:
        """Yield transient proxies and always balance a successful apartment initialization."""
        com = self._com_loader()
        initialized = False
        primary_error: BaseException | None = None
        try:
            try:
                com.pythoncom.CoInitialize()
            except Exception as error:
                raise _com_error(error, AdapterErrorCode.AUTOCAD_UNAVAILABLE) from error
            initialized = True
            try:
                application = com.client.GetActiveObject("AutoCAD.Application")
            except Exception as error:
                raise _com_error(error, AdapterErrorCode.AUTOCAD_UNAVAILABLE) from error
            if application is None:
                raise AdapterError(
                    AdapterErrorCode.AUTOCAD_UNAVAILABLE,
                    "Full AutoCAD is unavailable",
                    retryable=True,
                )

            document: object | None = None
            model_space: object | None = None
            if require_document:
                document, model_space = _document_and_model_space(application)
            yield AutoCADSession(com, application, document, model_space)
        except BaseException as error:
            primary_error = error
            raise
        finally:
            if initialized:
                _uninitialize(com, primary_error)
