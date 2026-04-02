import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32
from task import input_t, output_t

# DeepSeek R1 MLA constants (from reference)
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
BF16_DTYPE = torch.bfloat16


def quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization (sglang style)."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_tensor = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_tensor, scale.to(torch.float32).reshape(1)


def custom_kernel(data: input_t) -> output_t:
    q_bf16 = data.q  # (total_q, num_heads, 576)
    kv_data = data.kv_data

    # Use FP8 KV if available (highest performance)
    if kv_data.get("fp8") is not None:
        kv_fp8, kv_scale = kv_data["fp8"]
        kv_dequant = (kv_fp8.to(BF16_DTYPE) * kv_scale).view(-1, 1, 576)
    elif kv_data.get("mxfp4") is not None:
        kv_fp4x2, kv_e8m0 = kv_data["mxfp4"]
        kv_dequant = mxfp4_to_f32(kv_fp4x2, kv_e8m0).view(-1, 1, 576).to(BF16_DTYPE)
    else:
        kv_dequant = kv_data["bf16"]

    # Quantize Q to FP8 on-the-fly (matches reference)
    q_fp8, q_scale = quantize_fp8(q_bf16)

    # Ensure correct dtypes for aiter
    q_fp8 = q_fp8.to(FP8_DTYPE)
    kv_dequant = kv_dequant.to(BF16_DTYPE)

    # Allocate output
    total_q = q_bf16.size(0)
    num_heads = q_bf16.size(1)
    out = torch.empty((total_q, num_heads, V_HEAD_DIM), dtype=BF16_DTYPE, device=q_bf16.device)

    # Run MLA decode kernel
    mla_decode_fwd(
        q=q_fp8,
        k=kv_dequant,
        v=kv_dequant,
        out=out,
        sm_scale=SM_SCALE,
        page_size=PAGE_SIZE,
        num_kv_splits=NUM_KV_SPLITS,
        cu_seqlens_q=data.cu_seqlens_q,
        cu_seqlens_k=data.cu_seqlens_k,
        max_seqlen_q=data.max_seqlen_q,
        max_seqlen_k=data.max_seqlen_k,
        q_scale=q_scale,
        k_scale=kv_scale if kv_data.get("fp8") is not None else None,
        v_scale=kv_scale if kv_data.get("fp8") is not None else None,
        is_mla=True,
        q_data_type=FP8_DTYPE,
        kv_data_type=BF16_DTYPE,
    )

    return output_t(out=out)