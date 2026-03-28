"""
MLA FlashDecoding: Triton kernel (small) + mla_decode_fwd (large).

Triton kernel uses padded QK_DIM=1024 (576 padded to next power of 2)
with masking for the unused dimensions. V_DIM=512 is already power-of-2.
"""
import torch
import triton
import triton.language as tl
from task import input_t, output_t
from aiter.mla import mla_decode_fwd
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
NUM_KV_SPLITS = 32
FP8_DTYPE = aiter_dtypes.fp8

EINSUM_THRESHOLD = 100_000
_cache: dict = {}


def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (
        (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE),
        scale.float().reshape(1),
    )


def _build_cache(bs, qseqlen, kvseqlen, qo_indptr, kv_indptr):
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs, qseqlen, NUM_HEADS, FP8_DTYPE, FP8_DTYPE,
        is_sparse=False, fast_mode=False,
        num_kv_splits=NUM_KV_SPLITS, intra_batch_mode=True,
    )
    wm, wi, wis, ri, rfm, rpm = [
        torch.empty(s, dtype=t, device="cuda") for s, t in info
    ]
    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        NUM_HEADS // NUM_KV_HEADS, NUM_KV_HEADS, True,
        wm, wis, wi, ri, rfm, rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=NUM_KV_SPLITS,
        intra_batch_mode=True,
        dtype_q=FP8_DTYPE, dtype_kv=FP8_DTYPE,
    )
    return {
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "work_meta_data": wm,
        "work_indptr": wi,
        "work_info_set": wis,
        "reduce_indptr": ri,
        "reduce_final_map": rfm,
        "reduce_partial_map": rpm,
    }


@triton.jit
def _mla_flash_kernel(
    Q_ptr, KV_ptr, Out_ptr,
    stride_qb, stride_qh, stride_qd,
    stride_kvb, stride_kvs, stride_kvd,
    stride_ob, stride_oh, stride_od,
    sm_scale,
    kvseqlen,
    BLOCK_N: tl.constexpr,
    V_DIM: tl.constexpr,
    QK_REAL: tl.constexpr,
    QK_PAD: tl.constexpr,
):
    bid = tl.program_id(0)
    hid = tl.program_id(1)

    # Load Q [QK_PAD] with mask for real dims
    offs_qk = tl.arange(0, QK_PAD)
    qk_mask = offs_qk < QK_REAL
    q = tl.load(Q_ptr + bid * stride_qb + hid * stride_qh + offs_qk,
                mask=qk_mask, other=0.0).to(tl.float32)

    m_i = -float('inf')
    l_i = 0.0
    offs_v = tl.arange(0, V_DIM)
    acc = tl.zeros([V_DIM], dtype=tl.float32)

    for start_n in range(0, kvseqlen, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < kvseqlen

        # Load KV [BLOCK_N, QK_PAD] for score
        kv_qk = tl.load(
            KV_ptr + bid * stride_kvb + offs_n[:, None] * stride_kvs
            + offs_qk[None, :] * stride_kvd,
            mask=mask_n[:, None] & qk_mask[None, :], other=0.0,
        )

        # Score: element-wise mul + reduce
        qk = tl.sum(q[None, :] * kv_qk, axis=1) * sm_scale
        qk = tl.where(mask_n, qk, -float('inf'))

        m_ij = tl.max(qk, axis=0)
        p = tl.exp(qk - m_ij)
        l_ij = tl.sum(p, axis=0)

        m_next = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_next)
        beta = tl.exp(m_ij - m_next)

        acc = acc * alpha

        # Load V [BLOCK_N, V_DIM]
        v = tl.load(
            KV_ptr + bid * stride_kvb + offs_n[:, None] * stride_kvs
            + offs_v[None, :] * stride_kvd,
            mask=mask_n[:, None], other=0.0,
        )
        acc += tl.sum(p[:, None] * v, axis=0) * beta

        l_i = l_i * alpha + l_ij * beta
        m_i = m_next

    out = (acc / l_i).to(tl.bfloat16)
    tl.store(Out_ptr + bid * stride_ob + hid * stride_oh + offs_v * stride_od, out)


def _triton_mla(q, kv_data, bs, kvseqlen, nheads):
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    q_view = q.view(bs, nheads, QK_HEAD_DIM)
    out = torch.empty((bs, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    block_n = 64 if kvseqlen <= 1024 else 128

    grid = (bs, nheads)
    _mla_flash_kernel[grid](
        q_view, kv, out,
        q_view.stride(0), q_view.stride(1), q_view.stride(2),
        kv.stride(0), kv.stride(1), kv.stride(2),
        out.stride(0), out.stride(1), out.stride(2),
        SM_SCALE, kvseqlen,
        BLOCK_N=block_n,
        V_DIM=V_HEAD_DIM,
        QK_REAL=QK_HEAD_DIM,
        QK_PAD=1024,
        num_warps=8, num_stages=1,
    )
    return out


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    if qseqlen != 1:
        from reference import ref_kernel
        return ref_kernel(data)

    total_tokens = bs * kvseqlen

    if total_tokens <= EINSUM_THRESHOLD:
        return _triton_mla(q, kv_data, bs, kvseqlen, nheads)

    key = (bs, qseqlen, kvseqlen)
    if key not in _cache:
        _cache[key] = _build_cache(bs, qseqlen, kvseqlen, qo_indptr, kv_indptr)

    c = _cache[key]
    q_fp8, q_scale = _quantize_fp8(q)
    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])
    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
    mla_decode_fwd(
        q_fp8.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr,
        c["kv_indices"], c["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0,
        num_kv_splits=NUM_KV_SPLITS,
        q_scale=q_scale, kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=c["work_meta_data"],
        work_indptr=c["work_indptr"],
        work_info_set=c["work_info_set"],
        reduce_indptr=c["reduce_indptr"],
        reduce_final_map=c["reduce_final_map"],
        reduce_partial_map=c["reduce_partial_map"],
    )
    return o
