"""
MXFP4 MoE: Optimized direct dispatch with cached parameters and buffers.

Optimizations applied:
1. Parameter cache: block_m, split_k, padding cached per shape
2. Extended buffer cache: includes output tensors (tmp_out, out_stage1, a2)
3. Scale view cache: pre-computed fp8_e8m0 views
4. Local variable binding: reduced dict lookups in hot path
5. Inlined padding computation: cached per shape

Benchmark shapes:
  S1: 128tok, 8exp, top2,  d=7168, dexp=2048  -> est_m=32
  S2: 128tok, 256exp, top8, d=2048, dexp=1408 -> est_m=4
  S3: 512tok, 8exp, top2,  d=7168, dexp=2048  -> est_m=128
  S4: 512tok, 256exp, top8, d=2048, dexp=1408 -> est_m=16
  S5: 2048tok, 8exp, top2, d=7168, dexp=2048  -> est_m=512
  S6: 2048tok, 256exp, top8, d=2048, dexp=1408 -> est_m=64
"""

import os
import sys
import torch
from task import input_t, output_t

os.environ["AITER_USE_NT"] = "1"

# ---------------------------------------------------------------------------
# Try to import direct-dispatch components. If any fail, _USE_DIRECT = False.
# ---------------------------------------------------------------------------
_USE_DIRECT = False
try:
    import aiter
    from aiter import ActivationType, QuantType, dtypes
    from aiter.ops.triton.quant.fused_mxfp4_quant import (
        fused_dynamic_mxfp4_quant_moe_sort,
    )
    from aiter.jit.utils.chip_info import get_cu_num

    # Verify the CK tile GEMM functions exist
    assert hasattr(aiter, "moe_sorting_fwd"), "moe_sorting_fwd missing"
    assert hasattr(aiter, "moe_cktile2stages_gemm1"), "gemm1 missing"
    assert hasattr(aiter, "moe_cktile2stages_gemm2"), "gemm2 missing"
    assert hasattr(aiter, "silu_and_mul"), "silu_and_mul missing"

    _CU_NUM = get_cu_num()
    _USE_DIRECT = True
    print("[custom_dispatch] Direct CK dispatch enabled", file=sys.stderr)
except Exception as exc:
    print(f"[custom_dispatch] Direct dispatch unavailable: {exc}", file=sys.stderr)

# Fallback imports (always available)
from aiter import ActivationType, QuantType  # noqa: F811
from aiter.fused_moe import fused_moe

# ---------------------------------------------------------------------------
# Caches for optimized dispatch
# ---------------------------------------------------------------------------
_buf_cache: dict = {}
_param_cache: dict = {}  # NEW: Cache for block_m, split_k, padding
_scale_cache: dict = {}  # NEW: Cache for scale views
_fallback_ks: dict = {"v": None}


