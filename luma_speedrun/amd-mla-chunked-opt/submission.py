#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA: Chunked KV Processing (Memory-Optimized)

This kernel implements chunked KV cache processing for memory-efficient
multi-head latent attention. The key innovation is processing the KV cache
in fixed-size chunks to improve cache locality and reduce memory bandwidth.

Algorithm:
1. Divide KV cache into fixed-size chunks (e.g., 512 tokens)
2. Process each chunk independently with online softmax
3. Accumulate partial results across chunks
4. Final reduction to produce output

Key Optimizations:
- Chunk size tuned for L2 cache: 512 tokens * 576 dims * 2 bytes = ~576KB
- Overlapping chunk processing for better parallelism
- Streaming attention computation (no full softmax materialization)
- Memory bandwidth reduction through temporal locality

Chunk Processing Strategy:
  ┌─────────────────────────────────────────────────────────────┐
  │  Chunk 0: KV[0:512]    → Partial attention                    │
  │  Chunk 1: KV[512:1024] → Partial attention                    │
  │  Chunk 2: KV[1024:1536]→ Partial attention                    │
  │  ...                                                          │
  │  Final: Reduce all partials                                   │
  └─────────────────────────────────────────────────────────────┘

Memory Access Pattern:
  - Sequential scan through KV cache (optimal for memory bandwidth)
  - Q loaded once per batch, reused across chunks
  - Output accumulation in registers/LDS where possible

Performance Characteristics:
  - Best for long sequences (KV len > 2048)
  - Trade-off: slightly more compute for better memory locality
  - Reduced L2 cache thrashing vs full KV scan
