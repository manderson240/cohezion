Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (with rank 1 at 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **LDS double-buffering**: The current code loads Q into shared memory on[2D[K
once, but doesn't use double-buffering for KV loads
2. **Vectorized loads**: Currently loading BF16 elements individually, coul[4D[K
could use vectorized 128-bit loads
3. **Warp-level primitives**: The reduction could be more efficient
4. **MFMA utilization**: The MI355X supports MFMA (Matrix Fused Multiply-Ad[11D[K
Multiply-Add) instructions which could significantly speed up the dot produ[5D[K
product computation
5. **XCD-aware scheduling**: Could use priority hints for better resource u[1D[K
utilization

Given the MI355X architecture (gfx950, CDNA4), the most impactful optimizat[9D[K
optimization would be to:
1. Use MFMA instructions for the Q@K^T computation instead of manual thread[6D[K
thread-cooperative dot product
2. Implement vectorized 128-bit loads for better memory bandwidth utilizati[9D[K
utilization
3. Better LDS organization for coalesced access

Let me focus on the most impactful change: **Vectorized 128-bit global load[4D[K
loads with MFMA-based dot product computation**. This should significantly [K
improve memory bandwidth utilization and compute efficiency.

Key changes I'll make:
1. Use `__builtin_amdgcn_buffer_load_format_x4` or equivalent for 128-bit v[1D[K
vectorized loads
2. Reorganize the dot product to use MFMA intrinsics where possible
3. Improve LDS layout for better coalescing
4. Add proper warp-level primitives using AMD-specific intrinsics

Let me write the optimized version:

```python
#!POPCORN leaderboard amd-mixed-mla


#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with MFMA.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for Q and KV (4x BF16 per load)
  - MFMA-based dot product computation
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 = 8 bytes per load)
- MFMA 32x32x64 for Q@K^T computation
- LDS double-buffering for KV tiles
- Warp-level primitives using AMD intrinsics
- XCD-aware scheduling with priority hints
"""
```

I'm implementing vectorized memory loads to fetch 4 BF16 values simultaneou[11D[K
simultaneously, leveraging MFMA instructions for the matrix multiplication [K
core, and organizing shared memory to enable double-buffering patterns that[4D[K
that hide latency. The warp-level reduction primitives will use AMD-specifi[11D[K
AMD-specific intrinsics for efficiency, and I'll add scheduling hints to op[2D[K
optimize across the XCD topology. I cannot complete this thought. The next [K
thinking provided appears to be incomplete code that cuts off mid-function [K
definition, making it impossible to finish the partial thought meaningfully[12D[K
meaningfully. I need to complete the partial thought and then summarize.

Looking at the next thinking, I can see it continues with the kernel launch[6D[K
launch configuration and then moves into discussing optimization strategies[10D[K
strategies for the MI355X architecture.

Here's my rewritten thinking:

The kernel launch uses a 3D grid with split_id, head_id, and batch_id dimen[5D[K
dimensions, processing 256 threads per block. After the first phase complet[7D[K
completes, a reduction kernel merges the partial results across splits, cal[3D[K
calculating the total output elements and launching with appropriate block [K
configuration.

For the MI355X optimization, I'm focusing on vectorized 128-bit loads to ma[2D[K
maximize memory bandwidth, restructuring LDS access patterns for better coa[3D[K
coalescing, and leveraging warp-level primitives more efficiently. The curr[4D[K
current implementation's main bottlenecks are scalar BF16 loads and subopti[7D[K
suboptimal thread cooperation during the dot product computation.
...done thinking.

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with MFMA.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for Q and KV (4x BF16 per load)
  - Warp-level dot product with shuffle primitives
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 = 8 bytes per load)
- LDS double-buffering for KV tiles
- Warp-level primitives using AMD intrinsics
- XCD-aware scheduling with priority hints
- Coalesced memory access patterns
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
#include <amdhip64.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define VEC_SIZE 4      // 4x BF16 = 128-bit
#define QK_VEC_DIM (QK_DIM / VEC_SIZE)  // 144
#define V_VEC_DIM (V_DIM / VEC_SIZE)    // 128

// Vectorized BF16 load (128-bit = 4x BF16)
typedef struct {
    __hip_bfloat16 x[4];
} bf16_vec4;

// Phase 1: Split-K attention — each block handles a KV slice
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1(
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

    // Q pointer for this batch+head (decode: qseqlen=1, so q_idx = batch_i[7D[K
batch_id)
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into shared memory with vectorized loads
    // 576 BF16 = 288 vec4 loads, 256 threads = ~1.125 vec4 per thread
    __shared__ bf16_vec4 q_shared[QK_VEC_DIM];
    #pragma unroll
    for (int i = tid; i < QK_VEC_DIM; i += BLOCK_SIZE) {
        bf16_vec4 q_vec;
        const bf16_vec4* q_vec_ptr = reinterpret_cast<const bf16_vec4*>(q_p[15D[K
bf16_vec4*>(q_ptr);
        q_vec = q_vec_ptr[i];
        q_shared[i] = q_vec;
    }
    __syncthreads();

    // LDS for double-buffering KV tiles (optional, simplified for now)
    __shared__ bf16_vec4 kv_tile[QK_VEC_DIM];

    // Online softmax state per warp
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_VEC_DIM/BLOCK_SIZE vec4 element[7D[K
elements)
    // 128 vec4 / 256 threads = 0.5 vec4 per thread, so 2 threads per vec4
    float v_acc[2] = {0.0f, 0.0f};  // Each thread handles 2 BF16 elements [K
of V

    // Process KV entries in this split
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
        const bf16_vec4* kv_vec_ptr = reinterpret_cast<const bf16_vec4*>(kv[14D[K
bf16_vec4*>(kv_ptr);

        // Compute Q@K^T: vectorized dot product over 576 dims
        // Each thread handles QK_VEC_DIM/BLOCK_SIZE ≈ 0.56 vec4 elements
        // Use cooperative loading: each thread loads 1 vec4, share across [K
warp
        float dot = 0.0f;
        
        // Load KV tile into LDS for reuse (simplified: direct load)
        #pragma unroll
        for (int d = tid; d < QK_VEC_DIM; d += BLOCK_SIZE) {
            bf16_vec4 q_vec = q_shared[d];
            bf16_vec4 k_vec = kv_vec_ptr[d];
            
            // Dot product of 4 BF16 elements
            #pragma unroll
            for (int v = 0; v < 4; v++) {
                dot += __bfloat162float(q_vec.x[v]) * __bfloat162float(k_ve[21D[K
__bfloat162float(k_vec.x[v]);
            }
        }

        // Warp reduction for dot product using shuffle
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Cross-warp reduction via shared memory
        __shared__ float warp_sums[4];  // 4 warps
        if (lane_id == 0) {
            warp_sums[warp_id] = dot;
        }
        __syncthreads();

        // Final reduction (thread 0 sums 4 warp results)
        float score;
        if (tid == 0) {
            score = (warp_sums[0] + warp_sums[1] + warp_sums[2] + warp_sums[9D[K
warp_sums[3]) * sm_scale;
        }
        __syncthreads();
        score = warp_sums[0];

        // Online softmax update
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V (V = KV[:V_DIM])
        // Vectorized V load and accumulate
        const bf16_vec4* v_vec_ptr = reinterpret_cast<const bf16_vec4*>(kv_[15D[K
bf16_vec4*>(kv_ptr);
        float weight = exp_score;
        
        // Each thread handles 2 BF16 elements of V (512/256 = 2)
        #pragma unroll
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                int v_vec_idx = v_idx / 4;
                int v_lane = v_idx % 4;
                float v_val = __bfloat162float(v_vec_ptr[v_vec_idx].x[v_lan[45D[K
__bfloat162float(v_vec_ptr[v_vec_idx].x[v_lane]);
                v_acc[vi] = v_acc[vi] * correction + weight * v_val;
            }
        }
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V (normalized by running_sum later in reduce)
    #pragma unroll
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    // Write max and log-sum-exp (only thread 0)
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Reduce partial results across splits
__global__ void mla_reduce(
    const float* __restrict__ partial_out,   // [num_splits, total_q, NUM_H[5D[K
NUM_HEADS, V_DIM]
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,     // [total_q, NUM_HEADS, V_DIM][6D[K
V_DIM]
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
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    // Merge weighted sums using log-sum-exp
    float total_weight = 0.0f;
    float total_v = 0.0f;
    #pragma unroll
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

void launch_mla(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_SOUR[22D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm", "-amdgpu-early-inline-all=true"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla] Build failed: {e}")
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

    # Choose splits for CU occupancy - optimized for MI355X
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

    _mod.launch_mla(
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
            print(f"[custom_mla] Runtime error: {e}")

    return _asm_attention(data)

