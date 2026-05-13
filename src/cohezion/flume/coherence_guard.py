"""
Coherence Guard for Turbo Quant - AutoHarness verifier for quantized tensors.
Ensures that 4-bit/8-bit/Mixed precision quantization maintains HIHO stability.
"""

import logging
from typing import Any

import numpy as np
import torch

from cohezion.core.silicon_guard import get_silicon_guard


logger = logging.getLogger(__name__)


class TurboQuantHarness:
    """
    Deterministic verifier for Turbo Quant operations.
    Gates implementation based on numerical parity and HIHO stability.
    """

    def __init__(self, tolerance_mae: float = 0.05, tolerance_hiho: float = 0.005):
        self.tolerance_mae = tolerance_mae
        self.tolerance_hiho = tolerance_hiho

    def compute_coherence(self, z: torch.Tensor | np.ndarray) -> float:
        """
        Compute HIHO coherence of a latent vector.
        Matches the logic in cohezion.api.services.flume.
        """
        if isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()

        arr = np.array(z).flatten()
        z_dim = len(arr)
        n_chunks = 8
        chunk_size = z_dim // n_chunks
        variance_sum = 0.0

        for c in range(n_chunks):
            start = c * chunk_size
            end = (c + 1) * chunk_size if c < n_chunks - 1 else z_dim
            chunk_mean = float(np.mean(arr[start:end]))
            variance_sum += (chunk_mean - 0.5) ** 2

        variance = variance_sum / n_chunks
        return max(0.0, 1.0 - min(variance * 4.0, 1.0))

    def get_hiho_stability(self, coherence: float) -> float:
        """
        Calculate HIHO stability score (1.0 is perfect 0.5 coherence).
        Based on DESIGN.md: hiho_stability = 1.0 - abs(coherence - 0.5) * 2.0
        """
        return 1.0 - abs(coherence - 0.5) * 2.0

    def verify_quantization(
        self,
        original: torch.Tensor,
        dequantized: torch.Tensor,
        context_name: str = "tensor",
        perfect_mean: bool = False,
    ) -> dict[str, Any]:
        """
        Verify the integrity of a quantization-dequantization cycle with hardware safety.
        """
        # 0. Hardware Guardrail (Apex Safety)
        guard = get_silicon_guard()
        pressure = guard.check_safety()
        if pressure.is_throttled:
            logger.error("🛑 VERIFICATION HALTED: Silicon Overload Detected [%s]", pressure.reason)
            return {
                "success": False,
                "error": f"Silicon Overload: {pressure.reason}",
                "metrics": {},
            }

        # 1. Numerical Parity (Mean Absolute Error)
        mae = float(torch.mean(torch.abs(original - dequantized)))

        # 2. Coherence Check (Internal Consistency)
        coh_orig = self.compute_coherence(original)
        coh_quant = self.compute_coherence(dequantized)
        coh_delta = abs(coh_orig - coh_quant)

        # 3. HIHO Stability (Target Attraction)
        stability_orig = self.get_hiho_stability(coh_orig)
        stability_quant = self.get_hiho_stability(coh_quant)
        stability_delta = abs(stability_orig - stability_quant)

        success = mae <= self.tolerance_mae and (perfect_mean or stability_delta <= self.tolerance_hiho)

        metrics = {
            "context": context_name,
            "mae": mae,
            "coherence_original": coh_orig,
            "coherence_quantized": coh_quant,
            "coherence_delta": coh_delta,
            "stability_original": stability_orig,
            "stability_quantized": stability_quant,
            "stability_delta": stability_delta,
            "success": success,
        }

        if not success:
            logger.warning(
                "⚠️ TurboQuant Integrity Check Failed [%s]: MAE=%.4f, StabilityDelta=%.4f",
                context_name,
                mae,
                stability_delta,
            )
        else:
            logger.info(
                "✅ TurboQuant Integrity Check Passed [%s]: MAE=%.4f, StabilityDelta=%.4f",
                context_name,
                mae,
                stability_delta,
            )

        return metrics


def apply_dummy_int8_quantization(tensor: torch.Tensor) -> torch.Tensor:
    """Simple int8 quantization for harness testing."""
    scale = tensor.abs().max() / 127.0
    quantized = (tensor / scale).round().clamp(-128, 127).to(torch.int8)
    dequantized = quantized.to(torch.float32) * scale
    return dequantized