# ---------------------------------------------------------------------------
# Parameter selection (cached results)
# ---------------------------------------------------------------------------
def _select_block_m(num_tokens: int, topk: int, num_experts: int, inter_dim: int) -> int:
    """Compute optimal block_m using CU occupancy heuristic."""
    tile_n = 128
    tg_n = (inter_dim + tile_n - 1) // tile_n
    candidates = [32, 64, 128]
    best = (float("inf"), float("inf"), 32)
    for bm in candidates:
        max_tokens_padded = num_tokens * topk + num_experts * bm - topk
        tg_num = tg_n * ((max_tokens_padded + bm - 1) // bm)
        rounds = (tg_num + _CU_NUM - 1) // _CU_NUM
        empty = _CU_NUM - (tg_num % _CU_NUM) if tg_num % _CU_NUM else 0
        score = (rounds, empty, bm)
        if score < best:
            best = score
    return best[2]


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


def _compute_padding(hidden_pad: int, intermediate_pad: int) -> tuple:
    """Compute CK tile padding values."""
    n_pad_stage1 = (intermediate_pad // 64) * 64 * 2
    k_pad_stage1 = (hidden_pad // 128) * 128
    n_pad_stage2 = (hidden_pad // 64) * 64
    k_pad_stage2 = (intermediate_pad // 128) * 128
    return (n_pad_stage1, k_pad_stage1, n_pad_stage2, k_pad_stage2)


# ---------------------------------------------------------------------------
# Cached parameter retrieval
# ---------------------------------------------------------------------------
def _get_cached_params(
    M: int,
    topk: int,
    num_experts: int,
    model_dim: int,
    inter_dim_packed: int,
    hidden_pad: int,
    intermediate_pad: int,
) -> tuple:
    """Get cached parameters or compute and cache them."""
    key = (M, topk, num_experts, model_dim, inter_dim_packed)

    if key in _param_cache:
        return _param_cache[key]

    # Compute parameters
    estimated_m = (M * topk) // num_experts
    d_expert_approx = inter_dim_packed // 2
    block_m = _select_block_m(M, topk, num_experts, inter_dim_packed)
    split_k = _select_split_k(estimated_m, num_experts, model_dim, d_expert_approx)
    padding = _compute_padding(hidden_pad, intermediate_pad)

    params = (block_m, split_k, padding, estimated_m)
    _param_cache[key] = params
    return params


# ---------------------------------------------------------------------------
# Buffer allocation with extended caching (includes output tensors)
# ---------------------------------------------------------------------------
def _get_buffers(
    M: int,
    topk: int,
    num_experts: int,
    model_dim: int,
    inter_dim_packed: int,
    block_m: int,
    device: torch.device,
    split_k: int,
) -> dict:
    """Get cached buffers including output tensors."""
    key = (M, topk, num_experts, model_dim, inter_dim_packed, block_m, device.index, split_k)

    if key in _buf_cache:
        return _buf_cache[key]

    max_padded = M * topk + num_experts * block_m - topk
    max_m_blocks = (max_padded + block_m - 1) // block_m

    # Core buffers
    bufs = {
        "sorted_ids": torch.empty(max_padded, dtype=dtypes.i32, device=device),
        "sorted_weights": torch.empty(max_padded, dtype=dtypes.fp32, device=device),
        "sorted_expert_ids": torch.empty(max_m_blocks, dtype=dtypes.i32, device=device),
        "num_valid_ids": torch.empty(2, dtype=dtypes.i32, device=device),
        "moe_buf": torch.empty((M, model_dim), dtype=dtypes.bf16, device=device),
    }

    # Output buffers (cached to avoid allocation overhead)
    out_dim = model_dim * 8  # For uint32 packed weights

    if split_k > 1:
        bufs["tmp_out"] = torch.zeros((M, topk, inter_dim_packed), dtype=dtypes.bf16, device=device)
        bufs["out_stage1"] = torch.empty((M, topk, out_dim), dtype=dtypes.bf16, device=device)
    else:
        bufs["a2"] = torch.empty((M, topk, out_dim), dtype=dtypes.bf16, device=device)

    _buf_cache[key] = bufs
    return bufs


# ---------------------------------------------------------------------------
# Cached scale views
# ---------------------------------------------------------------------------
def _get_scale_views(w1_scale: torch.Tensor, w2_scale: torch.Tensor) -> tuple:
    """Get cached fp8_e8m0 scale views."""
    key = (id(w1_scale), id(w2_scale))

    if key in _scale_cache:
        return _scale_cache[key]

    views = (w1_scale.view(dtypes.fp8_e8m0), w2_scale.view(dtypes.fp8_e8m0))
    _scale_cache[key] = views
    return views


# ---------------------------------------------------------------------------
# Direct dispatch path (optimized)
# ---------------------------------------------------------------------------
def _direct_dispatch(
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
    """Execute MoE via direct CK kernel calls with caching optimizations."""
    M, topk = topk_ids.shape
    device = topk_ids.device
    num_experts = w1.shape[0]
    model_dim = w2.shape[1]
    inter_dim_packed = w1.shape[1]

    # Get cached parameters
    block_m, split_k, padding, estimated_m = _get_cached_params(
        M, topk, num_experts, model_dim, inter_dim_packed, hidden_pad, intermediate_pad
    )
    n_pad_stage1, k_pad_stage1, n_pad_stage2, k_pad_stage2 = padding

    # Get cached buffers (includes output tensors)
    bufs = _get_buffers(M, topk, num_experts, model_dim, inter_dim_packed, block_m, device, split_k)

    # Bind locals to reduce dict lookups
    sorted_ids = bufs["sorted_ids"]
    sorted_weights = bufs["sorted_weights"]
    sorted_expert_ids = bufs["sorted_expert_ids"]
    num_valid_ids = bufs["num_valid_ids"]
    moe_buf = bufs["moe_buf"]

    # Get cached scale views
    w1_scale_view, w2_scale_view = _get_scale_views(w1_scale, w2_scale)

    # --- Stage 0: Token sorting ---
    aiter.moe_sorting_fwd(
        topk_ids,
        topk_weights,
        sorted_ids,
        sorted_weights,
        sorted_expert_ids,
        num_valid_ids,
        moe_buf,
        num_experts,
        block_m,
        None,
        None,
        0,
    )

    # --- Stage 1: Fused MXFP4 quant + sort ---
    a1, a1_scale = fused_dynamic_mxfp4_quant_moe_sort(
        hidden_states,
        sorted_ids=sorted_ids,
        num_valid_ids=num_valid_ids,
        token_num=M,
        topk=1,
        block_size=block_m,
    )

    # --- Stage 2: CK tile GEMM1 (gate-up projection) ---
    if split_k > 1:
        # Split-K path: use cached buffers
        tmp_out = bufs["tmp_out"]
        out_stage1 = bufs["out_stage1"]

        aiter.moe_cktile2stages_gemm1(
            a1,
            w1,
            tmp_out,
            sorted_ids,
            sorted_expert_ids,
            num_valid_ids,
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
        # No split-K: use cached a2 buffer
        a2 = bufs["a2"]

        aiter.moe_cktile2stages_gemm1(
            a1,
            w1,
            a2,
            sorted_ids,
            sorted_expert_ids,
            num_valid_ids,
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

        # Re-quantize for stage 2
        inter_dim = w2.shape[2]
        if w2.dtype == torch.uint32:
            inter_dim = inter_dim * 8
        a2_flat = a2.reshape(-1, inter_dim)
        a2, a2_scale = fused_dynamic_mxfp4_quant_moe_sort(
            a2_flat,
            sorted_ids=sorted_ids,
            num_valid_ids=num_valid_ids,
            token_num=M,
            topk=topk,
            block_size=block_m,
        )
        a2 = a2.view(M, topk, -1)

    # --- Stage 3: CK tile GEMM2 (down projection) ---
    aiter.moe_cktile2stages_gemm2(
        a2,
        w2,
        moe_buf,
        sorted_ids,
        sorted_expert_ids,
        num_valid_ids,
        topk,
        n_pad_stage2,
        k_pad_stage2,
        sorted_weights,
        a2_scale,
        w2_scale_view,
        None,
        ActivationType.Silu,
        block_m,
    )

    return moe_buf


# ---------------------------------------------------------------------------
# Fallback path (proven fused_moe + adaptive KSPLIT)
# ---------------------------------------------------------------------------
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
    """Proven fused_moe with adaptive KSPLIT from current best."""
    num_experts = w1.shape[0]
    estimated_m = topk_ids.numel() // num_experts

    if estimated_m >= 100:
        ks = "default"
    else:
        ks = "4"

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
            return _direct_dispatch(
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
                print(f"[custom_dispatch] Direct failed, using fallback: {exc}", file=sys.stderr)
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
