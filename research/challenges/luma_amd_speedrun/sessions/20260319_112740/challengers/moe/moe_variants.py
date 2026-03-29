"""
MoE Variants — MXFP4 MoE with adaptive KSPLIT strategies.

Current best: ~155µs
Target: <150µs
Gap: 1.03× — almost there!

Key optimizations:
1. Adaptive KSPLIT based on K dimension (John Hahn technique)
2. Expert-centric KSPLIT: KSPLIT = f(expert count)
3. Token-centric KSPLIT: KSPLIT = f(token count)
4. Verify doweight_stage1=False is critical

Reference data (AITER baseline):
  bs=16, E=257, d_expert=256, top_k=9 → 152.7µs
  bs=128, E=257, d_expert=256, top_k=9 → 239.0µs
  bs=512, E=257, d_expert=256, top_k=9 → 336.5µs

  bs=16, E=33, d_expert=512, top_k=9 → 106.2µs (faster!)
  bs=128, E=33, d_expert=512, top_k=9 → 141.1µs
  bs=512, E=33, d_expert=512, top_k=9 → 225.0µs
"""

import os

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# CRITICAL: doweight_stage1 must be False (known broken in AITER)
DOWEIGHT_STAGE1 = False

# Enable OPUS sorting (improves routing efficiency)
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"


def _adaptive_ksplit_k(M: int, N: int, K: int, E: int) -> int:
    """
    Adaptive KSPLIT based on K dimension (John Hahn technique).

    Key insight: K>2048 shapes benefit from KSPLIT=8 (2.5× improvement).
    """
    if K > 2048:
        return 8
    elif K > 1024:
        return 4
    else:
        return 1


def _adaptive_ksplit_expert(M: int, N: int, K: int, E: int) -> int:
    """
    Adaptive KSPLIT based on expert count.

    Key insight: More experts = more parallelism = can use higher split.
    """
    if E >= 256:
        return 8
    elif E >= 64:
        return 4
    elif E >= 16:
        return 2
    else:
        return 1


def _adaptive_ksplit_token(M: int, N: int, K: int, E: int) -> int:
    """
    Adaptive KSPLIT based on token count.

    Key insight: More tokens = more per-token parallelism = higher split.
    """
    if M >= 256:
        return 8
    elif M >= 64:
        return 4
    elif M >= 16:
        return 2
    else:
        return 1


# ─── VARIANT 1: K-based adaptive KSPLIT (current best) ──────────────────────
def custom_kernel_v1(data: input_t) -> output_t:
    """
    Adaptive KSPLIT based on K dimension.

    John Hahn's technique: split_k=8 for K>2048.

    Expected: ~150-155µs
    """
    hidden, gate_up, down, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token, sorted_expert, num_valid = data[11:14]

    M, K = hidden.shape
    E = gate_up.shape[0] // 2
    N = gate_up.shape[1]

    hp = gate_up.shape[2] - K
    ip = down.shape[2] - N

    split_k = _adaptive_ksplit_k(M, N, K, E)
    os.environ["AITER_KSPLIT"] = str(split_k)

    return fused_moe(
        hidden,
        gate_up,
        down,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token,
        sorted_expert,
        num_valid,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=split_k,
        quant_type=QuantType.per_1x32,
        activation=ActivationType.Silu,
        doweight_stage1=DOWEIGHT_STAGE1,
        hidden_pad=hp,
        intermediate_pad=ip,
    )


# ─── VARIANT 2: Expert-centric KSPLIT ────────────────────────────────────────
def custom_kernel_v2(data: input_t) -> output_t:
    """
    Adaptive KSPLIT based on expert count.

    Key insight: E=33 shapes are faster than E=257 due to better coalescing.
    Higher expert count might benefit from more splits.

    Expected: ~148-152µs
    """
    hidden, gate_up, down, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token, sorted_expert, num_valid = data[11:14]

    M, K = hidden.shape
    E = gate_up.shape[0] // 2
    N = gate_up.shape[1]

    hp = gate_up.shape[2] - K
    ip = down.shape[2] - N

    split_k = _adaptive_ksplit_expert(M, N, K, E)
    os.environ["AITER_KSPLIT"] = str(split_k)

    return fused_moe(
        hidden,
        gate_up,
        down,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token,
        sorted_expert,
        num_valid,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=split_k,
        quant_type=QuantType.per_1x32,
        activation=ActivationType.Silu,
        doweight_stage1=DOWEIGHT_STAGE1,
        hidden_pad=hp,
        intermediate_pad=ip,
    )


