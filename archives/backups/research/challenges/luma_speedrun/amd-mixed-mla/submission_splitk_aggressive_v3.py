#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA Variant 1: Aggressive Split-K with Online Softmax Optimization.

Key Optimizations:
- Aggressive KV splitting: up to 64 splits for max parallelism on MI355X (304 CUs)
- Online softmax with fused max tracking and LSE computation
- Phase fusion: combine attention score computation with softmax in single pass
- Warp-shuffle reductions minimize shared memory traffic
- Cooperative thread groups for efficient dot products over 576-dim QK

The 576-dim dot product is distributed across 256 threads with cooperative loading.
Each thread handles 2-3 elements, using warp shuffle for horizontal reduction.
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves for max occupancy

// Aggressive splitting: support up to 64 splits
#define MAX_SPLITS 64

// Phase 1: Split-K attention with aggressive parallelism
// Each block processes a thin slice of KV for one (batch, head)
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_aggressive_phase1(
    const __hip_bfloat16* __restrict__ Q,       // [total_q, NUM_HEADS, QK_DIM]
    const __hip_bfloat16* __restrict__ KV,      // [total_kv, QK_DIM]
    float* __restrict__ partial_out,            // [num_splits, total_q, NUM_HEADS, V_DIM]
    float* __restrict__ partial_max,            // [num_splits, total_q, NUM_HEADS]
    float* __restrict__ partial_lse,            // [num_splits, total_q, NUM_HEADS]
    const int* __restrict__ kv_indptr,          // [batch_size + 1]
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    // Grid: (split_id, head_id, batch_id)
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    int wid = tid / WAVESIZE;  // warp id
    int lid = tid % WAVESIZE;  // lane id

    if (split_id >= num_splits) return;

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    // Compute this split's KV range with aggressive granularity
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    // Q index for this batch (decode: qseqlen=1)
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // Cooperative Q loading: 256 threads load 576 elements
    __shared__ float q_shared[QK_DIM];
    #pragma unroll 3
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // Online softmax state per split
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator: each thread handles V_DIM / BLOCK_SIZE = 2 elements
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries in this split
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute Q@K^T: thread-cooperative dot product
        float dot = 0.0f;

        // Each thread processes 2-3 elements (576/256 ≈ 2.25)
        // Unroll for QK_DIM=576 with BLOCK_SIZE=256
        #pragma unroll 3
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            float qval = q_shared[d];
            float kval = __bfloat162float(kv_ptr[d]);
            dot += qval * kval;
        }

        // Warp-level reduction using shuffle
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Store warp results in shared memory
        __shared__ float warp_dots[4];  // 4 warps
        if (lid == 0) {
            warp_dots[wid] = dot;
        }
        __syncthreads();

        // Final reduction by thread 0, broadcast result
        float score;
        if (tid == 0) {
            score = (warp_dots[0] + warp_dots[1] + warp_dots[2] + warp_dots[3]) * sm_scale;
            warp_dots[0] = score;
        }
        __syncthreads();
        score = warp_dots[0];

        // Online softmax update with numerical stability
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = (old_max > -1e20f) ? expf(old_max - new_max) : 0.0f;

        // Update running statistics
        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V (KV[:V_DIM] is the V component)
        // V is stored in first V_DIM elements of KV
        float weight = exp_score;  // Not yet normalized
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                // Apply correction to previous accumulation
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Write partial results to global memory
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write accumulated V (will be normalized in reduction phase)
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    // Thread 0 writes max and log-sum-exp
    if (tid == 0) {
        partial_max[out_base] = running_max;
        // LSE = log(sum(exp(score - max))) + max
        partial_lse[out_base] = (running_sum > 0.0f) ? logf(running_sum) + running_max : running_max;
    }
}

