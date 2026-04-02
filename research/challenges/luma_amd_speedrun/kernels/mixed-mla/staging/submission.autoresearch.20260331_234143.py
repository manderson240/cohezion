import torch
import aiter
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
BF16_DTYPE = torch.bfloat16


def custom_kernel(data: input_t) -> output_t:
    q = data["q"]
    kv_data = data["kv_data"]
    
    # Use fp8 path for both Q and KV as it's fastest on MI355X
    # Quantize Q if needed (reference uses fp8 on-the-fly)
    if q.dtype != FP8_DTYPE:
        # Dynamic per-tensor fp8 quantization (sglang style)
        finfo = torch.finfo(FP8_DTYPE)
        amax = q.abs().amax().clamp(min=1e-12)
        scale_q = amax / finfo.max
        q_fp8 = (q / scale_q).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    else:
        q_fp8 = q
        scale_q = torch.tensor([1.0], dtype=torch.float32, device=q.device)
    
    # Determine KV format and prepare fp8 KV
    if "fp8" in kv_data:
        kv_fp8, kv_scale = kv_data["fp8"]
        if kv_fp8.dtype != FP8_DTYPE:
            kv_fp8 = kv_fp8.to(FP8_DTYPE)
    elif "mxfp4" in kv_data:
        kv_mxfp4, fp8_scale = kv_data["mxfp4"]
        # Convert mxfp4 to fp8 for MLA kernel (faster than bf16 path)
        kv_bf16 = mxfp4_to_f32(kv_mxfp4.view(torch.float32), fp8_scale.view(torch.float32)).to(BF16_DTYPE)
        amax = kv_bf16.abs().amax().clamp(min=1e-12)
        scale = amax / finfo.max
        kv_fp8 = (kv_bf16 / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
        kv_scale = scale.to(torch.float32).reshape(1)
    else:  # bf16
        kv_bf16 = kv_data["bf16"]
        amax = kv_bf16.abs().amax().clamp(min=1e-12)
        scale = amax / finfo.max
        kv_fp8 = (kv_bf16 / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
        kv_scale = scale.to(torch.float32).reshape(1)
    
    # Prepare metadata for MLA decode
    total_q = q_fp8.size(0)
    total_kv = kv_fp8.size(0)
    num_q_heads = q_fp8.size(1)
    
    # Set metadata parameters
    metadata = aiter.get_mla_metadata_v1(
        total_q,
        total_kv,
        num_q_heads,
        NUM_KV_HEADS,
        KV_LORA_RANK,
        QK_ROPE_HEAD_DIM,
        V_HEAD_DIM,
        SM_SCALE,
        1,  # page_size
        32, # num_kv_splits
        False # enable_debug
    )
    
    # Allocate output tensor
    out = torch.empty((total_q, num_q_heads, V_HEAD_DIM), dtype=BF16_DTYPE, device=q.device)
    
    # Run MLA decode kernel with fp8 inputs
    mla_decode_fwd(
        q_fp8,
        kv_fp8,
        kv_scale,
        None,  # q_scale (None implies no scaling)
        None,  # block_table
        None,  # cu_seqlens
        None,  # max_seqlen
        out,
        metadata,
        False  # is_causal
    )
    
    return out