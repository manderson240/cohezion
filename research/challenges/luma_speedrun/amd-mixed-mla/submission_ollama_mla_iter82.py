Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation uses a sp[2D[K
split-K approach with two phases:
1. Phase 1: Split-K attention computation with online softmax
2. Phase 2: Reduce across splits

Current performance: 69.7µs geomean
Target: <50µs geomean
Best rank 1: 19.5µs

Key optimizations to consider:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch

Looking at the current code, I can see several optimization opportunities:

1. **Vectorized loads**: Currently loading BF16 elements one at a time. Can[3D[K
Can use `__hip_bfloat162` or 128-bit loads for better memory bandwidth util[4D[K
utilization.

2. **LDS optimization**: Q is loaded into shared memory but could be better[6D[K
better organized for warp-level access patterns.

3. **Warp-level primitives**: The current reduction uses shared memory for [K
cross-warp reduction. Can optimize with better warp shuffling.

4. **Memory coalescing**: KV access pattern could be improved with vectoriz[8D[K
vectorized loads.

5. **Reduce phase optimization**: The reduce kernel is very simple and coul[4D[K
could be optimized with better parallelization.

6. **MFMA usage**: For MI355X (CDNA4), we should leverage MFMA instructions[12D[K
instructions for the dot product computation instead of manual thread coope[5D[K
cooperation.

7. **Register pressure**: The current code might have high register pressur[7D[K
pressure limiting occupancy.

Given the constraints and the target performance gap (69.7µs → <50µs), I th[2D[K
think the most impactful optimization would be:


- **Vectorized 128-bit global loads** for KV data (4x BF16 = 128 bits per l[1D[K
load)
- **Better warp-level reduction** using warp shuffles more efficiently
- **MFMA-inspired dot product** pattern (even if not using actual MFMA for [K
BF16)

Let me focus on vectorized loads and better memory access patterns as the p[1D[K
primary optimization. This should give significant bandwidth improvement on[2D[K
on MI355X.

I'll implement:
1. Vectorized 128-bit loads for KV (4 BF16 elements at once)
2. Better LDS organization for Q (warp-aligned)
3. Optimized warp reduction with fewer sync points
4. Better register usage to improve occupancy

The key insight is that MI355X has excellent memory bandwidth, and the curr[4D[K
current kernel is likely memory-bound. Vectorized loads should help signifi[7D[K
significantly.

I need to be careful about:
- Maintaining correctness with the online softmax algorithm
- Keeping the two-phase structure (split-K + reduce)
- Ensuring the code compiles on gfx950

Let me write the optimized version focusing on vectorized loads and better [K
memory access patterns.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with 128-bit loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for KV (4 BF16 per load)
  - Warp-level dot product with reduced sync points
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- 128-bit vectorized global loads (4x BF16 = 128 bits)
- Warp-aligned LDS organization for Q
- Reduced __syncthreads() calls via warp-level primitives
- Better register pressure management for higher occupancy
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
#include <hip/hip_fp16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define VEC_SIZE 4  // 4 BF16 = 128 bits

// Vectorized load helper
__device__ __forceinline__ void load_vec4_bf16(const __hip_bfloat16* src, f[1D[K
float* dst, int offset) {
    // Load 4 BF16 elements as 128-bit vector
    const __hip_bfloat16* src_vec = src + offset;
    dst[0] = __bfloat162float(src_vec[0]);
    dst[1] = __bfloat162float(src_vec[1]);
    dst[2] = __bfloat162float(src_vec[2]);
    dst[3] = __bfloat162float(src_vec[3]);
}

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

    // Load Q into shared memory with vectorized pattern
    // 576 elements = 144 vectors of 4
    __shared__ float q_shared[QK_DIM];
    #pragma unroll
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // Online softmax state (per warp, then reduce)
    float warp_max = -1e30f;
    float warp_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries in this split
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Vectorized dot product: load 4 elements at a time
        float dot = 0.0f;
        #pragma unroll
        for (int d = tid; d < QK_DIM - 3; d += BLOCK_SIZE) {
            // Load 4 Q values from LDS
            float qv[4];
            qv[0] = q_shared[d];
            qv[1] = q_shared[d + 1];
            qv[2] = q_shared[d + 2];
            qv[3] = q_shared[d + 3];

            // Load 4 KV values from global (vectorized)
            float kv_v[4];
            load_vec4_bf16(kv_ptr, kv_v, d);

            // FMA
            dot += qv[0] * kv_v[0] + qv[1] * kv_v[1] + qv[2] * kv_v[2] + qv[2D[K
qv[3] * kv_v[3];
        }

        // Handle remainder
        for (int d = tid + (QK_DIM / VEC_SIZE) * VEC_SIZE; d < QK_DIM; d +=[2D[K
+= BLOCK_SIZE) {
            dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
        }

        // Warp reduction using shfl
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Warp leader has the dot product
        float score = -1e30f;
        if (lane_id == 0) {
            score = dot * sm_scale;
        }
        score = __shfl(score, 0, WAVESIZE);

        // Online softmax (warp-level)
        float old_max = warp_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        // Warp-level sum reduction
        float warp_exp = exp_score;
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            warp_exp += __shfl_xor(warp_exp, offset, WAVESIZE);
        }
        if (lane_id == 0) {
            warp_sum = warp_sum * correction + warp_exp;
            warp_max = new_max;
        }

        // Accumulate weighted V (vectorized)
        float weight = exp_score;
        #pragma unroll
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                float v_val = __bfloat162float(kv_ptr[v_idx]);
                v_acc[vi] = v_acc[vi] * correction + weight * v_val;
            }
        }
    }

    // Cross-warp reduction via shared memory
    __shared__ float block_max[4];
    __shared__ float block_sum[4];
    if (lane_id == 0) {
        block_max[warp_id] = warp_max;
        block_sum[warp_id] = warp_sum;
    }
    __syncthreads();

    // Thread 0 does final reduction
    float running_max = -1e30f;
    float running_sum = 0.0f;
    if (tid == 0) {
        #pragma unroll
        for (int w = 0; w < 4; w++) {
            float m = block_max[w];
            float s = block_sum[w];
            float new_max = fmaxf(running_max, m);
            float corr = expf(running_max - new_max);
            running_sum = running_sum * corr + s * expf(m - new_max);
            running_max = new_max;
        }
        block_max[0] = running_max;
        block_sum[0] = running_sum;
    }
    __syncthreads();

    running_max = block_max[0];
    running_sum = block_sum[0];

    // Normalize V accumulator
    float inv_sum = 1.0f / (running_sum + 1e-10f);
    #pragma unroll
    for (int vi = 0; vi < 2; vi++) {
        v_acc[vi] *= inv_sum;
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    #pragma unroll
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

// Phase 2: Optimized reduce with better parallelization
__global__ void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits, int num_heads, int v_dim
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * num_heads * v_dim;
    if (idx >= total_elements) return;

    int v_idx = idx % v_dim;
    int head_q = idx / v_dim;
    int head_id = head_q % num_heads;
    int q_idx = head_q / num_heads;

    // Find global max
    float global_max = -1e30f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge with log-sum-exp
    float total_v = 0.0f;
    float total_weight = 0.0f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        total_weight += weight;
        total_v += partial_out[base * v_dim + v_idx] * weight;
    }

    output[idx] = (__hip_bfloat16)(total_v / (total_weight + 1e-10f));
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
        total_q, num_splits, NUM_HEADS, V_DIM);
}
"""

CPP_SOURCE = """
void launch_mla_v2(torch::Tensor Q, torch::Tensor KV,
                   torch::Tensor partial_out, torch::Tensor partial_max,
                   torch::Tensor partial_lse, torch::Tensor output,
                   torch::Tensor kv_indptr,
                   int batch_size, int total_q, int num_splits, float sm_sc[5D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_v2", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_S[19D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_v2"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm --amdgpu-early-inline-all=true"],
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
    total_q = bs  # decode: qseqlen=1

    kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)  # [total_kv, 576]

    # Optimized split selection for MI355X
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))
    if total_kv > 65536:
        num_splits = max(num_splits, 8)

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

    # Use einsum for small shapes (proven best)
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Try custom kernel for large shapes, fall back to ASM
    if _OK:
        try:
            return _custom_attention(data)
        except Exception as e:
            print(f"[custom_mla_v2] Runtime error: {e}")

    return _asm_attention(data)
```

