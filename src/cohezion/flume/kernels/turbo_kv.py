"""
TurboQuant Hardware-Accelerated Kernels for Strix Halo (gfx1151).
Implements PolarQuant + QJL fused attention with Wave32 alignment.
"""

import os
from typing import NamedTuple

import torch
import triton
import triton.language as tl
from torch.utils.cpp_extension import load_inline


# --- Data Structures matching research/turboquant ---


class ProdQuantized(NamedTuple):
    mse_indices: torch.Tensor
    qjl_signs: torch.Tensor
    norms: torch.Tensor
    residual_norms: torch.Tensor


class ValueQuantized(NamedTuple):
    data: torch.Tensor
    scales: torch.Tensor
    zeros: torch.Tensor
    bits: int


# --- GFX1151 Optimized Fused Kernel (Triton) ---


@triton.jit
def _turbo_kv_fused_decode_kernel_gfx1151(
    Q_ROT_ptr,
    Q_SKETCH_ptr,
    MSE_ptr,
    SIGNS_ptr,
    NORMS_ptr,
    RES_NORMS_ptr,
    CENTROIDS_ptr,
    V_DATA_ptr,
    V_SCALES_ptr,
    V_ZEROS_ptr,
    OUT_ptr,
    stride_q_bh,
    stride_q_d,
    stride_m_bh,
    stride_m_n,
    stride_m_d,
    stride_s_bh,
    stride_s_n,
    stride_s_d,
    stride_n_bh,
    stride_n_n,
    stride_rn_bh,
    stride_rn_n,
    stride_v_bh,
    stride_v_n,
    stride_v_d,
    stride_vs_bh,
    stride_vs_n,
    stride_vs_g,
    stride_vz_bh,
    stride_vz_n,
    stride_vz_g,
    stride_o_bh,
    stride_o_d,
    N,
    D: tl.constexpr,
    PACKED_D_MSE: tl.constexpr,
    PACKED_D_SIGNS: tl.constexpr,
    N_GROUPS: tl.constexpr,
    GROUP_SIZE: tl.constexpr,
    BITS: tl.constexpr,
    VALS_PER_BYTE: tl.constexpr,
    QJL_SCALE,
    SM_SCALE,
    BLOCK_N: tl.constexpr,
    WAVE_SIZE: tl.constexpr = 32,  # STRIX HALO OPTIMIZATION
):
    pid_bh = tl.program_id(0)
    BIT_MASK: tl.constexpr = (1 << BITS) - 1

    # Online softmax state
    m_i = tl.zeros([1], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([1], dtype=tl.float32)
    acc = tl.zeros([D], dtype=tl.float32)

    num_blocks = tl.cdiv(N, BLOCK_N)

    for block_idx in range(num_blocks):
        n_start = block_idx * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offs < N

        # 1. MSE Score (PolarQuant)
        mse_scores = tl.zeros([BLOCK_N], dtype=tl.float32)
        for byte_idx in range(PACKED_D_MSE):
            packed = tl.load(
                MSE_ptr + pid_bh * stride_m_bh + n_offs * stride_m_n + byte_idx * stride_m_d,
                mask=n_mask,
                other=0,
            ).to(tl.int32)
            for sub in range(VALS_PER_BYTE):
                coord_idx = byte_idx * VALS_PER_BYTE + sub
                if coord_idx < D:
                    idx = (packed >> (sub * BITS)) & BIT_MASK
                    centroid_val = tl.load(CENTROIDS_ptr + idx)
                    q_val = tl.load(Q_ROT_ptr + pid_bh * stride_q_bh + coord_idx * stride_q_d).to(
                        tl.float32
                    )
                    mse_scores += q_val * centroid_val
        key_norms = tl.load(
            NORMS_ptr + pid_bh * stride_n_bh + n_offs * stride_n_n, mask=n_mask, other=0.0
        ).to(tl.float32)
        mse_scores = mse_scores * key_norms

        # 2. QJL Score (Error Correction)
        qjl_dot = tl.zeros([BLOCK_N], dtype=tl.float32)
        for byte_idx in range(PACKED_D_SIGNS):
            packed = tl.load(
                SIGNS_ptr + pid_bh * stride_s_bh + n_offs * stride_s_n + byte_idx * stride_s_d,
                mask=n_mask,
                other=0,
            ).to(tl.int32)
            for bit in range(8):
                coord_idx = byte_idx * 8 + bit
                if coord_idx < D:
                    sign_bit = (packed >> bit) & 1
                    sign_val = tl.where(sign_bit == 1, 1.0, -1.0)
                    q_val = tl.load(
                        Q_SKETCH_ptr + pid_bh * stride_q_bh + coord_idx * stride_q_d
                    ).to(tl.float32)
                    qjl_dot += q_val * sign_val
        res_norms = tl.load(
            RES_NORMS_ptr + pid_bh * stride_rn_bh + n_offs * stride_rn_n, mask=n_mask, other=0.0
        ).to(tl.float32)
        qjl_scores = qjl_dot * res_norms * QJL_SCALE

        # 3. Combine + Softmax
        scores = (mse_scores + qjl_scores) * SM_SCALE
        scores = tl.where(n_mask, scores, float("-inf"))
        m_new = tl.maximum(m_i, tl.max(scores, 0))
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new)
        l_i = l_i * alpha + tl.sum(p, 0)
        acc = acc * alpha

        # 4. Weighted Value Accumulation
        d_offs = tl.arange(0, D)
        v_quant = tl.load(
            V_DATA_ptr
            + pid_bh * stride_v_bh
            + n_offs[:, None] * stride_v_n
            + d_offs[None, :] * stride_v_d,
            mask=n_mask[:, None],
            other=0,
        ).to(tl.float32)
        g_offs = d_offs // GROUP_SIZE
        v_scale = tl.load(
            V_SCALES_ptr
            + pid_bh * stride_vs_bh
            + n_offs[:, None] * stride_vs_n
            + g_offs[None, :] * stride_vs_g,
            mask=n_mask[:, None],
            other=1.0,
        ).to(tl.float32)
        v_zero = tl.load(
            V_ZEROS_ptr
            + pid_bh * stride_vz_bh
            + n_offs[:, None] * stride_vz_n
            + g_offs[None, :] * stride_vz_g,
            mask=n_mask[:, None],
            other=0.0,
        ).to(tl.float32)
        v_dequant = v_quant * v_scale + v_zero
        acc += tl.sum(p[:, None] * v_dequant, 0)
        m_i = m_new

    acc = acc / l_i
    tl.store(OUT_ptr + pid_bh * stride_o_bh + d_offs * stride_o_d, acc)


