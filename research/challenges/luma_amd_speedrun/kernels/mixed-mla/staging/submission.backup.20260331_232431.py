import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import (
    dynamic_mxfp4_quant,
    e8m0_to_f32,
)
from task import input_t, output_t

# DeepSeek R1 MLA constants
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)
FP8_DTYPE = aiter_dtypes.fp8
MXFP4_BLOCK_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    q = data["q"]  # (total_q, num_heads, 576) in bf16
    kv_data = data["kv_data"]
    
    # Determine KV format and prepare
    if "mxfp4" in kv_data:
        # MXFP4 path (block-32 quantized)
        kv_buffer, scale_e8m0 = kv_data["mxfp4"]
        # Dequantize to bf16 for MLA decode (kernel handles internal quantization)
        scale_f32 = e8m0_to_f32(scale_e8m0)
        kv_bf16 = dynamic_mxfp4_quant.dequantize(kv_buffer, scale_f32).to(torch.bfloat16)
    elif "fp8" in kv_data:
        # FP8 path
        kv_fp8, scale = kv_data["fp8"]
        kv_bf16 = (kv_fp8.to(torch.bfloat16) * scale).to(torch.bfloat16)
    else:
        # BF16 path
        kv_bf16 = kv_data["bf16"].squeeze(1).to(torch.bfloat16)
    
    # Quantize query to FP8 for MLA kernel (matches reference behavior)
    q_fp8, q_scale = _quantize_fp8(q)
    
    # Prepare KV in required format for MLA decode
    # MLA decode expects: [total_kv, 1, 576] for KV cache
    kv_bf16 = kv_bf16.unsqueeze(1)
    
    # Prepare output tensor
    total_q = q.size(0)
    num_heads = q.size(1)
    out = torch.empty((total_q, num_heads, V_HEAD_DIM), dtype=torch.bfloat16, device=q.device)
    
    # MLA decode kernel parameters
    # Use FP8 Q and FP8 KV (via bf16 → kernel handles internal quantization)
    mla_decode_fwd(
        q_fp8,
        kv_bf16,
        None,  # no kv_cache
        out,
        None,  # no cu_seqlens
        None,  # no max_seqlen
        sm_scale=SM_SCALE,
        q_dtype=FP8_DTYPE,
        kv_dtype=FP8_DTYPE,
        num_heads_q=num_heads,
        num_heads_kv=NUM_KV_HEADS,
        q_head_dim=QK_HEAD_DIM,
        kv_head_dim=QK_HEAD_DIM,
        v_head_dim=V_HEAD_DIM,
        page_size=1,
        num_kv_splits=32,
        use_alibi=False,
        use_swish=False,
    )
    
    return out


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_tensor = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_tensor, scale.to(torch.float32).reshape(1)