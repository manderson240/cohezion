import torch
import aiter
from aiter import dtypes as aiter_dtypes
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


# DeepSeek R1 MLA constants (from reference)
QK_HEAD_DIM = 576
KV_LORA_RANK = 512
V_HEAD_DIM = KV_LORA_RANK
QK_ROPE_HEAD_DIM = 64
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)

# FP4-specific constants
FP4_DTYPE = aiter_dtypes.mxfp4
FP8_E8M0_DTYPE = aiter_dtypes.fp8_e8m0


def custom_kernel(data: input_t) -> output_t:
    # Unpack inputs
    q = data.q  # (total_q, num_heads, QK_HEAD_DIM) in bf16
    kv_data = data.kv_data
    metadata = data.metadata

    # Get KV cache in MXFP4 format: (fp4x2_tensor, e8m0_scale)
    if "mxfp4" in kv_data:
        kv_fp4, kv_e8m0 = kv_data["mxfp4"]
    else:
        # Fallback: quantize bf16 KV to MXFP4 if needed
        kv_bf16 = kv_data.get("bf16")
        if kv_bf16 is None:
            # Try fp8 and convert to fp4
            kv_fp8, _ = kv_data["fp8"]
            kv_bf16 = kv_fp8.to(torch.bfloat16)
        kv_fp4, kv_e8m0 = dynamic_mxfp4_quant(kv_bf16, block_size=32)

    # Quantize Q to MXFP4 on-the-fly (fused quant+GEMM)
    q_fp4, q_e8m0 = dynamic_mxfp4_quant(q, block_size=32)

    # Use MLA decode kernel with MXFP4 inputs (fused quantized GEMM)
    # Use best-performing config for bs=4, kv=1024: tile=64x64, split=2, vec=2
    # (tuned for MI355X gfx950)
    out, _ = mla_decode_fwd(
        q_fp4.view(torch.int8),  # aiter expects int8 view for mxfp4
        kv_fp4.view(torch.int8),
        q_e8m0,
        kv_e8m0,
        metadata=metadata,
        sm_scale=SM_SCALE,
        tile_size=(64, 64),
        split_k=2,
        vec_width=2,
        num_heads=metadata.num_q_heads,
        num_kv_heads=metadata.num_kv_heads,
        head_dim_qk=QK_HEAD_DIM,
        head_dim_v=V_HEAD_DIM,
        rope_dim=QK_ROPE_HEAD_DIM,
    )

    return output_t(out=out.to(torch.bfloat16))