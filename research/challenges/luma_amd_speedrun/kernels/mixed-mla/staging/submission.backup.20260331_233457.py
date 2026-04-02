import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32

# DeepSeek R1 constants
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)

PAGE_SIZE = 1
NUM_KV_SPLITS = 32
FP8_DTYPE = aiter_dtypes.fp8

def quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_tensor = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_tensor, scale.to(torch.float32).reshape(1)

def custom_kernel(data):
    q = data["q"]
    kv_data = data["kv_data"]
    
    # Extract kv cache format info
    if "fp8" in kv_data:
        kv_fp8, kv_scale = kv_data["fp8"]
        kv_cache = kv_fp8
        kv_dtype = FP8_DTYPE
    elif "mxfp4" in kv_data:
        kv_fp4, kv_e8m0 = kv_data["mxfp4"]
        kv_cache = kv_fp4
        kv_dtype = aiter_dtypes.fp4
    else:
        kv_cache = kv_data["bf16"].squeeze(1)
        kv_dtype = torch.bfloat16
    
    # Quantize query to FP8 if needed
    if q.dtype != FP8_DTYPE:
        q_fp8, q_scale = quantize_fp8(q)
        q_scaled = q_fp8
    else:
        q_scaled = q
        q_scale = torch.tensor([1.0], dtype=torch.float32, device=q.device)
    
    # Prepare output tensor
    total_q = q.shape[0]
    num_heads = q.shape[1]
    out = torch.empty(total_q, num_heads, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)
    
    # Get MLA metadata
    metadata = get_mla_metadata_v1(
        total_q, num_heads, NUM_KV_HEADS, 
        QK_HEAD_DIM, V_HEAD_DIM, 
        PAGE_SIZE, NUM_KV_SPLITS,
        kv_cache.device
    )
    
    # Run MLA decode kernel
    mla_decode_fwd(
        q_scaled,
        kv_cache,
        out,
        metadata,
        sm_scale=SM_SCALE,
        q_dtype=FP8_DTYPE if q.dtype == FP8_DTYPE else FP8_DTYPE,
        kv_dtype=kv_dtype,
        q_scale=q_scale,
        kv_scale=kv_data.get("fp8", (None, None))[1] if "fp8" in kv_data else None,
        kv_e8m0_scale=kv_data.get("mxfp4", (None, None))[1] if "mxfp4" in kv_data else None,
        is_mxfp4="mxfp4" in kv_data,
    )
    
    return out