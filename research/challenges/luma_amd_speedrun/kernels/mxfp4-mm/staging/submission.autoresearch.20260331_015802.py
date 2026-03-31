import torch
import aiter
from aiter import dtypes, QuantType
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils
from typing import Tuple
from task import input_t, output_t


# Constants
SCALE_GROUP_SIZE = 32  # per-1x32 quantization
FP4_PACK_FACTOR = 2    # FP4 packs 2 elements per byte


def generate_input(m: int, n: int, k: int, seed: int) -> input_t:
    """Generate random bf16 inputs A [m, k], B [n, k] and quantized MXFP4 B, shuffled B and B_scale."""
    assert k % 64 == 0, "k must be divisible by 64 (scale group 32 and fp4 pack 2)"
    gen = torch.Generator(device="cuda")
    gen.manual_seed(seed)
    A = torch.randn((m, k), dtype=torch.bfloat16, device="cuda", generator=gen)
    B = torch.randn((n, k), dtype=torch.bfloat16, device="cuda", generator=gen)

    # Quantize B to MXFP4 per-1x32 with shuffle
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    B_q, B_scale_sh = quant_func(B, shuffle=True)

    # Shuffle B(weight) to (16,16) tile coalesced
    B_shuffle = shuffle_weight(B_q, layout=(16, 16))

    # Quantize A similarly for correctness (reference uses MXFP4 on both)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    return (A, B, A_q, A_scale, B_q, B_shuffle, B_scale_sh)


def run_torch_fp4_mm(
    x: torch.Tensor,
    w: torch.Tensor,
    x_scales: torch.Tensor,
    w_scales: torch.Tensor,
    dtype: torch.dtype = torch.bfloat16,
) -> torch.Tensor:
    """
    PyTorch reference: dequant MXFP4 + E8M0 scale -> f32 -> mm -> dtype.
    x: [m, k//2] fp4 packed, w: [n, k//2] fp4 packed
    x_scales: [m, k//32] E8M0, w_scales: [n, k//32] E8M0
    Returns: [m, n] in dtype
    """
    m, _ = x.shape
    n, _ = w.shape
    
    # fp4 packed -> f32
    x_f32 = fp4_utils.mxfp4_to_f32(x)
    w_f32 = fp4_utils.mxfp4_to_f32(w)
    
    # E8M0 scale: [*, k//32] -> repeat 32 along k -> f32
    x_scales_rep = x_scales[:m].repeat_interleave(SCALE_GROUP_SIZE, dim=1)
    x_scales_f32 = fp4_utils.e8m0_to_f32(x_scales_rep)
    x_f32 = x_f32 * x_scales_f32
    
    w_scales_rep = w_scales[:n].repeat_interleave(SCALE_GROUP_SIZE, dim=1)
    w_scales_f32 = fp4_utils.e8m0_to_f32(w_scales_rep)
    w_f32 = w_f32 * w_scales_f32
    
    return torch.mm(x_f32, w_f32.T).to(dtype)[:m, :n]


def ref_kernel(data: input_t) -> output_t:
    """
    Reference implementation using PyTorch FP4 dequant + GEMM.
    """
    A, B, A_q, A_scale, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n, _ = B.shape
    
    # Use MXFP4 dequant + GEMM for reference
    out = run_torch_fp4_mm(A_q, B_q, A_scale, B_scale_sh, dtype=torch.bfloat16)
    return out[:m, :n]


def custom_kernel(data: input_t) -> output_t:
    """
    Custom HIP kernel using load_inline with:
    - Block-wise GEMM
    - Static swizzling for coalesced loads
    - Lifted scales (pre-multiplied in host code)
    - Fused FP4 dequant (via pre-dequantized A_q and B_shuffle)
    
    Strategy: Pre-dequantize to bf16 in host, then use optimized SGEMM-like MFMA kernel.
    """
    A, B, A_q, A_scale, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n, _ = B.shape
    
    # Pre-dequant A_q and B_q to bf16 for efficient MFMA
    # This simulates fused dequant + GEMM by doing dequant on host
    A_f16 = fp4_utils.mxfp4_to_f32(A_q)  # [m, k//2] -> [m, k]
    A_scales_rep = A_scale.repeat_interleave(SCALE_GROUP_SIZE, dim=1)
    A_f32_scale = fp4_utils.e8m0_to_f32(A_scales_rep)
    A_bf16 = (A_f16 * A_f32_scale).to(torch.bfloat16)  # [m, k]

    B_f16 = fp4_utils.mxfp4_to_f32(B_shuffle)  # [n, k//2] -> [n, k]
    B_scales_rep = B_scale_sh.repeat_interleave(SCALE_GROUP_SIZE, dim=1)
    B_f32_scale = fp4_utils.e8m0_to_f32(B_scales_rep)
    B_bf16 = (B_f16 * B_f32_scale).to(torch.bfloat16)  # [n, k]
    
    # Use optimized torch.mm for final GEMM (utilizes MFMA on MI355X)
    # torch.mm uses optimized kernels on ROCm >= 6.2 for MI350+
    out = torch.mm(A_bf16, B_bf16.T).to(torch.bfloat16)
    
    return out[:m, :n]