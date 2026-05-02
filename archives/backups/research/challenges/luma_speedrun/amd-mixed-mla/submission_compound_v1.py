#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Compound MLA v1: Phase 17 configuration with maximum hot-path reduction.

Combines all proven optimizations into a single submission:
1. OR routing: einsum for bs<=4 OR total_kv<=32768 (empirically optimal, Phase 11)
2. fast_mode=False + direct ASM dispatch: mla_decode_stage1_asm_fwd + mla_reduce_v1
   (fast_mode=False is counter-intuitively faster on MI355X, Phase 17)
3. Aggressive metadata + pre-allocated buffer caching (Phase 10)
4. Pre-resolved function references stored at module level (no per-call attribute lookup)
5. Adaptive num_kv_splits schedule tuned for MI355X 304-CU topology
6. All intermediate tensors (logits, attn_lse, output) pre-allocated in cache

Best known pure-Python geomean: ~67.8µs (Phase 17).
Leader: 33.0µs — gap requires single fused CK kernel (blocked by runner scanner).
"""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# OR routing thresholds: capture both failure modes for aiter
#   bs<=4:          aiter can't fill 304 CUs — pipeline overhead > compute
#   total_kv<=32768: aiter fixed overhead (~50µs) > einsum even at bs=32
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# ─── Pre-resolved function references (eliminate per-call attribute lookup) ───
_stage1_fn = mla_decode_stage1_asm_fwd
_reduce_fn = mla_reduce_v1
_finfo = torch.finfo(FP8_DTYPE)
_fp8_min = _finfo.min
_fp8_max = _finfo.max

# ─── Metadata + scratch buffer cache ─────────────────────────────────────────
_meta_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    """Adaptive split schedule tuned for ranked shapes on MI355X (304 CUs).

    Validated schedule from Phase 11 — do not modify without re-benchmarking.
    """
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _build_meta(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    q_dtype,
    kv_dtype,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    """Build metadata and pre-allocate all scratch buffers for one shape config."""
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        q_dtype,
        kv_dtype,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=num_kv_splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    wm, wi, wis, ri, rfm, rpm = work

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        NUM_HEADS // NUM_KV_HEADS,
        NUM_KV_HEADS,
        True,
        wm,
        wis,
        wi,
        ri,
        rfm,
        rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype,
        dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    total_q = bs * qseqlen
    return {
        "wm": wm,
        "wi": wi,
        "wis": wis,
        "ri": ri,
        "rfm": rfm,
        "rpm": rpm,
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len": kv_last_page_len,
        "logits": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.float32,
            device="cuda",
        ),
        "attn_lse": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS),
            dtype=torch.float32,
            device="cuda",
        ),
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }


def _get_cached_meta(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    q_dtype,
    kv_dtype,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key not in _meta_cache:
        _meta_cache[key] = _build_meta(
            bs,
            qseqlen,
            kvseqlen,
            q_dtype,
            kv_dtype,
            qo_indptr,
            kv_indptr,
            num_kv_splits,
        )
    return _meta_cache[key]


def _quantize_fp8(t: torch.Tensor):
    """Dynamic per-tensor FP8 quantization (sglang style)."""
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / _fp8_max
    fp8 = (t / scale).clamp(min=_fp8_min, max=_fp8_max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _einsum_attention(data: input_t) -> torch.Tensor:
    """Batch-matmul attention path: fastest for small bs or small total_kv."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _asm_attention(data: input_t) -> torch.Tensor:
    """Direct ASM path for large shapes: fast_mode=False is empirically faster."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_meta(
        bs,
        qseqlen,
        kvseqlen,
        q_fp8.dtype,
        kv_buffer_fp8.dtype,
        qo_indptr,
        kv_indptr,
        num_kv_splits,
    )

    _stage1_fn(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        None,
        meta["wm"],
        meta["wi"],
        meta["wis"],
        qseqlen,
        PAGE_SIZE,
        NUM_KV_HEADS,
        SM_SCALE,
        meta["logits"],
        meta["attn_lse"],
        meta["output"],
        q_scale,
        kv_scale,
    )
    _reduce_fn(
        meta["logits"],
        meta["attn_lse"],
        meta["ri"],
        meta["rfm"],
        meta["rpm"],
        qseqlen,
        meta["output"],
        None,
    )
    return meta["output"]


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # OR routing: einsum wins for small batch OR small KV sequence
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    return _asm_attention(data)
