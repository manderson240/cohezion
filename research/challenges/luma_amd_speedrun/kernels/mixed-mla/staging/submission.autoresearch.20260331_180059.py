import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import (
    dynamic_mxfp4_quant,
    e8m0_to_f32,
    mxfp4_to_f32,
)
from task import input_t, output_t

# DeepSeek R1 MLA constants (forward_absorb path)
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)

PAGE_SIZE = 1
NUM_KV_SPLITS = 256  # Optimized for large kvseqlen (8192), confirmed from research direction

# Platform-specific FP8 dtype
FP8_DTYPE = aiter_dtypes.fp8


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode kernel using persistent streaming paged attention (ASM kernel via aiter).
    Uses MXFP4 KV cache quantization for optimal performance on MI355X (gfx950).
    """
    q = data.q  # (total_q, num_heads, 576)
    kv_data = data.kv_data
    device = q.device
    
    # Extract KV cache components based on dtype
    if kv_data.dtype == "mxfp4":
        # MXFP4: (fp4x2 packed tensor, fp8_e8m0 scale tensor)
        kv_buffer, kv_scale = kv_data.data
    elif kv_data.dtype == "fp8":
        # FP8: (fp8 tensor, scalar scale)
        kv_buffer, kv_scale = kv_data.data
    else:
        # Fallback to bf16 (highest precision, slowest)
        kv_buffer = kv_data.data
        kv_scale = None
    
    # Determine block dimensions optimized for gfx950
    # Large KV splits for long sequences (research direction: kvseqlen=8192 bottleneck)
    # Tuned for MI355X: avoid register spills with moderate BLOCK_M and larger KSPLIT
    BLOCK_M = 64
    BLOCK_N = 64
    KSPLIT = NUM_KV_SPLITS
    
    # Prepare metadata for MLA decode
    metadata = mla_decode_fwd.get_mla_metadata(
        q,
        kv_buffer,
        None,  # kv_seq_lens - use default
        BLOCK_M,
        BLOCK_N,
        KSPLIT,
        page_size=PAGE_SIZE,
        causal=True,
        sm_scale=SM_SCALE,
        q_dtype=torch.bfloat16,
        kv_dtype=FP8_DTYPE if kv_data.dtype in ("fp8", "mxfp4") else torch.bfloat16,
        out_dtype=torch.bfloat16,
        device=device
    )
    
    # Output tensor
    total_q, num_heads, _ = q.shape
    out = torch.empty((total_q, num_heads, V_HEAD_DIM), dtype=torch.bfloat16, device=device)
    
    # Run MLA decode with persistent streaming kernel
    mla_decode_fwd(
        q,
        kv_buffer,
        None,  # k_seq
        None,  # v_seq
        out,
        metadata,
        sm_scale=SM_SCALE,
        q_dtype=torch.bfloat16,
        kv_dtype=FP8_DTYPE if kv_data.dtype in ("fp8", "mxfp4") else torch.bfloat16,
        out_dtype=torch.bfloat16,
        page_size=PAGE_SIZE,
        causal=True
    )
    
    return out