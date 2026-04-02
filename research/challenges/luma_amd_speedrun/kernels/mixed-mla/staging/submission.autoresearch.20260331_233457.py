import torch
import aiter
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32

# DeepSeek R1 MLA constants (same as reference)
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
FP4_DTYPE = aiter_dtypes.fp4x2


def custom_kernel(data):
    # Extract inputs
    q = data.q  # (total_q, num_heads, 576)
    kv_data = data.kv_data
    
    total_q = q.shape[0]
    num_heads = q.shape[1]
    
    # Preprocess Q: quantize to FP8 if needed (matching reference strategy)
    q_bf16 = q.to(torch.bfloat16)
    
    # Determine KV format and prepare quantized KV for MLA
    if "fp8" in kv_data:
        kv_fp8, kv_scale = kv_data["fp8"]
        kv_bf16 = (kv_fp8.to(torch.bfloat16) * kv_scale).unsqueeze(1)  # (total_kv, 1, 576)
    elif "mxfp4" in kv_data:
        kv_fp4, kv_e8m0 = kv_data["mxfp4"]
        # Convert MXFP4 to BF16 using aiter utilities (block-wise dequant)
        kv_bf16 = e8m0_to_f32(kv_e8m0).unsqueeze(-1) * mxfp4_to_f32(kv_fp4).unsqueeze(0)  # (32, total_kv, 576)
        # Reshape to match expected format: collapse block dim
        kv_bf16 = kv_bf16.view(-1, 1, 576)[:total_q]  # (total_kv, 1, 576)
    else:
        kv_bf16 = kv_data["bf16"].squeeze(1)  # (total_kv, 576) -> (total_kv, 1, 576)

    # Quantize Q to FP8 for performance (matching reference)
    if q_bf16.dtype != FP8_DTYPE:
        q_amax = q_bf16.abs().amax().clamp(min=1e-12)
        q_scale = q_amax / torch.finfo(FP8_DTYPE).max
        q_fp8 = (q_bf16 / q_scale).clamp(min=torch.finfo(FP8_DTYPE).min, max=torch.finfo(FP8_DTYPE).max).to(FP8_DTYPE)
    else:
        q_fp8 = q_bf16
        q_scale = torch.tensor(1.0, dtype=torch.float32, device=q.device)

    # Prepare outputs and workspace
    out = torch.empty((total_q, num_heads, V_HEAD_DIM), dtype=torch.bfloat16, device=q.device)
    
    # Use MLA decode kernel with FP8 Q and FP8/MXFP4 KV
    # Note: MLA kernel expects fp8 kv if fp8 format provided; otherwise bf16 fallback
    mla_decode_fwd(
        q_fp8,
        kv_fp8 if "fp8" in kv_data else kv_bf16,
        kv_scale if "fp8" in kv_data else None,
        out,
        sm_scale=SM_SCALE,
        page_size=PAGE_SIZE,
        num_kv_splits=NUM_KV_SPLITS,
        causal=True,
        use_fp8_kv=True if "fp8" in kv_data else False,
        use_fp8_q=True  # Always quantize Q to FP8 for speed
    )
    
    return out