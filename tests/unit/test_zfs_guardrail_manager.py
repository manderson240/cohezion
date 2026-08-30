"""Unit tests for ZFS Guardrail Manager."""

from __future__ import annotations

from cohezion.core.resource_management.zfs_guardrail_manager import ZFSGuardrailManager


def test_zfs_pool_health_query() -> None:
    mgr = ZFSGuardrailManager(primary_pool="rpool")
    health = mgr.get_pool_health()

    assert health is not None
    assert health.pool_name == "rpool"
    assert health.state in ("ONLINE", "DEGRADED")
    assert health.errors == "none"


def test_zfs_snapshot_listing() -> None:
    mgr = ZFSGuardrailManager(primary_pool="rpool")
    snaps = mgr.list_snapshots(dataset="rpool/var/lib/docker")

    assert isinstance(snaps, list)
    assert len(snaps) > 0
    assert snaps[0].dataset == "rpool/var/lib/docker"
