"""
MLA (Multi-head Latent Attention) decode kernel — persistent-mode optimized.

Phase 18: Pre-allocated persistent metadata + direct ASM dispatch.
Target: <35µs (Rank 1 is 32.972µs)

Key optimizations:
1. Pre-compute metadata once per shape, reuse buffers
2. Use persistent scheduling (ps=1) via proper metadata construction
3. Direct ASM dispatch - bypasses Python wrapper overhead

DeepSeek R1 forward_absorb MLA config:
  total_num_heads  = 128    (query heads before TP split)
  num_heads        = 128 // tp  (query heads per device, tp=4 → 32, tp=8 → 16)
  num_kv_heads     = 1      (shared latent KV head)
  kv_lora_rank     = 512    (latent dim)
  qk_rope_head_dim = 64     (RoPE dim)
  qk_head_dim      = 576    (kv_lora_rank + qk_rope_head_dim, absorbed q/k dim)
  v_head_dim       = 512    (= kv_lora_rank, output dim)
  sm_scale         = 1/sqrt(576)
"""

from __future__ import annotations

import os
from typing import Any

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"

# DeepSeek R1 MLA constants
SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Regime boundaries
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
A16W8_THRESHOLD = 262144

# Persistent kernel configuration
PERSISTENT_SPLITS = 16  # Match AITER_KSPLIT for persistent scheduling

# Caching for metadata and output buffers
_metadata_cache: dict[str, dict[str, Any]] = {}
_out_cache: dict[tuple[int, int], torch.Tensor] = {}

# ASM function references (loaded lazily)
_asm_stage1 = None
_asm_reduce = None


def _ensure_asm() -> None:
    """Load ASM functions lazily to avoid import overhead."""
    global _asm_stage1, _asm_reduce
    if _asm_stage1 is not None:
        return
    try:
        from aiter.mla import mla_decode_stage1_asm_fwd, mla_reduce_v1

        _asm_stage1 = mla_decode_stage1_asm_fwd
        _asm_reduce = mla_reduce_v1
    except ImportError:
        import aiter

        _asm_stage1 = getattr(aiter, "mla_decode_stage1_asm_fwd", None)
        _asm_reduce = getattr(aiter, "mla_reduce_v1", None)


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization (sglang style)."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (
        (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE),
        scale.float().reshape(1),
    )


def _choose_splits(total_kv: int) -> int:
    """Choose optimal KV split count for persistent scheduling."""
    # Persistent mode needs enough splits to keep GPU busy
    if total_kv <= 2048:
        return 4
    if total_kv <= 16384:
        return 8
    if total_kv <= 131072:
        return 16
    if total_kv <= 524288:
        return 16
    return 16  # Cap at 16 for persistent scheduling


def _build_metadata(
    bs: int,
    qseqlen: int,
    nheads: int,
    q_dtype: torch.dtype,
    kv_dtype: torch.dtype,
    num_splits: int,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    kvseqlen: int,
) -> dict[str, Any]:
    """Build MLA decode metadata buffers for ASM dispatch."""
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    # Get metadata info and allocate buffers
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        nheads,
        q_dtype,
        kv_dtype,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=num_splits,
        intra_batch_mode=True,
    )
    (work_meta_data, work_indptr, work_info_set, reduce_indptr, reduce_final_map, reduce_partial_map) = [
        torch.empty(s, dtype=t, device="cuda") for s, t in info
    ]

    # Populate metadata
    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        nheads // NUM_KV_HEADS,
        NUM_KV_HEADS,
        True,  # is_causal=True
        work_meta_data,
        work_info_set,
        work_indptr,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
        page_size=PAGE_SIZE,
        kv_granularity=16,
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype,
        dtype_kv=kv_dtype,
    )

    # Allocate output buffers for logits and LSE
    buf_ns = max(num_splits, 16)
    logits = torch.empty(
        (bs, buf_ns, nheads, 520), dtype=torch.float32, device="cuda"
    )
    attn_lse = torch.empty((bs, buf_ns, nheads), dtype=torch.float32, device="cuda")

    return {
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "wm": work_meta_data,
        "wi": work_indptr,
        "wis": work_info_set,
        "ri": reduce_indptr,
        "rfm": reduce_final_map,
        "rpm": reduce_partial_map,
        "logits": logits,
        "attn_lse": attn_lse,
        "num_splits": num_splits,
    }


# ---------------------------------------------------------------------------
# Regime 1: torch.einsum for small shapes
# ---------------------------------------------------------------------------


