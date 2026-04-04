"""MLA Submission - Complete API Fix for Benchmark Mode"""

import torch
import math
from aiter import get_mla_metadata_info_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode kernel using aiter.
    Fixed for proper benchmark compatibility.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    
    # Extract KV cache
    if "fp8" in kv_data:
        kv_buffer, kv_scale = kv_data["fp8"]
    elif "bf16" in kv_data:
        kv_buffer = kv_data["bf16"]
        kv_scale = None
    else:
        kv_buffer = list(kv_data.values())[0]
        kv_scale = None
    
    # FP8 quantization for query
    FP8_DTYPE = torch.float8_e4m3fn
    q_amax = q.abs().amax().clamp(min=1e-12)
    q_scale = q_amax / torch.finfo(FP8_DTYPE).max
    q_fp8 = (q / q_scale).clamp(min=torch.finfo(FP8_DTYPE).min, max=torch.finfo(FP8_DTYPE).max).to(FP8_DTYPE)
    
    # Get dimensions for metadata
    num_head_qo = q.shape[1]  # 16 heads
    
    # Calculate max_seqlen_qo from qo_indptr
    # qo_indptr shape is [batch_size + 1]
    max_seqlen_qo = config.get("max_seqlen_qo", q.shape[0] // num_head_qo)
    
    NUM_KV_SPLITS = 32
    
    # FIX: Complete get_mla_metadata_info_v1 call with all required args
    # Need: kv_indptr, scheduler_metadata, num_kv_splits, q_dtype, kv_dtype, is_sparse
    meta = get_mla_metadata_info_v1(
        kv_indptr,
        None,  # scheduler_metadata - optional
        NUM_KV_SPLITS,
        q_fp8.dtype,  # q_dtype - REQUIRED
        kv_buffer.dtype,  # kv_dtype - REQUIRED  
        False,  # is_sparse - REQUIRED
        getattr(config, "head_dim", 576),  # head_dim_v
        getattr(config, "num_heads", num_head_qo),  # num_head_qo
        getattr(config, "max_seqlen_qo", max_seqlen_qo),  # max_seqlen_qo
    )
    
    # Run MLA decode
    output = mla_decode_fwd(
        q_fp8,
        kv_buffer,
        kv_scale,
        torch.full((1,), q_scale, dtype=torch.float32, device=q.device),
        qo_indptr,
        kv_indptr,
        None,  # scheduler_metadata
        meta,
        sm_scale=1.0 / (576 ** 0.5),
        logits_soft_cap=0.0,
    )
    
    return output.to(torch.bfloat16)
