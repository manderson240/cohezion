import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32
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
FP4_DTYPE = aiter_dtypes.fp4x2
FP8_E8M0_DTYPE = aiter_dtypes.fp8_e8m0

def quantize_q_to_fp8(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization of query tensor."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = q.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_q = (q / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_q, scale.to(torch.float32).reshape(1)

def quantize_kv_to_mxfp4(kv: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Block-32 MXFP4 quantization using aiter's native implementation."""
    # aiter expects FP4 quantized as fp4x2 + fp8_e8m0 scale
    # kv shape: [total_kv, 1, 576] -> [total_kv, 576]
    kv_flat = kv.squeeze(1)  # [total_kv, 576]
    fp4_kv, fp8_scale = dynamic_mxfp4_quant(kv_flat)
    return fp4_kv, fp8_scale

def custom_kernel(data: input_t) -> output_t:
    q_bf16 = data["q"]  # [total_q, num_heads, 576], bf16
    kv_data = data["kv_data"]
    
    # Determine KV cache format
    if "mxfp4" in kv_data:
        # MXFP4 path (preferred for speed)
        fp4_kv, fp8_scale = kv_data["mxfp4"]
        # Reuse FP8 scale as FP8_E8M0 for MXFP4 decode
        scale = fp8_scale.to(torch.float32)
        # Convert MXFP4 to FP32 for reference compatibility (handled internally by kernel)
        # But kernel expects fp4x2 + fp8_e8m0 format, so pass as-is
        fp8_scale = fp8_scale.to(FP8_E8M0_DTYPE)
        
        # Quantize query to FP8 for consistency with reference
        q_fp8, q_scale = quantize_q_to_fp8(q_bf16)
        
        # Call MLA decode with FP8 Q and MXFP4 KV
        out = mla_decode_fwd(
            q_fp8, 
            None,  # kv_indices (for page mode)
            fp4_kv, 
            fp8_scale,
            q_scale,
            scale,
            None,  # cu_seqlens
            None,  # seq_len
            None,  # block_table
            None,  # max_seqlen
            None,  # window_size
            None,  # softcap
            None,  # alibi_slopes
            None,  # causal
            SM_SCALE,
            False, # return_lse
        )
    elif "fp8" in kv_data:
        # FP8 KV path (fallback)
        fp8_kv, kv_scale = kv_data["fp8"]
        q_fp8, q_scale = quantize_q_to_fp8(q_bf16)
        
        out = mla_decode_fwd(
            q_fp8,
            None,
            fp8_kv,
            kv_scale,
            q_scale,
            kv_scale,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            SM_SCALE,
            False,
        )
    else:
        # BF16 path (slowest, only if absolutely necessary)
        q_bf16, _ = quantize_q_to_fp8(q_bf16)  # Still quantize Q to FP8 for speed
        
        out = mla_decode_fwd(
            q_bf16,
            None,
            kv_data["bf16"],
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            SM_SCALE,
            False,
        )
    
    # Ensure output is bf16 as required by interface
    return out.to(torch.bfloat16)