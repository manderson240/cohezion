"""Tests for SmartOOMGovernor and CrossSessionFleetLock."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from cohezion.inference.smart_oom_governor import (
    CrossSessionFleetLock,
    SmartOOMGovernor,
)


def test_smart_oom_governor_memory_state():
    with patch("psutil.virtual_memory") as mock_vm, patch("psutil.swap_memory") as mock_sm:
        mock_vm.return_value = MagicMock(available=45.0 * (1024**3))
        mock_sm.return_value = MagicMock(used=0.5 * (1024**3))

        avail, swap, is_safe = SmartOOMGovernor.get_memory_state()
        assert avail == 45.0
        assert swap == 0.5
        assert is_safe is True


def test_smart_oom_governor_rejection_on_low_memory():
    with patch("psutil.virtual_memory") as mock_vm, patch("psutil.swap_memory") as mock_sm:
        mock_vm.return_value = MagicMock(available=20.0 * (1024**3))
        mock_sm.return_value = MagicMock(used=0.5 * (1024**3))

        can_exec, reason = SmartOOMGovernor.can_execute_local()
        assert can_exec is False
        assert "Memory backpressure" in reason


def test_smart_oom_governor_rejection_on_gtt_saturation():
    with patch("psutil.virtual_memory") as mock_vm, patch(
        "psutil.swap_memory"
    ) as mock_sm, patch.object(SmartOOMGovernor, "get_gtt_used_gib", return_value=55.0):
        mock_vm.return_value = MagicMock(available=50.0 * (1024**3))
        mock_sm.return_value = MagicMock(used=0.5 * (1024**3))

        can_exec, reason = SmartOOMGovernor.can_execute_local()
        assert can_exec is False
        assert "GPU GTT saturation" in reason


def test_smart_oom_governor_rejection_on_psi_pressure():
    with patch("psutil.virtual_memory") as mock_vm, patch(
        "psutil.swap_memory"
    ) as mock_sm, patch.object(
        SmartOOMGovernor, "get_gtt_used_gib", return_value=25.0
    ), patch.object(
        SmartOOMGovernor, "get_psi_pressure", return_value=35.0
    ):
        mock_vm.return_value = MagicMock(available=50.0 * (1024**3))
        mock_sm.return_value = MagicMock(used=0.5 * (1024**3))

        can_exec, reason = SmartOOMGovernor.can_execute_local()
        assert can_exec is False
        assert "Kernel memory pressure" in reason


def test_fleet_lock_acquisition_and_release(tmp_path):
    lock_file = tmp_path / "test_fleet.lock"
    with patch("cohezion.inference.smart_oom_governor.LOCK_PATH", lock_file):
        with CrossSessionFleetLock(timeout_sec=2.0) as lock:
            assert lock._fd is not None
            assert os.path.exists(lock_file)
        assert lock._fd is None