# ─── VARIANT 3: Token-centric KSPLIT ─────────────────────────────────────────
def custom_kernel_v3(data: input_t) -> output_t:
    """
    Adaptive KSPLIT based on token count.

    Key insight: Inference typically has small M (batch), training has large M.
    Different regimes need different splits.

    Expected: ~150-155µs
    """
    hidden, gate_up, down, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token, sorted_expert, num_valid = data[11:14]

    M, K = hidden.shape
    E = gate_up.shape[0] // 2
    N = gate_up.shape[1]

    hp = gate_up.shape[2] - K
    ip = down.shape[2] - N

    split_k = _adaptive_ksplit_token(M, N, K, E)
    os.environ["AITER_KSPLIT"] = str(split_k)

    return fused_moe(
        hidden,
        gate_up,
        down,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token,
        sorted_expert,
        num_valid,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=split_k,
        quant_type=QuantType.per_1x32,
        activation=ActivationType.Silu,
        doweight_stage1=DOWEIGHT_STAGE1,
        hidden_pad=hp,
        intermediate_pad=ip,
    )


# ─── VARIANT 4: Fixed high KSPLIT ────────────────────────────────────────────
def custom_kernel_v4(data: input_t) -> output_t:
    """
    Fixed KSPLIT=8 for all shapes.

    Test: Is K-based adaptation actually helping, or is high KSPLIT always better?

    Expected: ~152-158µs (may be worse than adaptive)
    """
    hidden, gate_up, down, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token, sorted_expert, num_valid = data[11:14]

    M, K = hidden.shape
    E = gate_up.shape[0] // 2
    N = gate_up.shape[1]

    hp = gate_up.shape[2] - K
    ip = down.shape[2] - N

    # Fixed high split
    os.environ["AITER_KSPLIT"] = "8"

    return fused_moe(
        hidden,
        gate_up,
        down,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token,
        sorted_expert,
        num_valid,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=8,
        quant_type=QuantType.per_1x32,
        activation=ActivationType.Silu,
        doweight_stage1=DOWEIGHT_STAGE1,
        hidden_pad=hp,
        intermediate_pad=ip,
    )


# ─── VARIANT 5: OPUS + adaptive (combined best) ──────────────────────────────
def custom_kernel_v5(data: input_t) -> output_t:
    """
    Combined optimizations:
    - OPUS sorting enabled
    - Adaptive KSPLIT based on K dimension
    - Verified doweight_stage1=False

    Expected: ~145-150µs (may match or beat leader)
    """
    hidden, gate_up, down, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token, sorted_expert, num_valid = data[11:14]

    M, K = hidden.shape
    E = gate_up.shape[0] // 2
    N = gate_up.shape[1]

    hp = gate_up.shape[2] - K
    ip = down.shape[2] - N

    split_k = _adaptive_ksplit_k(M, N, K, E)

    # Extra tuning
    os.environ["AITER_KSPLIT"] = str(split_k)
    os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"
    os.environ["AITER_USE_NT"] = "1"

    return fused_moe(
        hidden,
        gate_up,
        down,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token,
        sorted_expert,
        num_valid,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=split_k,
        quant_type=QuantType.per_1x32,
        activation=ActivationType.Silu,
        doweight_stage1=DOWEIGHT_STAGE1,
        hidden_pad=hp,
        intermediate_pad=ip,
    )


# Alias for compatibility
custom_kernel = custom_kernel_v1


if __name__ == "__main__":
    print("MoE Variants — Adaptive KSPLIT strategies")
    print("5 variants testing different KSPLIT adaptation strategies")
    print("Target: <150µs (current best: 155µs)")
    print("CRITICAL: doweight_stage1=False verified")
