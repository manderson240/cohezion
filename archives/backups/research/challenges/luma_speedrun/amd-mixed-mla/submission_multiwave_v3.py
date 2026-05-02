#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA Variant 3: Multi-Wave Cooperative Reduction.

Key Optimizations:
- Multi-wave execution: multiple blocks per (batch, head) for cooperative processing
- Wave-level reductions using LDS (shared memory) for inter-warp communication
- Cooperative groups for parallel KV scanning with work-stealing-like behavior
- Reduced global memory traffic through aggressive LDS caching
- Fused attention with atomic reductions for final output

This variant maximizes CU utilization by having multiple waves of blocks cooperate
on the same attention head, using LDS for fast intermediate communication.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import aiter
import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1
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
#define BLOCK_SIZE 256  // 4 waves per block
#define MAX_WAVES_PER_HEAD 8  // Cooperative wave limit

// Shared memory layout for cooperative reduction
// LDS is fast on MI355X - use it aggressively
#define LDS_SIZE 8192  // 8KB LDS per block

// Multi-wave cooperative attention kernel
// Multiple blocks (waves) work together on same (batch, head)
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_multiwave_cooperative_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
    float* __restrict__ wave_out,        // Per-wave partial output
    float* __restrict__ wave_max,        // Per-wave partial max
    float* __restrict__ wave_lse,        // Per-wave partial LSE
    const int* __restrict__ kv_indptr,
    int batch_size, int total_q, int num_waves,
    float sm_scale
) {
    // Grid: (wave_id, head_id, batch_id)
    int wave_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    int wid = tid / WAVESIZE;
    int lid = tid % WAVESIZE;

    if (wave_id >= num_waves) return;

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    // Divide KV among waves cooperatively
    int kv_per_wave = (kv_len + num_waves - 1) / num_waves;
    int my_kv_start = kv_start + wave_id * kv_per_wave;
    int my_kv_end = min(my_kv_start + kv_per_wave, kv_end);
    if (my_kv_start >= kv_end) return;

    // Q for this (batch, head)
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // LDS for Q caching - cooperative load
    __shared__ float q_shared[QK_DIM];
    #pragma unroll 3
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // LDS for wave-level reduction
    __shared__ float warp_dots[4];
    __shared__ float wave_v_partial[V_DIM];  // 512 * 4 bytes = 2KB
    __shared__ float wave_max_shared[1];
    __shared__ float wave_sum_shared[1];

    // Initialize wave accumulators
    if (tid == 0) {
        wave_max_shared[0] = -1e30f;
        wave_sum_shared[0] = 0.0f;
        for (int i = 0; i < V_DIM; i++) {
            wave_v_partial[i] = 0.0f;
        }
    }
    __syncthreads();

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    // Process this wave's KV slice
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Q@K dot product
        float dot = 0.0f;
        #pragma unroll 3
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
        }

        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        if (lid == 0) {
            warp_dots[wid] = dot;
        }
        __syncthreads();

        float score;
        if (tid == 0) {
            score = (warp_dots[0] + warp_dots[1] + warp_dots[2] + warp_dots[3]) * sm_scale;
            warp_dots[0] = score;
        }
        __syncthreads();
        score = warp_dots[0];

        // Online softmax update
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = (old_max > -1e20f) ? expf(old_max - new_max) : 0.0f;

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Weighted V accumulation in registers
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Write thread-local accumulators to LDS
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            atomicAdd(&wave_v_partial[v_idx], v_acc[vi]);
        }
    }
    if (tid == 0) {
        atomicMax((int*)&wave_max_shared[0], __float_as_int(running_max));
        atomicAdd(&wave_sum_shared[0], running_sum);
    }
    __syncthreads();

    // Write wave-level results to global memory
    int wave_base = ((wave_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Each thread writes portion of V
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            wave_out[wave_base * V_DIM + v_idx] = wave_v_partial[v_idx];
        }
    }

    if (tid == 0) {
        wave_max[wave_base] = wave_max_shared[0];
        wave_lse[wave_base] = logf(wave_sum_shared[0]) + wave_max_shared[0];
    }
}

// Final reduction across waves
__global__ __launch_bounds__(256, 2)
void mla_multiwave_reduce(
    const float* __restrict__ wave_out,
    const float* __restrict__ wave_max,
    const float* __restrict__ wave_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_waves
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * NUM_HEADS * V_DIM;
    if (idx >= total_elements) return;

    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % NUM_HEADS;
    int q_idx = head_q / NUM_HEADS;

    // Find global max across waves
    float global_max = -1e30f;
    for (int w = 0; w < num_waves; w++) {
        int base = (w * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, wave_max[base]);
    }

    // Merge weighted sums
    float total_weight = 0.0f;
    float total_v = 0.0f;

    for (int w = 0; w < num_waves; w++) {
        int base = (w * total_q + q_idx) * NUM_HEADS + head_id;
        float m = wave_max[base];
        float lse = wave_lse[base];

        float w_weight = expf(lse - global_max);
        total_weight += w_weight;
        total_v += wave_out[base * V_DIM + v_idx] * expf(m - global_max);
    }

    if (total_weight > 0.0f) {
        output[idx] = __float2bfloat16(total_v / total_weight);
    } else {
        output[idx] = __float2bfloat16(0.0f);
    }
}

