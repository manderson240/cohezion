"""
MLA decode — three-regime routing with direct ASM dispatch + fast_mode=False.

Phase 17 best: ~67.8µs ranked geomean.
1. Small (bs<=4 OR total_kv<=32768): torch.matmul 3D bf16
2. Medium (total_kv<=262144): aiter a16w8 direct ASM, adaptive splits
3. Large (total_kv>262144): aiter a8w8 direct ASM, high splits
"""
import os

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
A16W8_THRESHOLD = 262144

_cache: dict = {}
_out_cache: dict = {}
_f1 = _f2 = None


def _ensure_asm():
    global _f1, _f2
    if _f1:
        return
    try:
        from aiter.mla import mla_decode_stage1_asm_fwd, mla_reduce_v1
        _f1, _f2 = mla_decode_stage1_asm_fwd, mla_reduce_v1
    except ImportError:
        import aiter
        _f1 = getattr(aiter, "mla_decode_stage1_asm_fwd", None)
        _f2 = getattr(aiter, "mla_reduce_v1", None)


def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (
        (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE),
        scale.float().reshape(1),
    )


def _choose_splits(total_kv):
    if total_kv <= 2048:    return 1
    if total_kv <= 16384:   return 4
    if total_kv <= 131072:  return 8
    if total_kv <= 524288:  return 16
    return 32


def _build_metadata(bs, qseqlen, nheads, q_dtype, kv_dtype, num_splits, qo_indptr, kv_indptr, kvseqlen):
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nheads, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=False,
        num_kv_splits=num_splits, intra_batch_mode=True,
    )
    wm, wi, wis, ri, rfm, rpm = [
        torch.empty(s, dtype=t, device="cuda") for s, t in info
    ]
    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nheads // NUM_KV_HEADS, NUM_KV_HEADS, True,
        wm, wis, wi, ri, rfm, rpm,
        page_size=PAGE_SIZE, kv_granularity=16,
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype, dtype_kv=kv_dtype,
    )

    buf_ns = max(num_splits, 16)
    logits = torch.empty((bs, buf_ns, nheads, 520), dtype=torch.float32, device="cuda")
    attn_lse = torch.empty((bs, buf_ns, nheads), dtype=torch.float32, device="cuda")

    return {
        "kv_indices": kv_indices, "kv_last_page_len": kv_last_page_len,
        "wm": wm, "wi": wi, "wis": wis,
        "ri": ri, "rfm": rfm, "rpm": rpm,
        "logits": logits, "attn_lse": attn_lse,
        "num_splits": num_splits,
    }


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    total_q = q.shape[0]
    qseqlen = total_q // bs
    total_kv = bs * kvseqlen

    # Regime 1: Small batch — einsum bf16 (bypasses aiter pipeline overhead)
    # OR logic: captures both low-bs AND low-total_kv failure modes
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
        q_r = q.view(bs, qseqlen, nheads, QK_HEAD_DIM)
        scores = torch.einsum("bqnh,bsh->bnqs", q_r, kv).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v = kv[:, :, :V_HEAD_DIM]
        out = torch.einsum("bnqs,bsd->bqnd", weights, v)
        return out.reshape(-1, nheads, V_HEAD_DIM).to(torch.bfloat16)

    # Regime 2/3: Direct ASM dispatch
    _ensure_asm()

    use_a16w8 = total_kv <= A16W8_THRESHOLD
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

    key = (bs, qseqlen, kvseqlen, nheads, use_a16w8, num_splits)
    if key not in _cache:
        _cache[key] = _build_metadata(
            bs, qseqlen, nheads, q_dtype, FP8_DTYPE,
            num_splits, qo_indptr, kv_indptr, kvseqlen,
        )
    c = _cache[key]

    ok = (total_q, nheads)
    if ok not in _out_cache:
        _out_cache[ok] = torch.empty((total_q, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
    o = _out_cache[ok]

    if _f1 and _f2:
        _f1(
            q_input.view(-1, nheads, QK_HEAD_DIM), kv_4d,
            qo_indptr, kv_indptr,
            c["kv_indices"], c["kv_last_page_len"],
            None, c["wm"], c["wi"], c["wis"],
            qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
            c["logits"], c["attn_lse"], o,
            q_scale=q_scale, kv_scale=kv_scale,
        )
        _f2(c["logits"], c["attn_lse"], c["ri"], c["rfm"], c["rpm"], qseqlen, o)
        return o

    # Fallback: mla_decode_fwd wrapper
    from aiter.mla import mla_decode_fwd
    mla_decode_fwd(
        q_input.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr,
        c["kv_indices"], c["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0,
        num_kv_splits=num_splits,
        q_scale=q_scale, kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=c["wm"], work_indptr=c["wi"],
        work_info_set=c["wis"],
        reduce_indptr=c["ri"], reduce_final_map=c["rfm"],
        reduce_partial_map=c["rpm"],
    )
    return o
