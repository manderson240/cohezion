import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32
from task import input_t, output_t

# DeepSeek R1 MLA constants (forward_absorb path)
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)

# Platform-specific FP8 dtype
FP8_DTYPE = aiter_dtypes.fp8


def custom_kernel(data: input_t) -> output_t:
    q = data.q  # (total_q, num_heads, 576) in bf16
    kv_data = data.kv_data
    
    # Extract KV cache components based on format
    if "bf16" in kv_data:
        kv_data_bf16 = kv_data["bf16"]  # (total_kv, 1, 576)
    elif "fp8" in kv_data:
        kv_fp8, kv_scale = kv_data["fp8"]
    elif "mxfp4" in kv_data:
        kv_fp4, kv_e8m0 = kv_data["mxfp4"]
    
    # Convert query to FP8 on-the-fly for optimal performance on MI355X
    # Dynamic per-tensor quantization (sglang style)
    finfo = torch.finfo(FP8_DTYPE)
    q_amax = q.abs().amax().clamp(min=1e-12)
    q_scale = q_amax / finfo.max
    q_fp8 = (q / q_scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    
    # Determine KV format and prepare for MLA kernel
    if "mxfp4" in kv_data:
        # MXFP4 path: use native aiter MXFP4 MLA kernel
        # MXFP4 tensors already in correct format: kv_fp4 (uint8), kv_e8m0 (fp8_e8m0)
        # No additional conversion needed; kernel handles dequant internally
        output = mla_decode_fwd(
            q_fp8,
            kv_fp4,
            kv_e8m0,
            sm_scale=SM_SCALE,
            q_dtype=FP8_DTYPE,
            k_dtype=FP8_DTYPE,  # placeholder; kernel uses mxfp4 internally
            v_dtype=FP8_DTYPE,  # placeholder
        )
    elif "fp8" in kv_data:
        # FP8 path: use standard FP8 MLA kernel
        output = mla_decode_fwd(
            q_fp8,
            kv_fp8,
            sm_scale=SM_SCALE,
            q_dtype=FP8_DTYPE,
            k_dtype=FP8_DTYPE,
            v_dtype=FP8_DTYPE,
        )
    else:
        # Fallback to BF16 path (slower but correct)
        output = mla_decode_fwd(
            q.to(torch.bfloat16),
            kv_data_bf16.to(torch.bfloat16),
            sm_scale=SM_SCALE,
            q_dtype=torch.bfloat16,
            k_dtype=torch.bfloat16,
            v_dtype=torch.bfloat16,
        )
    
    return output