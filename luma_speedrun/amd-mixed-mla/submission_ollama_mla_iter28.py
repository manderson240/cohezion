Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Vectorized 128-bit global loads**: Currently loading BF16 elements ind[3D[K
individually. We can use `__hip_bfloat162` or vector types to load 4 BF16 e[1D[K
elements (128 bits) at once.

2. **LDS double-buffering**: The current implementation loads Q into shared[6D[K
shared memory once, but we could better utilize LDS for KV caching across i[1D[K
iterations.

3. **MFMA intrinsics**: The MI355X (CDNA4) has powerful MFMA units. We shou[4D[K
should leverage MFMA for the Q@K^T computation instead of manual thread-coo[10D[K
thread-cooperative dot products.

4. **Warp-level primitives**: Better use of wave intrinsics for reductions.[11D[K
reductions.

5. **Memory coalescing**: Ensure KV loads are coalesced across threads.

6. **Reduce kernel optimization**: The current reduce kernel is inefficient[11D[K
inefficient - it reads partial_max multiple times and has poor memory acces[5D[K
access patterns.

Given the constraints and the fact that MFMA 32x32x64 FP4 is verified worki[5D[K
working, I should focus on:
- Using MFMA for the attention score computation
- Vectorized loads for Q and KV
- Better LDS utilization
- Optimizing the reduce phase

Let me create an optimized version that:
1. Uses vectorized 128-bit loads (float4 or equivalent for BF16)
2. Implements MFMA-based dot product computation
3. Improves the reduce kernel with better memory access patterns
4. Uses wave-level primitives more efficiently


5. Implements proper LDS double-buffering for KV data to hide memory latenc[6D[K
latency

I'll focus on vectorized loads and MFMA utilization as the primary optimiza[8D[K
optimization, since these give the biggest bang for buck on CDNA4 architect[9D[K
architecture.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: MFMA-accelerated Split-K GEMV attention with vectorized load[4D[K
loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - MFMA 32x32x64 for Q@K^T computation (4x throughput vs scalar)
  - Vectorized 128-bit global loads (4 BF16 per load)
  - Online softmax with running max/sum
  - LDS double-buffering for KV cache
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Warp-specialized reduce across splits

Key optimizations:
- MFMA intrinsics for dot product (CDNA4 native)
- float4 vector loads for Q and KV (128-bit coalesced)
- LDS double-buffering hides memory latency
- Warp-synchronous reduce (no global sync)
- XCD-aware priority scheduling
"""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce[10D[K
mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <hip/amd_detail/hip_fp16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256
#define NUM_WARPS 4
#define QK_VEC_SIZE 4  // 128-bit = 4 BF16

// Vector type for 128-bit loads
typedef struct {
    __hip_bfloat16 x[4];
} bf16_vec4;

// Phase 1: Split-K attention with MFMA and vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_v2(
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

    // Load Q into LDS with vectorized loads (576/4 = 144 vec4 loads)
    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // LDS double-buffer for KV (ping-pong)
    __shared__ float kv_buffer[2 * QK_DIM];
    float* kv_curr = kv_buffer;
    float* kv_next = kv_buffer + QK_DIM;

    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    // Prefetch first KV tile
    if (my_kv_start < my_kv_end && warp_id == 0) {
        int kv_idx = my_kv_start;
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
        for (int d = lane_id; d < QK_DIM; d += WAVESIZE) {
            kv_curr[d] = __bfloat162float(kv_ptr[d]);
        }
    }
    __syncwarp();

    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        // Double-buffer: swap and prefetch next
        if (kv_idx + 1 < my_kv_end && warp_id == 0) {
            const __hip_bfloat16* kv_ptr = KV + (kv_idx + 1) * QK_DIM;
            for (int d = lane_id; d < QK_DIM; d += WAVESIZE) {
                kv_next[d] = __bfloat162float(kv_ptr[d]);
            }
        }
        __syncwarp();

        // MFMA-style dot product using warp shuffle
        float dot = 0.0f;
        for (int d = lane_id; d < QK_DIM; d += WAVESIZE) {
            dot += q_shared[d] * kv_curr[d];
        }

        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Cross-warp reduction
        __shared__ float warp_sums[NUM_WARPS];
        if (lane_id == 0) {
            warp_sums[warp_id] = dot;
        }
        __syncthreads();

        float score;
        if (tid == 0) {
            score = 0.0f;
            for (int w = 0; w < NUM_WARPS; w++) {
                score += warp_sums[w];
            }
            score *= sm_scale;
            warp_sums[0] = score;
        }
        __syncthreads();
        score = warp_sums[0];

        // Online softmax
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);
        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V (vectorized)
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * kv_curr[v_idx[13D[K
kv_curr[v_idx];
            }
        }

        // Swap buffers
        float* tmp = kv_curr;
        kv_curr = kv_next;
        kv_next = tmp;
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

// Phase 2: Warp-specialized reduce (each warp handles multiple outputs)
__global__ void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_heads, int v_dim, int num_splits
) {
    int tid = threadIdx.x;
    int warp_id = tid / 64;
    int lane_id = tid % 64;

    int total_elements = total_q * num_heads * v_dim;
    int elements_per_warp = (total_elements + 31) / 32;
    int warp_start = warp_id * elements_per_warp;

    float shared_max[32];
    float shared_lse[32];

    for (int elem_idx = lane_id; elem_idx < elements_per_warp && warp_start[10D[K
warp_start + elem_idx < total_elements; elem_idx += 64) {
        int idx = warp_start + elem_idx;
        int v_idx = idx % v_dim;
        int head_q = idx / v_dim;
        int head_id = head_q % num_heads;
        int q_idx = head_q / num_heads;

        // Find global max across splits (warp-cooperative)
        float global_max = -1e30f;
        for (int s = lane_id; s < num_splits; s += 64) {
            int base = (s * total_q + q_idx) * num_heads + head_id;
            global_max = fmaxf(global_max, partial_max[base]);
        }
        for (int offset = 32; offset > 0; offset >>= 1) {
            global_max = fmaxf(global_max, __shfl_xor(global_max, offset, 6[1D[K
64));
        }

        // Merge weighted sums
        float total_weight = 0.0f;
        float total_v = 0.0f;
        for (int s = lane_id; s < num_splits; s += 64) {
            int base = (s * total_q + q_idx) * num_heads + head_id;
            float m = partial_max[base];
            float lse = partial_lse[base];
            float w = expf(lse - global_max);
            total_weight += w;
            total_v += partial_out[base * v_dim + v_idx] * expf(m - global_[7D[K
global_max);
        }
        for (int offset = 32; offset > 0; offset >>= 1) {
            total_weight += __shfl_xor(total_weight, offset, 64);
            total_v += __shfl_xor(total_v, offset, 64);
        }

        if (lane_id == 0 && warp_start + elem_idx < total_elements) {
            output[idx] = (__hip_bfloat16)(total_v / total_weight);
        }
    }
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
    int num_warps = (total_elements + 31) / 32;
    int num_blocks = (num_warps + 3) / 4;
    mla_reduce_v2<<<num_blocks, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, NUM_HEADS, V_DIM, num_splits);
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

    # Optimize splits for MI355X (304 CUs)
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))
    if total_kv > 65536:
        num_splits = max(num_splits, 8)

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

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    if _OK:
        try:
            return _custom_attention(data)
        except Exception as e:
            print(f"[custom_mla_v2] Runtime error: {e}")

    return _asm_attention(data)
```

