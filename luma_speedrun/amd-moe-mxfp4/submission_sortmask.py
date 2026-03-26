"""MXFP4 MoE — moe_sorting_fwd with local_expert_mask to skip empty experts.

Hypothesis: For small bs, only ~9-13/257 experts are active. The default sort
allocates M-tiles for ALL 257 experts (most empty). local_expert_mask compacts
this so the CK kernel launches ~9-13 tiles instead of ~260+.

Risk: CK stage1/stage2 may require full-size sorted arrays → may crash.
This is the only untried path from Phase 18 exhaustion.

Key rules preserved:
- NEVER doweight_stage1=True
- NEVER KSPLIT=4 for 32-expert shapes
- MoE tolerance is STRICT (zero mismatches required)
"""

import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)
_AITER_JIT_BUILD = os.path.join(_AITER_JIT_DIR, "build")
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch
from aiter import ActivationType, QuantType, dtypes
from aiter import dtypes as aiter_dtypes
from aiter.fused_moe import (
    get_2stage_cfgs,
    get_inter_dim,
    get_padded_M,
)
from aiter.ops.moe_sorting import moe_sorting_fwd
from aiter.ops.triton.quant.fused_mxfp4_quant import fused_dynamic_mxfp4_quant_moe_sort
from aiter.utility import fp4_utils
from task import input_t, output_t


BLOCK_SIZE_M = 32


