"""MLA decode — CUDA Graph capture + replay to eliminate Python dispatch overhead.

The benchmarking harness records timing events on a specific hipStream_t. All
GPU work must land on that stream. CUDA graphs replay captured ops on the
CURRENT stream (the harness stream), satisfying this requirement.

Two-kernel path (stage1 ASM + reduce_v1) captured in a CUDA graph once per
shape. Replay overhead: ~0.5µs q_copy + near-zero dispatch ≈ 21-25µs total.

Call sequence per shape:
  Call 1 → warmup (normal dispatch, ~70µs)
  Call 2 → capture graph + replay (~70µs, one-time cost)
  Call 3+ → fast: copy q_fp8 + replay graph (~21-25µs)

Address stability requirement for kv_4d / qo_indptr / kv_indptr:
  Benchmark runner reuses the same pre-allocated tensors → addresses stable →
  graph reads current content at the captured address (correct + no copy).
  If addresses change (test mode with fresh allocs) → fallback to normal.

Baseline: ~70µs | Leader: ~33µs | Target: match/beat via graph dispatch.
"""

import torch
from aiter import (
    dtypes as aiter_dtypes,
)
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
from task import input_t, output_t


# ── DeepSeek R1 MLA constants ──
NUM_HEADS = 16
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# ── Routing thresholds ──
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# ── Per-shape caches ──
_meta_cache: dict = {}
_warmup_done: set = set()        # shapes that completed warmup
_graph_cache: dict = {}          # shape_key → graph_info dict  |  False (capture failed)


# ══════════════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════════════

def _choose_num_kv_splits(total_kv: int) -> int:
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE), scale.to(torch.float32).reshape(1)


