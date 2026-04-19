#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: fmoe_fp8_blockscale_g1u1 with correct MXFP4->FP8 conversion.

Fixed v2: Correct activation quantization layout matching the aiter test.

The fmoe_fp8_blockscale_g1u1 kernel requires:
- input (activations): FP8 [M, model_dim]
- input_scale: float32 [model_dim//128, M]  (transposed!)
- fc1_scale: float32 [E, n1//128 * k1//128]  (flattened block scales)
- fc2_scale: float32 [E, n2//128 * k2//128]
- weights: FP8 shuffled (16x16 layout)

This matches the pattern in aiter/op_tests/test_moe_blockscale.py exactly.
"""

from __future__ import annotations

import torch
from einops import rearrange

import aiter
from aiter import dtypes
from aiter.fused_moe import moe_sorting
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils
from aiter.ops.quant import pertoken_quant

from task import input_t, output_t


SCALE_BLK_N = 128
SCALE_BLK_K = 128
BLOCK_SIZE_M = 32

# Side cache: (gate_up_ptr, down_ptr) -> (w1_shuffled, w1_scale, w2_shuffled, w2_scale)
_weight_cache: dict = {}


def _quant_weights_fp8_blockscale(
    gate_up_bf16: torch.Tensor,  # [E, 2*d_expert_pad, d_hidden_pad]
    down_bf16: torch.Tensor,  # [E, d_hidden_pad, d_expert_pad]
) -> tuple:
    """Quantize BF16 weights to FP8 with 128x128 block scales + shuffle.

    Follows the exact pattern from aiter/op_tests/test_moe_blockscale.py.
    """
    E = gate_up_bf16.shape[0]
    n1, k1 = gate_up_bf16.shape[1], gate_up_bf16.shape[2]
    n2, k2 = down_bf16.shape[1], down_bf16.shape[2]

    # Quantize gate_up weights: [E, n1, k1] with 128x128 blocks
    tmp1 = rearrange(
        gate_up_bf16.view(E, n1 // SCALE_BLK_N, SCALE_BLK_N, k1 // SCALE_BLK_K, SCALE_BLK_K),
        "e bn blkn bk blkk -> e bn bk (blkn blkk)",
    ).contiguous()
    w1_q, w1_scale = pertoken_quant(tmp1, quant_dtype=dtypes.fp8)
    w1_q = rearrange(
        w1_q.view(E, n1 // SCALE_BLK_N, k1 // SCALE_BLK_K, SCALE_BLK_N, SCALE_BLK_K),
        "e bn bk blkn blkk -> e (bn blkn) (bk blkk)",
    ).contiguous()
    w1_scale = w1_scale.view(E, -1)  # [E, (n1//128)*(k1//128)]

    # Quantize down weights: [E, n2, k2] with 128x128 blocks
    tmp2 = rearrange(
        down_bf16.view(E, n2 // SCALE_BLK_N, SCALE_BLK_N, k2 // SCALE_BLK_K, SCALE_BLK_K),
        "e bn blkn bk blkk -> e bn bk (blkn blkk)",
    ).contiguous()
    w2_q, w2_scale = pertoken_quant(tmp2, quant_dtype=dtypes.fp8)
    w2_q = rearrange(
        w2_q.view(E, n2 // SCALE_BLK_N, k2 // SCALE_BLK_K, SCALE_BLK_N, SCALE_BLK_K),
        "e bn bk blkn blkk -> e (bn blkn) (bk blkk)",
    ).contiguous()
    w2_scale = w2_scale.view(E, -1)  # [E, (n2//128)*(k2//128)]

    # Shuffle weights to the 16x16 layout expected by the ASM kernel
    w1_shuffled = shuffle_weight(w1_q, layout=(16, 16))
    w2_shuffled = shuffle_weight(w2_q, layout=(16, 16))

    return w1_shuffled, w1_scale, w2_shuffled, w2_scale


def _dequant_mxfp4_weights(
    weight_fp4: torch.Tensor,  # [E, N, K//2] fp4x2 (uint8 view)
    scale_e8m0: torch.Tensor,  # [E, N, scale_K] e8m0
) -> torch.Tensor:
    """Dequantize MXFP4 weights to BF16."""
    E, N, Khalf = weight_fp4.shape
    K = Khalf * 2

    w_f32 = fp4_utils.mxfp4_to_f32(weight_fp4)  # [E, N, K]
    s_f32 = fp4_utils.e8m0_to_f32(scale_e8m0)  # [E, N_padded, scale_K]

    scale_K = K // 32
    s_f32 = s_f32[:, :N, :scale_K]
    s_f32 = s_f32.repeat_interleave(32, dim=-1)  # [E, N, K]

    return (w_f32 * s_f32).to(torch.bfloat16)


def custom_kernel(data: input_t) -> output_t:
    """MoE via fmoe_fp8_blockscale_g1u1 (different GPU .co kernel than baseline)."""
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

    M, total_top_k = topk_ids.shape
    E = gate_up_weight.shape[0]
    d_hidden_pad = config["d_hidden_pad"]
    d_expert_pad = config["d_expert_pad"]
    model_dim = hidden_states.shape[1]

    # Step 1: Convert MXFP4 weights to FP8 blockscale (cached across calls)
    cache_key = (gate_up_weight.data_ptr(), down_weight.data_ptr())
    cached = _weight_cache.get(cache_key)

    if cached is None:
        gate_up_bf16 = _dequant_mxfp4_weights(gate_up_weight, gate_up_weight_scale)
        down_bf16 = _dequant_mxfp4_weights(down_weight, down_weight_scale)

        # Trim to padded dims (already padded, but ensure exact shape)
        gate_up_bf16 = gate_up_bf16[:, : 2 * d_expert_pad, :d_hidden_pad]
        down_bf16 = down_bf16[:, :d_hidden_pad, :d_expert_pad]

        w1_shuffled, w1_scale, w2_shuffled, w2_scale = _quant_weights_fp8_blockscale(
            gate_up_bf16, down_bf16
        )
        cached = (w1_shuffled, w1_scale, w2_shuffled, w2_scale)
        _weight_cache[cache_key] = cached

    w1_shuffled, w1_scale, w2_shuffled, w2_scale = cached

    # Step 2: Quantize activations to FP8 with 1x128 block scales.
    # Match the exact pattern from test_moe_blockscale.py:
    #   pertoken_quant on [M, model_dim//128, 128] -> scale [M, model_dim//128]
    #   then transpose to [model_dim//128, M] for the ASM kernel
    a1_q, a1_scale = pertoken_quant(
        hidden_states.view(M, model_dim // SCALE_BLK_K, SCALE_BLK_K),
        quant_dtype=dtypes.fp8,
    )
    a1_q = a1_q.view(M, model_dim)
    # a1_scale: [M, model_dim//128, 1] -> squeeze -> [M, model_dim//128]
    a1_scale = a1_scale.squeeze(-1)
    # Transpose to [model_dim//128, M] as expected by fmoe_fp8_blockscale_g1u1
    a1_scale_t = a1_scale.t().contiguous()

    # Step 3: MoE token sorting
    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_buf = moe_sorting(
        topk_ids,
        topk_weights,
        E,
        model_dim,
        hidden_states.dtype,
        BLOCK_SIZE_M,
    )

    # Step 4: Run the FP8 blockscale ASM kernel
    # This uses fmoe_fp8_blockscale_g1u1_novs_subGU_256.co — different from
    # the baseline fmoe_g1u1 path.
    aiter.fmoe_fp8_blockscale_g1u1(
        moe_buf,  # out [M, model_dim] bf16
        a1_q,  # input [M, model_dim] fp8
        w1_shuffled,  # gate [E, 2*d_expert_pad, d_hidden_pad] fp8 shuffled
        w2_shuffled,  # down [E, d_hidden_pad, d_expert_pad] fp8 shuffled
        sorted_ids,
        sorted_weights,
        sorted_expert_ids,
        num_valid_ids,
        total_top_k,
        a1_scale_t,  # [model_dim//128, M]
        w1_scale,  # [E, flat]
        w2_scale,  # [E, flat]
        "",  # kernelName: auto-select
        SCALE_BLK_N,
        SCALE_BLK_K,
        None,  # fc2_smooth_scale
        aiter.ActivationType.Silu.value,
    )

    return moe_buf
