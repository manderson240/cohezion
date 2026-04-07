#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA: fmha_v3_varlen_fwd with padded V dimensions.

fmha_v3 requires K_dim == V_dim, but MLA has K_dim=576 and V_dim=512.
Solution: Pad V to match K, run attention, then unpad result.
"""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import torch
import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1
from task import input_t, output_t

NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

_cache: dict = {}


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _einsum_attention(data) -> torch.Tensor:
    """Regime 1: torch.einsum attention for small batches."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    kv = kv_data["bf16"]
    kv_b = kv.view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, nheads, QK_HEAD_DIM)

    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv_b).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv_b[:, :, :V_HEAD_DIM]
    return torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, nheads, V_HEAD_DIM).to(torch.bfloat16)


def _standard_mla(data) -> torch.Tensor:
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
            bs, qseqlen, nq, q_fp8.dtype, kv_fp8.dtype,
            is_sparse=False, fast_mode=False, num_kv_splits=num_splits, intra_batch_mode=True
        )
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, wis, ri, rfm, rpm = work
        get_mla_metadata_v1(
            qo_indptr, kv_indptr, kvl, nq//nkv, nkv, True, wm, wis, wi, ri, rfm, rpm,
            page_size=PAGE_SIZE, kv_granularity=16, max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
            fast_mode=False, max_split_per_batch=num_splits, intra_batch_mode=True,
            dtype_q=q_fp8.dtype, dtype_kv=kv_fp8.dtype
        )
        tq = bs * qseqlen
        tkv = int(kv_indptr[-1].item())
        buf = max(num_splits, 16)
        _cache[key] = {
            "wm": wm, "wi": wi, "wis": wis, "ri": ri, "rfm": rfm, "rpm": rpm,
            "kvi": torch.arange(tkv, dtype=torch.int32, device="cuda"), "kvl": kvl,
            "logits": torch.empty((buf, tq, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda"),
            "lse": torch.empty((buf, tq, nq), dtype=torch.float32, device="cuda"),
            "out": torch.empty((tq, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
        }
    m = _cache[key]

    mla_decode_stage1_asm_fwd = aiter.mla_decode_stage1_asm_fwd
    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM), kv_4d, qo_indptr, kv_indptr,
        m["kvi"], m["kvl"], None, m["wm"], m["wi"], m["wis"],
        qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE, m["logits"], m["lse"], m["out"],
        q_scale=q_scale, kv_scale=kv_scale
    )
    mla_reduce_v1(m["logits"], m["lse"], m["ri"], m["rfm"], m["rpm"], qseqlen, m["out"])
    return m["out"]


def _try_fmha_v3_padded(data) -> torch.Tensor | None:
    """Try fmha_v3_varlen_fwd with padded V dimensions.

    MLA: K uses all 576 dims, V uses only first 512 dims.
    fmha_v3 requires K_dim == V_dim, so we pad V from 512 to 576.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]

    # Use bf16 path for fmha_v3 (more reliable than fp8 for this API)
    kv_buffer = kv_data["bf16"]

    try:
        from aiter import fmha_v3_varlen_fwd

        # Reshape inputs: [total_kv, 1, 576] -> [total_kv, 1, 576] for K
        # For V: pad from 512 to 576 dimensions
        kv_3d = kv_buffer.view(-1, NUM_KV_HEADS, QK_HEAD_DIM)

        # Q: [total_q, nheads, 576]
        total_q = bs * qseqlen
        q_3d = q.view(total_q, NUM_HEADS, QK_HEAD_DIM)

        # K: use all 576 dims from kv_buffer
        k_full = kv_3d  # [total_kv, 1, 576]

        # V: pad from 512 to 576 dims
        # Create padded V buffer [total_kv, 1, 576] with last 64 dims as zeros
        v_padded = torch.zeros(
            (kv_3d.shape[0], NUM_KV_HEADS, QK_HEAD_DIM),
            dtype=kv_buffer.dtype,
            device=kv_buffer.device
        )
        # Copy first V_HEAD_DIM (512) values from kv_buffer
        v_padded[:, :, :V_HEAD_DIM] = kv_3d[:, :, :V_HEAD_DIM]

        # Call fmha_v3_varlen_fwd
        out_tuple = fmha_v3_varlen_fwd(
            q_3d,                  # q [total_q, nheads, 576]
            k_full,                # k [total_kv, nkv, 576]
            v_padded,              # v [total_kv, nkv, 576] (padded from 512)
            qo_indptr,             # cu_seqlens_q
            kv_indptr,             # cu_seqlens_k
            qseqlen,               # max_seqlen_q
            kvseqlen,              # max_seqlen_k
            1,                     # min_seqlen_q
            0.0,                   # dropout_p
            SM_SCALE,              # softmax_scale
            0.0,                   # logits_soft_cap
            False,                 # zero_tensors
            False,                 # is_causal (decode = no causal mask)
            -1,                    # window_size_left
            -1,                    # window_size_right
            False,                 # return_softmax_lse
            False,                 # return_dropout_randval
            0,                     # how_v3_bf16_cvt
        )

        # Result is [total_q, nheads, 576], trim back to [total_q, nheads, 512]
        out = out_tuple[0] if isinstance(out_tuple, tuple) else out_tuple
        return out[:, :, :V_HEAD_DIM].to(torch.bfloat16)

    except Exception as e:
        # Log error for debugging but silently fall back
        return None


def custom_kernel(data: input_t) -> output_t:
    """MLA decode with fmha_v3 padded V fallback.

    Regime 1: torch.einsum for small batches
    Regime 2: fmha_v3_varlen_fwd with padded V (if available)
    Regime 3: Standard 2-dispatch MLA (fallback)
    """
    _, _, _, _, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Regime 1: Einsum for small batches
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Regime 2: Try fmha_v3 with padded V
    result = _try_fmha_v3_padded(data)
    if result is not None:
        return result

    # Regime 3: Standard MLA fallback
    return _standard_mla(data)
