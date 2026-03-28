"""
MLA decode: SDPA for small shapes, aiter fp8 for large.

Hypothesis: F.scaled_dot_product_attention fuses score+softmax+value into
a SINGLE C++ dispatch. Even if it falls back to math backend, this eliminates
3-4 Python op dispatches (2x matmul + softmax + scale).

For MLA with K_dim=576 and V_dim=512: pad V to 576, trim output.
"""
import torch
import torch.nn.functional as F
from task import input_t, output_t
from aiter.mla import mla_decode_fwd
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

EINSUM_THRESHOLD = 131072

_cache: dict = {}


def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (
        (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE),
        scale.float().reshape(1),
    )


def _build_cache(bs, qseqlen, kvseqlen, nheads, num_kv_splits,
                 qo_indptr, kv_indptr):
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    q_dtype = FP8_DTYPE
    kv_dtype = FP8_DTYPE

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nheads, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=False,
        num_kv_splits=num_kv_splits, intra_batch_mode=True,
    )
    wm, wi, wis, ri, rfm, rpm = [
        torch.empty(s, dtype=t, device="cuda") for s, t in info
    ]
    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nheads // NUM_KV_HEADS, NUM_KV_HEADS, True,
        wm, wis, wi, ri, rfm, rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype, dtype_kv=kv_dtype,
    )
    return {
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "work_meta_data": wm, "work_indptr": wi, "work_info_set": wis,
        "reduce_indptr": ri, "reduce_final_map": rfm, "reduce_partial_map": rpm,
    }


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    total_kv = bs * kvseqlen

    # Regime 1: SDPA — fused score+softmax+value in single dispatch
    if total_kv <= EINSUM_THRESHOLD:
        kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)

        # Q: [bs, nheads, qseqlen, 576]
        q_sdpa = q.view(bs, qseqlen, nheads, QK_HEAD_DIM).permute(0, 2, 1, 3)

        # K: [bs, 1, kvseqlen, 576] — broadcast for MQA
        k_sdpa = kv.unsqueeze(1)

        # V: [bs, 1, kvseqlen, 576] — pad from 512 to 576
        v_padded = F.pad(kv[:, :, :V_HEAD_DIM], (0, QK_HEAD_DIM - V_HEAD_DIM))
        v_sdpa = v_padded.unsqueeze(1)

        # Fused attention: [bs, nheads, qseqlen, 576]
        out = F.scaled_dot_product_attention(
            q_sdpa, k_sdpa, v_sdpa, scale=SM_SCALE,
        )

        # Trim padding and reshape: [bs, nheads, qseqlen, 512] -> [total_q, nheads, 512]
        return out[:, :, :, :V_HEAD_DIM].permute(0, 2, 1, 3).reshape(-1, nheads, V_HEAD_DIM)

    # Regime 2: aiter a8w8
    num_kv_splits = 32

    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    q_input, q_scale = _quantize_fp8(q)

    key = (bs, qseqlen, kvseqlen, nheads, num_kv_splits)
    if key not in _cache:
        _cache[key] = _build_cache(
            bs, qseqlen, kvseqlen, nheads, num_kv_splits,
            qo_indptr, kv_indptr,
        )
    c = _cache[key]

    o = torch.empty(
        (q.shape[0], nheads, V_HEAD_DIM),
        dtype=torch.bfloat16, device="cuda",
    )

    mla_decode_fwd(
        q_input.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr,
        c["kv_indices"], c["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0,
        num_kv_splits=num_kv_splits,
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
