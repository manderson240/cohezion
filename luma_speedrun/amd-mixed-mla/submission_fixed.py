"""
MLA Submission - Fixed for leaderboard compatibility
Uses aiter mla_decode_fwd with proper input/output types
"""

import torch
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode kernel using aiter.
    
    Input: (q, kv_data, qo_indptr, kv_indptr, config)
    - q: (total_q, 16, 576) bfloat16 - absorbed query
    - kv_data: dict with KV cache
    - qo_indptr: indices for Q/O
    - kv_indptr: indices for KV
    - config: metadata
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    
    # Extract KV based on format
    if "fp8" in kv_data:
        kv_buffer, kv_scale = kv_data["fp8"]
    elif "bf16" in kv_data:
        kv_buffer = kv_data["bf16"]
        kv_scale = None
    else:
        # Fallback
        kv_buffer = list(kv_data.values())[0]
        kv_scale = None
    
    # Use aiter MLA decode
    # Quantize Q to fp8 for a8w8 kernel (faster)
    FP8_DTYPE = torch.float8_e4m3fn  # Standard fp8
    
    # Dynamic per-tensor FP8 quantization
    q_amax = q.abs().amax().clamp(min=1e-12)
    q_scale = q_amax / torch.finfo(FP8_DTYPE).max
    q_fp8 = (q / q_scale).clamp(min=torch.finfo(FP8_DTYPE).min, max=torch.finfo(FP8_DTYPE).max).to(FP8_DTYPE)
    
    # MLA metadata
    PAGE_SIZE = 1
    NUM_KV_SPLITS = 32
    
    # Get metadata - FIX: Added required arguments q_dtype, kv_dtype, is_sparse
    meta = get_mla_metadata_info_v1(
        kv_indptr,
        None,  # scheduler_metadata
        NUM_KV_SPLITS,
        q_fp8.dtype,  # q_dtype - REQUIRED
        kv_buffer.dtype,  # kv_dtype - REQUIRED
        False,  # is_sparse - REQUIRED
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
        sm_scale=1.0 / (576 ** 0.5),  # 1/sqrt(head_dim)
        logits_soft_cap=0.0,
    )
    
    return output.to(torch.bfloat16)