def _get_meta(
    bs: int, qseqlen: int, kvseqlen: int,
    q_dtype: torch.dtype, kv_dtype: torch.dtype,
    qo_indptr: torch.Tensor, kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key in _meta_cache:
        return _meta_cache[key]

    nq, nkv = NUM_HEADS, NUM_KV_HEADS
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nq, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=False,
        num_kv_splits=num_kv_splits, intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    work_metadata, work_indptr, work_info_set, reduce_indptr, reduce_final_map, reduce_partial_map = work

    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nq // nkv, nkv, True,
        work_metadata, work_info_set, work_indptr,
        reduce_indptr, reduce_final_map, reduce_partial_map,
        page_size=PAGE_SIZE, kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=False, max_split_per_batch=num_kv_splits,
        intra_batch_mode=True, dtype_q=q_dtype, dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    total_q = bs * qseqlen
    meta = {
        "kv_indices":         torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len":   kv_last_page_len,
        "work_meta_data":     work_metadata,
        "work_indptr":        work_indptr,
        "work_info_set":      work_info_set,
        "reduce_indptr":      reduce_indptr,
        "reduce_final_map":   reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "logits":   torch.empty((num_kv_splits, total_q, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda"),
        "attn_lse": torch.empty((num_kv_splits, total_q, nq), dtype=torch.float32, device="cuda"),
        "output":   torch.empty((total_q, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
    }
    _meta_cache[key] = meta
    return meta


def _normal_dispatch(
    q_fp8_3d: torch.Tensor,
    kv_4d: torch.Tensor,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    meta: dict,
    q_scale: torch.Tensor,
    kv_scale: torch.Tensor,
    qseqlen: int,
    num_kv_splits: int,
) -> None:
    """Python-dispatch path: two kernel calls, ~40-50µs Python overhead total."""
    mla_decode_stage1_asm_fwd(
        q_fp8_3d, kv_4d, qo_indptr, kv_indptr,
        meta["kv_indices"], meta["kv_last_page_len"],
        None,                                            # num_kv_splits_indptr
        meta["work_meta_data"], meta["work_indptr"], meta["work_info_set"],
        qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
        meta["logits"], meta["attn_lse"], meta["output"],
        q_scale, kv_scale,
    )
    mla_reduce_v1(
        meta["logits"], meta["attn_lse"],
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_partial_map"],
        qseqlen, meta["output"], None,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs       = config["batch_size"]
    qseqlen  = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # ── Regime 1: torch.matmul for small shapes ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv_bf16 = kv_data["bf16"]
        q_3d    = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
        kv_per  = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)
        scores  = torch.matmul(q_3d, kv_per.transpose(1, 2)).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        return torch.matmul(weights, kv_per[:, :, :V_HEAD_DIM]).view(bs * qseqlen, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2+3: ASM kernel via CUDA graph (or fallback) ──
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)
    meta = _get_meta(
        bs, qseqlen, kvseqlen,
        q_fp8.dtype, kv_buffer_fp8.dtype,
        qo_indptr, kv_indptr, num_kv_splits,
    )
    q_fp8_3d  = q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM)
    shape_key = (bs, qseqlen, kvseqlen, num_kv_splits)

    gi = _graph_cache.get(shape_key)

    # ── Fast path: graph already captured ──
    if gi is not None and gi is not False:
        if (kv_4d.data_ptr()      == gi["kv_ptr"]
                and qo_indptr.data_ptr() == gi["qo_ptr"]
                and kv_indptr.data_ptr() == gi["ki_ptr"]):
            # Address-stable: copy only q_fp8 (~288KB ≈ 0.5µs), then replay
            gi["sq"].copy_(q_fp8_3d)
            gi["sqs"].copy_(q_scale)
            gi["sks"].copy_(kv_scale)
            gi["graph"].replay()
            return meta["output"]
        # Addresses changed (test mode diff allocs) → fall through to normal
        _normal_dispatch(q_fp8_3d, kv_4d, qo_indptr, kv_indptr, meta, q_scale, kv_scale, qseqlen, num_kv_splits)
        return meta["output"]

    # ── Graph already attempted but failed ──
    if gi is False:
        _normal_dispatch(q_fp8_3d, kv_4d, qo_indptr, kv_indptr, meta, q_scale, kv_scale, qseqlen, num_kv_splits)
        return meta["output"]

    # ── Warmup call (first time for this shape) ──
    if shape_key not in _warmup_done:
        _warmup_done.add(shape_key)
        _normal_dispatch(q_fp8_3d, kv_4d, qo_indptr, kv_indptr, meta, q_scale, kv_scale, qseqlen, num_kv_splits)
        return meta["output"]

    # ── Second call: capture CUDA graph ──
    # Pre-allocate static q tensors — content updated before every replay
    static_q  = q_fp8_3d.clone()    # same shape, fp8, fixed address
    static_qs = q_scale.clone()     # (1,) float32
    static_ks = kv_scale.clone()    # (1,) float32

    # Copy current values so graph capture AND first replay use correct data
    static_q.copy_(q_fp8_3d)
    static_qs.copy_(q_scale)
    static_ks.copy_(kv_scale)

    try:
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g):
            # kv_4d, qo_indptr, kv_indptr are captured at their current addresses.
            # Benchmark runner reuses the same tensor objects every call →
            # replay reads fresh content from stable addresses.
            _normal_dispatch(
                static_q, kv_4d, qo_indptr, kv_indptr,
                meta, static_qs, static_ks,
                qseqlen, num_kv_splits,
            )

        # Execute the captured graph to produce this call's result
        g.replay()

        _graph_cache[shape_key] = {
            "graph": g,
            "sq":    static_q,
            "sqs":   static_qs,
            "sks":   static_ks,
            "kv_ptr": kv_4d.data_ptr(),
            "qo_ptr": qo_indptr.data_ptr(),
            "ki_ptr": kv_indptr.data_ptr(),
        }

    except Exception:
        # Graph capture failed (e.g. aiter has CPU-GPU sync) → always use normal
        _graph_cache[shape_key] = False
        _normal_dispatch(q_fp8_3d, kv_4d, qo_indptr, kv_indptr, meta, q_scale, kv_scale, qseqlen, num_kv_splits)

    return meta["output"]
