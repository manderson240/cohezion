import torch
import aiter
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32
from task import input_t, output_t

# DeepSeek R1 MLA constants (forward_absorb path)
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)

PAGE_SIZE = 1
NUM_KV_HEADS = 1

# Platform-specific FP8 dtype (MI355X)
FP8_DTYPE = aiter_dtypes.fp8
MXFP4_DTYPE = aiter_dtypes.mxfp4
FP8_E8M0_DTYPE = aiter_dtypes.fp8_e8m0


def quantize_q_to_fp8(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization for Q."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = q.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_q = (q / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_q, scale.to(torch.float32).reshape(1)


def custom_kernel(data: input_t) -> output_t:
    # Unpack inputs
    q_bf16 = data["q"]  # (total_q, num_heads, 576)
    kv_data = data["kv_data"]
    
    # Determine actual shapes
    total_q, num_heads, _ = q_bf16.shape
    # Ensure consistent with MLA expectations
    num_kv_splits = data.get("num_kv_splits", 16)
    if num_kv_splits < 8:
        num_kv_splits = 8
    elif num_kv_splits > 24:
        num_kv_splits = 24

    # Get metadata (v1)
    meta = aiter.get_mla_metadata_v1(
        num_heads=num_heads,
        num_kv_heads=NUM_KV_HEADS,
        qk_head_dim=QK_HEAD_DIM,
        v_head_dim=V_HEAD_DIM,
        num_kv_splits=num_kv_splits,
        page_size=PAGE_SIZE,
    )

    # Process KV cache: prefer MXFP4 for MI355X performance
    if "mxfp4" in kv_data:
        kv_fp4, kv_scale = kv_data["mxfp4"]
        # Convert to MXFP4 format expected by MLA kernel
        # MXFP4: fp4x2 + fp8_e8m0 scale per block-32
        kv_fp4 = kv_fp4.to(MXFP4_DTYPE)
        kv_scale = kv_scale.to(FP8_E8M0_DTYPE)
        kv_cache = (kv_fp4, kv_scale)
    elif "fp8" in kv_data:
        # Fall back to FP8 if MXFP4 not available or not optimal for this config
        kv_fp8, kv_scale = kv_data["fp8"]
        kv_cache = (kv_fp8.to(FP8_DTYPE), kv_scale)
    else:
        # Fallback to BF16 (slowest)
        kv_cache = (kv_data["bf16"].to(torch.bfloat16), None)

    # Quantize Q to FP8 (on-the-fly, as reference does)
    q_fp8, q_scale = quantize_q_to_fp8(q_bf16)

    # Allocate output
    output = torch.empty(
        (total_q, num_heads, V_HEAD_DIM),
        dtype=torch.bfloat16,
        device=q_bf16.device,
    )

    # Run MLA decode kernel with MXFP4/KV cache and FP8 Q
    mla_decode_fwd(
        q=q_fp8,
        kv_cache=kv_cache,
        output=output,
        sm_scale=SM_SCALE,
        meta=meta,
        q_scale=q_scale,
        # Note: kernel handles KV scale internally if MXFP4
    )

    # Return expected output format
    return output