// Phase 2: Log-sum-exp reduction across splits with aggressive unrolling
__global__ __launch_bounds__(256, 2)
void mla_splitk_reduce(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * NUM_HEADS * V_DIM;
    if (idx >= total_elements) return;

    // Decode linear index
    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % NUM_HEADS;
    int q_idx = head_q / NUM_HEADS;

    // Find global max across all splits for numerical stability
    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Accumulate weighted contributions
    float total_weight = 0.0f;
    float total_v = 0.0f;

    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];

        // Weight = exp(lse - global_max) gives the normalized contribution
        float w = expf(lse - global_max);
        total_weight += w;
        total_v += partial_out[base * V_DIM + v_idx] * expf(m - global_max);
    }

    // Normalize and write output
    if (total_weight > 0.0f) {
        output[idx] = __float2bfloat16(total_v / total_weight);
    } else {
        output[idx] = __float2bfloat16(0.0f);
    }
}

void launch_mla_splitk(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    // Phase 1: Split-K computation
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_aggressive_phase1<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    // Phase 2: Reduction
    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_splitk_reduce<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla_splitk(torch::Tensor Q, torch::Tensor KV,
                       torch::Tensor partial_out, torch::Tensor partial_max,
                       torch::Tensor partial_lse, torch::Tensor output,
                       torch::Tensor kv_indptr,
                       int batch_size, int total_q, int num_splits, float sm_scale);
"""

# Compile the kernel
try:
    _mod_splitk = load_inline(
        name="mla_splitk_aggressive_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_splitk"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-ffast-math"],
    )
    _SPLITK_OK = True
except Exception as e:
    print(f"[splitk_aggressive] Build failed: {e}")
    _SPLITK_OK = False

# Constants
NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Thresholds for routing
EINSUM_MAX_TOTAL_KV = 4096
MATMUL_MAX_BS = 4

# Caches
_cache = {}
_partial_cache = {}


def _quantize_fp8(t):
    """Quantize tensor to FP8 with per-tensor scaling."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits_aggressive(total_kv, batch_size):
    """Aggressive splitting strategy for max CU utilization on MI355X (304 CUs).

    More splits = more parallelism but higher reduction overhead.
    Target: enough splits to saturate all CUs.
    """
    # MI355X has 304 CUs. Each block uses 256 threads.
    # For aggressive splitting, we want many blocks per batch
    total_heads = batch_size * NUM_HEADS

    if total_kv <= 2048:
        return 1
    if total_kv <= 8192:
        return 4
    if total_kv <= 32768:
        return 8
    if total_kv <= 131072:
        return 16
    if total_kv <= 524288:
        return 32
    return 64  # Max aggressive splits


def _einsum_attention(data):
    """Pure PyTorch einsum attention for small shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
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

    num_kv_splits = _choose_num_kv_splits_aggressive(total_kv, bs)
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


def _splitk_attention(data):
    """Custom Split-K attention with aggressive splitting."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs  # decode: qseqlen=1

    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Choose aggressive splits
    num_splits = _choose_num_kv_splits_aggressive(total_kv, bs)

    # Allocate or retrieve partial buffers
    pk = (total_q, NUM_HEADS, num_splits)
    if pk not in _partial_cache:
        _partial_cache.clear()
        _partial_cache[pk] = (
            torch.empty(
                (num_splits, total_q, NUM_HEADS, V_DIM), dtype=torch.float32, device="cuda"
            ),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"),
            torch.empty((total_q, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"),
        )

    partial_out, partial_max, partial_lse, output = _partial_cache[pk]

    _mod_splitk.launch_mla_splitk(
        q,
        kv_flat,
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


def custom_kernel(data: input_t) -> output_t:
    """Main entry: route to best implementation based on shape."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Small shapes: einsum is fastest
    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Try custom aggressive split-k for medium-large shapes
    if _SPLITK_OK:
        try:
            return _splitk_attention(data)
        except Exception as e:
            print(f"[splitk_aggressive] Runtime error: {e}")

    # Fallback to aiter ASM
    return _aiter_attention(data)
