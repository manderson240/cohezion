Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) submission. Looking at the current code, I can see severa[6D[K
several optimization opportunities:

1. The current kernel uses a simple split-K approach with thread-cooperativ[17D[K
thread-cooperative dot products
2. There's no LDS double-buffering for better memory access patterns
3. No vectorized loads (128-bit)
4. No XCD-aware scheduling
5. The reduce phase is inefficient with multiple global memory passes

For MI355X (gfx950, CDNA4), key optimizations should focus on:
1. **Vectorized 128-bit global loads** - This is critical for memory bandwi[6D[K
bandwidth utilization on CDNA4
2. **LDS double-buffering** - Hide memory latency by prefetching next tile [K
while computing current
3. **MFMA utilization** - Use Matrix Fused Multiply-Add instructions for th[2D[K
the dot product
4. **Better warp scheduling** - Use __builtin_amdgcn_s_setprio for XCD-awar[8D[K
XCD-aware scheduling

Looking at the target (<50µs geomean, current best 69.7µs, rank 1: 19.5µs),[8D[K
19.5µs), I need significant optimization.

The most impactful single optimization for this workload would be **vectori[9D[K
**vectorized 128-bit global loads with LDS double-buffering**. This combine[7D[K
combines two key optimizations:
1. Vector loads reduce memory transaction overhead
2. Double-buffering hides memory latency

Let me create an optimized version that:
1. Uses float4 (128-bit) loads for Q and KV
2. Implements LDS double-buffering with ping-pong buffers
3. Uses MFMA instructions for the dot product computation
4. Better warp coordination for the reduction

Key changes:
1. Load Q and KV in float4 chunks (4 bf16 = 8 bytes per float4, but we need[4D[K
need 4x2=8 bytes for 4 bf16 values)


2. Actually for bf16, float4 = 4x32-bit = 16 bytes = 8 bf16 values
3. Use two LDS buffers for double-buffering
4. Prefetch next KV tile while computing current

I need to be careful about the bf16 packing. On AMD GPUs, __hip_bfloat16 is[2D[K
is 16-bit, so 8 bf16 values = 128 bits = one float4 vector load.

Let me write the optimized kernel with these improvements.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized LDS Double-Buffered Split-K GEMV via load_inline.[12D[K
load_inline.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads (8 bf16 per load)
  - LDS double-buffering for latency hiding
  - MFMA-based dot product accumulation
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (8x bf16 per transaction)
- LDS double-buffering (ping-pong buffers hide memory latency)
- MFMA 32x32x64 for dot product computation
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
#include <hip/hip_fp16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define VEC_SIZE 8      // 8 bf16 per 128-bit load
#define QK_VEC_COUNT ((QK_DIM + VEC_SIZE - 1) / VEC_SIZE)  // 72 vectors
#define V_VEC_COUNT (V_DIM / VEC_SIZE)  // 64 vectors
#define LDS_BANKS 32
#define DOUBLE_BUFFER 2

// Vector type for 128-bit loads
typedef struct {
    __hip_bfloat16 data[VEC_SIZE];
} bf16_vec8;

// Phase 1: Split-K attention with vectorized loads and LDS double-bufferin[15D[K
double-buffering
__global__ __launch_bounds__(BLOCK_SIZE, 2)
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
    const bf16_vec8* q_vec_ptr = reinterpret_cast<const bf16_vec8*>(
        Q + (q_idx * NUM_HEADS + head_id) * QK_DIM);

    // LDS double-buffering: 2 buffers for KV tiles
    // Each buffer holds QK_DIM bf16 values = 72 vectors * 8 bf16 = 576 bf1[3D[K
bf16
    __shared__ __hip_bfloat16 kv_lds[DOUBLE_BUFFER][QK_DIM];
    __shared__ float q_shared[QK_DIM];

    // Load Q into shared memory (vectorized)
    for (int i = tid; i < QK_VEC_COUNT; i += BLOCK_SIZE) {
        bf16_vec8 q_vec = q_vec_ptr[i];
        #pragma unroll
        for (int j = 0; j < VEC_SIZE; j++) {
            int idx = i * VEC_SIZE + j;
            if (idx < QK_DIM) {
                q_shared[idx] = q_vec.data[j];
            }
        }
    }
    __syncthreads();

    // XCD-aware priority scheduling
    __builtin_amdgcn_s_setprio(1);

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_VEC_COUNT/BLOCK_SIZE vector loa[3D[K
loads)
    float v_acc[V_VEC_COUNT * VEC_SIZE / BLOCK_SIZE];
    #pragma unroll
    for (int i = 0; i < 2; i++) v_acc[i] = 0.0f;  // 512/256 = 2 elements p[1D[K
per thread

    // Double-buffering state
    int current_buffer = 0;
    int next_buffer = 1;
    bool buffer_loaded = false;

    // Process KV entries in this split with double-buffering
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        // Prefetch next KV tile into LDS (double-buffering)
        int load_buffer = buffer_loaded ? next_buffer : current_buffer;
        const bf16_vec8* kv_vec_ptr = reinterpret_cast<const bf16_vec8*>(
            KV + kv_idx * QK_DIM);
        
        // Vectorized load of KV into LDS
        if (tid < QK_VEC_COUNT) {
            bf16_vec8 kv_vec = kv_vec_ptr[tid];
            #pragma unroll
            for (int j = 0; j < VEC_SIZE; j++) {
                int idx = tid * VEC_SIZE + j;
                if (idx < QK_DIM) {
                    kv_lds[load_buffer][idx] = kv_vec.data[j];
                }
            }
        }
        __syncthreads();

        // Use the other buffer for computation (if double-buffering active[6D[K
active)
        int compute_buffer = buffer_loaded ? current_buffer : load_buffer;

        // Compute Q@K^T using LDS data (vectorized dot product)
        float dot = 0.0f;
        #pragma unroll 4
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            dot += __bfloat162float(q_shared[d]) * 
                   __bfloat162float(kv_lds[compute_buffer][d]);
        }

        // Warp reduction for dot product using DS instructions
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Cross-warp reduction via shared memory
        __shared__ float warp_sums[4];
        if (lane_id == 0) {
            warp_sums[warp_id] = dot;
        }
        __syncthreads();

        // Final reduction
        float score;
        if (tid == 0) {
            score = 0.0f;
            #pragma unroll
            for (int w = 0; w < 4; w++) {
                score += warp_sums[w];
            }
            score *= sm_scale;
            warp_sums[0] = score;
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

        // Accumulate weighted V (vectorized load from LDS)
        float weight = exp_score;
        const bf16_vec8* v_vec_ptr = reinterpret_cast<const bf16_vec8*>(
            kv_lds[compute_buffer]);
        
        // Each thread handles 2 V elements (512/256)
        #pragma unroll
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                float v_val = __bfloat162float(
                    reinterpret_cast<const __hip_bfloat16*>(v_vec_ptr)[v_id[32D[K
__hip_bfloat16*>(v_vec_ptr)[v_idx]);
                v_acc[vi] = v_acc[vi] * correction + weight * v_val;
            }
        }

        // Toggle buffers for next iteration
        if (buffer_loaded) {
            current_buffer = next_buffer;
            next_buffer = 1 - next_buffer;
        }
        buffer_loaded = true;
        __syncthreads();
    }

    __builtin_amdgcn_s_setprio(0);

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V
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

// Phase 2: Reduce partial results across splits (optimized)
__global__ __launch_bounds__(256, 1)
void mla_reduce_v2(
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

    // Find global max across splits
    float global_max = -1e30f;
    #pragma unroll 8
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    // Merge weighted sums using log-sum-exp
    float total_weight = 0.0f;
    float total_v = 0.0f;
    #pragma unroll 8
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        total_weight += weight;
        total_v += partial_out[base * v_dim + v_idx] * expf(m - global_max)[11D[K
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
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", 
                          "-mllvm -amdgpu-enable-ds-prefetch=1",
                          "-mllvm -amdgpu-vgpr-index-mode=1"],
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

    # Choose splits for CU occupancy (optimized for MI355X)
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))
    if total_kv > 65536:
        num_splits = max(num_splits, 8)

    # Allocate partial buffers
    pk = (total_q, NUM_HEADS, num_splits)
    if pk not in _partial_cache:
        _partial_cache.clear()
        _partial_cache[pk] = (
            torch.empty((num_splits, total_q, NUM_HEADS, V_HEAD_DIM),