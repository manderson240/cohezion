from unittest.mock import patch

import torch

from cohezion.core.silicon_guard import HardwarePressure, SiliconGuard
from cohezion.flume.coherence_guard import TurboQuantHarness, apply_dummy_int8_quantization

# Strix Halo has >87GB VRAM usage; patch silicon guard to not fire during unit tests
_safe_guard = SiliconGuard(gtt_limit_gb=200.0, temp_limit=100.0)
_not_throttled = HardwarePressure(temp_c=40.0, gpu_mem_used_gb=50.0, npu_active=False, is_throttled=False, reason="")


def test_harness_coherence_calculation():
    harness = TurboQuantHarness()
    # Vector near 0.5 should have high coherence
    z = torch.full((256,), 0.5)
    coherence = harness.compute_coherence(z)
    assert coherence == 1.0

    # Vector far from 0.5 should have lower coherence
    z_noisy = torch.randn(256) * 0.1 + 0.5
    coherence_noisy = harness.compute_coherence(z_noisy)
    assert coherence_noisy < 1.0


def test_hiho_stability_calculation():
    harness = TurboQuantHarness()
    # 0.5 coherence = 1.0 stability
    assert harness.get_hiho_stability(0.5) == 1.0
    # 0.0 coherence = 0.0 stability (1.0 - abs(0.0-0.5)*2 = 1.0 - 1.0 = 0.0)
    assert harness.get_hiho_stability(0.0) == 0.0
    # 1.0 coherence = 0.0 stability (1.0 - abs(1.0-0.5)*2 = 1.0 - 1.0 = 0.0)
    assert harness.get_hiho_stability(1.0) == 0.0


def test_verify_quantization_success():
    harness = TurboQuantHarness(tolerance_mae=0.1, tolerance_hiho=0.1)
    original = torch.randn(256) * 0.05 + 0.5
    # Dummy quant should be close enough for low-noise tensors
    dequantized = apply_dummy_int8_quantization(original)

    with patch("cohezion.flume.coherence_guard.get_silicon_guard", return_value=_safe_guard):
        result = harness.verify_quantization(original, dequantized)
    assert result["success"] is True
    assert result["mae"] < 0.1


def test_verify_quantization_failure():
    harness = TurboQuantHarness(tolerance_mae=0.0001, tolerance_hiho=0.0001)
    original = torch.randn(256)
    # This should fail due to tight tolerances and high noise
    dequantized = apply_dummy_int8_quantization(original)

    result = harness.verify_quantization(original, dequantized)
    assert result["success"] is False
