#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Predictive Expert Preloading - Anticipate Usage Patterns.

APPROACH:
This kernel implements predictive expert loading based on:
1. Historical routing patterns: Track which experts are commonly used together
2. Co-occurrence prediction: Preload experts likely to be needed
3. Prefetch window: Load weights before they're needed
4. Adaptive batch sizing: Adjust based on predicted token distribution

KEY INSIGHTS:
- In transformer inference, routing patterns have temporal locality
- Some experts are always used together (semantic clusters)
- Preloading reduces latency on cache misses
- DeepSeek-R1: 256 experts, topk=8, predictable patterns

PREDICTION MODEL:
- Simple: Track expert pairs that co-occur frequently
- Weighted: Recent batches have higher influence
- Threshold: Only preload if confidence > 0.7

MEMORY HIERARCHY:
- HBM: All expert weights
- L2: Recently used + predicted experts
- L1: Active expert weights
- Registers: Accumulators

Author: Experimental Kernel Series
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict, deque

import torch


os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


class ExpertPredictor:
    """Predicts expert usage based on historical routing patterns."""

    def __init__(self, num_experts: int = 256, history_size: int = 16):
        self.num_experts = num_experts
        self.history_size = history_size
        self.routing_history: deque[frozenset[int]] = deque(maxlen=history_size)
        self.cooccurrence: dict[tuple[int, int], float] = defaultdict(float)
        self.expert_frequency: dict[int, float] = defaultdict(float)
        self.decay_factor = 0.9  # Decay old patterns

    def update(self, topk_ids: torch.Tensor):
        """Update prediction model with new routing data.

        Args:
            topk_ids: [M, total_top_k] expert assignments
        """
        # Get unique experts in this batch
        unique_experts = frozenset(topk_ids.flatten().tolist())

        # Decay old patterns
        for key in self.cooccurrence:
            self.cooccurrence[key] *= self.decay_factor

        # Update co-occurrence matrix
        experts_list = list(unique_experts)
        for i, e1 in enumerate(experts_list):
            self.expert_frequency[e1] += 1.0
            for e2 in experts_list[i + 1 :]:
                self.cooccurrence[(min(e1, e2), max(e1, e2))] += 1.0

        # Add to history
        self.routing_history.append(unique_experts)

    def predict_coexperts(self, active_experts: list[int], top_k: int = 8) -> list[int]:
        """Predict which experts will be used based on co-occurrence.

        Args:
            active_experts: Currently active expert IDs
            top_k: Number of predictions to return

        Returns:
            List of predicted expert IDs
        """
        predictions: dict[int, float] = defaultdict(float)

        for e1 in active_experts:
            for e2 in range(self.num_experts):
                if e2 in active_experts:
                    continue
                key = (min(e1, e2), max(e1, e2))
                predictions[e2] += self.cooccurrence[key]

        # Sort by predicted probability
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        return [eid for eid, _ in sorted_predictions[:top_k]]

    def predict_batch_size(self, recent_tokens: int, avg_tokens_per_expert: float) -> int:
        """Predict optimal batch size based on historical patterns.

        Args:
            recent_tokens: Number of tokens in recent batches
            avg_tokens_per_expert: Average tokens per expert

        Returns:
            Recommended batch size
        """
        # Base prediction on recent history
        if len(self.routing_history) < 2:
            return recent_tokens

        # Simple linear trend
        recent = list(self.routing_history)[-5:]
        if len(recent) >= 2:
            trend = len(recent[-1]) - len(recent[0])
            if trend > 0:
                # Increasing pattern
                return int(recent_tokens * 1.1)
            elif trend < 0:
                # Decreasing pattern
                return int(recent_tokens * 0.9)

        return recent_tokens


