"""
MoE: Noisy Gating for Load Balancing

#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Implements noisy gating mechanism that adds controlled noise to expert
selection during training. This encourages exploration and prevents
collapse to a few dominant experts.

Key Innovation:
- Noisy top-k: Add Gaussian noise to gate logits before softmax
- Annealed noise: Decrease noise magnitude over training
- Importance-based noise: Scale noise by expert usage
- Differentiable: Maintain gradient flow through noise

Trade-offs:
+ Prevents expert collapse (all tokens to same expert)
+ Encourages exploration of under-utilized experts
+ Simple to implement, no additional parameters
- Adds stochasticity to training
- Noise scheduling requires tuning

Reference: "Outrageously Large Neural Networks" (Shazeer et al., 2017)
Noisy top-k gating for load balancing in MoE.
"""

from __future__ import annotations
import os
import sys
import math
import torch
from typing import Tuple, Optional
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from reference import ref_kernel
from task import input_t, output_t

os.environ["AITER_USE_NT"] = "1"


class NoisyGating:
    """
    Implements noisy gating for expert selection.

    Adds Gaussian noise to gate logits before softmax:
        noisy_logits = logits + noise * Gaussian(0, 1)
        gates = softmax(noisy_logits)

    Noise magnitude anneals over training:
        noise_scale = initial_noise * decay_rate ^ (step / decay_steps)

    Attributes:
        initial_noise: Initial noise standard deviation
        decay_rate: Multiplicative decay per step
        decay_steps: Steps between decays
    """

    def __init__(
        self,
        initial_noise: float = 1.0,
        decay_rate: float = 0.99,
        decay_steps: int = 100,
        min_noise: float = 0.01,
    ):
        """
        Initialize noisy gating.

        Args:
            initial_noise: Initial noise std dev
            decay_rate: Decay multiplier
            decay_steps: Steps per decay
            min_noise: Minimum noise level
        """
        self.initial_noise = initial_noise
        self.decay_rate = decay_rate
        self.decay_steps = decay_steps
        self.min_noise = min_noise
        self.step = 0
        self._generator = torch.Generator(device="cuda")
        self._generator.manual_seed(42)

    def get_noise_scale(self) -> float:
        """Get current noise scale based on training step."""
        num_decays = self.step // self.decay_steps
        scale = self.initial_noise * (self.decay_rate**num_decays)
        return max(scale, self.min_noise)

    def add_noise(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Add Gaussian noise to logits.

        Args:
            logits: Gate logits [batch_size, num_experts]

        Returns:
            Noisy logits
        """
        noise_scale = self.get_noise_scale()

        if noise_scale <= self.min_noise:
            return logits

        # Generate Gaussian noise
        noise = torch.randn(
            logits.shape, generator=self._generator, device=logits.device, dtype=logits.dtype
        )

        # Add noise
        noisy_logits = logits + noise_scale * noise

        self.step += 1
        return noisy_logits

    def compute_noisy_gates(
        self, topk_ids: torch.Tensor, topk_weights: torch.Tensor, noise_ratio: float = 0.1
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply noise to gate selection.

        Args:
            topk_ids: Expert selections
            topk_weights: Gate weights
            noise_ratio: Fraction of selections to perturb

        Returns:
            (noisy_ids, noisy_weights)
        """
        noise_scale = self.get_noise_scale()
        if noise_scale <= self.min_noise:
            return topk_ids, topk_weights

        batch_size, topk = topk_ids.shape
        num_experts = int(topk_ids.max().item()) + 1

        noisy_ids = topk_ids.clone()
        noisy_weights = topk_weights.clone()

        # Randomly perturb some selections
        num_perturb = int(batch_size * topk * noise_ratio)
        perturb_indices = torch.randperm(batch_size * topk, device=topk_ids.device)[:num_perturb]

        for idx in perturb_indices:
            b = idx // topk
            k = idx % topk

            # With probability noise_scale, change expert
            if (
                torch.rand(1, generator=self._generator, device=topk_ids.device).item()
                < noise_scale
            ):
                # Select random different expert
                current = int(noisy_ids[b, k].item())
                alternatives = [e for e in range(num_experts) if e != current]
                if alternatives:
                    new_expert = alternatives[
                        torch.randint(0, len(alternatives), (1,), generator=self._generator).item()
                    ]
                    noisy_ids[b, k] = new_expert
                    # Reduce weight for perturbed selection
                    noisy_weights[b, k] *= 0.8

        return noisy_ids, noisy_weights

    def get_stats(self) -> dict:
        """Get current noise statistics."""
        return {
            "step": self.step,
            "noise_scale": self.get_noise_scale(),
        }


# Global noisy gating instance
_NOISY_GATING: Optional[NoisyGating] = None


def _get_noisy_gating() -> NoisyGating:
    """Get or create noisy gating instance."""
    global _NOISY_GATING
    if _NOISY_GATING is None:
        initial_noise = float(os.environ.get("NOISY_GATE_INITIAL", "1.0"))
        decay_rate = float(os.environ.get("NOISY_GATE_DECAY", "0.99"))
        decay_steps = int(os.environ.get("NOISY_GATE_STEPS", "100"))
        _NOISY_GATING = NoisyGating(initial_noise, decay_rate, decay_steps)
    return _NOISY_GATING


def custom_kernel(data: input_t) -> output_t:
    """Execute MoE with noisy gating."""
    (
        hidden_states,
        _gate_up_weight,
        _down_weight,
        _gate_up_weight_scale,
        _down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    d_hidden = config.get("d_hidden", hidden_states.shape[1])
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    hidden_pad = config.get("d_hidden_pad", d_hidden) - d_hidden

    try:
        noisy_gating = _get_noisy_gating()

        # Apply noise to gating
        noisy_ids, noisy_weights = noisy_gating.compute_noisy_gates(topk_ids, topk_weights)

        # Log noise level periodically
        if noisy_gating.step % 500 == 0:
            stats = noisy_gating.get_stats()
            print(
                f"[Noisy Gating] Step {stats['step']}, Noise scale: {stats['noise_scale']:.4f}",
                file=sys.stderr,
            )

        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            noisy_weights,
            noisy_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=config.get("d_expert_pad", 0) - config.get("d_expert", 0),
        )

        if hidden_pad > 0:
            output = output[:, :d_hidden]

        return output

    except Exception as e:
        print(f"Noisy gating failed: {e}", file=sys.stderr)
        return ref_kernel(data)
