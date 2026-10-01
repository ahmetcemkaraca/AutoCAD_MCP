from __future__ import annotations

import importlib
import sys

import pytest
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode


def test_windows_modules_import_without_loading_com_packages() -> None:
    """An eager COM import would make this portable boundary unusable."""
    names = (
        "autocad_mcp.adapter.windows_session",
        "autocad_mcp.adapter.windows",
        "pythoncom",
        "win32com",
        "win32com.client",
        "pyautocad",
    )
    for name in names:
        sys.modules.pop(name, None)

    for name in (
        "autocad_mcp.adapter",
        "autocad_mcp.adapter.protocol",
        "autocad_mcp.adapter.capabilities",
        "autocad_mcp.adapter.provider",
        "autocad_mcp.adapter.windows_session",
        "autocad_mcp.adapter.windows",
    ):
        importlib.import_module(name)

    assert not {"pythoncom", "win32com", "win32com.client", "pyautocad"} & set(sys.modules)


def test_non_windows_loader_returns_redacted_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-Windows host must not expose an import implementation detail."""
    session = importlib.import_module("autocad_mcp.adapter.windows_session")
    monkeypatch.setattr(session.sys, "platform", "linux")

    with pytest.raises(AdapterError) as raised:
        session.load_com_modules()

    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert "ModuleNotFoundError" not in raised.value.public_message


def test_missing_windows_dependency_returns_redacted_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing pywin32 module must not escape from the delayed loader."""
    session = importlib.import_module("autocad_mcp.adapter.windows_session")
    monkeypatch.setattr(session.sys, "platform", "win32")

    def missing(name: str) -> object:
        raise ModuleNotFoundError(name=name)

    monkeypatch.setattr(session.importlib, "import_module", missing)

    with pytest.raises(AdapterError) as raised:
        session.load_com_modules()

    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert "pythoncom" not in raised.value.public_message
