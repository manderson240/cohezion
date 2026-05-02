#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Compound kernel v1: dynamic_mxfp4_quant + fused HIP shuffle + aiter.gemm_a4w4_asm.

The key insight from skill aiter-mxfp4-api-limitations Limitation 13:
  The e8m0_shuffle step costs ~12.9us and IS eliminable by writing scales
  directly into the shuffled layout inside the quant kernel.

This version compounds two things differently:
1. Use dynamic_mxfp4_quant (fast Triton, ~10us) for quantization — don't replace it.
2. Use a custom HIP e8m0_shuffle kernel that writes scales directly to the
   shuffled layout, replacing the separate e8m0_shuffle call (~12.9us).
3. Pre-resolved function refs + shape-specific gemm_a4w4_asm dispatch.

Expected: dynamic_mxfp4_quant (~10us) + fused_shuffle (~1us) + gemm (~8us) = ~19us
vs baseline: dynamic_mxfp4_quant (~10us) + e8m0_shuffle (~12.9us) + gemm (~8us) = ~31us

The fused_shuffle kernel: takes the [M_pad, K//32] linear uint8 scale output from
dynamic_mxfp4_quant and writes it into the pre-zeroed shuffled buffer in one pass,
using the closed-form shuffle_index() formula.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# ── Pre-resolved references ─────────────────────────────────────────────────
_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16

# ── HIP kernel: linear E8M0 scale → shuffled layout ────────────────────────
# Takes [M_raw, K//32] uint8 linear scale (output of dynamic_mxfp4_quant)
# and writes each byte directly to its shuffled position in the output buffer.
# One thread per scale element. Grid is flat over M * (K//32) elements.
#
# shuffle_index formula (from Limitation 13):
#   e8m0_shuffle does view(sm//32, 2, 16, sn//8, 2, 4).permute(0,3,5,2,4,1)
#   Inverse: flat_out = d0*(sn/8*256) + d3*256 + d5*64 + d2*4 + d4*2 + d1
#   where: d0=row//32, r32=row%32, d1=r32//16, d2=r32%16
#          d3=grp//8, c8=grp%8, d4=c8//4, d5=c8%4

_SHUFFLE_KERNEL_SRC = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>

__device__ __forceinline__ int shuffle_index(int row, int grp, int sn) {
    int d0  = row >> 5;
    int r32 = row & 31;
    int d1  = r32 >> 4;
    int d2  = r32 & 15;
    int d3  = grp >> 3;
    int c8  = grp & 7;
    int d4  = c8 >> 2;
    int d5  = c8 & 3;
    int stride_d0 = (sn >> 3) * 256;  // sn/8 * 256
    return d0 * stride_d0 + d3 * 256 + d5 * 64 + d2 * 4 + d4 * 2 + d1;
}

// Scatter linear scale to shuffled positions.
// Each thread handles one (row, grp) element.
// Grid: flat over M * num_groups, blockDim = 256.
__global__
void scatter_shuffle(
    const uint8_t* __restrict__ src,   // [M_raw, num_groups] linear scale
    uint8_t*       __restrict__ dst,   // [sm * sn] shuffled, pre-zeroed
    int M_raw,      // actual M (not padded)
    int num_groups, // K // 32
    int sn          // padded num_groups (multiple of 8)
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int total = M_raw * num_groups;
    if (tid >= total) return;

    int row  = tid / num_groups;
    int grp  = tid % num_groups;

    uint8_t val = src[tid];
    int dst_idx = shuffle_index(row, grp, sn);
    dst[dst_idx] = val;
}

void fused_e8m0_shuffle(
    torch::Tensor src,   // [M_raw, num_groups] uint8
    torch::Tensor dst,   // [sm * sn] uint8, zero-initialized
    int sn
) {
    int M_raw      = src.size(0);
    int num_groups = src.size(1);
    int total      = M_raw * num_groups;

    const int BLOCK = 256;
    dim3 block(BLOCK);
    dim3 grid((total + BLOCK - 1) / BLOCK);

    scatter_shuffle<<<grid, block>>>(
        src.data_ptr<uint8_t>(),
        dst.data_ptr<uint8_t>(),
        M_raw, num_groups, sn
    );
}
"""

_CPP_WRAPPER = "void fused_e8m0_shuffle(torch::Tensor, torch::Tensor, int);"

try:
    _mod = load_inline(
        name="compound_shuffle_v1",
        cpp_sources=[_CPP_WRAPPER],
        cuda_sources=[_SHUFFLE_KERNEL_SRC],
        functions=["fused_e8m0_shuffle"],
        verbose=False,
        extra_cuda_cflags=[
            "--offload-arch=gfx950",
            "-std=c++17",
            "-O3",
        ],
    )
    _MOD_OK = True
except Exception as _compile_err:
    _MOD_OK = False
    print(f"[compound_v1] load_inline failed: {_compile_err}")

# ── Shape-specific ASM kernel names (Limitation 8) ─────────────────────────
_KERN_SMALL = "f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128"
_KERN_LARGE = "f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128"

try:
    _gemm_asm = aiter.gemm_a4w4_asm
    _HAS_ASM = True
except AttributeError:
    _HAS_ASM = False

# Pre-allocate the maximum-size scale buffer once at module load.
# Competition shapes: M<=256, K<=7168 → num_groups<=224, sm_max=256, sn_max=224.
# Allocate with margin to avoid reallocation. Zero-init once; reused via fill_.
_MAX_SM = 256  # ceil(256/256)*256
_MAX_SN = 232  # ceil(224/8)*8 = 224; use 232 as safe margin
_scale_buf: torch.Tensor | None = None


def _get_scale_buf(sm: int, sn: int, device: torch.device) -> torch.Tensor:
    """Return a zero-filled [sm*sn] uint8 buffer, reusing the pre-allocated one."""
    global _scale_buf
    needed = sm * sn
    if _scale_buf is None or _scale_buf.numel() < needed or _scale_buf.device != device:
        # Allocate once, large enough for all competition shapes
        alloc_size = max(needed, _MAX_SM * _MAX_SN)
        _scale_buf = torch.zeros(alloc_size, dtype=torch.uint8, device=device)
    else:
        # Reuse: only zero the region we'll write into (fast fill_ on small slice)
        _scale_buf[:needed].fill_(0)
    return _scale_buf[:needed]


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B_shuffle.shape[0]

    # Quantize A (fast Triton kernel, ~10us)
    Aq_raw, Asc_raw = dynamic_mxfp4_quant(A.contiguous())

    num_groups = K >> 5  # K // 32
    # Trim scale to valid region [M, num_groups]
    Asc_linear = Asc_raw[:M, :num_groups].contiguous().view(torch.uint8)

    if _MOD_OK:
        # Shuffle into pre-allocated buffer (avoids torch.zeros allocation cost)
        sm = ((M + 255) // 256) * 256
        sn = ((num_groups + 7) // 8) * 8
        Asc_shuffled = _get_scale_buf(sm, sn, A.device)
        _mod.fused_e8m0_shuffle(Asc_linear, Asc_shuffled, sn)
        A_scale_view = Asc_shuffled.view(sm, sn).view(_fp8_e8m0)
    else:
        # Python fallback for e8m0_shuffle
        A_scale_view = e8m0_shuffle(Asc_raw).view(_fp8_e8m0)

    A_fp4_view = Aq_raw.view(_fp4x2)

    # Shape-specific ASM dispatch
    pm = ((M + 31) // 32) * 32  # padded M
    if _HAS_ASM:
        kern = _KERN_SMALL if pm <= 32 else _KERN_LARGE
        out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
        try:
            _gemm_asm(
                A_fp4_view,
                B_shuffle,
                A_scale_view,
                B_scale_sh,
                out,
                kernelName=kern,
                bias=None,
                alpha=1.0,
                beta=0.0,
                bpreshuffle=True,
                log2_k_split=0,
            )
            return out
        except Exception:
            pass  # fall through to gemm_a4w4

    return _gemm(
        A_fp4_view,
        B_shuffle,
        A_scale_view,
        B_scale_sh,
        dtype=_bf16,
        bpreshuffle=True,
    )
