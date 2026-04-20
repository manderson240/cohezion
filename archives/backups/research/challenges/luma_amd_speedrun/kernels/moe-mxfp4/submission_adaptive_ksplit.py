"""
MXFP4 MoE: Adaptive Split-K Routing

Implements shape-aware split-K routing for MoE kernel.
Large-K shapes: split_k=8 (2.5× improvement)
Small-K shapes: split_k=1 (direct path)

Target: 140 µs (vs 158 µs baseline, 145 µs leader)

Submit via:
    popcorn-cli submit --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 kernels/moe-mxfp4/submission_adaptive_ksplit.py
"""

from aiter.fused_moe import fused_moe
from task import input_t, output_t


def _choose_split_k(M: int, N: int, K: int, E: int) -> int:
    """
    Adaptive split-K selection based on shape characteristics.

    John Hahn's technique: split_k=8 for large-K shapes (2.5× improvement)
    """
    # Large-K threshold (K > 2048 benefits from split-K)
    if K > 2048:
        return 8

    # Medium-K (K > 1024, moderate split)
    if K > 1024:
        return 4

    # Small-K (direct path, no split overhead)
    return 1


def custom_kernel(data: input_t) -> output_t:
    """
    Adaptive split-K MoE kernel.

    Routes to split-K path for large-K shapes, direct path for small-K.
    """
    x, w1, w2, w1_scale, w2_scale = data[:5]
    scale_act, a1_scale, a2_scale = data[5:8]
    expert_ids, topk_weights, topk_ids = data[8:11]
    sorted_token_ids, sorted_expert_ids, num_valid_ids = data[11:14]

    M, K = x.shape
    N = w1.shape[1]
    E = w1.shape[0] // 2  # Number of experts

    # Choose split-K based on shape
    split_k = _choose_split_k(M, N, K, E)

    # MoE forward with adaptive split-K
    out = fused_moe(
        x,
        w1,
        w2,
        expert_ids,
        topk_weights,
        topk_ids,
        sorted_token_ids,
        sorted_expert_ids,
        num_valid_ids,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=a1_scale,
        a2_scale=a2_scale,
        scale_act=scale_act,
        split_k=split_k,
        quant_type=0,  # per_1x32 MXFP4
        activation=0,  # SiLU
    )

    return out


if __name__ == "__main__":
    # Test split-K selection
    test_shapes = [
        (16, 7168, 2112, 256),  # Large-K → split_k=8
        (64, 2048, 4096, 256),  # Medium-K → split_k=4
        (4, 512, 2880, 256),  # Small-K → split_k=1
    ]

    for M, K, N, E in test_shapes:
        split_k = _choose_split_k(M, N, K, E)
        print(f"M={M}, K={K}, N={N}, E={E} → split_k={split_k}")
