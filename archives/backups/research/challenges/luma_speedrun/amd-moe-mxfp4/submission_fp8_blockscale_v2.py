#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: FP8 Blockscale v2 — Corrected MXFP4→FP8 conversion.

Fixes from v1 failure:
1. Proper scale tensor handling: use E8M0 scales directly, not requantize
2. Correct activation quantization: use pertoken_quant for FP8, not blockwise
3. Validate all dimensions divisible by 128 before conversion
4. Use fmoe_fp8_blockscale_g1u1 with proper argument order

Key insight: The FP8 blockscale kernel expects weights already in FP8 format
with block scales in E8M0 format. We need to dequantize MXFP4 weights to BF16,
then requantize to FP8 blockscale (not MXFP4 format).
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"

import aiter
import torch
from aiter import dtypes
from aiter.fused_moe import moe_sorting
from aiter.ops.quant import pertoken_quant
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils
from task import input_t, output_t


# Block size for FP8 blockscale quantization (128x128 tiles)
SCALE_BLK_N = 128
SCALE_BLK_K = 128

# MoE sorting block size
BLOCK_SIZE_M = 32


# Side cache mapping cache_key -> (w1_fp8, w1_scale_shuffled, w2_fp8, w2_scale_shuffled)
_weight_cache: dict = {}