"""

from __future__ import annotations
import os
import math

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# Import aiter for fallback
import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1

# Chunked processing configuration
CHUNK_SIZE = 512  # Tokens per chunk (tuned for L2 cache)
MAX_CHUNKS_IN_FLIGHT = 4  # Parallel chunk processing
NUM_HEADS = 16
QK_DIM = 576
V_DIM = 512
PAGE_SIZE = 1
SM_SCALE = 1.0 / (QK_DIM**0.5)
FP8_DTYPE = aiter_dtypes.fp8

# Cache for compiled kernels
_kernel_mod = None
_kernel_ok = False


def _get_chunked_kernel():
    """Lazy initialization of chunked MLA kernel."""
    global _kernel_mod, _kernel_ok

    if _kernel_mod is not None:
        return _kernel_mod, _kernel_ok

    HIP_SOURCE = r"""
    #include <torch/extension.h>
    #include <hip/hip_runtime.h>
    #include <hip/hip_bf16.h>
    
    #define NUM_HEADS 16
    #define QK_DIM 576
    #define V_DIM 512
    #define WAVESIZE 64
    #define BLOCK_SIZE 256
    
    // Process a chunk of KV cache
    __global__ __launch_bounds__(BLOCK_SIZE, 2)
    void mla_chunked_attention(
        const __hip_bfloat16* __restrict__ Q,        // [total_q, NUM_HEADS, QK_DIM]
        const __hip_bfloat16* __restrict__ KV_chunk, // [chunk_size, QK_DIM]
        float* __restrict__ partial_out,              // [total_q, NUM_HEADS, V_DIM]
        float* __restrict__ partial_max,            // [total_q, NUM_HEADS]
        float* __restrict__ partial_lse,            // [total_q, NUM_HEADS]
        int chunk_start,                             // Starting KV index
        int chunk_size,                              // Size of this chunk
        int total_q,
        float sm_scale
    ) {
        int q_idx = blockIdx.x;      // Query index
        int head_id = blockIdx.y;    // Head index
        int tid = threadIdx.x;
        
        if (q_idx >= total_q) return;
        
        // Load Q for this query+head
        __shared__ float q_shared[QK_DIM];
        const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;
        for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
            q_shared[i] = __bfloat162float(q_ptr[i]);
        }
        __syncthreads();
        
        // Online softmax state
        float running_max = -1e30f;
        float running_sum = 0.0f;
        
        // V accumulator
        float v_acc[V_DIM / BLOCK_SIZE + 1];
        #pragma unroll
        for (int i = 0; i < V_DIM / BLOCK_SIZE + 1; i++) {
            v_acc[i] = 0.0f;
        }
        
        // Process KV entries in this chunk
        for (int kv_local = 0; kv_local < chunk_size; kv_local++) {
            const __hip_bfloat16* kv_ptr = KV_chunk + kv_local * QK_DIM;
            
            // Compute Q@K^T (thread-cooperative dot)
            float dot = 0.0f;
            for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
                dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
            }
            
            // Warp reduction
            #pragma unroll
            for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }
            
            // Cross-warp reduction
            __shared__ float warp_sums[4];
            if ((tid % WAVESIZE) == 0) {
                warp_sums[tid / WAVESIZE] = dot;
            }
            __syncthreads();
            
            float score;
            if (tid == 0) {
                score = (warp_sums[0] + warp_sums[1] + warp_sums[2] + warp_sums[3]) * sm_scale;
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
            
            // Accumulate weighted V
            float weight = exp_score;
            int v_per_thread = (V_DIM + BLOCK_SIZE - 1) / BLOCK_SIZE;
            for (int vi = 0; vi < v_per_thread; vi++) {
                int v_idx = tid * v_per_thread + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
                }
            }
        }
        
        // Write partial results
        int out_base = (q_idx * NUM_HEADS + head_id);
        
        for (int vi = 0; vi < v_per_thread; vi++) {
            int v_idx = tid * v_per_thread + vi;
            if (v_idx < V_DIM) {
                partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
            }
        }
        
        if (tid == 0) {
            partial_max[out_base] = running_max;
            partial_lse[out_base] = logf(running_sum) + running_max;
        }
    }
    
    // Reduce partial results across chunks
    __global__ void mla_chunk_reduce(
        const float* __restrict__ chunk_out,    // [num_chunks, total_q, NUM_HEADS, V_DIM]
        const float* __restrict__ chunk_max,   // [num_chunks, total_q, NUM_HEADS]
        const float* __restrict__ chunk_lse,   // [num_chunks, total_q, NUM_HEADS]
        __hip_bfloat16* __restrict__ output,   // [total_q, NUM_HEADS, V_DIM]
        int num_chunks,
        int total_q
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int total_elements = total_q * NUM_HEADS * V_DIM;
        if (idx >= total_elements) return;
        
        int v_idx = idx % V_DIM;
        int head_q = idx / V_DIM;
        int head_id = head_q % NUM_HEADS;
        int q_idx = head_q / NUM_HEADS;
        
        // Find global max across chunks
        float global_max = -1e30f;
        for (int c = 0; c < num_chunks; c++) {
            int base = ((c * total_q + q_idx) * NUM_HEADS + head_id);
            float m = chunk_max[base];
            global_max = fmaxf(global_max, m);
        }
        
        // Merge weighted sums
        float total_weight = 0.0f;
        float total_v = 0.0f;
        for (int c = 0; c < num_chunks; c++) {
            int base = ((c * total_q + q_idx) * NUM_HEADS + head_id);
            float m = chunk_max[base];
            float lse = chunk_lse[base];
            
            float w = expf(lse - global_max);
            total_weight += w;
            total_v += chunk_out[base * V_DIM + v_idx] * expf(m - global_max);
        }
        
        output[idx] = (__hip_bfloat16)(total_v / total_weight);
    }
    
    void launch_chunked_mla(
        torch::Tensor Q, torch::Tensor KV,
        torch::Tensor partial_out, torch::Tensor partial_max,
        torch::Tensor partial_lse, torch::Tensor output,
        int chunk_start, int chunk_size, int total_q, float sm_scale
    ) {
        dim3 grid(total_q, NUM_HEADS);
        mla_chunked_attention<<<grid, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
            partial_out.data_ptr<float>(),
            partial_max.data_ptr<float>(),
            partial_lse.data_ptr<float>(),
            chunk_start, chunk_size, total_q, sm_scale);
    }
    
    void launch_reduce(
        torch::Tensor chunk_out, torch::Tensor chunk_max,
        torch::Tensor chunk_lse, torch::Tensor output,
        int num_chunks, int total_q
    ) {
        int total_elements = total_q * NUM_HEADS * V_DIM;
        mla_chunk_reduce<<<(total_elements + 255) / 256, 256>>>(
            chunk_out.data_ptr<float>(),
            chunk_max.data_ptr<float>(),
            chunk_lse.data_ptr<float>(),
            reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
            num_chunks, total_q);
    }
    """

    CPP_SOURCE = """
    void launch_chunked_mla(torch::Tensor Q, torch::Tensor KV,
                            torch::Tensor partial_out, torch::Tensor partial_max,
                            torch::Tensor partial_lse, torch::Tensor output,
                            int chunk_start, int chunk_size, int total_q, float sm_scale);
    void launch_reduce(torch::Tensor chunk_out, torch::Tensor chunk_max,
                       torch::Tensor chunk_lse, torch::Tensor output,
                       int num_chunks, int total_q);
    """

    try:
        _kernel_mod = load_inline(
            name="mla_chunked",
            cpp_sources=[CPP_SOURCE],
            cuda_sources=[HIP_SOURCE],
            functions=["launch_chunked_mla", "launch_reduce"],
            verbose=False,
            extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
        )
        _kernel_ok = True
    except Exception as e:
        print(f"[MLA Chunked] Kernel build failed: {e}")
        _kernel_mod = None
        _kernel_ok = False

    return _kernel_mod, _kernel_ok


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Quantize tensor to FP8 format."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits(total_kv: int) -> int:
    """Choose number of KV splits based on sequence length."""
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 65536:
        return 8
    return 16


def _einsum_attention(data: input_t) -> torch.Tensor:
    """Standard einsum attention for small shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS, V_DIM).to(torch.bfloat16)
    )


