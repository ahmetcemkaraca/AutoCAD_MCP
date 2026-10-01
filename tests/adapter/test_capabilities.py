from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from autocad_mcp.adapter.capabilities import (
    AdapterCapability,
    AdapterCapabilityIssue,
    AdapterCapabilityIssueCode,
    AdapterCapabilityReport,
)


def test_capability_report_records_available_capabilities_and_immutable_issues() -> None:
    issue = AdapterCapabilityIssue(
        AdapterCapabilityIssueCode.MEMBER_UNAVAILABLE,
        AdapterCapability.GET_ENTITY_INFO,
        "ObjectID",
        "ObjectID is unavailable",
    )
    report = AdapterCapabilityReport(frozenset({AdapterCapability.CONNECTION}), (issue,))

    assert report.supports(AdapterCapability.CONNECTION) is True
    assert report.supports(AdapterCapability.GET_ENTITY_INFO) is False
    assert report.issues == (issue,)
    with pytest.raises(FrozenInstanceError):
        issue.member = "Handle"
    with pytest.raises(FrozenInstanceError):
        report.issues = ()