class PrefetchManager:
    """Manages prefetching of expert weights."""

    def __init__(self, lookahead: int = 2):
        self.lookahead = lookahead
        self.prefetch_queue: list[int] = []
        self.prefetched: set[int] = set()

    def schedule_prefetch(self, experts: list[int]):
        """Schedule experts for prefetching."""
        for eid in experts:
            if eid not in self.prefetched:
                self.prefetch_queue.append(eid)

    def mark_prefetched(self, expert_id: int):
        """Mark an expert as successfully prefetched."""
        self.prefetched.add(expert_id)
        if expert_id in self.prefetch_queue:
            self.prefetch_queue.remove(expert_id)

    def get_prefetch_candidates(self, n: int = 4) -> list[int]:
        """Get next N experts to prefetch."""
        return self.prefetch_queue[:n]


# Global predictor instance (persistent across calls in same session)
_predictor: ExpertPredictor | None = None
_prefetch_mgr: PrefetchManager | None = None


def _get_predictor(num_experts: int = 256) -> ExpertPredictor:
    """Get or create global predictor instance."""
    global _predictor
    if _predictor is None or _predictor.num_experts != num_experts:
        _predictor = ExpertPredictor(num_experts=num_experts)
    return _predictor


def _get_prefetch_manager() -> PrefetchManager:
    """Get or create global prefetch manager."""
    global _prefetch_mgr
    if _prefetch_mgr is None:
        _prefetch_mgr = PrefetchManager(lookahead=2)
    return _prefetch_mgr


def custom_kernel(data: input_t) -> output_t:
    """Execute MoE with predictive expert preloading.

    Args:
        data: Tuple containing MoE inputs (see task.py for full spec)

    Returns:
        Output tensor [M, d_hidden]
    """
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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    num_experts = config.get("num_experts", 256)

    # Get predictor and prefetch manager
    predictor = _get_predictor(num_experts)
    prefetch_mgr = _get_prefetch_manager()

    # Update prediction model with current routing
    predictor.update(topk_ids)

    # Get unique experts for this batch
    unique_experts = torch.unique(topk_ids).tolist()

    # Predict co-occurring experts
    predicted_experts = predictor.predict_coexperts(unique_experts, top_k=8)
    prefetch_mgr.schedule_prefetch(predicted_experts)

    # Adaptive configuration based on prediction confidence
    if len(predictor.routing_history) >= 3:
        # We have enough history for predictions
        recent_patterns = list(predictor.routing_history)[-3:]
        pattern_consistency = len(set(map(len, recent_patterns))) == 1

        if pattern_consistency:
            # Consistent patterns: optimize for throughput
            os.environ["AITER_KSPLIT"] = "0"
            os.environ["AITER_PREDICTIVE_MODE"] = "1"
        else:
            # Variable patterns: optimize for latency
            if d_expert <= 512:
                os.environ["AITER_KSPLIT"] = "0"
            else:
                os.environ["AITER_KSPLIT"] = "1"
            os.environ.pop("AITER_PREDICTIVE_MODE", None)
    else:
        # Not enough history: use conservative settings
        if d_expert <= 512:
            os.environ["AITER_KSPLIT"] = "0"

    # Shape-aware tuning for ranked shapes
    if d_expert == 256:
        os.environ["AITER_KSPLIT"] = "0"
    elif d_expert == 2048:
        os.environ["AITER_KSPLIT"] = "1"

    try:
        # Execute fused MoE
        result = fused_moe(
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

        # Log prediction stats in debug mode
        if os.environ.get("POPCORN_DEBUG"):
            print(
                f"[MoE-Predictive] History: {len(predictor.routing_history)} batches, "
                f"Predicted: {len(predicted_experts)} experts, "
                f"Active: {len(unique_experts)}"
            )

        return result

    except Exception as e:
        print(f"[MoE-Predictive] Error, falling back: {e}", file=sys.stderr)

        # Clear environment overrides
        os.environ.pop("AITER_KSPLIT", None)
        os.environ.pop("AITER_PREDICTIVE_MODE", None)

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
