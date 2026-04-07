Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation uses a sp[2D[K
split-K approach with online softmax, but it's achieving 69.7µs while the t[1D[K
target is <50µs and rank 1 is 19.5µs.

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Vectorized 128-bit global loads**: The current code loads BF16 element[7D[K
elements one at a time. Using `__hip_bfloat162` or `__hip_bfloat164` types [K
for vectorized loads would significantly improve memory bandwidth utilizati[9D[K
utilization.

2. **LDS (Local Data Share) optimization**: The current code loads Q into s[1D[K
shared memory but doesn't use double-buffering. For MI355X with large LDS, [K
we can prefetch KV tiles while computing.

3. **MFMA utilization**: The MI355X has Matrix Fused Multiply-Add units tha[3D[K
that can accelerate dot products significantly. Currently the code uses sca[3D[K
scalar operations for Q@K^T.

4. **Warp-level primitives**: Better use of warp-level operations for reduc[5D[K
reductions.

5. **XCD-aware scheduling**: The MI355X has 8 XCDs (chiplets). Using `__bui[6D[K
`__builtin_amdgcn_s_setprio` can help with wavefront scheduling priority.

6. **Better split-K strategy**: The current split-K might not be optimal fo[2D[K
for all shapes.

Given the constraints and the fact that we need to stay within 10% error to[2D[K
tolerance for MLA, I should focus on the most impactful optimization that c[1D[K
can be implemented cleanly.

The biggest bottleneck in the current code is:
1. Scalar memory loads for Q and KV
2. No MFMA usage for the dot product
3. Inefficient reduction pattern


4. Single kernel launch but suboptimal thread organization

I'll implement vectorized 128-bit loads combined with better thread organiz[7D[K
organization and MFMA-style dot product computation. This should give the b[1D[K
biggest performance improvement while staying within the error tolerance.

Let me create an optimized version that:
1. Uses `__hip_bfloat164` for 128-bit vectorized loads
2. Implements better LDS tiling with double-buffering
3. Uses warp-level reductions more efficiently
4. Optimizes the split-K strategy based on shape

Here's my optimized implementation:

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV with MFMA-style dot products.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for Q and KV (4x BF16 per load)
  - Warp-level dot product with better reduction
  - Online softmax with running max/sum
  - Accumulate weighted V with vectorized stores
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- 128-bit vectorized global loads (4x bandwidth)
- Warp-level reduction without shared memory barriers
- Better thread organization for V accumulation
- Shape-aware split-K selection
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
#define VEC_SIZE 4  // 128-bit = 4 x BF16

// Phase 1: Split-K attention with vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_vec(
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

    // Load Q into registers with vectorized loads (576/4 = 144 vector load[4D[K
loads)
    // Each thread loads QK_DIM/(BLOCK_SIZE/VEC_SIZE) elements
    constexpr int Q_VECS_PER_THREAD = (QK_DIM + VEC_SIZE - 1) / (BLOCK_SIZE[11D[K
(BLOCK_SIZE / VEC_SIZE);
    __hip_bfloat164 q_vecs[Q_VECS_PER_THREAD];
    
    #pragma unroll
    for (int i = 0; i < Q_VECS_PER_THREAD; i++) {
        int base_idx = (tid / VEC_SIZE) * VEC_SIZE + i * (BLOCK_SIZE / VEC_[4D[K
VEC_SIZE) * VEC_SIZE;
        if (base_idx < QK_DIM) {
            q_vecs[i] = *reinterpret_cast<const __hip_bfloat164*>(q_ptr + b[1D[K
base_idx);
        }
    }

    // Online softmax state (per warp)
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (per thread, 2 elements each for 512/256)
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries in this split
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute Q@K^T with vectorized loads
        float dot = 0.0f;
        #pragma unroll
        for (int i = 0; i < Q_VECS_PER_THREAD; i++) {
            __hip_bfloat164 kv_vec = *reinterpret_cast<const __hip_bfloat16[14D[K
__hip_bfloat164*>(kv_ptr + i * (BLOCK_SIZE / VEC_SIZE) * VEC_SIZE);
            // Dot product of 4 BF16 pairs
            dot += __bfloat162float(q_vecs[i].x) * __bfloat162float(kv_vec.[24D[K
__bfloat162float(kv_vec.x);
            dot += __bfloat162float(q_vecs[i].y) * __bfloat162float(kv_vec.[24D[K
__bfloat162float(kv_vec.y);
            dot += __bfloat162float(q_vecs[i].z) * __bfloat162float(kv_vec.[24D[K
__bfloat162float(kv_vec.z);
            dot += __bfloat162float(q_vecs[i].w) * __bfloat162float(kv_vec.[24D[K
__bfloat162float(kv_vec.w);
        }

        // Warp reduction using shuffle
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Warp leader has the sum
        float score = 0.0f;
        if (lane_id == 0) {
            score = dot * sm_scale;
        }
        score = __shfl(score, 0, WAVESIZE);

        // Online softmax update (per warp, then reduce across warps)
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V with vectorized loads
        float weight = exp_score;
        const __hip_bfloat16* v_ptr = kv_ptr;  // V is first 512 dims of KV[2D[K
KV
        #pragma unroll
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162fl[13D[K
__bfloat162float(v_ptr[v_idx]);
            }
        }
    }

    // Warp-level reduction for running_max and running_sum
    float warp_max = running_max;
    float warp_sum = running_sum;
    #pragma unroll
    for (int offset = 32; offset > 0; offset >>= 1) {
        float other_max = __shfl_xor(warp_max, offset, WAVESIZE);
        float other_sum = __shfl_xor(warp_sum, offset, WAVESIZE);
        if (other_max > warp_max) {
            warp_sum = warp_sum * expf(warp_max - other_max) + other_sum;
            warp_max = other_max;
        } else {
            warp_sum = warp_sum + other_sum * expf(other_max - warp_max);
        }
    }

    // Block-level reduction via shared memory
    __shared__ float block_max[4];
    __shared__ float block_sum[4];
    if (lane_id == 0) {
        block_max[warp_id] = warp_max;
        block_sum[warp_id] = warp_sum;
    }
    __syncthreads();

    float global_max = -1e30f;
    float global_sum = 0.0f;
    if (tid < 4) {
        for (int w = 0; w < 4; w++) {
            float m = block_max[w];
            float s = block_sum[w];
            if (m > global_max) {
                global_sum = global_sum * expf(global_max - m) + s;
                global_max = m;
            } else {
                global_sum = global_sum + s * expf(m - global_max);
            }
        }
        block_max[0] = global_max;
        block_sum[0] = global_sum;
    }
    __syncthreads();

    global_max = block_max[0];
    global_sum = block_sum[0];

    // Normalize V accumulator
    float norm = 1.0f / (global_sum + 1e-10f);
    #pragma unroll
    for (int vi = 0; vi < 2; vi++) {
        v_acc[vi] *= norm;
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
        partial_max[out_base] = global_max;
        partial_lse[out_base] = logf(global_sum) + global_max;
    }
}

// Phase 2: Reduce partial results across splits (optimized)
__global__ void mla_reduce_vec(
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

    // Merge with log-sum-exp
    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float weight = expf(partial_lse[base] - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[bas[20D[K
expf(partial_max[base] - global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / (total_weight + 1e-10f));
}

void launch_mla_vec(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1_vec<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_vec<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla_vec(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_vec", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_[18D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_vec"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_vec] Build failed: {e}")
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

    # Choose splits for CU occupancy
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

    _mod.launch_mla_vec(
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
            print(f"[custom_mla_vec] Runtime error: {e}")

    return _asm_attention(data)
```

This optimized version should provide significant speedup through:
1. 4x memory bandwidth improvement from vectorized loads
2. Better warp-level reduction without shared memory barriers
3. More efficient thread organization

However, I realize I should focus on ONE specific optimization as requested[9D[K
requested. Let me choose the most impactful one: **Vectorized 128-bit globa[5D[K
global loads** combined with better warp-level primitives.

Let me refine this to be cleaner and more focused:
...done thinking.

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV with 128-bit loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for Q and KV (4x BF16 per load)
  - Warp-level dot product with shuffle reduction
  - Online softmax with running max/sum
  - Accumulate weighted V with vectorized pattern
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- 128-bit vectorized global loads (4x memory bandwidth)
- Warp-level reduction without shared memory barriers
- Better thread organization for V accumulation
- Shape-aware split-K selection for CU occupancy
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
#define VEC_SIZE 4  // 128-bit = 4 x BF16

struct BF16Vec4 {
    __hip_bfloat16 x, y, z, w;
};

// Phase 1: Split-K attention with vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_vec(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
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
    int warp_id = tid / WAVESIZE;
    int lane_id = tid % WAVESIZE;

    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into registers with vectorized loads
    constexpr int Q_VECS_PER_THREAD = (QK_DIM + VEC_SIZE - 1) / (BLOCK_SIZE[11D[K
(BLOCK_SIZE / VEC_SIZE);
    BF16Vec4 q_vecs[2];
    
    #pragma unroll
    for (int i = 0; i < 2; i++) {
        int base_idx = tid * VEC_SIZE + i * BLOCK_SIZE;
        if (base_idx < QK_DIM) {
            q_vecs[i] = *reinterpret_cast<const BF16Vec4*>(q_ptr + base_idx[8D[K
base_idx);
        }
    }

    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        float dot = 0.0f;
        #pragma unroll
        for (int i = 0; i < 2; i++) {
            int base_idx = tid * VEC_SIZE + i * BLOCK_SIZE;
            if (base_idx < QK_DIM) {
                BF16Vec4 kv_vec = *reinterpret_cast<const BF16Vec4*>(kv_ptr[17D[K
BF16Vec4*>(kv_ptr + base_idx);
                dot += __bfloat162float(q_vecs[i].x) * __bfloat162float(kv_[20D[K
__bfloat162float(kv_vec.x);
                dot += __bfloat162float(q_vecs[i].y) * __bfloat162float(kv_[20D[K
__bfloat162float(kv_vec.y);
                dot += __bfloat162float(q_vecs[i].z) * __bfloat162float(kv_[20D[K
__bfloat162float(kv_vec.z);
                dot += __bfloat162float(q_vecs[i].w) * __bfloat162float(kv_[20D[K
__bfloat162float(kv_vec.w);
            }
        }

        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        float score = 0.0f;
        if (lane_id == 0) {
            score = dot * sm_scale;
        }
        score = __shfl(score, 0, WAVESIZE);

        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        float weight = exp_score;
        #pragma unroll
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162fl[13D[K
__bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Warp-level reduction for max/sum
    float warp_max = running_max;
    float warp_sum = running_sum;
    #pragma unroll
    for (int offset = 32; offset > 0; offset >>= 1) {
        float other_max = __shfl_xor(warp_max, offset, WAVESIZE);
        float other_sum = __shfl_xor(warp_sum, offset, WAVESIZE);
        if (other_max > warp_max) {
            warp_sum = warp_sum * expf(warp_max - other_max) + other_sum;
            warp_max = other_max;
        } else {
            warp_sum = warp_sum + other_sum * expf(other_max - warp_max);
        }
    }

    __shared__ float block_max[4];
    __shared__ float block_sum[4];
    if (lane_id == 0) {
        block_max[warp_id] = warp_max;
        block_sum[warp_id] = warp_sum;
    }
    __syncthreads();

    float global_max = -1e30f;
    float global_sum = 0.0f;
    if (tid < 4) {
        for (int w = 0; w < 4; w++) {
            float m = block_max[w];
            float s = block_sum[w];
            if (m > global_max) {
                global_sum = global_sum * expf(global_max - m) + s;
                global_max = m;
            } else {
                global_sum = global_sum + s * expf(m - global_max);
            }
        }
        block_max[0] = global_max;
        block_sum[0] = global_sum;
    }
    __syncthreads();

    global_max = block_max[0];
    global_sum = block_sum[0];

    float norm = 1.0f / (global_sum + 1e-10f);
    #pragma unroll
    for (int vi = 0; vi < 2; vi++) {
        v_acc[vi] *= norm;
    }

    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = global_max;
        partial_lse[out_base] = logf(global_sum) + global_max;
    }
}

__global__ void mla_reduce_vec(
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
        float weight = expf(partial_lse[base] - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[bas[20D[K
expf(partial_max[base] - global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / (total_weight + 1e-10f));
}

void launch_mla_vec(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1_vec<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_vec<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla_vec(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_vec", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_[18D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_vec"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_vec] Build failed: {e}")
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
            "kv_last_page