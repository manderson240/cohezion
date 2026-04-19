import torch

from cohezion.flume.coherence_guard import TurboQuantHarness, apply_dummy_int8_quantization


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
