#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Random Fourier Features for Attention - Kernel Approximation.

Random Fourier Features Concept:
- Standard attention: softmax(Q @ K^T) = exp(Q @ K^T)
- Kernel view: attention as kernel function
- RFF: Approximate kernel via random feature maps
- Complexity: O(D) vs O(S) where D << S

Kernel Approximation:
- Shift-invariant kernel: k(x,y) = k(x-y)
- Bochner's theorem: k is Fourier transform of probability measure
- RFF: Draw random frequencies from p(ω)
- Feature map: φ(x) = [cos(ω^T x), sin(ω^T x)]
- Approximation: k(x,y) ≈ φ(x)^T φ(y)

Benefits for Attention:
- Linear complexity in sequence length
- Fixed-size feature maps
- Approximates softmax kernel
- No materialization of attention matrix

Implementation:
1. Draw random Fourier frequencies
2. Compute feature maps for Q and K
3. Approximate attention via feature inner products
4. Reduced memory: O(D) per position

Reference: "Random Features for Large-Scale Kernel Machines", NIPS 2007.
"""

from __future__ import annotations

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import math

import torch
from aiter import dtypes as aiter_dtypes
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256
#define NUM_FEATURES 256  // Number of random Fourier features

// Random Fourier Features for attention
__global__ void rff_attention_phase1(
    const __hip_bfloat16* __restrict__ Q,       // [total_q, NUM_HEADS, QK_DIM]
    const __hip_bfloat16* __restrict__ KV,      // [total_kv, 1, QK_DIM]
    const float* __restrict__ omega,            // [NUM_FEATURES, QK_DIM] random frequencies
    float* __restrict__ phi_Q,                  // [total_q, NUM_HEADS, 2*NUM_FEATURES]
    float* __restrict__ partial_out,
    float* __restrict__ partial_max,
    float* __restrict__ partial_lse,
    const int* __restrict__ kv_indptr,
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;

    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    if (kv_len == 0) return;

    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // Compute RFF for query: φ(q) = [cos(ω^T q), sin(ω^T q)]
    __shared__ float q_features[2 * NUM_FEATURES];

    for (int f = tid; f < NUM_FEATURES; f += BLOCK_SIZE) {
        // Compute ω^T q for this feature
        float proj = 0.0f;
        for (int d = 0; d < QK_DIM; d++) {
            proj += omega[f * QK_DIM + d] * __bfloat162float(q_ptr[d]);
        }

        // Apply feature map
        q_features[f] = cosf(proj);           // Cosine component
        q_features[f + NUM_FEATURES] = sinf(proj);  // Sine component
    }
    __syncthreads();

    // Compute attention via RFF: φ(q)^T φ(k) ≈ exp(q^T k)
    // But we actually compute attention directly with softmax
    // RFF helps with linear approximation

    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute RFF for key (on-the-fly)
        float k_proj = 0.0f;
        #pragma unroll 4
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            // Cooperative reduction
            float val = omega[tid % NUM_FEATURES * QK_DIM + d] *
                       __bfloat162float(kv_ptr[d]);
            k_proj += val;
        }

        // Warp reduction for projection
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            k_proj += __shfl_xor(k_proj, offset, WAVESIZE);
        }

        // Approximate kernel via RFF
        // k(q, k) ≈ φ(q)^T φ(k)
        __shared__ float k_features[2 * NUM_FEATURES];
        if (tid < NUM_FEATURES) {
            k_features[tid] = cosf(k_proj);
            k_features[tid + NUM_FEATURES] = sinf(k_proj);
        }
        __syncthreads();

        // Compute approximate kernel value
        float kernel_approx = 0.0f;
        if (tid == 0) {
            for (int f = 0; f < 2 * NUM_FEATURES; f++) {
                kernel_approx += q_features[f] * k_features[f];
            }
            // Normalize by dimension
            kernel_approx /= (2.0f * NUM_FEATURES);
        }

        __shared__ float shared_score;
        if (tid == 0) {
            shared_score = kernel_approx;
        }
        __syncthreads();

        float score = shared_score;

        // Online softmax update
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Reduce phase
__global__ void rff_reduce(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * NUM_HEADS * V_DIM;
    if (idx >= total_elements) return;

    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % NUM_HEADS;
    int q_idx = head_q / NUM_HEADS;

    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float lse = partial_lse[base];
        total_weight += expf(lse - global_max);
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[base] - global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
}

void launch_rff_attention(
    torch::Tensor Q, torch::Tensor KV, torch::Tensor omega,
    torch::Tensor phi_Q, torch::Tensor partial_out,
    torch::Tensor partial_max, torch::Tensor partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    rff_attention_phase1<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        omega.data_ptr<float>(),
        phi_Q.data_ptr<float>(),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    rff_reduce<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_rff_attention(
    torch::Tensor Q, torch::Tensor KV, torch::Tensor omega,
    torch::Tensor phi_Q, torch::Tensor partial_out,
    torch::Tensor partial_max, torch::Tensor partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale);
"""

try:
    _mod = load_inline(
        name="mla_rff",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_rff_attention"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[mla_rff] Build failed: {e}")
    _OK = False

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Number of random Fourier features
NUM_RANDOM_FEATURES = 256

_cache = {}
_partial_cache = {}
_omega_cache = {}


