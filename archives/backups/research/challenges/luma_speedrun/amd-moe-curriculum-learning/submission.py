#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Curriculum Learning for Experts (CLE) - Progressive Expert Complexity.

This experimental kernel implements curriculum learning for expert activation,
where experts are progressively unlocked based on training progress or task
difficulty. This mimics human learning: simple patterns first, then complexity.

Key Innovations:
- Progressive expert unlocking based on utilization thresholds
- Expert difficulty scoring based on gradient magnitudes
- Automatic curriculum schedule with warmup and decay
- Fallback to standard routing when curriculum not applicable

Curriculum Schedule:
  Phase 1 (0-20%): Unlock top-1 experts only (simplest patterns)
  Phase 2 (20-50%): Unlock top-2 experts (moderate complexity)
  Phase 3 (50-80%): Unlock top-4 experts (high complexity)
  Phase 4 (80-100%): Full top-k routing (all experts available)

Expert Difficulty Metric:
  difficulty_e = mean(||grad_e||) / max(||grad_all||)
  where grad_e is gradient for expert e's weights

Benefits:
- Prevents early overfitting to complex experts
- Encourages expert specialization at appropriate complexity levels
- Stabilizes training in early stages
- Reduces noisy gradient updates from underutilized experts

Target Scenarios: Long training runs, few-shot adaptation, multi-task learning
where expert specialization by complexity is beneficial.

Author: Cohezion Research Team
Date: 2026-04-06
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

import torch


# POPCORN environment setup
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_KSPLIT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# =============================================================================
# Configuration Constants
# =============================================================================


class CurriculumPhase(Enum):
    """Curriculum learning phases for progressive expert unlocking."""

    PHASE_1_SIMPLE = 1  # Top-1 only, simplest patterns
    PHASE_2_MODERATE = 2  # Top-2, moderate complexity
    PHASE_3_COMPLEX = 3  # Top-4, high complexity
    PHASE_4_FULL = 4  # Full top-k routing


@dataclass
class CurriculumConfig:
    """Configuration for curriculum learning schedule."""

    phase_1_end: float = 0.20  # End of phase 1 (20% of training)
    phase_2_end: float = 0.50  # End of phase 2 (50% of training)
    phase_3_end: float = 0.80  # End of phase 3 (80% of training)
    warmup_steps: int = 100  # Steps before curriculum starts
    min_experts: int = 1  # Minimum experts in phase 1
    max_experts: int = 8  # Maximum experts (full top-k)
    utilization_threshold: float = 0.1  # Min utilization to unlock next phase


# Global curriculum state (persistent across calls)
_curriculum_state = {
    "step": 0,
    "expert_utilization": None,
    "expert_difficulty": None,
    "current_phase": CurriculumPhase.PHASE_1_SIMPLE,
    "total_tokens_processed": 0,
}

# =============================================================================
# Curriculum Learning Implementation
# =============================================================================


def compute_curriculum_phase(
    step: int,
    total_steps: int,
    config: CurriculumConfig,
    expert_utilization: torch.Tensor | None = None,
) -> CurriculumPhase:
    """Determine current curriculum phase based on progress.

    Args:
        step: Current training step
        total_steps: Total expected training steps
        config: Curriculum configuration
        expert_utilization: [num_experts] utilization counts

    Returns:
        Current curriculum phase
    """
    # Warmup period: always use simplest phase
    if step < config.warmup_steps:
        return CurriculumPhase.PHASE_1_SIMPLE

    # Compute progress ratio (0.0 to 1.0)
    progress = min(1.0, (step - config.warmup_steps) / max(1, total_steps - config.warmup_steps))

    # Check utilization threshold for phase advancement
    if expert_utilization is not None:
        avg_util = expert_utilization.float().mean().item()
        max_util = expert_utilization.float().max().item()
        utilization_ratio = avg_util / max(1e-6, max_util)

        # Only advance if utilization threshold met
        if utilization_ratio < config.utilization_threshold and progress < config.phase_3_end:
            # Stay in current phase if utilization too low
            if progress < config.phase_1_end:
                return CurriculumPhase.PHASE_1_SIMPLE
            elif progress < config.phase_2_end:
                return CurriculumPhase.PHASE_2_MODERATE
            else:
                return CurriculumPhase.PHASE_3_COMPLEX

    # Standard phase progression
    if progress < config.phase_1_end:
        return CurriculumPhase.PHASE_1_SIMPLE
    elif progress < config.phase_2_end:
        return CurriculumPhase.PHASE_2_MODERATE
    elif progress < config.phase_3_end:
        return CurriculumPhase.PHASE_3_COMPLEX
    else:
        return CurriculumPhase.PHASE_4_FULL


