import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from cohezion.integrations.puppetmaster_bridge import PuppetmasterBridge, PuppetmasterReceipt
from cohezion.reliability.oom_guard import MemoryState

def test_puppetmaster_bridge_admission_denied_oom():
    bridge = PuppetmasterBridge()
    with patch(
        "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
        return_value=MemoryState(
            available_gb=10.0,
            total_gb=128.0,
            swap_used_gb=30.0,
            shmem_gb=0.5,
            is_safe=False,
            dynamic_floor_gb=20.0,
        ),
    ):
        admitted = bridge.acquire_hardware_admission("heavy-task")
        assert admitted is False

def test_puppetmaster_bridge_admission_granted():
    bridge = PuppetmasterBridge()
    with patch(
        "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
        return_value=MemoryState(
            available_gb=35.0,
            total_gb=128.0,
            swap_used_gb=0.0,
            shmem_gb=0.5,
            is_safe=True,
            dynamic_floor_gb=20.0,
        ),
    ):
        with patch("cohezion.integrations.puppetmaster_bridge.FleetLock") as mock_lock:
            mock_lock.return_value.__enter__.return_value = None
            admitted = bridge.acquire_hardware_admission("safe-task")
            assert admitted is True

@pytest.mark.asyncio
async def test_publish_job_completion():
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    
    async def mock_pub(evt):
        return None
    mock_bus.publish.side_effect = mock_pub

    bridge = PuppetmasterBridge(event_bus=mock_bus)
    receipt = PuppetmasterReceipt(
        job_id="job_test_123",
        status="completed",
        target_worktree="/tmp/worktree",
        prompt="Audit security",
        artifacts_count=3,
        total_tokens=450,
        duration_s=12.5,
    )
    await bridge.publish_job_completion(receipt)
    assert mock_bus.publish.called
