#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA Breakthrough: MXFP4 KV Cache Implementation.

Based on official spec:
- KV cache in mxfp4 format: (kv_buffer fp4x2, fp8_e8m0 scale)
- 4x bandwidth savings over BF16.
- Uses aiter mla_decode_fwd with MXFP4 inputs.
"""

import torch
import aiter
from aiter.mla import mla_decode_fwd
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from task import input_t, output_t

# Architecture Constants
NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

_METADATA_CACHE = {}

def _get_cached_metadata(bs, qsl, kvsl, q_dtype, kv_dtype, qo_indptr, kv_indptr, num_splits):
    key = (bs, qsl, kvsl, q_dtype, kv_dtype, num_splits)
    if key in _METADATA_CACHE: return _METADATA_CACHE[key]
    
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(bs, qsl, NUM_HEADS, q_dtype, kv_dtype, 
                                    is_sparse=False, fast_mode=True, 
                                    num_kv_splits=num_splits, intra_batch_mode=True)
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    (wm, wi, wis, ri, rfm, rpm) = work
    
    get_mla_metadata_v1(qo_indptr, kv_indptr, kv_last_page_len, NUM_HEADS, NUM_KV_HEADS, True,
                        wm, wis, wi, ri, rfm, rpm,
                        page_size=PAGE_SIZE, kv_granularity=16,
                        max_seqlen_qo=qsl, uni_seqlen_qo=qsl,
                        fast_mode=True, max_split_per_batch=num_splits,
                        intra_batch_mode=True, dtype_q=q_dtype, dtype_kv=kv_dtype)
    
    meta = {"wm": wm, "wi": wi, "wis": wis, "ri": ri, "rfm": rfm, "rpm": rpm, "kv_lpl": kv_last_page_len}
    _METADATA_CACHE[key] = meta
    return meta

def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    scale = tensor.abs().amax().clamp(min=1e-12) / finfo.max
    return (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE), scale.float().reshape(1)

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs, qsl, kvsl = config["batch_size"], config["q_seq_len"], config["kv_seq_len"]
    total_q = q.shape[0]
    
    # 1. Use the requested MXFP4 KV cache
    # kv_data["mxfp4"] is (kv_buffer fp4x2, fp8_e8m0 scale)
    kv_buffer, kv_scale = kv_data["mxfp4"]
    
    # 2. Quantize Q to FP8 (as the reference does)
    q_fp8, q_scale = _quantize_fp8(q)
    
    # 3. Reshape KV to 4D for aiter
    # [total_kv, 1, 576] -> [total_kv, page_size, nhead_kv, dim]
    kv_buffer_4d = kv_buffer.view(-1, 1, 1, 576)
    
    # 4. Metadata with Split-K
    total_kv = bs * kvsl
    num_splits = 16 if total_kv > 16384 else 8 if total_kv > 4096 else 4
    meta = _get_cached_metadata(bs, qsl, kvsl, q_fp8.dtype, kv_buffer.dtype, qo_indptr, kv_indptr, num_splits)
    
    # 5. Output Buffer
    out = torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
    
    # 6. Execute mla_decode_fwd
    kv_indices = torch.arange(kv_buffer.shape[0], dtype=torch.int32, device="cuda")
    
    mla_decode_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_buffer_4d,
        out,
        qo_indptr,
        kv_indptr,
        kv_indices,
        meta["kv_lpl"],
        qsl,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_splits,
        q_scale=q_scale,
        kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=meta["wm"],
        work_indptr=meta["wi"],
        work_info_set=meta["wis"],
        reduce_indptr=meta["ri"],
        reduce_final_map=meta["rfm"],
        reduce_partial_map=meta["rpm"]
    )
    
    return out
