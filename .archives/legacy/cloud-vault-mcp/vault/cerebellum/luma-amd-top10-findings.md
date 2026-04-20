# Luma AMD Speedrun - Top 10 Optimization Findings

## Overview
The transition from wrapper-based implementations to direct hardware dispatch has revealed a significant "Python Tax" in the `aiter` library, which was adding 2-30$\mu$s of latency depending on the kernel. To reach the Top 10, the strategy shifted to eliminating this overhead and implementing hardware-specific memory patterns.

## 1. MXFP4 GEMM: Direct CK Dispatch
### Findings
*   **Binary Extraction**: Discovered 35 pre-compiled `.co` kernels in `/home/mike-anderson/dev/aiter/hsa/gfx950/f4gemm/`.
*   **Argument Layout**: The CK kernels expect a 288-byte packed struct.
*   **B001 Blocker**: Direct calls via `ctypes` initially failed with stream isolation errors. This was traced to the Python garbage collector reclaiming the argument buffer before the GPU had launched the kernel.
*   **Solution**: 
    *   Convert `bytearray` to `bytes` to create a persistent object during the launch.
    *   Utilize `torch.cuda.current_stream().cuda_stream` to avoid stream mismatch.

### Performance Gain
Eliminated $\sim 3\mu$s of wrapper overhead. Tiling is now adaptive based on the `f4gemm_bf16_per1x32Fp4.csv` metadata.

## 2. Mixed MLA: Zero-Overhead Execution & Stability
### Findings
*   **Metadata Overhead**: `aiter` metadata generation for MLA is expensive (up to 30$\mu$s) because it involves C++ allocations and index calculations on every call.
*   **Buffer Noise**: Constant reallocation of output tensors creates timing jitter.
*   **Sequence Contamination**: Persistent buffers were causing numerical instability/accuracy failures for long sequences (`kvseqlen: 8192`) because buffers were reused across requests with different shapes.

### Solution
*   **Sequence-Aware Persistent Buffers**: Implement a cache keyed by `(bs, qseqlen, nheads, kvseqlen)`. This ensures that the $\sim 20\text{--}30\mu$s win from persistent memory is retained without contaminating results across different sequence lengths.
*   **Strict Synchronous Path**: Wrapped the call in `torch.cuda.stream(torch.cuda.default_stream())` and enforced `torch.cuda.synchronize()`.
*   **SASS-style HIP**: Used `__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4` to bypass high-level API abstractions.

### Result
Successfully stabilized MLA across all sequence lengths with Top 10 latency ($\sim 47\mu$s to $294\mu$s).

## 3. MoE: Direct Stage Dispatch
### Findings
*   **Fused vs Direct**: `fused_moe` is a convenience wrapper that introduces unnecessary sanity checks and dispatch overhead.
*   **Occupancy**: Performance varies wildly based on the tokens-per-expert ratio.

### Solution
*   **Explicit Stages**: Called `ck_moe_stage1` and `ck_moe_stage2` directly.
*   **Block-M Heuristic**: Implemented an adaptive `block_m` (32 for sparse, 64 for dense) based on `bs * topk // num_experts`.

## Hardware Insights (gfx950 / MI355X)
*   **Non-Temporal Loads**: `AITER_USE_NT=1` is critical for MoE performance to avoid polluting the L2 cache with weights.
*   **MFMA Pipeline**: Performance on MLA is bound by the efficiency of the MFMA pipeline; minimizing the "launch-to-compute" gap is the only way to hit $\le 20\mu$s.
