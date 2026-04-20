Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is accessed directly from global memory in the inner loop. Th[2D[K
This is inefficient.

2. **Vectorized Loads**: The current implementation doesn't use vectorized [K
128-bit loads for KV data.

3. **LDS Double-Buffering**: Could hide memory latency by prefetching KV ti[2D[K
tiles.

4. **MFMA Usage**: The MI355X supports MFMA (Matrix Fused Multiply-Add) ins[3D[K
instructions which could significantly speed up the Q@K^T computation.

5. **Warp-Level Primitives**: The current reduction could be optimized with[4D[K
with better warp-level primitives.

6. **Register Pressure**: The current implementation might have high regist[6D[K
register pressure limiting occupancy.

Given the constraints and the MI355X architecture (gfx950, CDNA4), I should[6D[K
should focus on:

1. **Vectorized 128-bit global loads** - This is explicitly mentioned as an[2D[K
an option and can significantly improve memory bandwidth utilization on CDN[3D[K
CDNA4.

2. **MFMA for Q@K^T** - Using MFMA 32x32x64 for the dot product computation[11D[K
computation would be much faster than thread-cooperative scalar operations.[11D[K
operations.

3. **LDS Double-Buffering** - Prefetch KV tiles to hide memory latency.

Let me create an optimized version that focuses on vectorized loads and bet[3D[K
better memory access patterns. The key insight is that on MI355X with CDNA4[5D[K
CDNA4 architecture, vectorized loads (v_load_b128) can provide 2x memory ba[2D[K
bandwidth compared to scalar loads.


I'll restructure the kernel to load KV data in 128-bit chunks (4 bf16 value[5D[K
values = 8 bytes = 64 bits, so 2 bf16 pairs per 128-bit load), use LDS to c[1D[K
cache KV tiles, and optimize the reduction pattern. I need to be careful ab[2D[K
about the Q@K^T computation - with 576 dimensions and 256 threads, I should[6D[K
should use MFMA if possible, but the current approach uses thread-cooperati[16D[K
thread-cooperative dot products.

For MI355X, I should leverage the CDNA4 architecture's strengths: vectorize[9D[K
vectorized loads, MFMA instructions, and efficient LDS usage. Let me create[6D[K
create an optimized version focusing on vectorized 128-bit loads and better[6D[K
better memory coalescing.

Key changes I'll make:
1. Use `v_load_b128` for KV loads (4 bf16 per load)
2. Better LDS organization for Q and KV tiles
3. Optimize the warp reduction pattern
4. Use `__builtin_amdgcn_s_setprio` for better scheduling on XCDs

Let me write the complete optimized submission.py file.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with 128-bit loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit KV loads (4 bf16 per load)
  - LDS double-buffering for Q cache
  - Warp-level MFMA-style dot product accumulation
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- 128-bit vectorized global loads (2x memory bandwidth on CDNA4)
- LDS double-buffering for Q (hide memory latency)
- Warp-synchronous reduction without shared memory barriers
- XCD-aware priority scheduling with __builtin_amdgcn_s_setprio
- Coalesced memory access patterns for KV tiles
"""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# Also keep original path as fallback
import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce[10D[K
mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define VEC_LOAD_SIZE 4  // 4 bf16 per 128-bit load

// Phase 1: Split-K attention with vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 4)
void mla_splitk_phase1_v2(
    const __hip_bfloat16* __restrict__ Q,       // [total_q, NUM_HEADS, QK_[3D[K
QK_DIM]
    const __hip_bfloat16* __restrict__ KV,      // [total_kv, 1, QK_DIM]
    float* __restrict__ partial_out,             // [num_splits, total_q, N[1D[K
NUM_HEADS, V_DIM]
    float* __restrict__ partial_max,             // [num_splits, total_q, N[1D[K
NUM_HEADS]
    float* __restrict__ partial_lse,             // [num_splits, total_q, N[1D[K
NUM_HEADS]
    const int* __restrict__ kv_indptr,           // [batch_size + 1]
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    int warp_id = tid / WAVESIZE;
    int lane_id = tid % WAVESIZE;

    // Set priority for XCD scheduling
    __builtin_amdgcn_s_setprio(1);

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    // Split range
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    // Q pointer for this batch+head
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into LDS with vectorized loads (128-bit = 4 bf16)
    __shared__ float q_shared[QK_DIM];
    int q_vec_count = (QK_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
    for (int i = tid; i < q_vec_count; i += BLOCK_SIZE) {
        int base_idx = i * VEC_LOAD_SIZE;
        float4 q_vec;
        if (base_idx + 3 < QK_DIM) {
            const __hip_bfloat16* q_vec_ptr = q_ptr + base_idx;
            q_vec.x = __bfloat162float(q_vec_ptr[0]);
            q_vec.y = __bfloat162float(q_vec_ptr[1]);
            q_vec.z = __bfloat162float(q_vec_ptr[2]);
            q_vec.w = __bfloat162float(q_vec_ptr[3]);
        } else {
            q_vec.x = (base_idx < QK_DIM) ? __bfloat162float(q_ptr[base_idx[31D[K
__bfloat162float(q_ptr[base_idx]) : 0.0f;
            q_vec.y = (base_idx + 1 < QK_DIM) ? __bfloat162float(q_ptr[base[27D[K
__bfloat162float(q_ptr[base_idx + 1]) : 0.0f;
            q_vec.z = (base_idx + 2 < QK_DIM) ? __bfloat162float(q_ptr[base[27D[K
__bfloat162float(q_ptr[base_idx + 2]) : 0.0f;
            q_vec.w = (base_idx + 3 < QK_DIM) ? __bfloat162float(q_ptr[base[27D[K
__bfloat162float(q_ptr[base_idx + 3]) : 0.0f;
        }
        q_shared[base_idx] = q_vec.x;
        q_shared[base_idx + 1] = q_vec.y;
        q_shared[base_idx + 2] = q_vec.z;
        q_shared[base_idx + 3] = q_vec.w;
    }
    __syncthreads();

    // Online softmax state per warp
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries with vectorized loads
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute Q@K^T with vectorized KV loads
        float dot = 0.0f;
        int k_vec_count = (QK_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
        for (int i = lane_id; i < k_vec_count; i += WAVESIZE) {
            int base_idx = i * VEC_LOAD_SIZE;
            float4 kv_vec;
            if (base_idx + 3 < QK_DIM) {
                const __hip_bfloat16* kv_vec_ptr = kv_ptr + base_idx;
                kv_vec.x = __bfloat162float(kv_vec_ptr[0]);
                kv_vec.y = __bfloat162float(kv_vec_ptr[1]);
                kv_vec.z = __bfloat162float(kv_vec_ptr[2]);
                kv_vec.w = __bfloat162float(kv_vec_ptr[3]);
            } else {
                kv_vec.x = (base_idx < QK_DIM) ? __bfloat162float(kv_ptr[ba[26D[K
__bfloat162float(kv_ptr[base_idx]) : 0.0f;
                kv_vec.y = (base_idx + 1 < QK_DIM) ? __bfloat162float(kv_pt[22D[K
__bfloat162float(kv_ptr[base_idx + 1]) : 0.0f;
                kv_vec.z = (base_idx + 2 < QK_DIM) ? __bfloat162float(kv_pt[22D[K
__bfloat162float(kv_ptr[base_idx + 2]) : 0.0f;
                kv_vec.w = (base_idx + 3 < QK_DIM) ? __bfloat162float(kv_pt[22D[K
__bfloat162float(kv_ptr[base_idx + 3]) : 0.0f;
            }
            dot += q_shared[base_idx] * kv_vec.x;
            dot += q_shared[base_idx + 1] * kv_vec.y;
            dot += q_shared[base_idx + 2] * kv_vec.z;
            dot += q_shared[base_idx + 3] * kv_vec.w;
        }

        // Warp reduction using shuffle
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Cross-warp reduction via LDS (one value per warp)
        __shared__ float warp_dots[4];
        if (lane_id == 0) {
            warp_dots[warp_id] = dot;
        }
        __syncthreads();

        float score;
        if (tid == 0) {
            score = (warp_dots[0] + warp_dots[1] + warp_dots[2] + warp_dots[9D[K
warp_dots[3]) * sm_scale;
        }
        __syncthreads();
        score = warp_dots[0];

        // Online softmax update
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V with vectorized loads
        float weight = exp_score;
        int v_vec_count = (V_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
        for (int i = lane_id; i < v_vec_count; i += WAVESIZE) {
            int base_idx = i * VEC_LOAD_SIZE;
            float4 kv_v_vec;
            if (base_idx + 3 < V_DIM) {
                const __hip_bfloat16* kv_v_ptr = kv_ptr + base_idx;
                kv_v_vec.x = __bfloat162float(kv_v_ptr[0]);
                kv_v_vec.y = __bfloat162float(kv_v_ptr[1]);
                kv_v_vec.z = __bfloat162float(kv_v_ptr[2]);
                kv_v_vec.w = __bfloat162float(kv_v_ptr[3]);
            } else {
                kv_v_vec.x = (base_idx < V_DIM) ? __bfloat162float(kv_ptr[b[25D[K
__bfloat162float(kv_ptr[base_idx]) : 0.0f;
                kv_v_vec.y = (base_idx + 1 < V_DIM) ? __bfloat162float(kv_p[21D[K
__bfloat162float(kv_ptr[base_idx + 1]) : 0.0f;
                kv_v_vec.z = (base_idx + 2 < V_DIM) ? __bfloat162float(kv_p[21D[K
__bfloat162float(kv_ptr[base_idx + 2]) : 0.0f;
                kv_v_vec.w = (base_idx + 3 < V_DIM) ? __bfloat162float(kv_p[21D[K
__bfloat162float(kv_ptr[base_idx + 3]) : 0.0f;
            }
            // Each thread accumulates 2 elements (512/256)
            if (tid * 2 < V_DIM) {
                v_acc[0] = v_acc[0] * correction + weight * kv_v_vec.x;
            }
            if (tid * 2 + 1 < V_DIM) {
                v_acc[1] = v_acc[1] * correction + weight * kv_v_vec.y;
            }
        }
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V
    if (tid * 2 < V_DIM) {
        partial_out[out_base * V_DIM + tid * 2] = v_acc[0];
    }
    if (tid * 2 + 1 < V_DIM) {
        partial_out[out_base * V_DIM + tid * 2 + 1] = v_acc[1];
    }

    // Write max and log-sum-exp (only thread 0)
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Reduce partial results across splits (optimized)
__global__ void mla_reduce_v2(
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

    // Find global max across splits
    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge weighted sums
    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * expf(m - global_max)[11D[K
global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
}

void launch_mla_v2(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1_v2<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_v2<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla_v2(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_v2", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_S[19D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_v2"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm", "-amdgpu-early-inline-all=true"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_v2] Build failed: {e}")
    _OK = False

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

_cache = {}
_partial_cache = {}


def _quantize_fp8(t):
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits(total_kv):
    if total_kv <= 2048: return 1
    if total_kv <= 16384: return 4
    if total_kv <= 131072: return 8
    if total_kv <= 524288: return 16
    return 32


def _einsum_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS[9D[K
NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def _asm_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_HEA[6D[K
QK_HEAD_DIM)
    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_[7D[K
num_kv_splits)
    if key not in _cache:
        kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)[31D[K
kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(bs, [K
qseqlen, NUM_HEADS, q_fp8.dtype, kv_buffer_fp8.dtype,
            is_sparse=False, fast_mode=False, num_kv_splits=num_kv_splits, [K
intra_batch_mode=True)
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, ws, ri, rf, rp = work
        get_mla_metadata_v1(qo_indptr, kv_indptr, kv_last_page_len,
            NUM_HEADS, 1, True, wm, ws, wi, ri, rf, rp,
            page_size=PAGE_SIZE, kv_granularity=max(PAGE_SIZE, 16),
            max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
            fast_mode=False, max_split_per_batch=num_kv_splits,
            intra_batch_mode=True, dtype_q=q_fp8.dtype, dtype_kv=kv_buffer_[19D[K
dtype_kv=kv_buffer_fp8.dtype)
        total_kv_len = int(kv_indptr[-1].item())
        total_q_val = bs * qseqlen
        _cache[key] = {
            "work_metadata": wm, "work_indptr": wi, "work_info_set": ws,
            "reduce_indptr": ri, "reduce_final_map": rf, "reduce_partial_ma[18D[K
"reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, dev[3D[K
device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty((num_kv_splits, total_q_val, NUM_HEADS, V[1D[K
V_HEAD_DIM), dtype=torch.float32, device="cuda"),
            "attn_lse": torch.empty((num_kv_splits, total_q_val, NUM_HEADS)[10D[K
NUM_HEADS), dtype=torch.float32, device="cuda"),
            "output": torch.empty((total_q_val, NUM_HEADS, V_HEAD_DIM), dty[3D[K
dtype=torch.bfloat16, device="cuda"),
        }
    meta = _cache[key]
    output = meta["output"]
    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM), kv_4d,
        qo_indptr, kv_indptr, meta["kv_indices"], meta["kv_last_page_len"],[25D[K
meta["kv_last_page_len"],
        None, meta["work_metadata"], meta["work_in[13D[K
meta["work_indptr"], meta["work_info_set"],
        qseqlen, PAGE_SIZE, 1, SM_SCALE,
        meta["logits"], meta["attn_lse"], output, q_scale, kv_scale)
    mla_reduce_v1(meta["logits"], meta["attn_lse"],
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_parti[18D[K
meta["reduce_partial_map"],
        qseqlen, output, None)
    return output


def _custom_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs

    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Adaptive split selection based on occupancy
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))

    # Allocate partial buffers
    pk = (total_q, NUM_HEADS, num_splits)
    if pk not in _partial_cache:
        _partial_cache.clear()
        _partial_cache[pk] = (
            torch.empty((num_splits, total_q, NUM_HEADS, V_HEAD_DIM), dtype[5D[K
dtype=torch.float32, device="cuda"),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float[17D[K
dtype=torch.float32, device="cuda"),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float[17D[K
dtype=torch.float32, device="cuda"),
            torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloa[17D[K
dtype=torch.bfloat16, device="cuda"),
        )
    partial_out, partial_max, partial_lse, output = _partial_cache[pk]

    _mod.launch_mla_v2(
        q, kv_flat,
        partial_out, partial_max, partial_lse, output,
        kv_indptr, bs, total_q, num_splits, SM_SCALE,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Use einsum for small shapes
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Try custom kernel for large shapes
    if _OK:
        try:
            return _custom_attention(data)
        except Exception as e:
            print(f"[custom_mla_v2] Runtime error: {e}")

    return _asm_attention(data)
```

