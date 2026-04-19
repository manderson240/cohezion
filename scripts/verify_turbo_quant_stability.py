import torch

from cohezion.flume.coherence_guard import TurboQuantHarness
from cohezion.flume.turbo_quant import TurboQuantCPU


def verify_stability():
    tq = TurboQuantCPU(head_dim=256)
    harness = TurboQuantHarness()

    # Generate a vector with high initial coherence (near 0.5)
    # We use a normal distribution centered at 0.5
    original = torch.randn(1, 256) * 0.01 + 0.5

    compressed = tq.compress_kv(original)
    recovered = tq.decompress_kv(compressed)

    metrics = harness.verify_quantization(
        original, recovered,
        context_name="TurboQuant-CPU-Ref",
        perfect_mean=True
    )

    print("\n--- Turbo Quant Stability Verification ---")
    print(f"Success: {metrics['success']}")
    print(f"MAE: {metrics['mae']:.6f}")
    print(f"Coherence Original: {metrics['coherence_original']:.4f}")
    print(f"Coherence Recovered: {metrics['coherence_quantized']:.4f}")
    print(f"Stability Delta: {metrics['stability_delta']:.4f}")

    assert metrics['stability_delta'] <= 0.005, f"Stability delta {metrics['stability_delta']} exceeds tolerance 0.005"

if __name__ == "__main__":
    verify_stability()
