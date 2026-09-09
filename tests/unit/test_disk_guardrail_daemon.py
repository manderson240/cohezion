"""Unit tests for Autonomous Disk & Resource Guardrail System."""

from __future__ import annotations

from cohezion.core.resource_management.disk_guardrail_daemon import DiskGuardrailSystem


def test_storage_status_inspection() -> None:
    guard = DiskGuardrailSystem(monitored_path="/", warning_percent=85.0, critical_percent=92.0)
    status = guard.check_storage()

    assert status.total_gb > 0.0
    assert status.free_gb > 0.0
    assert 0.0 <= status.percent_used <= 100.0


def test_ephemeral_prune() -> None:
    guard = DiskGuardrailSystem()
    res = guard.prune_ephemeral_caches()
    assert res["status"] == "ephemeral_pruned"


def test_google_workspace_alert_generation() -> None:
    guard = DiskGuardrailSystem()
    status = guard.check_storage()
    alert = guard.generate_google_workspace_alert(status)

    assert "Google Workspace Alert Gateway" in alert["service"]
    assert "Cohezion Storage Warning" in alert["subject"]
    assert str(status.free_gb) in alert["body"]
