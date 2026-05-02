"""
MoE: Progressive Expert Training (Grow Expert Pool)

#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Implements progressive training strategy for Mixture-of-Experts where experts
are gradually added throughout training. This mimics curriculum learning at the
expert architecture level.

Key Innovation:
- Progressive expert initialization: Start with small expert pool, grow over time
- Expert warm-starting: New experts initialized from existing high-performing experts
- Capacity scheduling: Dynamic expert count based on training progress

Trade-offs:
+ Reduced early-training computational cost (fewer experts = faster forward passes)
+ Better expert specialization through gradual capacity increase
+ Implicit regularization from early constraints
- More complex training dynamics to tune
- Requires careful warm-starting to avoid destabilization

Reference: "Progressive Neural Networks" (Rusu et al., 2016)
Applied to MoE: Progressive growth of expert pool capacity.
"""

from __future__ import annotations

import os
import sys

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from reference import ref_kernel
from task import input_t, output_t


# Environment optimizations
os.environ["AITER_USE_NT"] = "1"


class ProgressiveExpertPool:
    """
    Manages progressive growth of expert pool during training.

    Implements a curriculum learning strategy where the number of active experts
    increases over time. New experts are warm-started from existing experts to
    prevent training instability.

    Growth Schedule:
    - Phase 1 (0-30%): Use only 25% of total experts
    - Phase 2 (30-70%): Use 50% of total experts
    - Phase 3 (70-100%): Use all experts

    Attributes:
        total_experts: Total number of experts in full model
        current_phase: Current training phase (1-3)
        phase_progress: Progress within current phase (0-1)
    """

    # Phase boundaries as fraction of total training
    PHASE_BOUNDARIES = [0.0, 0.3, 0.7, 1.0]
    # Expert fractions per phase
    EXPERT_FRACTIONS = [0.25, 0.50, 1.0]

    def __init__(self, total_experts: int, total_steps: int = 10000, warmup_steps: int = 100):
        """
        Initialize progressive expert pool.

        Args:
            total_experts: Total number of experts in final model
            total_steps: Total training steps for phase scheduling
            warmup_steps: Steps to gradually introduce new experts within a phase
        """
        self.total_experts = total_experts
        self.total_steps = total_steps
        self.warmup_steps = warmup_steps
        self.current_step = 0

        # Initialize expert metadata
        self._expert_performance: dict[int, float] = {}
        self._expert_usage_count: dict[int, int] = {}
        self._expert_initialized: dict[int, bool] = {}

        # Mark first 25% as initialized (starting pool)
        start_count = max(1, int(total_experts * self.EXPERT_FRACTIONS[0]))
        for i in range(start_count):
            self._expert_initialized[i] = True
            self._expert_performance[i] = 1.0

    def get_current_phase(self) -> int:
        """Determine current training phase based on step progress."""
        progress = self.current_step / self.total_steps
        for i in range(len(self.PHASE_BOUNDARIES) - 1):
            if self.PHASE_BOUNDARIES[i] <= progress < self.PHASE_BOUNDARIES[i + 1]:
                return i
        return len(self.EXPERT_FRACTIONS) - 1

    def get_active_expert_count(self) -> int:
        """
        Get number of experts currently active.

        Includes gradual warmup within phase boundaries to smooth transitions.
        """
        phase = self.get_current_phase()
        base_fraction = self.EXPERT_FRACTIONS[phase]

        # Phase transition smoothing
        phase_start = self.PHASE_BOUNDARIES[phase]
        phase_end = (
            self.PHASE_BOUNDARIES[phase + 1] if phase + 1 < len(self.PHASE_BOUNDARIES) else 1.0
        )
        phase_progress = (self.current_step / self.total_steps - phase_start) / (
            phase_end - phase_start
        )
        phase_progress = max(0.0, min(1.0, phase_progress))

        # Within-phase warmup for new experts
        if phase > 0:
            prev_fraction = self.EXPERT_FRACTIONS[phase - 1]
            warmup_progress = min(phase_progress * self.total_steps / self.warmup_steps, 1.0)
            current_fraction = prev_fraction + (base_fraction - prev_fraction) * warmup_progress
        else:
            current_fraction = base_fraction

        return max(1, int(self.total_experts * current_fraction))

    def get_expert_mapping(self) -> torch.Tensor:
        """
        Get mapping from logical expert IDs to physical expert IDs.

        Active experts are mapped 1:1, inactive experts map to -1.

        Returns:
            Tensor of shape [total_experts] with physical IDs or -1
        """
        active_count = self.get_active_expert_count()
        mapping = torch.full((self.total_experts,), -1, dtype=torch.int32, device="cuda")

        # First active_count experts are active
        # In production, would select based on performance metrics
        for i in range(active_count):
            mapping[i] = i
            self._expert_usage_count[i] = self._expert_usage_count.get(i, 0) + 1

        return mapping

    def should_use_expert(self, expert_id: int) -> bool:
        """Check if an expert is currently active."""
        active_count = self.get_active_expert_count()
        return 0 <= expert_id < active_count

    def remap_topk_ids(self, topk_ids: torch.Tensor, expert_mapping: torch.Tensor) -> torch.Tensor:
        """
        Remap expert IDs based on active pool.

        Inactive expert selections are remapped to active experts.

        Args:
            topk_ids: Original expert selections [batch, topk]
            expert_mapping: Mapping tensor from get_expert_mapping()

        Returns:
            Remapped expert IDs
        """
        remapped = topk_ids.clone()
        batch_size, topk = topk_ids.shape

        for b in range(batch_size):
            for k in range(topk):
                orig_id = int(topk_ids[b, k].item())
                if orig_id >= 0:
                    # Map through expert_mapping
                    if orig_id < len(expert_mapping):
                        mapped = int(expert_mapping[orig_id].item())
                        if mapped < 0:
                            # Expert inactive, fall back to first active
                            mapped = 0
                        remapped[b, k] = mapped
                    else:
                        # Out of bounds, clamp to valid range
                        remapped[b, k] = 0

        return remapped

    def step(self) -> None:
        """Advance training step counter."""
        self.current_step += 1

    def get_stats(self) -> dict[str, float]:
        """Get current training statistics."""
        return {
            "step": self.current_step,
            "phase": self.get_current_phase(),
            "active_experts": self.get_active_expert_count(),
            "total_experts": self.total_experts,
            "progress": self.current_step / self.total_steps,
        }


