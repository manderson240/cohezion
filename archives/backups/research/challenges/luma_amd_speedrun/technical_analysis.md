# Technical Deep-Dive: MXFP4 & MLA Optimization

## 1. MLA Decode: The MXFP4 Opportunity
The current reference kernel (`mixed-mla/reference.py`) provides MXFP4 KV cache data but falls back to **FP8 (`a8w8`)** for the actual attention computation. 
- **Observation:** Memory bandwidth is the primary bottleneck in decode-only attention.
- **Strategy:** Implement a **native MXFP4 decode kernel (`a4w4` or `a8w4`)**. By using the `mxfp4` (fp4x2 + scale) data directly, we reduce the KV cache bandwidth requirement by ~2x compared to the FP8 reference.
- **Key Primitives:** Use **HipKittens** tiles to handle the 4-bit dequantization and scaling efficiently in shared memory before the GEMV/GEMM operations.

## 2. MXFP4 MoE: Fusion & Scheduling
The `moe-mxfp4/reference.py` uses AITER's `fused_moe`, which is already a high-performance baseline.
- **Optimization 1: Inter-stage Fusion:** Fuse the Gate+Up GEMM and Down GEMM into a single kernel. This eliminates the need to write the intermediate SwiGLU activations back to global memory.
- **Optimization 2: Dynamic Quantization Fusion:** The reference quantizes the `hidden_states` (activations) to MXFP4 *before* the kernel call. Fusing this quantization into the first GEMM's prologue will save one full memory round-trip of the activation tensor.
- **Optimization 3: Shared Expert Specialization:** Since the shared expert is always active (weight=1.0), it can be computed as a separate, dense, highly-optimized GEMM and fused with the top-k routed expert reduction.

## 3. MXFP4 GEMM: Tile Efficiency
The `mxfp4-mm` reference uses `aiter.gemm_a4w4`.
- **Strategy:** Focus on **tiling strategies** specific to the AMD Instinct™ MI355X architecture. Using **HipKittens** can help us achieve better L2 cache hit rates and more efficient use of the hardware's vector/matrix cores for MXFP4 math.

## 4. Hardware Specifics (MI355X)
- **Shared Memory (LDS):** Crucial for fusing the scaling factors (E8M0) with the 4-bit weights.
- **Warp Level Primitives:** Leverage `mfma` (Matrix Fused Multiply-Add) instructions if the MI355X supports direct MXFP4 acceleration, or optimize the bit-packing and unpacking for software-level emulation.

## 5. Next Implementation Steps
1. **Analyze `aiter/fused_moe.py` source:** (If available) to see the exact CK kernel templates being used.
2. **Prototype `a4w4` MLA Decode:** Start with a simple Triton or HIP kernel that handles the MXFP4 KV cache.
3. **Benchmark Ref Kernels:** Run the initial baseline to confirm where the AITER kernels are currently hitting performance plateaus.