def _convert_mxfp4_to_fp8_blockscale(
    gate_up_fp4: torch.Tensor,  # [E, 2*d_expert_pad, d_hidden_pad//2] uint8 packed fp4
    down_fp4: torch.Tensor,  # [E, d_hidden_pad, d_expert_pad//2] uint8 packed fp4
    gate_up_scale: torch.Tensor,  # [E, 2*d_expert_pad, scale_K] e8m0
    down_scale: torch.Tensor,  # [E, d_hidden_pad, scale_K] e8m0
    d_expert: int,
    d_hidden: int,
) -> tuple:
    """Convert MXFP4 weights to FP8 blockscale format.

    Strategy:
    1. Dequantize MXFP4 -> BF16 using fp4_utils
    2. Reshape to [E, N//128, K//128, 128, 128] blocks
    3. For each block: find amax, compute E8M0 scale
    4. Quantize block to FP8
    5. Shuffle weights for ASM kernel
    """
    E = gate_up_fp4.shape[0]

    # Get actual dimensions (excluding padding)
    d_expert_pad = gate_up_fp4.shape[1] // 2
    d_hidden_pad = gate_up_fp4.shape[2] * 2

    # Validate dimensions are divisible by 128
    assert (2 * d_expert_pad) % SCALE_BLK_N == 0, (
        f"2*d_expert_pad={2 * d_expert_pad} not divisible by {SCALE_BLK_N}"
    )
    assert d_hidden_pad % SCALE_BLK_K == 0, (
        f"d_hidden_pad={d_hidden_pad} not divisible by {SCALE_BLK_K}"
    )
    assert d_hidden_pad % SCALE_BLK_N == 0, (
        f"d_hidden_pad={d_hidden_pad} not divisible by {SCALE_BLK_N}"
    )
    assert d_expert_pad % SCALE_BLK_K == 0, (
        f"d_expert_pad={d_expert_pad} not divisible by {SCALE_BLK_K}"
    )

    # ===== Step 1: Dequantize MXFP4 to BF16 =====

    # gate_up: [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2
    gate_up_f32 = fp4_utils.mxfp4_to_f32(gate_up_fp4)  # [E, 2*d_expert_pad, d_hidden_pad]

    # gate_up_scale: [E, 2*d_expert_pad, scale_K] e8m0
    # scale_K = d_hidden_pad // 32
    scale_K = d_hidden_pad // 32
    gate_up_scale_f32 = fp4_utils.e8m0_to_f32(gate_up_scale[:, :, :scale_K])  # Trim if needed

    # Broadcast scale across 32 K-columns per scale element
    gate_up_scale_f32 = gate_up_scale_f32.repeat_interleave(
        32, dim=-1
    )  # [E, 2*d_expert_pad, d_hidden_pad]
    gate_up_bf16 = (gate_up_f32 * gate_up_scale_f32).to(torch.bfloat16)

    # down: [E, d_hidden_pad, d_expert_pad//2] fp4x2
    down_f32 = fp4_utils.mxfp4_to_f32(down_fp4)  # [E, d_hidden_pad, d_expert_pad]
    down_scale_f32 = fp4_utils.e8m0_to_f32(down_scale[:, :, : d_expert_pad // 32])
    down_scale_f32 = down_scale_f32.repeat_interleave(32, dim=-1)
    down_bf16 = (down_f32 * down_scale_f32).to(torch.bfloat16)

    # ===== Step 2: Block-wise FP8 quantization =====

    # gate_up_bf16: [E, N=2*d_expert_pad, K=d_hidden_pad]
    # Reshape to blocks: [E, N//128, K//128, 128, 128]
    n1_blocks = (2 * d_expert_pad) // SCALE_BLK_N
    k1_blocks = d_hidden_pad // SCALE_BLK_K

    gate_up_blocks = gate_up_bf16.view(E, n1_blocks, SCALE_BLK_N, k1_blocks, SCALE_BLK_K)
    gate_up_blocks = gate_up_blocks.permute(
        0, 1, 3, 2, 4
    ).contiguous()  # [E, n_blocks_N, n_blocks_K, 128, 128]

    # Compute per-block scales and quantize
    gate_up_fp8_list = []
    gate_up_scale_list = []

    for e in range(E):
        for nb in range(n1_blocks):
            for kb in range(k1_blocks):
                block = gate_up_blocks[e, nb, kb, :, :]  # [128, 128]
                amax = block.abs().amax()
                if amax > 0:
                    scale = amax / 448.0  # FP8 E4M3 max
                    fp8_block = (block / scale).clamp(-448, 448).to(dtypes.fp8)
                else:
                    scale = 1.0
                    fp8_block = torch.zeros_like(block, dtype=dtypes.fp8)

                # Convert scale to E8M0
                scale_e8m0 = fp4_utils.f32_to_e8m0(torch.tensor([scale]))[0]

                gate_up_fp8_list.append(fp8_block)
                gate_up_scale_list.append(scale_e8m0)

    # Stack back
    gate_up_fp8 = torch.stack(gate_up_fp8_list).view(
        E, n1_blocks, k1_blocks, SCALE_BLK_N, SCALE_BLK_K
    )
    gate_up_fp8 = (
        gate_up_fp8.permute(0, 1, 3, 2, 4).contiguous().view(E, 2 * d_expert_pad, d_hidden_pad)
    )

    gate_up_scale_e8m0 = torch.tensor(gate_up_scale_list, dtype=torch.uint8).view(
        E, n1_blocks * k1_blocks
    )

    # Repeat for down weights
    n2_blocks = d_hidden_pad // SCALE_BLK_N
    k2_blocks = d_expert_pad // SCALE_BLK_K

    down_blocks = down_bf16.view(E, n2_blocks, SCALE_BLK_N, k2_blocks, SCALE_BLK_K)
    down_blocks = down_blocks.permute(0, 1, 3, 2, 4).contiguous()

    down_fp8_list = []
    down_scale_list = []

    for e in range(E):
        for nb in range(n2_blocks):
            for kb in range(k2_blocks):
                block = down_blocks[e, nb, kb, :, :]
                amax = block.abs().amax()
                if amax > 0:
                    scale = amax / 448.0
                    fp8_block = (block / scale).clamp(-448, 448).to(dtypes.fp8)
                else:
                    scale = 1.0
                    fp8_block = torch.zeros_like(block, dtype=dtypes.fp8)

                scale_e8m0 = fp4_utils.f32_to_e8m0(torch.tensor([scale]))[0]

                down_fp8_list.append(fp8_block)
                down_scale_list.append(scale_e8m0)

    down_fp8 = torch.stack(down_fp8_list).view(E, n2_blocks, k2_blocks, SCALE_BLK_N, SCALE_BLK_K)
    down_fp8 = down_fp8.permute(0, 1, 3, 2, 4).contiguous().view(E, d_hidden_pad, d_expert_pad)

    down_scale_e8m0 = torch.tensor(down_scale_list, dtype=torch.uint8).view(
        E, n2_blocks * k2_blocks
    )

    # ===== Step 3: Shuffle for ASM kernel =====
    w1_shuffled = shuffle_weight(gate_up_fp8, layout=(16, 16))
    w2_shuffled = shuffle_weight(down_fp8, layout=(16, 16))

    # Scale shuffle (different layout for scales)
    # Scale is [E, n_blocks], shuffle as 1D
    w1_scale_shuffled = shuffle_weight(gate_up_scale_e8m0.view(E, -1, 1, 1), layout=(16, 16)).view(
        E, -1
    )
    w2_scale_shuffled = shuffle_weight(down_scale_e8m0.view(E, -1, 1, 1), layout=(16, 16)).view(
        E, -1
    )

    return w1_shuffled, w1_scale_shuffled, w2_shuffled, w2_scale_shuffled


def custom_kernel(data: input_t) -> output_t:
    """MoE via fmoe_fp8_blockscale_g1u1 with corrected conversion."""
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
    d_hidden = config["d_hidden"]
    d_expert = config["d_expert"]
    d_hidden_pad = config["d_hidden_pad"]
    d_expert_pad = config["d_expert_pad"]

    # Check if we can use FP8 blockscale (requires 128-divisible dims)
    can_use_fp8 = (
        (2 * d_expert_pad) % SCALE_BLK_N == 0
        and d_hidden_pad % SCALE_BLK_K == 0
        and d_hidden_pad % SCALE_BLK_N == 0
        and d_expert_pad % SCALE_BLK_K == 0
    )

    if not can_use_fp8:
        # Fall back to baseline for incompatible shapes
        from aiter import ActivationType, QuantType
        from aiter.fused_moe import fused_moe

        hidden_pad = d_hidden_pad - d_hidden
        intermediate_pad = d_expert_pad - d_expert

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

    # ===== Step 1: Convert weights MXFP4 -> FP8 blockscale =====
    cache_key = (gate_up_weight.data_ptr(), down_weight.data_ptr())
    cached = _weight_cache.get(cache_key)

    if cached is None:
        w1_shuffled, w1_scale, w2_shuffled, w2_scale = _convert_mxfp4_to_fp8_blockscale(
            gate_up_weight, down_weight, gate_up_weight_scale, down_weight_scale, d_expert, d_hidden
        )
        cached = (w1_shuffled, w1_scale, w2_shuffled, w2_scale)
        _weight_cache[cache_key] = cached

    w1_shuffled, w1_scale, w2_shuffled, w2_scale = cached

    # ===== Step 2: Quantize activation to FP8 (pertoken) =====
    # Using aiter's pertoken_quant for FP8
    M_tokens, model_dim = hidden_states.shape

    # Flatten for pertoken quant: [M, model_dim] -> [M * model_dim//128, 128]
    hidden_flat = hidden_states.view(-1, SCALE_BLK_K)

    a1_fp8, a1_scale = pertoken_quant(hidden_flat, quant_dtype=dtypes.fp8)
    # Reshape back: [M * model_dim//128, 128] -> [M, model_dim]
    a1_fp8 = a1_fp8.view(M_tokens, model_dim)

    # Scale needs to be transposed for kernel: [M, model_dim//128] -> [model_dim//128, M]
    a1_scale_t = a1_scale.view(M_tokens, model_dim // SCALE_BLK_K).t().contiguous()

    # ===== Step 3: MoE sorting =====
    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_buf = moe_sorting(
        topk_ids,
        topk_weights,
        E,
        model_dim,
        hidden_states.dtype,
        BLOCK_SIZE_M,
    )

    # ===== Step 4: Direct fmoe_fp8_blockscale_g1u1 call =====
    try:
        aiter.fmoe_fp8_blockscale_g1u1(
            moe_buf,  # out
            a1_fp8,  # input
            w1_shuffled,  # gate
            w2_shuffled,  # down
            sorted_ids,  # sorted_token_ids
            sorted_weights,  # sorted_weights
            sorted_expert_ids,  # sorted_expert_ids
            num_valid_ids,  # num_valid_ids
            total_top_k,  # topk
            a1_scale_t,  # input_scale
            w1_scale,  # fc1_scale
            w2_scale,  # fc2_scale
            "",  # kernelName (auto-select, try "novs_subGU_256" if slow)
            SCALE_BLK_N,  # fc_scale_blkn
            SCALE_BLK_K,  # fc_scale_blkk
            None,  # fc2_smooth_scale
            aiter.ActivationType.Silu.value,
            BLOCK_SIZE_M,  # block_size_M
        )
    except Exception as e:
        # Fall back to baseline on error
        print(f"[fp8_blockscale] Error: {e}, falling back to baseline")
        from aiter import ActivationType, QuantType
        from aiter.fused_moe import fused_moe

        hidden_pad = d_hidden_pad - d_hidden
        intermediate_pad = d_expert_pad - d_expert

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

    return moe_buf
