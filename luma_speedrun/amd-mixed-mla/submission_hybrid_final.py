#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA Final Push: Hybrid BF16/ASM Strategy.
- Uses pure BF16 attention for small shapes (total_kv <= 65536) to avoid JIT/quant overhead.
- Uses direct ASM dispatch (mla_decode_stage1_asm_fwd + mla_reduce_v1) for large shapes.
- Leverages 10% error tolerance for maximum speed.
"""

import torch
import aiter
from aiter.mla import mla_decode_stage1_asm_fwd, mla_reduce_v1
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from task import input_t, output_t

# Architecture Constants
NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

_META_CACHE = {}

def _get_mla_metadata(bs, qsl, kvsl, q_dtype, kv_dtype, qo_indptr, kv_indptr, num_splits):
    key = (bs, qsl, kvsl, q_dtype, kv_dtype, num_splits)
    if key in _META_CACHE: return _META_CACHE[key]
    
    kv_lpl = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(bs, qsl, NUM_HEADS, q_dtype, kv_dtype, 
                                    is_sparse=False, fast_mode=True, 
                                    num_kv_splits=num_splits, intra_batch_mode=True)
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    (wm, wi, wis, ri, rfm, rpm) = work
    
    get_mla_metadata_v1(qo_indptr, kv_indptr, kv_lpl, NUM_HEADS, NUM_KV_HEADS, True,
                        wm, wis, wi, ri, rfm, rpm,
                        page_size=PAGE_SIZE, kv_granularity=16,
                        max_seqlen_qo=qsl, uni_seqlen_qo=qsl,
                        fast_mode=True, max_split_per_batch=num_splits,
                        intra_batch_mode=True, dtype_q=q_dtype, dtype_kv=kv_dtype)
    
    meta = {"wm": wm, "wi": wi, "wis": wis, "ri": ri, "rfm": rfm, "rpm": rpm, "kv_lpl": kv_lpl}
    _META_CACHE[key] = meta
    return meta

def _bf16_attention(q, kv_bf16, qo_indptr, kv_indptr, bs, kvsl):
    # Pure BF16 path for small shapes
    # q: [total_q, 16, 576], kv_bf16: [total_kv, 1, 576]
    k = kv_bf16 # [total_kv, 1, 576]
    v = kv_bf16[:, :, :V_HEAD_DIM] # [total_kv, 1, 512]
    
    # Simplified attention for decode (q_seq_len=1)
    # scores: [bs, 16, kvsl]
    q = q.view(bs, 1, 16, QK_HEAD_DIM)
    k = k.view(bs, kvsl, 1, QK_HEAD_DIM)
    scores = torch.einsum("bqhd,bkhd->bqhk", q, k) * SM_SCALE
    attn = torch.softmax(scores, dim=-1)
    
    # out: [bs, 1, 16, 512]
    v = v.view(bs, kvsl, 1, V_HEAD_DIM)
    out = torch.einsum("bqhk,bkhv->bqhv", attn, v)
    return out.view(-1, NUM_HEADS, V_HEAD_DIM)

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs, qsl, kvsl = config["batch_size"], config["q_seq_len"], config["kv_seq_len"]
    total_kv = bs * kvsl
    
    # Threshold for BF16 path: total_kv <= 65536 (roughly 32MB)
    if total_kv <= 65536:
        return _bf16_attention(q, kv_data["bf16"], qo_indptr, kv_indptr, bs, kvsl)
    
    # ASM path for large shapes
    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(-1, PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)
    
    num_splits = 16 if total_kv > 65536 else 8
    meta = _get_mla_metadata(bs, qsl, kvsl, torch.float8_e4m3fn, kv_fp8.dtype, qo_indptr, kv_indptr, num_splits)
    
    total_q = q.shape[0]
    logits = torch.empty((num_splits, total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.float32, device="cuda")
    lse = torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda")
    o = torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
    
    # Quantize Q inline (simplified)
    q_scale = q.abs().max() / 448.0
    q_fp8 = (q / q_scale).to(torch.float8_e4m3fn)
    
    kv_indices = torch.arange(kv_fp8.shape[0], dtype=torch.int32, device="cuda")
    
    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM), kv_4d, 
        qo_indptr, kv_indptr, kv_indices, meta["kv_lpl"],
        None, meta["wm"], meta["wi"], meta["wis"],
        qsl, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
        logits, lse, o, q_scale=q_scale.view(1), kv_scale=kv_scale
    )
    
    mla_reduce_v1(logits, lse, meta["ri"], meta["rfm"], meta["rpm"], qsl, o)
    return o
