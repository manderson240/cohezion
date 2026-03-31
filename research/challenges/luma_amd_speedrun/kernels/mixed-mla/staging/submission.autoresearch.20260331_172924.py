import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant
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
NUM_KV_SPLITS = 32

# Platform-specific FP8 dtype
FP8_DTYPE = aiter_dtypes.fp8


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode kernel using aiter's mla_decode_fwd with persistent streaming
    and MXFP4 KV cache support. Optimized for MI355X (gfx950).
    
    Uses fp8 quantization for Q (on-the-fly) and MXFP4 for KV to maximize
    throughput while maintaining accuracy (rtol=1e-2).
    """
    q = data["q"]  # (total_q, num_heads, 576) in bf16
    kv_data = data["kv_data"]
    
    # Determine KV cache format
    kv_format = kv_data.get("format", "mxfp4") if isinstance(kv_data, dict) else "mxfp4"
    if isinstance(kv_data, dict):
        kv_data = kv_data["kv_buffer"] if "kv_buffer" in kv_data else kv_data.get("mxfp4")
    
    # Convert Q to FP8 on-the-fly (following sglang style)
    if q.dtype != FP8_DTYPE:
        # Dynamic per-tensor FP8 quantization for Q
        finfo = torch.finfo(FP8_DTYPE)
        amax = q.abs().amax().clamp(min=1e-12)
        scale = amax / finfo.max
        q_fp8 = (q / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    else:
        q_fp8 = q
        scale = torch.tensor([1.0], dtype=torch.float32, device=q.device)
    
    # Prepare KV cache for MXFP4 format
    if kv_format == "mxfp4":
        # MXFP4 format: (fp4_tensor, scale_e8m0)
        if isinstance(kv_data, (list, tuple)) and len(kv_data) == 2:
            kv_fp4, kv_scale = kv_data
            # Ensure correct dtypes
            kv_fp4 = kv_fp4.to(torch.uint8)  # MXFP4 stored as uint8
            kv_scale = kv_scale.to(aiter_dtypes.fp8_e8m0)
        else:
            # Quantize to MXFP4 if not already
            kv_fp4, kv_scale = dynamic_mxfp4_quant(kv_data.to(torch.bfloat16))
    else:
        # Fallback to BF16 if not MXFP4
        kv_fp4 = kv_data.to(torch.bfloat16)
        kv_scale = None
    
    # Get metadata for MLA decode (persistent mode)
    metadata = torch.empty(1024, dtype=torch.int32, device=q.device)
    
    # Prepare output tensor
    batch_size, num_heads_q, _ = q.shape
    out = torch.empty(
        (batch_size, num_heads_q, V_HEAD_DIM), 
        dtype=torch.bfloat16, 
        device=q.device
    )
    
    # Call aiter MLA decode kernel with persistent streaming
    mla_decode_fwd(
        q=q_fp8,
        kv_cache=kv_fp4,
        kv_scale=kv_scale,
        out=out,
        sm_scale=SM_SCALE,
        metadata=metadata,
        num_kv_splits=NUM_KV_SPLITS,
        page_size=PAGE_SIZE,
        window_size=-1  # No sliding window
    )
    
    return out