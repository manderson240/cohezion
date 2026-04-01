import aiter
import torch
from aiter import dtypes as aiter_dtypes
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
NUM_KV_SPLITS = 128  # Optimized for kvseqlen=8192 (increased from 32 to reduce bottleneck)

# Platform-specific FP8 dtype for MI355X
FP8_DTYPE = aiter_dtypes.fp8


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode kernel optimized for MI355X using aiter.mla_decode_fwd.
    
    Key optimizations:
    - Use MXFP4 KV cache (block-32 quantization) for memory bandwidth savings
    - Increased NUM_KV_SPLITS=128 for large kvseqlen (8192)
    - Leverage persistent kernel mode via get_mla_metadata_v1
    - On-the-fly FP8 quantization of Q for compute efficiency
    
    Follows sglang-style dynamic per-tensor FP8 quantization.
    """
    # Extract inputs from data
    q_bf16 = data.q  # (total_q, num_heads, 576)
    kv_data = data.kv_data
    cu_seqlens_q = data.cu_seqlens_q
    max_seqlen_q = data.max_seqlen_q
    cu_seqlens_k = data.cu_seqlens_k
    max_seqlen_k = data.max_seqlen_k
    
    # Prepare Q: quantize to FP8 (on-the-fly as in reference)
    q_fp8, q_scale = _quantize_fp8(q_bf16)
    
    # Prepare KV cache: use MXFP4 if available (preferred), fallback to FP8
    if "mxfp4" in kv_data:
        kv_cache_fp4, kv_scale_fp8 = kv_data["mxfp4"]
        use_mxfp4 = True
    elif "fp8" in kv_data:
        kv_cache_fp8, kv_scale = kv_data["fp8"]
        use_mxfp4 = False
    else:
        # Fallback to BF16 (slowest, but correct)
        kv_cache_bf16 = kv_data["bf16"]
        use_mxfp4 = False
    
    # Allocate output tensor
    total_q = q_bf16.size(0)
    num_heads = q_bf16.size(1)
    device = q_bf16.device
    out = torch.empty(total_q, num_heads, V_HEAD_DIM, dtype=torch.bfloat16, device=device)
    
    # Prepare metadata for persistent kernel mode
    metadata = aiter.get_mla_metadata_v1(
        cu_seqlens_q,
        cu_seqlens_k,
        max_seqlen_q,
        max_seqlen_k,
        num_heads,
        NUM_KV_HEADS,
        KV_LORA_RANK,
        QK_ROPE_HEAD_DIM,
        PAGE_SIZE,
        NUM_KV_SPLITS,
        q_fp8.dtype,
        FP8_DTYPE,  # KV dtype
        True,  # causal
        False,  # deterministic
    )
    
    # Run MLA decode kernel
    if use_mxfp4:
        # MXFP4 path (block-32 quantized)
        aiter.mla_decode_fwd(
            q_fp8,
            kv_cache_fp4,
            kv_scale_fp8,
            cu_seqlens_k,
            max_seqlen_k,
            out,
            metadata,
            sm_scale=SM_SCALE,
            q_scale=q_scale,
            kv_dtype=aiter_dtypes.float4,
        )
    else:
        # FP8 path (per-tensor quantized)
        kv_cache = kv_cache_fp8 if "fp8" in kv_data else kv_cache_bf16.to(FP8_DTYPE)
        kv_scale_val = kv_scale if "fp8" in kv_data else torch.tensor(1.0, device=device)
        
        aiter.mla_decode_fwd(
            q_fp8,
            kv_cache,
            kv_scale_val,
            cu_seqlens_k,
            max_seqlen_k,
            out,
            metadata,
            sm_scale=SM_SCALE,
            q_scale=q_scale,
            kv_dtype=FP8_DTYPE,
        )
    
    return out.contiguous()


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Dynamic per-tensor FP8 quantization (sglang style).
    Returns quantized tensor and scale.
    """
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8_tensor = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8_tensor, scale.to(torch.float32).reshape(1)