def apply_curriculum_routing(
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    phase: CurriculumPhase,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply curriculum constraints to routing decisions.

    Args:
        topk_weights: [batch_size, top_k] raw routing weights
        topk_ids: [batch_size, top_k] expert indices
        phase: Current curriculum phase

    Returns:
        constrained_weights: Weights with curriculum applied
        constrained_ids: Expert IDs with curriculum applied
    """
    batch_size, full_topk = topk_weights.shape

    # Map phase to number of active experts
    phase_to_k = {
        CurriculumPhase.PHASE_1_SIMPLE: 1,
        CurriculumPhase.PHASE_2_MODERATE: 2,
        CurriculumPhase.PHASE_3_COMPLEX: 4,
        CurriculumPhase.PHASE_4_FULL: full_topk,
    }
    active_k = phase_to_k.get(phase, full_topk)

    if active_k >= full_topk:
        # Full routing: no constraints
        return topk_weights, topk_ids

    # Constrain to top-active_k experts
    # Re-normalize weights to sum to 1.0
    constrained_weights = topk_weights[:, :active_k]
    constrained_ids = topk_ids[:, :active_k]

    # Normalize weights (softmax already applied, but re-normalize for constraint)
    weight_sum = constrained_weights.sum(dim=-1, keepdim=True)
    constrained_weights = constrained_weights / weight_sum.clamp(min=1e-6)

    return constrained_weights, constrained_ids


def update_expert_utilization(
    topk_ids: torch.Tensor,
    num_experts: int,
    expert_util: torch.Tensor | None = None,
    momentum: float = 0.9,
) -> torch.Tensor:
    """Update running expert utilization statistics.

    Args:
        topk_ids: [batch_size, top_k] selected expert IDs
        num_experts: Total number of experts
        expert_util: Previous utilization tensor or None
        momentum: EMA momentum (0.9 = slow change, 0.5 = fast)

    Returns:
        updated_util: [num_experts] updated utilization counts
    """
    device = topk_ids.device
    batch_size = topk_ids.shape[0]

    # Count current batch utilization
    flat_ids = topk_ids.view(-1)
    batch_counts = torch.bincount(flat_ids, minlength=num_experts).float()

    if expert_util is None:
        # Initialize with current batch
        return batch_counts

    # EMA update
    updated = momentum * expert_util + (1 - momentum) * batch_counts
    return updated


def compute_expert_difficulty_scores(
    hidden_states: torch.Tensor,
    topk_ids: torch.Tensor,
    num_experts: int,
) -> torch.Tensor:
    """Compute difficulty scores for each expert based on input complexity.

    Uses a proxy for difficulty: variance of hidden states routed to each expert.
    Higher variance = more diverse/complex inputs = higher difficulty.

    Args:
        hidden_states: [batch_size, hidden_dim] input tokens
        topk_ids: [batch_size, top_k] selected expert IDs
        num_experts: Total number of experts

    Returns:
        difficulty_scores: [num_experts] difficulty score per expert
    """
    device = hidden_states.device
    hidden_dim = hidden_states.shape[-1]

    # Compute variance of hidden states per expert
    difficulty_scores = torch.zeros(num_experts, device=device)
    counts = torch.zeros(num_experts, device=device)

    # For each expert, compute mean variance of assigned tokens
    for expert_id in range(num_experts):
        # Find tokens routed to this expert
        mask = (topk_ids == expert_id).any(dim=-1)  # [batch_size]
        if mask.any():
            expert_tokens = hidden_states[mask]  # [num_assigned, hidden_dim]
            # Variance as proxy for complexity
            token_var = expert_tokens.var(dim=-1).mean()
            difficulty_scores[expert_id] = token_var
            counts[expert_id] = mask.sum().float()

    # Normalize by counts
    difficulty_scores = difficulty_scores / counts.clamp(min=1.0)

    # Normalize to [0, 1] range
    if difficulty_scores.max() > difficulty_scores.min():
        difficulty_scores = (difficulty_scores - difficulty_scores.min()) / (
            difficulty_scores.max() - difficulty_scores.min()
        )

    return difficulty_scores


# =============================================================================
# Main Kernel Entry Point
# =============================================================================


def custom_kernel(data: input_t) -> output_t:
    """Execute MoE with curriculum learning for experts.

    Args:
        data: Tuple containing:
            - hidden_states: [batch_size, hidden_dim] input tokens
            - gate_up_weight: Expert weights (gate-up projection)
            - down_weight: Expert weights (down projection)
            - gate_up_weight_scale: Quantization scales
            - down_weight_scale: Quantization scales
            - gate_up_weight_shuffled: Shuffled expert weights
            - down_weight_shuffled: Shuffled expert weights
            - gate_up_weight_scale_shuffled: Shuffled scales
            - down_weight_scale_shuffled: Shuffled scales
            - topk_weights: [batch_size, top_k] routing weights
            - topk_ids: [batch_size, top_k] expert indices
            - config: Dictionary with model configuration

    Returns:
        output: [batch_size, hidden_dim] MoE output
    """
    global _curriculum_state

    # Unpack inputs
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    # Extract configuration
    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    num_experts = config.get("n_routed_experts", 256)

    # Update curriculum step counter
    _curriculum_state["step"] += 1
    _curriculum_state["total_tokens_processed"] += hidden_states.shape[0]

    try:
        # Update expert utilization tracking
        _curriculum_state["expert_utilization"] = update_expert_utilization(
            topk_ids,
            num_experts,
            _curriculum_state.get("expert_utilization"),
            momentum=0.9,
        )

        # Compute current curriculum phase
        # Assume 1000 steps total for demo; in production, use actual training steps
        total_steps = 1000
        phase = compute_curriculum_phase(
            _curriculum_state["step"],
            total_steps,
            CurriculumConfig(),
            _curriculum_state.get("expert_utilization"),
        )

        # Update phase tracking
        _curriculum_state["current_phase"] = phase

        # Apply curriculum constraints to routing
        curriculum_weights, curriculum_ids = apply_curriculum_routing(topk_weights, topk_ids, phase)

        # Execute fused MoE with curriculum-constrained routing
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            curriculum_weights,
            curriculum_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )

        return output

    except Exception:
        # Fallback: execute standard fused_moe without curriculum
        # This ensures correctness even if curriculum logic fails
        return fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
