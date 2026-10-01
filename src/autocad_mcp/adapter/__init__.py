"""Pure public AutoCAD adapter contracts and portable test fake."""

from autocad_mcp.adapter.capabilities import (
    AdapterCapability,
    AdapterCapabilityIssue,
    AdapterCapabilityIssueCode,
    AdapterCapabilityReport,
)
from autocad_mcp.adapter.context_protocol import (
    CONTEXT_ADAPTER_SCHEMA_VERSION,
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterDocumentIdentity,
    AdapterDocumentRevisionToken,
    AdapterEntityFacts,
    AdapterEntityPage,
    AdapterEntityReadRequest,
    ContextAdapterProvider,
    ContextAutoCADAdapter,
    ContextInclude,
)
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.fake_context import FakeContextAutoCADAdapter, StaticContextAdapterProvider
from autocad_mcp.adapter.protocol import (
    AdapterError,
    AdapterErrorCode,
    AutoCADAdapter,
    ConnectionInfo,
    EntityDetails,
    EntitySummary,
)
from autocad_mcp.adapter.provider import (
    AdapterProvider,
    StaticAdapterProvider,
    WindowsAdapterProvider,
)

__all__ = [
    "CONTEXT_ADAPTER_SCHEMA_VERSION",
    "AdapterContextIssue",
    "AdapterDocumentContext",
    "AdapterDocumentIdentity",
    "AdapterDocumentRevisionToken",
    "AdapterEntityFacts",
    "AdapterEntityPage",
    "AdapterEntityReadRequest",
    "ContextAdapterProvider",
    "ContextAutoCADAdapter",
    "ContextInclude",
    "FakeContextAutoCADAdapter",
    "StaticContextAdapterProvider",
    "AdapterCapability",
    "AdapterCapabilityIssue",
    "AdapterCapabilityIssueCode",
    "AdapterCapabilityReport",
    "AdapterError",
    "AdapterErrorCode",
    "AdapterProvider",
    "AutoCADAdapter",
    "ConnectionInfo",
    "EntityDetails",
    "EntitySummary",
    "FakeAutoCADAdapter",
    "StaticAdapterProvider",
    "WindowsAdapterProvider",
]
