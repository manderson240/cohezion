import torch
from aiter import dtypes as aiter_dtypes
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import e8m0_to_f32, mxfp4_to_f32
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
NUM_KV_SPLITS = 32
FP8_DTYPE = aiter_dtypes.fp8

def quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization (sglang style)."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_tensor = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_tensor, scale.to(torch.float32).reshape(1)

def custom_kernel(data: input_t) -> output_t:
    # Extract inputs
    q = data["q"]  # (total_q, num_heads, 576) bfloat16
    kv_data = data["kv_data"]
    
    # Determine KV cache format and prepare data
    kv_dtype = kv_data["kv_dtype"]
    total_kv = kv_data["total_kv"]
    block_tables = kv_data["block_tables"]
    kv_cache = kv_data["kv_cache"]
    
    # Prepare Q: quantize to fp8 for high performance
    q_fp8, q_scale = quantize_fp8(q)
    
    # Prepare KV: depending on format
    if kv_dtype == "bf16":
        kv_cache_fp8, kv_scale = quantize_fp8(kv_cache)
        kv_cache_out = kv_cache_fp8
        kv_scale_out = kv_scale
        use_mxfp4 = False
    elif kv_dtype == "fp8":
        kv_cache_out = kv_cache
        kv_scale_out = kv_data["scale"]
        use_mxfp4 = False
    elif kv_dtype == "mxfp4":
        # MXFP4: kv_cache is (packed_fp4, fp8_e8m0_scale)
        fp4_tensor, e8m0_scale = kv_cache
        # Convert MXFP4 to FP8 using aiter utility for compatibility with MLA kernel
        # Note: MLA decode kernel supports fp8 input; we'll use fp8 intermediate
        fp32_dequant = mxfp4_to_f32(fp4_tensor, e8m0_to_f32(e8m0_scale))
        kv_cache_fp8, kv_scale = quantize_fp8(fp32_dequant)
        kv_cache_out = kv_cache_fp8
        kv_scale_out = kv_scale
        use_mxfp4 = False
    else:
        raise ValueError(f"Unsupported KV dtype: {kv_dtype}")
    
    # Prepare parameters for MLA decode
    num_q_heads = q.size(1)
    num_kv_heads = NUM_KV_HEADS
    head_dim_qk = QK_HEAD_DIM
    head_dim_v = V_HEAD_DIM
    sm_scale = SM_SCALE
    q_dtype = FP8_DTYPE
    kv_dtype_kernel = FP8_DTYPE  # MLA kernel expects fp8 for best perf on MI355X
    
    # Call aiter MLA decode kernel
    # Note: aiter MLA decode kernel expects fp8 inputs and handles quantization internally if needed
    out = mla_decode_fwd(
        q=q_fp8,
        kv_data=kv_cache_out,
        kv_scale=kv_scale_out,
        block_tables=block_tables,
        seq_lens=kv_data["seq_lens"],
        page_size=PAGE_SIZE,
        num_q_heads=num_q_heads,
        num_kv_heads=num_kv_heads,
        head_dim_qk=head_dim_qk,
        head_dim_v=head_dim_v,
        sm_scale=sm_scale,
        q_dtype=q_dtype,
        kv_dtype=kv_dtype_kernel,
        output_dtype=torch.bfloat16,
        max_seqlen_q=1,  # decode only
    )
    
    return out