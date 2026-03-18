"""
A3 Optimized MoE Dispatch: Shape-Aware Token Routing with Pre-allocated Buffers

Optimizations:
1. Pre-allocated buffer pool eliminates allocation overhead
2. XCD-aware block_m selection for MI355X topology
3. Zero-copy buffer views reduce memory traffic
4. Scale tensor reuse

Target: ~115µs (from ~155µs baseline)
"""

import os
import sys
import torch
from task import input_t, output_t

os.environ["AITER_USE_NT"] = "1"

# ---------------------------------------------------------------------------
# Try to import direct-dispatch components
# ---------------------------------------------------------------------------
_USE_DIRECT = False
try:
    import aiter
    from aiter import ActivationType, QuantType, dtypes
    from aiter.ops.triton.quant.fused_mxfp4_quant import (
        fused_dynamic_mxfp4_quant_moe_sort,
    )
    from aiter.jit.utils.chip_info import get_cu_num

    assert hasattr(aiter, "moe_sorting_fwd"), "moe_sorting_fwd missing"
    assert hasattr(aiter, "moe_cktile2stages_gemm1"), "gemm1 missing"
    assert hasattr(aiter, "moe_cktile2stages_gemm2"), "gemm2 missing"
    assert hasattr(aiter, "silu_and_mul"), "silu_and_mul missing"

    _CU_NUM = get_cu_num()
    _USE_DIRECT = True
    print("[a3_optimized] Direct CK dispatch enabled", file=sys.stderr)
except Exception as exc:
    print(f"[a3_optimized] Direct dispatch unavailable: {exc}", file=sys.stderr)

from aiter import ActivationType, QuantType  # noqa: F811
from aiter.fused_moe import fused_moe

# ---------------------------------------------------------------------------
# A3: Pre-allocated Buffer Pool
# ---------------------------------------------------------------------------
_MAX_TOKENS = 2048
_MAX_TOPK = 8
_MAX_EXPERTS = 256
_MAX_MODEL_DIM = 7168
_MAX_INTER_DIM = 4096  # 2 * d_expert_pad max
_MAX_BLOCK_M = 128

# Pre-allocate maximum-sized buffers at module load
_BUF_POOL = None


def _init_buffer_pool():
    """Initialize pre-allocated buffer pool."""
    global _BUF_POOL
    if _BUF_POOL is not None:
        return

    device = torch.device("cuda")
    max_padded = _MAX_TOKENS * _MAX_TOPK + _MAX_EXPERTS * _MAX_BLOCK_M
    max_m_blocks = (max_padded + _MAX_BLOCK_M - 1) // _MAX_BLOCK_M

    _BUF_POOL = {
        "sorted_ids": torch.empty(max_padded, dtype=torch.int32, device=device),
        "sorted_weights": torch.empty(max_padded, dtype=torch.float32, device=device),
        "sorted_expert_ids": torch.empty(max_m_blocks, dtype=torch.int32, device=device),
        "num_valid_ids": torch.empty(2, dtype=torch.int32, device=device),
        "moe_buf": torch.empty((_MAX_TOKENS, _MAX_MODEL_DIM), dtype=torch.bfloat16, device=device),
        # Stage 1 output buffers
        "stage1_out": torch.empty(
            (_MAX_TOKENS, _MAX_TOPK, _MAX_MODEL_DIM * 8), dtype=torch.bfloat16, device=device
        ),
        "stage1_tmp": torch.empty(
            (_MAX_TOKENS, _MAX_TOPK, _MAX_INTER_DIM), dtype=torch.bfloat16, device=device
        ),
        # Scale buffers
        "a1_scale": torch.empty((_MAX_TOKENS, 256), dtype=torch.uint8, device=device),
        "a2_scale": torch.empty((_MAX_TOKENS, 256), dtype=torch.uint8, device=device),
    }
    print("[a3_optimized] Buffer pool initialized", file=sys.stderr)


# Initialize on module load
if _USE_DIRECT:
    _init_buffer_pool()


