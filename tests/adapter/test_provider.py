from __future__ import annotations

import sys

from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.provider import StaticAdapterProvider, WindowsAdapterProvider


def test_static_provider_returns_its_injected_adapter() -> None:
    adapter = FakeAutoCADAdapter()

    assert StaticAdapterProvider(adapter).get() is adapter


def test_windows_provider_defers_the_windows_import_until_get() -> None:
    sys.modules.pop("autocad_mcp.adapter.windows", None)

    provider = WindowsAdapterProvider(factory=FakeAutoCADAdapter)

    assert "autocad_mcp.adapter.windows" not in sys.modules
    assert isinstance(provider.get(), FakeAutoCADAdapter)


def test_default_windows_provider_creates_the_windows_adapter_without_loading_com() -> None:
    sys.modules.pop("autocad_mcp.adapter.windows", None)

    adapter = WindowsAdapterProvider().get()

    from autocad_mcp.adapter.windows import WindowsAutoCADAdapter

    assert isinstance(adapter, WindowsAutoCADAdapter)
    assert not {"pythoncom", "win32com", "win32com.client"} & set(sys.modules)