def _moe_sorting_masked(
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    num_experts: int,
    model_dim: int,
    moebuf_dtype,
    block_size: int = BLOCK_SIZE_M,
) -> tuple:
    """Run moe_sorting_fwd with a local_expert_mask covering only active experts.

    The mask is a per-expert int32 tensor: 1 = active, 0 = skip.
    This compacts sorted_expert_ids so CK skips empty-expert M-tiles.
    """
    device = topk_ids.device
    M, topk = topk_ids.shape

    # Build local_expert_mask: which experts appear in this batch?
    # bincount is fast for small topk*M counts
    flat_ids = topk_ids.view(-1).long()
    local_expert_mask = (
        torch.bincount(flat_ids, minlength=num_experts) > 0
    ).to(torch.int32, device=device)

    # Allocate sort buffers at full size (same as normal sort — CK requires this)
    max_num_tokens_padded = int(topk_ids.numel() + num_experts * block_size - topk)
    max_num_m_blocks = int((max_num_tokens_padded + block_size - 1) // block_size)

    sorted_ids = torch.empty(max_num_tokens_padded, dtype=dtypes.i32, device=device)
    sorted_weights = torch.empty(max_num_tokens_padded, dtype=dtypes.fp32, device=device)
    sorted_expert_ids = torch.empty(max_num_m_blocks, dtype=dtypes.i32, device=device)
    num_valid_ids = torch.empty(2, dtype=dtypes.i32, device=device)
    moe_buf = torch.empty((M, model_dim), dtype=moebuf_dtype, device=device)

    moe_sorting_fwd(
        topk_ids,
        topk_weights,
        sorted_ids,
        sorted_weights,
        sorted_expert_ids,
        num_valid_ids,
        moe_buf,
        num_experts,
        int(block_size),
        local_expert_mask,   # <-- the key difference
        None,                # num_local_tokens
        0,                   # dispatch_policy
    )

    return sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_buf


def _fused_moe_masked(
    hidden_states: torch.Tensor,
    w1: torch.Tensor,
    w2: torch.Tensor,
    topk_weight: torch.Tensor,
    topk_ids: torch.Tensor,
    w1_scale,
    w2_scale,
    hidden_pad: int,
    intermediate_pad: int,
) -> torch.Tensor:
    """fused_moe with masked sorting — skips empty-expert M-tiles.

    Mirrors the per_1x32 / fp4x2 / Silu / shuffled / 2-stage path from
    fused_moe_.py fused_moe_2stages(), but replaces the moe_sorting call
    with our masked variant.
    """
    M, topk = topk_ids.shape
    E, model_dim, inter_dim = get_inter_dim(w1.shape, w2.shape)
    dtype = hidden_states.dtype  # bf16
    device = topk_ids.device
    q_dtype_a = aiter_dtypes.fp4x2
    q_dtype_w = aiter_dtypes.fp4x2
    quant_type = QuantType.per_1x32
    activation = ActivationType.Silu
    is_shuffled = getattr(w1, "is_shuffled", False)

    # Get metadata (determines stage1/stage2 kernel selection + block_m)
    metadata = get_2stage_cfgs(
        get_padded_M(M),
        model_dim,
        inter_dim,
        E,
        topk,
        dtype,
        q_dtype_a,
        q_dtype_w,
        quant_type,
        True,   # isG1U1 (gate+up fused)
        activation,
        False,  # doweight_stage1
        hidden_pad,
        intermediate_pad,
        is_shuffled,
    )

    block_size_M = int(metadata.block_m)

    # ── Masked sort ──
    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_out = (
        _moe_sorting_masked(
            topk_ids, topk_weight, E, model_dim, dtype, block_size_M
        )
    )

    # ── Activation quantization (matches fused_moe_2stages per_1x32 path) ──
    token_num_quant_moe_sort_switch = 1024
    token_num = hidden_states.shape[0]

    if token_num <= token_num_quant_moe_sort_switch:
        # fused quant + sort for small batches
        a1, a1_scale = fused_dynamic_mxfp4_quant_moe_sort(
            hidden_states,
            sorted_ids=sorted_ids,
            num_valid_ids=num_valid_ids,
            token_num=token_num,
            topk=1,
            block_size=block_size_M,
        )
    else:
        from aiter import get_hip_quant
        quant_func = get_hip_quant(quant_type)
        a1, a1_scale = quant_func(
            hidden_states,
            scale=None,
            quant_dtype=q_dtype_a,
            num_rows=None,
        )
        a1_scale = fp4_utils.moe_mxfp4_sort(
            a1_scale,
            sorted_ids=sorted_ids,
            num_valid_ids=num_valid_ids,
            token_num=token_num,
            block_size=block_size_M,
        )

    # ── Stage 1: gate+up GEMM + SiLU ──
    a2 = torch.empty((token_num, topk, inter_dim), dtype=dtype, device=device)
    a2 = metadata.stage1(
        a1,
        w1,
        w2,
        sorted_ids,
        sorted_expert_ids,
        num_valid_ids,
        a2,
        topk,
        block_m=block_size_M,
        a1_scale=a1_scale,
        w1_scale=(
            w1_scale.view(aiter_dtypes.fp8_e8m0) if w1.dtype == aiter_dtypes.fp4x2 else w1_scale
        ),
        sorted_weights=None,  # doweight_stage1=False
    )

    # ── Stage 2 quantization ──
    a2 = a2.view(-1, inter_dim)
    if token_num <= token_num_quant_moe_sort_switch:
        a2, a2_scale = fused_dynamic_mxfp4_quant_moe_sort(
            a2,
            sorted_ids=sorted_ids,
            num_valid_ids=num_valid_ids,
            token_num=token_num,
            topk=topk,
            block_size=block_size_M,
        )
    else:
        from aiter import get_hip_quant
        quant_func = get_hip_quant(quant_type)
        a2, a2_scale = quant_func(
            a2,
            scale=None,
            quant_dtype=q_dtype_a,
            num_rows=None,
            num_rows_factor=topk,
        )
        a2_scale = fp4_utils.moe_mxfp4_sort(
            a2_scale[: token_num * topk, :].view(token_num, topk, -1),
            sorted_ids=sorted_ids,
            num_valid_ids=num_valid_ids,
            token_num=token_num,
            block_size=block_size_M,
        )
    a2 = a2.view(token_num, topk, -1)

    # ── Stage 2: down GEMM + weighted reduce ──
    metadata.stage2(
        a2,
        w1,
        w2,
        sorted_ids,
        sorted_expert_ids,
        num_valid_ids,
        moe_out,
        topk,
        w2_scale=(
            w2_scale.view(aiter_dtypes.fp8_e8m0) if w2.dtype == aiter_dtypes.fp4x2 else w2_scale
        ),
        a2_scale=a2_scale,
        block_m=block_size_M,
        sorted_weights=sorted_weights,  # doweight_stage1=False → weight at stage2
    )

    return moe_out


def custom_kernel(data: input_t) -> output_t:
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

    return _fused_moe_masked(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        hidden_pad,
        intermediate_pad,
    )