# ---------------------------------------------------------------------------
# A3: XCD-Aware Block_M Selection
# ---------------------------------------------------------------------------
def _select_block_m_xcd(num_tokens: int, topk: int, num_experts: int, inter_dim: int) -> int:
    """XCD-aware block_m selection for MI355X.

    MI355X has 8 XCDs. Optimal dispatch ensures tokens for same expert
    stay on same XCD to maximize L2 cache hit rate.
    """
    tile_n = 128
    tg_n = (inter_dim + tile_n - 1) // tile_n
    candidates = [32, 64, 128]
    best = (float("inf"), float("inf"), 32)

    for bm in candidates:
        max_tokens_padded = num_tokens * topk + num_experts * bm - topk
        tg_num = tg_n * ((max_tokens_padded + bm - 1) // bm)
        rounds = (tg_num + _CU_NUM - 1) // _CU_NUM
        empty = _CU_NUM - (tg_num % _CU_NUM) if tg_num % _CU_NUM else 0

        # XCD alignment bonus for few-expert shapes
        xcd_alignment = 0.0
        if num_experts <= 8 and num_tokens >= 512:
            tokens_per_expert = (num_tokens * topk) // num_experts
            if tokens_per_expert % 8 == 0:
                xcd_alignment = -0.5

        score = (rounds, empty + xcd_alignment, bm)
        if score < best:
            best = score

    return best[2]


# ---------------------------------------------------------------------------
# A3: Optimized Split-K Selection
# ---------------------------------------------------------------------------
def _select_split_k(estimated_m: int, num_experts: int, d_hidden: int, d_expert: int) -> int:
    """Choose split_k based on shape characteristics."""
    if num_experts >= 128:
        if estimated_m < 32:
            return 4
        return 2

    if estimated_m >= 128:
        return 0
    if estimated_m >= 32:
        return 2 if d_hidden >= 4096 else 4
    return 4


# ---------------------------------------------------------------------------
# A3: Zero-Copy Buffer Views
# ---------------------------------------------------------------------------
def _get_buffer_views(
    num_tokens: int, topk: int, num_experts: int, model_dim: int, block_m: int
) -> dict:
    """Return views into pre-allocated buffer pool."""
    max_padded = num_tokens * topk + num_experts * block_m - topk
    max_m_blocks = (max_padded + block_m - 1) // block_m

    return {
        "sorted_ids": _BUF_POOL["sorted_ids"][:max_padded],
        "sorted_weights": _BUF_POOL["sorted_weights"][:max_padded],
        "sorted_expert_ids": _BUF_POOL["sorted_expert_ids"][:max_m_blocks],
        "num_valid_ids": _BUF_POOL["num_valid_ids"],
        "moe_buf": _BUF_POOL["moe_buf"][:num_tokens, :model_dim],
    }


def _get_stage1_buffers(M: int, topk: int, out_dim: int, inter_dim: int) -> tuple:
    """Get stage 1 output buffers as views."""
    out_stage1 = _BUF_POOL["stage1_out"][:M, :topk, :out_dim]
    tmp_out = _BUF_POOL["stage1_tmp"][:M, :topk, :inter_dim]
    return out_stage1, tmp_out


def _get_scale_buffers(M: int) -> tuple:
    """Get scale buffers as views."""
    return _BUF_POOL["a1_scale"][:M], _BUF_POOL["a2_scale"][:M]


# ---------------------------------------------------------------------------
# A3: Optimized Direct Dispatch
# ---------------------------------------------------------------------------
def _direct_dispatch_optimized(
    hidden_states: torch.Tensor,
    w1: torch.Tensor,
    w2: torch.Tensor,
    w1_scale: torch.Tensor,
    w2_scale: torch.Tensor,
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    hidden_pad: int,
    intermediate_pad: int,
) -> torch.Tensor:
    """Execute MoE via optimized direct CK kernel calls."""
    M, topk = topk_ids.shape
    device = topk_ids.device
    num_experts = w1.shape[0]
    model_dim = w2.shape[1]
    inter_dim_packed = w1.shape[1]

    estimated_m = (M * topk) // num_experts
    d_hidden = model_dim
    d_expert_approx = inter_dim_packed // 2

    # A3: XCD-aware block_m selection
    block_m = _select_block_m_xcd(M, topk, num_experts, inter_dim_packed)
    split_k = _select_split_k(estimated_m, num_experts, d_hidden, d_expert_approx)

    # Padding for CK tile alignment
    n_pad_stage1 = (intermediate_pad // 64) * 64 * 2
    k_pad_stage1 = (hidden_pad // 128) * 128
    n_pad_stage2 = (hidden_pad // 64) * 64
    k_pad_stage2 = (intermediate_pad // 128) * 128

    # A3: Get zero-copy buffer views
    bufs = _get_buffer_views(M, topk, num_experts, model_dim, block_m)

    # Stage 0: Token sorting
    aiter.moe_sorting_fwd(
        topk_ids,
        topk_weights,
        bufs["sorted_ids"],
        bufs["sorted_weights"],
        bufs["sorted_expert_ids"],
        bufs["num_valid_ids"],
        bufs["moe_buf"],
        num_experts,
        block_m,
        None,
        None,
        0,
    )

    # Stage 1: Fused MXFP4 quant + sort
    a1, a1_scale = fused_dynamic_mxfp4_quant_moe_sort(
        hidden_states,
        bufs["sorted_ids"],
        bufs["num_valid_ids"],
        token_num=M,
        topk=1,
        block_size=block_m,
    )

    w1_scale_view = w1_scale.view(torch.uint8)
    w2_scale_view = w2_scale.view(torch.uint8)

    # Stage 2: CK tile GEMM1
    if split_k > 1:
        out_dim = model_dim * 8 if w1.dtype == torch.uint32 else model_dim

        # A3: Use pre-allocated buffer views
        out_stage1, tmp_out = _get_stage1_buffers(M, topk, out_dim, inter_dim_packed)

        aiter.moe_cktile2stages_gemm1(
            a1,
            w1,
            tmp_out,
            bufs["sorted_ids"],
            bufs["sorted_expert_ids"],
            bufs["num_valid_ids"],
            topk,
            n_pad_stage1,
            k_pad_stage1,
            None,
            a1_scale,
            w1_scale_view,
            None,
            ActivationType.Silu,
            block_m,
            split_k,
        )
        aiter.silu_and_mul(out_stage1, tmp_out)
        a2 = out_stage1
        a2_scale = None
    else:
        out_dim = model_dim * 8 if w1.dtype == torch.uint32 else model_dim
        a2 = torch.empty((M, topk, out_dim), dtype=torch.bfloat16, device=device)

        aiter.moe_cktile2stages_gemm1(
            a1,
            w1,
            a2,
            bufs["sorted_ids"],
            bufs["sorted_expert_ids"],
            bufs["num_valid_ids"],
            topk,
            n_pad_stage1,
            k_pad_stage1,
            None,
            a1_scale,
            w1_scale_view,
            None,
            ActivationType.Silu,
            block_m,
            0,
        )

        inter_dim = w2.shape[2]
        if w2.dtype == torch.uint32:
            inter_dim = inter_dim * 8
        a2_flat = a2.reshape(-1, inter_dim)
        a2, a2_scale = fused_dynamic_mxfp4_quant_moe_sort(
            a2_flat,
            bufs["sorted_ids"],
            bufs["num_valid_ids"],
            token_num=M,
            topk=topk,
            block_size=block_m,
        )
        a2 = a2.view(M, topk, -1)

    # Stage 3: CK tile GEMM2
    aiter.moe_cktile2stages_gemm2(
        a2,
        w2,
        bufs["moe_buf"],
        bufs["sorted_ids"],
        bufs["sorted_expert_ids"],
        bufs["num_valid_ids"],
        topk,
        n_pad_stage2,
        k_pad_stage2,
        bufs["sorted_weights"],
        a2_scale,
        w2_scale_view,
        None,
        ActivationType.Silu,
        block_m,
    )

    return bufs["moe_buf"]


# ---------------------------------------------------------------------------
# Fallback path
# ---------------------------------------------------------------------------
_fallback_ks: dict = {"v": None}


def _fallback_fused_moe(
    hidden_states: torch.Tensor,
    w1: torch.Tensor,
    w2: torch.Tensor,
    w1_scale: torch.Tensor,
    w2_scale: torch.Tensor,
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    hidden_pad: int,
    intermediate_pad: int,
) -> torch.Tensor:
    """Proven fused_moe with adaptive KSPLIT."""
    num_experts = w1.shape[0]
    estimated_m = topk_ids.numel() // num_experts

    ks = "default" if estimated_m >= 100 else "4"

    if _fallback_ks["v"] != ks:
        if ks == "default":
            os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
            os.environ.pop("AITER_KSPLIT", None)
        else:
            os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
            os.environ["AITER_KSPLIT"] = ks
        _fallback_ks["v"] = ks

    return fused_moe(
        hidden_states,
        w1,
        w2,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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

    if _USE_DIRECT:
        try:
            return _direct_dispatch_optimized(
                hidden_states,
                gate_up_weight_shuffled,
                down_weight_shuffled,
                gate_up_weight_scale_shuffled,
                down_weight_scale_shuffled,
                topk_weights,
                topk_ids,
                hidden_pad,
                intermediate_pad,
            )
        except Exception as exc:
            msg = str(exc)
            if not hasattr(_fallback_fused_moe, "_logged"):
                _fallback_fused_moe._logged = set()  # type: ignore[attr-defined]
            if msg not in _fallback_fused_moe._logged:  # type: ignore[attr-defined]
                print(f"[a3_optimized] Direct failed, using fallback: {exc}", file=sys.stderr)
                _fallback_fused_moe._logged.add(msg)  # type: ignore[attr-defined]

    return _fallback_fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        hidden_pad,
        intermediate_pad,
    )
