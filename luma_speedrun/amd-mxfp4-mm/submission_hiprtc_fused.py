#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
HIPRTC-based MXFP4 GEMM using torch.cuda._compile_kernel.

Attempting fused quant+GEMM via _compile_kernel.
If _compile_kernel fails, falls back to standard aiter path.
"""

import os
import sys
import torch

# Environment setup for aiter
os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in os.environ.get("PYTHONPATH", ""):
    if _AITER_JIT_DIR not in sys.path:
        sys.path.insert(0, _AITER_JIT_DIR)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# FP4 to float conversion table (E2M1 format)
# Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 and negatives
FP4_TO_F32_TABLE = torch.tensor([
    0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,
    -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0
], dtype=torch.float32, device="cuda")


def _fp4_to_f32(packed: torch.Tensor) -> torch.Tensor:
    """Convert packed FP4x2 to float32."""
    # packed: [M, K//2] uint8
    low = packed & 0xF
    high = (packed >> 4) & 0xF
    # Interleave to get [M, K] f32
    f32_low = FP4_TO_F32_TABLE[low]
    f32_high = FP4_TO_F32_TABLE[high]
    # Stack and reshape
    M = packed.shape[0]
    K = packed.shape[1] * 2
    result = torch.empty((M, K), dtype=torch.float32, device=packed.device)
    result[:, 0::2] = f32_low
    result[:, 1::2] = f32_high
    return result


def _e8m0_to_f32(scale_e8m0: torch.Tensor) -> torch.Tensor:
    """Convert E8M0 scale to float32."""
    # scale_e8m0: [M, K//32] uint8
    # Convert to float: f = 2^(e8m0 - 127)
    scale_f32 = torch.pow(2.0, scale_e8m0.float() - 127.0)
    return scale_f32


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM - attempt fused path via torch operations."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]

    # Dynamic quantize A to MXFP4
    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # Shuffle scales
    num_scale_groups = K // 32
    A_scale_bytes = A_scale[:M, :num_scale_groups].contiguous().view(torch.uint8)
    A_scale_sh = e8m0_shuffle(A_scale_bytes.view(dtypes.fp8_e8m0))

    # Use aiter gemm_a4w4 with direct ASM dispatch
    # Bypass tuning config for fastest path
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh.view(dtypes.fp8_e8m0),
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