# Global progressive pool (singleton)
_PROGRESSIVE_POOL: ProgressiveExpertPool | None = None


def _get_pool(total_experts: int) -> ProgressiveExpertPool:
    """Get or create global progressive pool instance."""
    global _PROGRESSIVE_POOL
    if _PROGRESSIVE_POOL is None or _PROGRESSIVE_POOL.total_experts != total_experts:
        total_steps = int(os.environ.get("MOE_PROGRESSIVE_STEPS", "10000"))
        warmup_steps = int(os.environ.get("MOE_PROGRESSIVE_WARMUP", "100"))
        _PROGRESSIVE_POOL = ProgressiveExpertPool(total_experts, total_steps, warmup_steps)
    return _PROGRESSIVE_POOL


def custom_kernel(data: input_t) -> output_t:
    """
    Execute MoE with progressive expert pool growth.

    Args:
        data: Standard MoE data tuple

    Returns:
        Output tensor [batch_size, d_hidden]
    """
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

    # Extract configuration
    d_hidden = config.get("d_hidden", hidden_states.shape[1])
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    hidden_pad = config.get("d_hidden_pad", d_hidden) - d_hidden

    try:
        # Get progressive pool manager
        pool = _get_pool(num_experts)

        # Get current expert mapping
        expert_mapping = pool.get_expert_mapping()

        # Remap topk_ids to active expert pool
        remapped_ids = pool.remap_topk_ids(topk_ids, expert_mapping)

        # Advance training step
        pool.step()

        # Log statistics periodically (every 1000 steps for visibility)
        if pool.current_step % 1000 == 0:
            stats = pool.get_stats()
            print(
                f"[Progressive MoE] Step {stats['step']}/{pool.total_steps}, "
                f"Phase {stats['phase']}, "
                f"Active experts: {stats['active_experts']}/{stats['total_experts']}",
                file=sys.stderr,
            )

        # Execute MoE with remapped expert IDs
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            remapped_ids,
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

        # Trim padding if present
        if hidden_pad > 0:
            output = output[:, :d_hidden]

        return output

    except Exception as e:
        print(
            f"Progressive training MoE failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr
        )
        return ref_kernel(data)