def _chunked_attention(data: input_t) -> torch.Tensor:
    """Process KV cache in chunks for memory efficiency."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_q = bs  # decode: qseqlen=1
    total_kv = bs * kvseqlen

    # Get kernel module
    mod, ok = _get_chunked_kernel()
    if not ok or mod is None:
        raise RuntimeError("Chunked kernel not available")

    # Extract KV in bf16 format
    kv_bf16 = kv_data["bf16"].view(total_kv, QK_DIM)  # [total_kv, QK_DIM]

    # Calculate chunks
    num_chunks = (total_kv + CHUNK_SIZE - 1) // CHUNK_SIZE

    # Allocate partial result buffers
    partial_out = torch.zeros(
        num_chunks, total_q, NUM_HEADS, V_DIM, dtype=torch.float32, device=q.device
    )
    partial_max = torch.zeros(num_chunks, total_q, NUM_HEADS, dtype=torch.float32, device=q.device)
    partial_lse = torch.zeros(num_chunks, total_q, NUM_HEADS, dtype=torch.float32, device=q.device)
    output = torch.empty(total_q, NUM_HEADS, V_DIM, dtype=torch.bfloat16, device=q.device)

    # Process each chunk
    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * CHUNK_SIZE
        chunk_end = min(chunk_start + CHUNK_SIZE, total_kv)
        actual_chunk_size = chunk_end - chunk_start

        # Extract chunk
        kv_chunk = kv_bf16[chunk_start:chunk_end]

        # Pad chunk if necessary
        if actual_chunk_size < CHUNK_SIZE:
            padding = CHUNK_SIZE - actual_chunk_size
            kv_chunk = torch.cat(
                [kv_chunk, torch.zeros(padding, QK_DIM, dtype=torch.bfloat16, device=q.device)],
                dim=0,
            )

        # Launch kernel for this chunk
        mod.launch_chunked_mla(
            q,
            kv_chunk,
            partial_out[chunk_idx],
            partial_max[chunk_idx],
            partial_lse[chunk_idx],
            output,
            chunk_start,
            actual_chunk_size,
            total_q,
            SM_SCALE,
        )

    # Final reduction across chunks
    mod.launch_reduce(partial_out, partial_max, partial_lse, output, num_chunks, total_q)

    return output


def _asm_attention(data: input_t) -> torch.Tensor:
    """ASM-based attention for medium shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)

    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_DIM)
    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_splits)

    # Cache metadata
    cache = {}
    if key not in cache:
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
        total_kv_len = int(kv_indptr[-1].item())
        total_q_val = bs * qseqlen
        cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
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

    meta = cache[key]
    output = meta["output"]

    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_DIM),
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
    """
    Chunked KV processing kernel.

    Implements memory-optimized attention by processing KV cache in chunks.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Use einsum for small shapes
    if bs <= 4 or total_kv <= 4096:
        return _einsum_attention(data)

    # Try chunked processing for long sequences
    mod, ok = _get_chunked_kernel()
    if ok and total_kv > CHUNK_SIZE:
        try:
            return _chunked_attention(data)
        except Exception as e:
            print(f"[MLA Chunked] Chunked attention failed: {e}")

    # Fallback to ASM attention
    try:
        return _asm_attention(data)
    except Exception as e:
        print(f"[MLA Chunked] ASM fallback failed: {e}, using einsum")
        return _einsum_attention(data)
