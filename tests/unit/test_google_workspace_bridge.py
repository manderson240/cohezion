"""Unit tests for Google Workspace Bridge."""

from __future__ import annotations

from cohezion.integrations.google_workspace_bridge import GoogleWorkspaceBridge


def test_email_alert_dispatch() -> None:
    bridge = GoogleWorkspaceBridge(default_recipient="test@example.com")
    alert = bridge.dispatch_email_alert(
        subject="Disk Warning: 88% used",
        body_markdown="Disk threshold reached. Pruning initiated.",
        priority="HIGH",
    )

    assert alert.recipient == "test@example.com"
    assert "Disk Warning" in alert.subject
    assert len(bridge.alert_log) == 1


def test_crm_spreadsheet_row_formatting() -> None:
    bridge = GoogleWorkspaceBridge()
    row = bridge.format_crm_spreadsheet_row(
        {"id": "stk_1", "name": "Alice", "organization_id": "org_quantum", "email": "alice@qc.io", "affinity_score": 0.892}
    )

    assert row[0] == "stk_1"
    assert row[1] == "Alice"
    assert row[2] == "org_quantum"
    assert row[4] == 0.892


def test_large_report_offload() -> None:
    bridge = GoogleWorkspaceBridge()
    doc = bridge.offload_large_report_to_docs(
        "DIRD 37 Comprehensive Synthesis",
        "# DIRD Synthesis\nDetailed multi-megabyte analysis...",
    )

    assert doc.title == "DIRD 37 Comprehensive Synthesis"
    assert "docs.google.com" in doc.cloud_url
    assert doc.bytes_offloaded > 0
