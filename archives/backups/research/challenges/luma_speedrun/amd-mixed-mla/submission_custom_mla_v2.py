#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA v2: Per-thread KV processing (FlashDecoding style).

v1 FAILURE: thread-cooperative dot per KV entry = O(kv_len × sync) = 16ms.
v2 FIX: each thread processes MULTIPLE KV entries independently.

Architecture:
- Grid: (num_splits, NUM_HEADS, batch_size)
- Block: 64 threads (1 wave) — NO inter-thread sync during KV loop
- Each thread handles ALL 576 dims of Q@K^T for its assigned KV entries
- Online softmax + V accumulation fully in registers
- Only ONE reduction at the end (across threads within the block)

This matches FlashDecoding: independent processing, late reduction.
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
#define BLOCK_SIZE 64  // 1 wave — no inter-thread sync needed

// Each thread independently processes a subset of KV entries
// and maintains its own online softmax state
__global__ __launch_bounds__(BLOCK_SIZE, 8)
void mla_flash_decode(
    const __hip_bfloat16* __restrict__ Q,    // [total_q, NUM_HEADS, QK_DIM]
    const __hip_bfloat16* __restrict__ KV,   // [total_kv, QK_DIM]
    __hip_bfloat16* __restrict__ output,     // [total_q, NUM_HEADS, V_DIM]
    const int* __restrict__ kv_indptr,       // [batch_size + 1]
    int batch_size, float sm_scale
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;

    // Total splits = gridDim.x
    int num_splits = gridDim.x;

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;
    if (kv_len == 0) return;

    // Each thread handles a strided subset: thread i processes KV entries
    // i, i+BLOCK_SIZE, i+2*BLOCK_SIZE, ... within this split's range
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);

    // Q pointer for this batch+head
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // Load Q into registers (576 values, each thread loads all of them)
    // 576 bf16 values = 576 * 2 = 1152 bytes per thread
    // This is ~18 VGPRs as float32 or 9 as bf16 pairs
    // Too many registers? Use shared memory for Q instead
    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();  // Only ONE sync — to load Q

    // Per-thread online softmax state
    float my_max = -1e30f;
    float my_sum = 0.0f;
    float my_v[8];  // V_DIM/BLOCK_SIZE = 512/64 = 8 elements per thread
    #pragma unroll
    for (int i = 0; i < 8; i++) my_v[i] = 0.0f;

    // Process KV entries: each thread handles entries tid, tid+BLOCK_SIZE, ...
    for (int kv_idx = my_kv_start + tid; kv_idx < my_kv_end; kv_idx += BLOCK_SIZE) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute full 576-dim dot product (this thread does all 576 dims)
        float dot = 0.0f;
        #pragma unroll 8
        for (int d = 0; d < QK_DIM; d++) {
            dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
        }
        float score = dot * sm_scale;

        // Online softmax update (fully in registers, no sync!)
        float old_max = my_max;
        my_max = fmaxf(my_max, score);
        float correction = expf(old_max - my_max);
        float exp_score = expf(score - my_max);

        my_sum = my_sum * correction + exp_score;

        // Accumulate weighted V
        #pragma unroll
        for (int vi = 0; vi < 8; vi++) {
            int v_idx = tid + vi * BLOCK_SIZE;
            if (v_idx < V_DIM) {
                my_v[vi] = my_v[vi] * correction +
                           exp_score * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Normalize V by sum
    float inv_sum = (my_sum > 0.0f) ? 1.0f / my_sum : 0.0f;

    // Now we need to merge across threads within the block
    // Each thread has (my_max, my_sum, my_v[8]) for its KV subset
    // Use shared memory for the online softmax merge
    __shared__ float s_max[BLOCK_SIZE];
    __shared__ float s_sum[BLOCK_SIZE];
    __shared__ float s_v[BLOCK_SIZE * 8];

    s_max[tid] = my_max;
    s_sum[tid] = my_sum;
    #pragma unroll
    for (int vi = 0; vi < 8; vi++) {
        s_v[tid * 8 + vi] = my_v[vi];
    }
    __syncthreads();  // Second and LAST sync

    // Thread 0 merges all partial results
    if (tid == 0) {
        float global_max = -1e30f;
        for (int t = 0; t < BLOCK_SIZE; t++) {
            global_max = fmaxf(global_max, s_max[t]);
        }

        // Compute total output
        int out_base = (q_idx * NUM_HEADS + head_id) * V_DIM;

        // For each V element, accumulate across all threads
        for (int v_idx = 0; v_idx < V_DIM; v_idx++) {
            int owner_thread = v_idx % BLOCK_SIZE;
            int owner_vi = v_idx / BLOCK_SIZE;

            float total_w = 0.0f;
            float total_v = 0.0f;

            // Each thread's contribution
            for (int t = 0; t < BLOCK_SIZE; t++) {
                float t_max = s_max[t];
                float t_sum = s_sum[t];
                float correction = expf(t_max - global_max);
                float weight = t_sum * correction;
                total_w += weight;

                // Only the owner thread has this V element
                if (t == owner_thread) {
                    total_v += s_v[t * 8 + owner_vi] * correction;
                }
            }

            output[out_base + v_idx] = (__hip_bfloat16)(total_v / total_w);
        }
    }
}

void launch_mla(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor output, torch::Tensor kv_indptr,
                int batch_size, int num_splits, float sm_scale) {
    dim3 grid(num_splits, NUM_HEADS, batch_size);
    mla_flash_decode<<<grid, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        kv_indptr.data_ptr<int>(),
        batch_size, sm_scale);
}
"""

CPP_SOURCE = """
void launch_mla(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor output, torch::Tensor kv_indptr,
                int batch_size, int num_splits, float sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_v2",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_mla"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_v2] Build: {e}")
    _OK = False

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
FP8_DTYPE = aiter_dtypes.fp8

_cache = {}


def _einsum_attention(data):
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


def _quantize_fp8(t):
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _asm_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    def choose_splits(tv):
        if tv <= 2048:
            return 1
        if tv <= 16384:
            return 4
        if tv <= 131072:
            return 8
        if tv <= 524288:
            return 16
        return 32

    num_kv_splits = choose_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], 1, 1, QK_HEAD_DIM)
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
            page_size=1,
            kv_granularity=16,
            max_seqlen_qo=qseqlen,
            uni_seqlen_qo=qseqlen,
            fast_mode=False,
            max_split_per_batch=num_kv_splits,
            intra_batch_mode=True,
            dtype_q=q_fp8.dtype,
            dtype_kv=kv_buffer_fp8.dtype,
        )
        total_kv_len = int(kv_indptr[-1].item())
        tq = bs * qseqlen
        _cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty(
                (num_kv_splits, tq, NUM_HEADS, V_HEAD_DIM), dtype=torch.float32, device="cuda"
            ),
            "attn_lse": torch.empty(
                (num_kv_splits, tq, NUM_HEADS), dtype=torch.float32, device="cuda"
            ),
            "output": torch.empty((tq, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
        }
    meta = _cache[key]
    output = meta["output"]
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
        1,
        1,
        SM_SCALE,
        meta["logits"],
        meta["attn_lse"],
        output,
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
        output,
        None,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # For now, always use ASM (proven best)
    # Custom kernel v2 needs more work on the reduction
    return _asm_attention(data)
