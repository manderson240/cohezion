#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA: Try fmha_v3_varlen_fwd (FlashMHA v3) — discovered on runner via probe.
This might be a single-dispatch attention that eliminates the 2-dispatch overhead.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import aiter
import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

_cache = {}


def _quantize_fp8(t):
    fi = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    sc = amax / fi.max
    return (t / sc).clamp(fi.min, fi.max).to(FP8_DTYPE), sc.float().reshape(1)


def _einsum_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, nheads, QK_HEAD_DIM)
    sc = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    w = torch.softmax(sc, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return torch.einsum("bnqs,bsd->bqnd", w, v).reshape(-1, nheads, V_HEAD_DIM).to(torch.bfloat16)


def _try_fmha_v3(data):
    """Try fmha_v3_varlen_fwd — single-dispatch FlashMHA v3."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]

    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    # fmha_v3_varlen_fwd: full FlashAttention API
    # Sig: fmha_v3_varlen_fwd(q, k, v, cu_seqlens_q, cu_seqlens_k,
    #   max_seqlen_q, max_seqlen_k, min_seqlen_q,
    #   dropout_p, softmax_scale, logits_soft_cap,
    #   zero_tensors, is_causal,
    #   window_size_left, window_size_right,
    #   return_softmax_lse, return_dropout_randval,
    #   how_v3_bf16_cvt, ...)
    try:
        from aiter import fmha_v3_varlen_fwd

        # For MLA decode: Q is [total_q, nheads, qk_dim], K/V from fused KV buffer
        # K and V have DIFFERENT dims: K=576, V=512. fmha_v3 expects K_dim == V_dim.
        # Pad V to 576 or use only 512 dims of K.
        kv_buf = kv_fp8.view(kv_fp8.shape[0], NUM_KV_HEADS, QK_HEAD_DIM)
        q_3d = q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM)

        # Use full 576-dim for both K and V (pad V with zeros)
        k_full = kv_buf  # [total_kv, 1, 576]
        v_padded = torch.zeros_like(kv_buf)
        v_padded[:, :, :V_HEAD_DIM] = kv_buf[:, :, :V_HEAD_DIM]

        out_tuple = fmha_v3_varlen_fwd(
            q_3d,  # q [total_q, nheads, 576]
            k_full,  # k [total_kv, nkv, 576]
            v_padded,  # v [total_kv, nkv, 576] (padded)
            qo_indptr,  # cu_seqlens_q
            kv_indptr,  # cu_seqlens_k
            qseqlen,  # max_seqlen_q
            kvseqlen,  # max_seqlen_k
            1,  # min_seqlen_q
            0.0,  # dropout_p
            SM_SCALE,  # softmax_scale
            0.0,  # logits_soft_cap
            False,  # zero_tensors
            False,  # is_causal (decode = no causal mask)
            -1,  # window_size_left
            -1,  # window_size_right
            False,  # return_softmax_lse
            False,  # return_dropout_randval
            0,  # how_v3_bf16_cvt
            None,  # out
            None,  # block_table
            None,  # bias
            None,  # alibi_slopes
            q_scale,  # q_descale (FP8 scale)
            kv_scale,  # k_descale (FP8 scale)
            kv_scale,  # v_descale (FP8 scale, same as K)
        )
        # Result is tuple (out, ...), take first element and trim V padding
        out = out_tuple[0]  # [total_q, nheads, 576]
        return out[:, :, :V_HEAD_DIM].to(torch.bfloat16)
    except Exception as e:
        print(f"[fmha_v3] Error: {e}")
        return None


def _standard_mla(data):
    """Standard 2-dispatch MLA (fallback)."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_splits = 16 if total_kv > 16384 else 8 if total_kv > 2048 else 4
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_fp8.dtype, num_splits)
    if key not in _cache:
        nq, nkv = NUM_HEADS, NUM_KV_HEADS
        kvl = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(
            bs,
            qseqlen,
            nq,
            q_fp8.dtype,
            kv_fp8.dtype,
            is_sparse=False,
            fast_mode=False,
            num_kv_splits=num_splits,
            intra_batch_mode=True,
        )
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, wis, ri, rfm, rpm = work
        get_mla_metadata_v1(
            qo_indptr,
            kv_indptr,
            kvl,
            nq // nkv,
            nkv,
            True,
            wm,
            wis,
            wi,
            ri,
            rfm,
            rpm,
            page_size=PAGE_SIZE,
            kv_granularity=16,
            max_seqlen_qo=qseqlen,
            uni_seqlen_qo=qseqlen,
            fast_mode=False,
            max_split_per_batch=num_splits,
            intra_batch_mode=True,
            dtype_q=q_fp8.dtype,
            dtype_kv=kv_fp8.dtype,
        )
        tq = bs * qseqlen
        tkv = int(kv_indptr[-1].item())
        buf = max(num_splits, 16)
        _cache[key] = {
            "wm": wm,
            "wi": wi,
            "wis": wis,
            "ri": ri,
            "rfm": rfm,
            "rpm": rpm,
            "kvi": torch.arange(tkv, dtype=torch.int32, device="cuda"),
            "kvl": kvl,
            "logits": torch.empty((buf, tq, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda"),
            "lse": torch.empty((buf, tq, nq), dtype=torch.float32, device="cuda"),
            "out": torch.empty((tq, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
        }
    m = _cache[key]

    mla_decode_stage1_asm_fwd = aiter.mla_decode_stage1_asm_fwd  # top-level, not in aiter.mla
    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        m["kvi"],
        m["kvl"],
        None,
        m["wm"],
        m["wi"],
        m["wis"],
        qseqlen,
        PAGE_SIZE,
        NUM_KV_HEADS,
        SM_SCALE,
        m["logits"],
        m["lse"],
        m["out"],
        q_scale=q_scale,
        kv_scale=kv_scale,
    )
    mla_reduce_v1(m["logits"], m["lse"], m["ri"], m["rfm"], m["rpm"], qseqlen, m["out"])
    return m["out"]


def custom_kernel(data):
    _, _, _, _, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Try fmha_v3 first
    result = _try_fmha_v3(data)
    if result is not None:
        return result

    return _standard_mla(data)
