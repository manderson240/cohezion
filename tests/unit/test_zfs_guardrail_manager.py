"""Unit tests for ZFS Guardrail Manager (source-level mocks, no live ZFS)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from cohezion.core.resource_management.zfs_guardrail_manager import ZFSGuardrailManager


ZPOOL_STATUS_ONLINE = """  pool: rpool
 state: ONLINE
config:

NAME        STATE     READ WRITE CKSUM
rpool       ONLINE       0     0     0
errors: No known data errors
"""

ZFS_LIST_POOL = "rpool\t120G\t60G\n"

ZFS_SNAPSHOTS = """rpool/var/lib/docker@snap1\t0B\t-
rpool/var/lib/docker@snap2\t10K\t-
rpool@nightly\t1M\t-
"""


def test_zfs_pool_health_query() -> None:
    """get_pool_health parses zpool/zfs output; subprocess mocked at source."""

    def fake_run(cmd, **kwargs):
        if cmd[0] == "zpool":
            return subprocess.CompletedProcess(cmd, 0, stdout=ZPOOL_STATUS_ONLINE, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=ZFS_LIST_POOL, stderr="")

    mgr = ZFSGuardrailManager(primary_pool="rpool")
    with patch(
        "cohezion.core.resource_management.zfs_guardrail_manager.subprocess.run",
        side_effect=fake_run,
    ):
        health = mgr.get_pool_health()

    assert health is not None
    assert health.pool_name == "rpool"
    assert health.state == "ONLINE"
    assert health.errors == "none"
    assert health.has_scrub_errors is False
    assert health.used_human == "120G"


def test_zfs_pool_health_missing_binary_returns_none() -> None:
    """Missing zpool binary (CI runners) must yield None, not raise."""

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    mgr = ZFSGuardrailManager(primary_pool="rpool")
    with patch(
        "cohezion.core.resource_management.zfs_guardrail_manager.subprocess.run",
        side_effect=fake_run,
    ):
        health = mgr.get_pool_health()

    assert health is None


def test_zfs_snapshot_listing() -> None:
    """list_snapshots parses `zfs list -t snapshot` rows deterministically."""
    mgr = ZFSGuardrailManager(primary_pool="rpool")
    with patch(
        "cohezion.core.resource_management.zfs_guardrail_manager.subprocess.run"
    ) as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            ["zfs"], 0, stdout=ZFS_SNAPSHOTS, stderr=""
        )
        snaps = mgr.list_snapshots(dataset="rpool/var/lib/docker")

    assert isinstance(snaps, list)
    assert len(snaps) == 3
    assert snaps[0].dataset == "rpool/var/lib/docker"
    assert snaps[0].name == "snap1"
    assert snaps[0].used == "0B"
    assert snaps[1].name == "snap2"


def test_zfs_snapshot_listing_binary_error_returns_empty() -> None:
    """`zfs` failing (missing binary / bad dataset) yields [], not raise."""
    mgr = ZFSGuardrailManager(primary_pool="rpool")
    with patch(
        "cohezion.core.resource_management.zfs_guardrail_manager.subprocess.run"
    ) as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            ["zfs"], 1, stdout="", stderr="cannot open dataset"
        )
        snaps = mgr.list_snapshots(dataset="rpool/var/lib/docker")

    assert snaps == []