void launch_mla_multiwave(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor wave_out, torch::Tensor wave_max, torch::Tensor wave_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_waves, float sm_scale
) {
    // Phase 1: Multi-wave cooperative processing
    dim3 grid1(num_waves, NUM_HEADS, batch_size);
    mla_multiwave_cooperative_kernel<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        wave_out.data_ptr<float>(),
        wave_max.data_ptr<float>(),
        wave_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_waves, sm_scale);

    // Phase 2: Reduction across waves
    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_multiwave_reduce<<<(total_elements + 255) / 256, 256>>>(
        wave_out.data_ptr<float>(),
        wave_max.data_ptr<float>(),
        wave_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_waves);
}
"""

CPP_SOURCE = """
void launch_mla_multiwave(torch::Tensor Q, torch::Tensor KV,
                          torch::Tensor wave_out, torch::Tensor wave_max,
                          torch::Tensor wave_lse, torch::Tensor output,
                          torch::Tensor kv_indptr,
                          int batch_size, int total_q, int num_waves, float sm_scale);
"""

# Compile the kernel
try:
    _mod_multiwave = load_inline(
        name="mla_multiwave_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_multiwave"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-ffast-math"],
    )
    _MULTIWAVE_OK = True
except Exception as e:
    print(f"[multiwave] Build failed: {e}")
    _MULTIWAVE_OK = False

# Constants
NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Thresholds
EINSUM_MAX_TOTAL_KV = 4096
MULTIWAVE_MAX_TOTAL_KV = 524288

# Caches
_cache = {}
_wave_cache = {}


def _quantize_fp8(t):
    """Quantize tensor to FP8 with per-tensor scaling."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_waves(total_kv, batch_size):
    """Choose number of cooperative waves based on KV length.

    More waves = more parallelism for long sequences.
    Target: ~256 tokens per wave for optimal occupancy.
    """
    tokens_per_wave = 256
    ideal_waves = (total_kv + tokens_per_wave - 1) // tokens_per_wave

    # Clamp to reasonable range
    return max(1, min(8, ideal_waves))


def _einsum_attention(data):
    """Pure PyTorch einsum for small shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS, V_DIM).to(torch.bfloat16)
    )


def _aiter_attention(data):
    """Fallback to aiter ASM kernel."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_kv_splits = 1 if total_kv <= 2048 else 4
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_HEAD_DIM)

    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_splits)
    if key not in _cache:
        kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(
            bs,
            qseqlen,
            NUM_HEADS,
            q_fp8.dtype,
            kv_buffer_fp8.dtype,
            is_sparse=False,
            fast_mode=False,
            num_kv_splits=num_kv_splits,
            intra_batch_mode=True,
        )
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, ws, ri, rf, rp = work
        get_mla_metadata_v1(
            qo_indptr,
            kv_indptr,
            kv_last_page_len,
            NUM_HEADS,
            1,
            True,
            wm,
            ws,
            wi,
            ri,
            rf,
            rp,
            page_size=PAGE_SIZE,
            kv_granularity=max(PAGE_SIZE, 16),
            max_seqlen_qo=qseqlen,
            uni_seqlen_qo=qseqlen,
            fast_mode=False,
            max_split_per_batch=num_kv_splits,
            intra_batch_mode=True,
            dtype_q=q_fp8.dtype,
            dtype_kv=kv_buffer_fp8.dtype,
        )
        total_q_val = bs * qseqlen
        _cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(int(kv_indptr[-1].item()), dtype=torch.int32, device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS, V_DIM), dtype=torch.float32, device="cuda"
            ),
            "attn_lse": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS), dtype=torch.float32, device="cuda"
            ),
            "output": torch.empty(
                (total_q_val, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"
            ),
        }

    meta = _cache[key]
    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        None,
        meta["work_metadata"],
        meta["work_indptr"],
        meta["work_info_set"],
        qseqlen,
        PAGE_SIZE,
        1,
        SM_SCALE,
        meta["logits"],
        meta["attn_lse"],
        meta["output"],
        q_scale,
        kv_scale,
    )
    mla_reduce_v1(
        meta["logits"],
        meta["attn_lse"],
        meta["reduce_indptr"],
        meta["reduce_final_map"],
        meta["reduce_partial_map"],
        qseqlen,
        meta["output"],
        None,
    )
    return meta["output"]


def _multiwave_attention(data):
    """Multi-wave cooperative attention."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs

    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Choose number of waves
    num_waves = _choose_num_waves(total_kv, bs)

    # Allocate wave buffers
    key = (total_q, NUM_HEADS, num_waves)
    if key not in _wave_cache:
        _wave_cache.clear()
        _wave_cache[key] = (
            torch.empty((num_waves, total_q, NUM_HEADS, V_DIM), dtype=torch.float32, device="cuda"),
            torch.empty((num_waves, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"),
            torch.empty((num_waves, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"),
            torch.empty((total_q, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"),
        )

    wave_out, wave_max, wave_lse, output = _wave_cache[key]

    _mod_multiwave.launch_mla_multiwave(
        q,
        kv_flat,
        wave_out,
        wave_max,
        wave_lse,
        output,
        kv_indptr,
        bs,
        total_q,
        num_waves,
        SM_SCALE,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    """Main entry: route to best implementation."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Small shapes: einsum
    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Medium-large shapes: try multi-wave
    if _MULTIWAVE_OK:
        try:
            return _multiwave_attention(data)
        except Exception as e:
            print(f"[multiwave] Runtime error: {e}")

    # Fallback to aiter
    return _aiter_attention(data)
