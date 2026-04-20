import pytest
import torch
from cohezion.core.silicon_guard import SiliconGuard

def test_silicon_guard_thermal_throttling():
    # Simulate high temperature
    guard = SiliconGuard(temp_limit=30.0) # Set very low limit to trigger
    
    # We can't easily mock the /sys/ file here without complexity,
    # but we can verify the logic if get_temperature is forced
    
    payload = {"prompt": "Analyze", "max_tokens": 1000}
    
    # Manually check if it triggers a throttle based on the default 45C baseline
    pressure = guard.check_safety()
    assert pressure.is_throttled is True
    assert "Thermal limit" in pressure.reason
    
    throttled_payload = guard.apply_guardrails(payload)
    assert throttled_payload["max_tokens"] == 128
    assert throttled_payload["temperature"] == 0.1

def test_silicon_guard_memory_limit_mock():
    from unittest.mock import patch
    guard = SiliconGuard(gtt_limit_gb=10.0)
    
    # Mock get_gpu_memory to return high pressure
    with patch.object(SiliconGuard, 'get_gpu_memory', return_value=15.0):
        pressure = guard.check_safety()
        assert pressure.is_throttled is True
        assert "VRAM over-subscription" in pressure.reason
        
        payload = {"max_tokens": 1000}
        throttled = guard.apply_guardrails(payload)
        assert throttled["max_tokens"] == 128