def _einsum_attention(data: input_t) -> output_t:
    """Einsum-based attention for small batch sizes.

    Uses torch.einsum with 3D tensors to bypass aiter dispatch overhead.
    Optimal for bs<=4 or total_kv<=32768.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    q_r = q.view(bs, 1, nheads, QK_HEAD_DIM)  # q_seqlen=1 for decode

    # QK^T: (batch, q_seqlen=1, nheads, head_dim) @ (batch, kv_seqlen, head_dim)
    # -> (batch, nheads, 1, kv_seqlen)
    scores = torch.einsum("bqnh,bsh->bnqs", q_r, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)

    # V: use first V_HEAD_DIM of KV
    v = kv[:, :, :V_HEAD_DIM]  # (bs, kvseqlen, 512)
    out = torch.einsum("bnqs,bsd->bqnd", weights, v)

    return out.reshape(-1, nheads, V_HEAD_DIM).to(torch.bfloat16)


# ---------------------------------------------------------------------------
# Regime 2/3: Direct ASM dispatch with persistent mode
# ---------------------------------------------------------------------------


def _asm_attention(data: input_t, use_a16w8: bool) -> output_t:
    """Direct ASM dispatch to aiter MLA kernel with persistent optimization.

    Args:
        data: Input tuple (q, kv_data, qo_indptr, kv_indptr, config)
        use_a16w8: If True, use bf16 Q + fp8 KV (better accuracy at medium sizes)
                   If False, use fp8 Q + fp8 KV (maximum bandwidth savings)
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    total_q = q.shape[0]
    qseqlen = total_q // bs
    total_kv = bs * kvseqlen

    _ensure_asm()

    num_splits = _choose_splits(total_kv)
    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    if use_a16w8:
        q_input = q
        q_scale = None
        q_dtype = torch.bfloat16
    else:
        q_input, q_scale = _quantize_fp8(q)
        q_dtype = FP8_DTYPE

    # Build or retrieve cached metadata
    key = (bs, qseqlen, kvseqlen, nheads, use_a16w8, num_splits)
    if key not in _metadata_cache:
        _metadata_cache[key] = _build_metadata(
            bs,
            qseqlen,
            nheads,
            q_dtype,
            FP8_DTYPE,
            num_splits,
            qo_indptr,
            kv_indptr,
            kvseqlen,
        )
    c = _metadata_cache[key]

    # Reuse output buffer if shape matches
    ok = (total_q, nheads)
    if ok not in _out_cache:
        _out_cache[ok] = torch.empty(
            (total_q, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"
        )
    o = _out_cache[ok]

    # Try direct ASM dispatch with persistent mode
    if _asm_stage1 and _asm_reduce:
        # Dispatch stage1 with persistent scheduling
        # Passing None for num_kv_splits_indptr triggers persistent mode (ps=1)
        # The C++ code will allocate PS_META_BUFFER internally if work_meta_data is null
        _asm_stage1(
            q_input.view(-1, nheads, QK_HEAD_DIM),
            kv_4d,
            qo_indptr,
            kv_indptr,
            c["kv_indices"],
            c["kv_last_page_len"],
            None,  # v is in kv_4d
            c["wm"],  # work_meta_data - C++ will allocate persistent buffer if needed
            c["wi"],
            c["wis"],
            qseqlen,
            PAGE_SIZE,
            NUM_KV_HEADS,
            SM_SCALE,
            c["logits"],
            c["attn_lse"],
            o,
            q_scale=q_scale,
            kv_scale=kv_scale,
        )
        _asm_reduce(
            c["logits"],
            c["attn_lse"],
            c["ri"],
            c["rfm"],
            c["rpm"],
            qseqlen,
            o,
        )
        return o

    # Fallback to mla_decode_fwd wrapper
    from aiter.mla import mla_decode_fwd

    mla_decode_fwd(
        q_input.view(-1, nheads, QK_HEAD_DIM),
        kv_4d,
        o,
        qo_indptr,
        kv_indptr,
        c["kv_indices"],
        c["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_splits,
        q_scale=q_scale,
        kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=c["wm"],
        work_indptr=c["wi"],
        work_info_set=c["wis"],
        reduce_indptr=c["ri"],
        reduce_final_map=c["rfm"],
        reduce_partial_map=c["rpm"],
    )
    return o


# ---------------------------------------------------------------------------
# Main dispatcher: three-regime routing
# ---------------------------------------------------------------------------


def custom_kernel(data: input_t) -> output_t:
    """Three-regime MLA attention dispatch with persistent mode optimization.

    Regime 1 (bs<=4 OR total_kv<=32768):
        torch.einsum bf16 attention — bypasses aiter dispatch overhead

    Regime 2 (total_kv<=262144):
        aiter a16w8 direct ASM — bf16 Q + fp8 KV for medium sizes

    Regime 3 (total_kv>262144):
        aiter a8w8 direct ASM — fp8 Q + fp8 KV for large sizes
    """
    _, _, _, _, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Regime 1: Small batch — einsum bf16
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Regime 2: Medium — a16w8 (bf16 Q + fp8 KV)
    if total_kv <= A16W8_THRESHOLD:
        return _asm_attention(data, use_a16w8=True)

    # Regime 3: Large — a8w8 (fp8 Q + fp8 KV)
    return _asm_attention(data, use_a16w8=False)