# --- HIP Load-Inline (Wave32 Hardware Lock) ---

HIP_WAVE32_SRC = r"""
#include <hip/hip_runtime.h>

__global__ void __launch_bounds__(32) wave32_identity_kernel(float* out) {
    // Identity kernel to verify Wave32 alignment
    if (threadIdx.x == 0) {
        #if defined(__AMDGCN_WAVEFRONT_SIZE) && __AMDGCN_WAVEFRONT_SIZE == 32
            *out = 32.0f;
        #else
            *out = 64.0f;
        #endif
    }
}

float check_wave_size() {
    float* d_out;
    float h_out = 0;
    hipMalloc(&d_out, sizeof(float));
    wave32_identity_kernel<<<1, 32>>>(d_out);
    hipMemcpy(&h_out, d_out, sizeof(float), hipMemcpyDeviceToHost);
    hipFree(d_out);
    return h_out;
}
"""


class TurboKVKernel:
    def __init__(self):
        self.has_wave32 = False
        if torch.cuda.is_available():
            try:
                # Force gfx1151 overrides
                os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.5.1"
                os.environ["PYTORCH_ROCM_ARCH"] = "gfx1151"

                # Check for Wave32 support via inline HIP
                # Note: This is a diagnostic step to ensure we aren't "silently locked"
                self.diag_module = load_inline(
                    name="wave32_diag",
                    cpp_sources=["float check_wave_size();"],
                    cuda_sources=[HIP_WAVE32_SRC],
                    functions=["check_wave_size"],
                    extra_cuda_cflags=["-mwavefrontsize32", "--offload-arch=gfx1151"],
                )
                wave_size = self.diag_module.check_wave_size()
                self.has_wave32 = wave_size == 32.0
            except Exception:
                self.has_wave32 = False

    def fused_decode(
        self,
        query: torch.Tensor,
        quantized_key: ProdQuantized,
        value_quantized: ValueQuantized,
        Pi: torch.Tensor,
        S: torch.Tensor,
        centroids: torch.Tensor,
        mse_bits: int,
        qjl_scale: float,
        sm_scale: float,
        group_size: int = 32,
    ) -> torch.Tensor:
        """Fully fused attention over compressed TQ KV cache."""
        if query.dim() == 3:
            query = query.squeeze(1)
        BH, D = query.shape

        # Precompute rotations (1x1 matmul overhead)
        q_rot = torch.matmul(query.float(), Pi.T)
        q_sketch = torch.matmul(query.float(), S.T)

        mse_packed = quantized_key.mse_indices
        qjl_signs = quantized_key.qjl_signs
        norms = quantized_key.norms
        res_norms = quantized_key.residual_norms

        # Flatten batch/head
        if mse_packed.dim() > 3:
            BH_actual = mse_packed.shape[0] * mse_packed.shape[1]
            mse_packed = mse_packed.reshape(BH_actual, mse_packed.shape[2], -1)
            qjl_signs = qjl_signs.reshape(BH_actual, qjl_signs.shape[2], -1)
            norms = norms.reshape(BH_actual, -1)
            res_norms = res_norms.reshape(BH_actual, -1)

        N = mse_packed.shape[1]
        packed_d_mse = mse_packed.shape[2]
        packed_d_signs = qjl_signs.shape[2]

        v_data = value_quantized.data
        v_scales = value_quantized.scales
        v_zeros = value_quantized.zeros

        N_GROUPS = D // group_size
        # Packing mapping
        bits_map = {1: (1, 8), 2: (2, 4), 3: (4, 2), 4: (4, 2)}
        eff_bits, vals_per_byte = bits_map.get(mse_bits, (8, 1))

        out = torch.zeros(BH, D, device=query.device, dtype=torch.float32)
        BLOCK_N = min(64, triton.next_power_of_2(N))

        # Launch GFX1151 Optimized Kernel
        _turbo_kv_fused_decode_kernel_gfx1151[(BH,)](
            q_rot,
            q_sketch,
            mse_packed,
            qjl_signs,
            norms,
            res_norms,
            centroids,
            v_data,
            v_scales,
            v_zeros,
            out,
            q_rot.stride(0),
            q_rot.stride(1),
            mse_packed.stride(0),
            mse_packed.stride(1),
            mse_packed.stride(2),
            qjl_signs.stride(0),
            qjl_signs.stride(1),
            qjl_signs.stride(2),
            norms.stride(0),
            norms.stride(1),
            res_norms.stride(0),
            res_norms.stride(1),
            v_data.stride(0),
            v_data.stride(1),
            v_data.stride(2),
            v_scales.stride(0),
            v_scales.stride(1),
            v_scales.stride(2),
            v_zeros.stride(0),
            v_zeros.stride(1),
            v_zeros.stride(2),
            out.stride(0),
            out.stride(1),
            N=N,
            D=D,
            PACKED_D_MSE=packed_d_mse,
            PACKED_D_SIGNS=packed_d_signs,
            N_GROUPS=N_GROUPS,
            GROUP_SIZE=group_size,
            BITS=eff_bits,
            VALS_PER_BYTE=vals_per_byte,
            QJL_SCALE=qjl_scale,
            SM_SCALE=sm_scale,
            BLOCK_N=BLOCK_N,
            num_warps=4 if self.has_wave32 else 8,
        )

        return out.to(query.dtype)
