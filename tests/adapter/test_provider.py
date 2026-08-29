from __future__ import annotations

import sys

import pytest
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.adapter.provider import StaticAdapterProvider, WindowsAdapterProvider


def test_static_provider_returns_its_injected_adapter() -> None:
    adapter = FakeAutoCADAdapter()

    assert StaticAdapterProvider(adapter).get() is adapter


def test_windows_provider_defers_the_windows_import_until_get() -> None:
    sys.modules.pop("autocad_mcp.adapter.windows", None)

    provider = WindowsAdapterProvider(factory=FakeAutoCADAdapter)

    assert "autocad_mcp.adapter.windows" not in sys.modules
    assert isinstance(provider.get(), FakeAutoCADAdapter)


def test_default_windows_provider_classifies_missing_implementation_as_unavailable() -> None:
    sys.modules.pop("autocad_mcp.adapter.windows", None)

    with pytest.raises(AdapterError) as raised:
        WindowsAdapterProvider().get()

    assert raised.value.code is AdapterErrorCode.AUTOCAD_UNAVAILABLE
    assert raised.value.retryable is True