def _get_random_fourier_features(
    dim: int, num_features: int, device: str, sigma: float = 1.0
) -> torch.Tensor:
    """Generate random Fourier frequencies for Gaussian kernel.

    For Gaussian kernel k(x,y) = exp(-||x-y||^2 / 2*sigma^2),
    random frequencies drawn from N(0, 1/sigma^2).

    Args:
        dim: Input dimension
        num_features: Number of random features
        device: Target device
        sigma: Kernel bandwidth

    Returns:
        Random frequencies [num_features, dim]
    """
    cache_key = (dim, num_features, device, sigma)

    if cache_key not in _omega_cache:
        # Draw from Gaussian
        omega = torch.randn(num_features, dim, device=device) / sigma
        _omega_cache[cache_key] = omega

    return _omega_cache[cache_key]


def _random_fourier_features(
    x: torch.Tensor, omega: torch.Tensor, return_both: bool = True
) -> torch.Tensor:
    """Compute Random Fourier Features.

    φ(x) = [cos(ω^T x), sin(ω^T x)] / sqrt(num_features)

    Args:
        x: Input [..., dim]
        omega: Random frequencies [num_features, dim]
        return_both: Return concatenated cos and sin

    Returns:
        RFF features [..., 2*num_features] or [..., num_features]
    """
    # Project: ω @ x^T
    proj = torch.matmul(x, omega.T)  # [..., num_features]

    # Apply feature map
    cos_features = torch.cos(proj)
    sin_features = torch.sin(proj)

    if return_both:
        features = torch.cat([cos_features, sin_features], dim=-1)
        features = features / math.sqrt(omega.shape[0])
    else:
        features = cos_features / math.sqrt(omega.shape[0])

    return features


def _approximate_attention_via_rff(
    Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, omega: torch.Tensor, num_features: int
) -> torch.Tensor:
    """Approximate attention using Random Fourier Features.

    softmax(Q @ K^T) @ V ≈ normalize(RFF(Q) @ RFF(K)^T) @ V

    But more efficiently:
    = RFF(Q) @ (RFF(K)^T @ V)

    Args:
        Q: Queries [B, H, D]
        K: Keys [B, S, D]
        V: Values [B, S, D_v]
        omega: Random frequencies
        num_features: Number of random features

    Returns:
        Attention output [B, H, D_v]
    """
    B, H, D = Q.shape
    S = K.shape[1]
    D_v = V.shape[-1]

    # Compute RFF for Q and K
    phi_Q = _random_fourier_features(Q, omega)  # [B, H, 2*F]
    phi_K = _random_fourier_features(K, omega)  # [B, S, 2*F]

    # Approximate attention
    # φ(Q) @ (φ(K)^T @ V) / normalization
    KV = torch.matmul(phi_K.transpose(-2, -1), V)  # [B, 2*F, D_v]
    output = torch.matmul(phi_Q, KV)  # [B, H, D_v]

    # Normalize
    norm = torch.sum(phi_Q**2, dim=-1, keepdim=True) ** 0.5
    output = output / (norm + 1e-6)

    return output


def _einsum_rff_attention(data):
    """Einsum attention with Random Fourier Features approximation.

    Args:
        data: Input tuple

    Returns:
        Attention output
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)

    # Extract Q, K, V
    queries = qr.view(bs, NUM_HEADS, QK_HEAD_DIM)
    keys = kv.view(bs, kvseqlen, QK_HEAD_DIM)
    values = kv[:, :, :V_HEAD_DIM].view(bs, kvseqlen, V_HEAD_DIM)

    # Get random Fourier features
    omega = _get_random_fourier_features(QK_HEAD_DIM, NUM_RANDOM_FEATURES, q.device, sigma=1.0)

    # Approximate attention
    output = _approximate_attention_via_rff(queries, keys, values, omega, NUM_RANDOM_FEATURES)

    return output.reshape(-1, NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def custom_kernel(data: input_t) -> output_t:
    """MLA kernel with Random Fourier Features for linear attention.

    Args:
        data: Input tuple (q, kv_data, qo_indptr, kv_indptr, config)

    Returns:
        Attention output tensor
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs

    # Use RFF for long sequences
    use_rff = kvseqlen >= 2048

    if not use_rff:
        # Standard einsum for shorter sequences
        kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
        qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)

        scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v = kv[:, :, :V_HEAD_DIM]
        output = (
            torch.einsum("bnqs,bsd->bqnd", weights, v)
            .reshape(-1, NUM_HEADS, V_HEAD_DIM)
            .to(torch.bfloat16)
        )

        return output

    # Use RFF approximation
    if _OK:
        try:
            print("[RFF] Using Random Fourier Features approximation")

            # Get omega
            omega = _get_random_fourier_features(QK_HEAD_DIM, NUM_RANDOM_FEATURES, q.device)

            # Prepare buffers
            kv_bf16 = kv_data["bf16"]
            kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

            num_splits = max(1, min(16, 304 // (bs * NUM_HEADS)))

            # Allocate
            pk = (total_q, NUM_HEADS, num_splits)
            if pk not in _partial_cache:
                _partial_cache.clear()
                _partial_cache[pk] = (
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS, V_DIM), dtype=torch.float32, device="cuda"
                    ),
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"
                    ),
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"
                    ),
                    torch.empty((total_q, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"),
                    torch.empty(
                        (total_q, NUM_HEADS, 2 * NUM_RANDOM_FEATURES),
                        dtype=torch.float32,
                        device="cuda",
                    ),
                )
            partial_out, partial_max, partial_lse, output, phi_Q = _partial_cache[pk]

            # Launch kernel
            _mod.launch_rff_attention(
                q,
                kv_flat,
                omega,
                phi_Q,
                partial_out,
                partial_max,
                partial_lse,
                output,
                kv_indptr,
                bs,
                total_q,
                num_splits,
                SM_SCALE,
            )

            return output

        except Exception as e:
            print(f"[RFF] Kernel error: {e}")

    # Fallback to einsum RFF
    return _einsum_rff_attention(data)
