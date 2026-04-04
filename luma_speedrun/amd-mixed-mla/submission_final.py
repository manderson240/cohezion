#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA decode via aiter - simple working implementation."""

import torch
from aiter.mla import mla_decode_fwd
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    """MLA decode kernel."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    
    # Extract KV cache
    if "fp8" in kv_data:
        kv_buffer, kv_scale = kv_data["fp8"]
    else:
        kv_buffer = kv_data.get("bf16", list(kv_data.values())[0])
        kv_scale = None
    
    # Call aiter MLA decode
    return mla_decode_fwd(q, kv_buffer, kv_scale, qo_indptr, kv_indptr, config)
