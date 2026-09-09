# Frontier Cloud Model Hardware Optimization Synthesis (AMD Strix Halo)

**Date**: 2026-08-21 11:18:30
**Hardware Target**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (128GB Unified LPDDR5X-7500)

---

## Perspective: Qwen3.5-397B (Frontier Scale Systems Architecture Specialist)

## Architectural Review: AMD Strix Halo Inference Stack
**System:** AMD Ryzen AI MAX+ 395 (Strix Halo)
**Memory:** 128GB LPDDR5X-7500 (210 GB/s)
**Compute:** XDNA2 NPU (50 TOPS) + RDNA 3.5 iGPU (40 CU) + Zen 5 CPU
**Current Throughput:** 88.1 tok/s (3.3B Active MoE)
**Theoretical Bandwidth Limit:** ~127 tok/s (INT4, 3.3B active params)
**Efficiency:** ~69%

**Verdict:** Your stack is impressive, but you are leaving ~30% performance on the table due to suboptimal kernel occupancy, conservative quantization, and underutilized heterogeneous scheduling. The 128GB Unified Memory Architecture (UMA) is your killer feature; current pipelines treat components too discretely.

Here are the concrete, cutting-edge recommendations to breach the 110+ tok/s barrier and maximize intelligence density.

---

### 1. Advanced Speculative Decoding: "NPU-Draft, GPU-Tree-Verify"
Current speculative decoding often bottlenecks on the verification step or draft latency. On Strix Halo, we can exploit the distinct latency/throughput profiles of the NPU and iGPU.

*   **Recommendation:** Implement **EAGLE-2 Style Speculative Decoding** with Heterogeneous Split.
    *   **Draft Model:** Host a 1B Dense model (e.g., `Qwen-1.5B-INT4`) exclusively on the **XDNA2 NPU**. The NPU's 50 TOPS is overkill for a 1B model, allowing it to generate draft tokens at extreme speed with low power, freeing the iGPU.
    *   **Verification:** Use the **RDNA 3.5 iGPU** to verify the draft tree.
    *   **Optimization:** Instead of linear verification, implement **Tree Attention Verification**. RDNA 3.5's 40 CUs can parallelize the verification of multiple draft branches simultaneously.
    *   **Zero-Copy:** Since memory is unified, the draft KV cache and target KV cache reside in the same physical address space. Eliminate `memcpy` between draft and target contexts. Use HIP IPC handles to share the KV buffer directly between the NPU driver and ROCm runtime.
*   **Expected Gain:** +25-35% effective throughput (acceptance rate ~0.6 on conversational data).

### 2. Kernel-Level Optimizations: RDNA 3.5 & UMA Tuning
Standard `llama.cpp` Vulkan/ROCm backends are generic. Strix Halo requires custom HIP kernels to saturate the 210 GB/s bus.

*   **FlashDecoding++ for RDNA 3.5:**
    *   Standard FlashAttention v2/v3 is optimized for HBM. For LPDDR5X, latency is higher. Implement **FlashDecoding** (splitting the reduction dimension across wavefronts) to hide memory latency.
    *   **WMMA Intrinsics:** Ensure your ROCm build is utilizing `wmma` (Wave Matrix Multiply Accumulate) instructions specific to RDNA 3.5, rather than generic `mfma` (which is for CDNA/Instinct). This reduces register pressure.
*   **PagedAttention v3 (UMA-Optimized):**
    *   Standard vLLM PagedAttention assumes discrete VRAM. On UMA, page faults trigger system RAM latency.
    *   **Action:** Implement a **Contiguous KV Reserve** for the active context window (e.g., 32k). Only page out to system RAM for the "long tail" (32k-128k). This keeps the hot KV cache in the memory controller's active row buffer.
*   **Split-K Prefill on CPU:**
    *   For the `Mistral-Medium-3.5-128B` on CPU: Use **AVX-512 VNNI Split-K**. Zen 5 has massive L3 cache. Tile the matrix multiplication to fit the Q/K/V projections entirely within L3 during prefill to avoid DDR5 contention with the iGPU.

### 3. Quantization Strategy: Hybrid Precision
You are mixing MXFP4 and IQ4_KT. This is safe, but not optimal for RDNA 3.5's compute units.

*   **iGPU (RDNA 3.5):** Switch to **OCP FP8 (E4M3)**.
    *   RDNA 3.5 has native FP8 DOT4 instructions. MXFP4 saves bandwidth but forces conversion overhead on compute. FP8 offers a better compute/bandwidth balance on this architecture.
    *   **Target:** `Qwen3-Coder-30B-A3B-FP8`.
    *   **Why:** FP8 on RDNA 3.5 yields ~2x matrix throughput compared to INT4 unpacking overhead in some ROCm versions, while maintaining near-BF16 accuracy.
*   **NPU (XDNA2):** Stick to **INT4 (Symmetric)**.
    *   XDNA2 is hard-wired for INT8/INT4. Do not use FP8 here.
*   **MoE Router:** **Force FP16/BF16**.
    *   *Critical:* Never quantize the MoE gating network below FP16. Quantizing the router (IQ3_XXS) causes "expert collapse" where the model routes all tokens to 1-2 experts, destroying the MoE benefit. Keep the router in high precision in SRAM/L3.
*   **CPU (AVX-512):** Use **IQ4_XS**.
    *   For the 128B model, IQ4_XS offers better perplexity than IQ4_KT with negligible speed penalty on Zen 5 VNNI.

### 4. Heterogeneous Swarm: "Expert Parallelism" & Async Prefill
You are currently splitting by *model*. To maximize the 128GB UMA, split by *compute graph*.

*   **Dynamic Expert Parallelism (MoE-Specific):**
    *   In your 35B MoE (3B active), you have ~32 experts.
    *   **Strategy:** Pin 16 Experts to the **iGPU** and 16 Experts to the **NPU**.
    *   **Routing:** The Router (on iGPU) calculates gates. If a token routes to an NPU-hosted expert, dispatch the vector via a low-latency doorbell register to the NPU.
    *   **Benefit:** This effectively doubles the compute surface area for the active parameters. Since memory is unified, the weight fetch cost is identical; you gain pure compute parallelism.
*   **Async Prefill/Decode:**
    *   **CPU:** Handles **Prefill** (Prompt Processing). Zen 5 AVX-512 is bandwidth-efficient for large batched prefills.
    *   **iGPU/NPU:** Handles **Decode** (Token Generation).
    *   **Mechanism:** When a user sends a prompt, the CPU ingests it and populates the KV Cache in UMA. It then signals the iGPU/NPU to begin decoding from the last token. This prevents the iGPU from stalling on memory-bound prompt ingestion.
*   **Gateway Integration (`cohezion-hermes-router`):**
    *   Modify the router to be **Load-Aware**. If the iGPU thermal throttles (Strix Halo runs hot), dynamically offload the `waslmedia-qwen3-4b` conversational model to the NPU temporarily.
    *   Implement **Batch Fusion**: If two users send requests within 5ms, fuse them into a single batch on the iGPU to maximize occupancy, even if it adds 5ms latency.

### 5. Critical Bottleneck Warning: Thermal & Memory Bandwidth
*   **The 210 GB/s Wall:** You are currently at 88.1 tok/s. The theoretical max for 3.3B active params @ 4-bit is ~127 tok/s. To reach 110+, you must reduce **non-matrix memory traffic**.
    *   **Action:** Enable **KV Cache Quantization (KV Cache INT8)**. This reduces the memory footprint of the context by 50%, effectively doubling your bandwidth for decode.
*   **Thermal Throttling:** Strix Halo APU packages are dense. Sustained 210 GB/s memory traffic + 50 TOPS NPU + 40 CU GPU will trigger thermal throttling within 3 minutes.
    *   **Action:** Implement a **Power Cap** at 65W for the APU socket. It yields 90% of performance with 70% of the heat, preventing clock frequency oscillation which causes token generation jitter.

### Summary of Action Items
1.  **Kernel:** Port FlashDecoding++ to HIP for RDNA 3.5; enable WMMA intrinsics.
2.  **Quant:** Move iGPU models to **FP8**; keep NPU at **INT4**; keep MoE Routers at **FP16**.
3.  **SpecDec:** Deploy **NPU-Draft (1B) / GPU-Verify (30B)** pipeline with shared KV cache.
4.  **MoE:** Implement **Expert Parallelism** across NPU/iGPU boundaries.
5.  **System:** Cap power at 65W; Quantize KV Cache to INT8.

**Projected Outcome:**
*   **Decode Speed:** 115-120 tok/s (sustained).
*   **Latency:** TTFT reduced by 40% (CPU Prefill offload).
*   **Capacity:** Simultaneous 128k context sessions increased by 2x (KV Quantization).

Execute these changes, and your Strix Halo deployment will outperform discrete L40S setups in tokens-per-watt and latency for this specific MoE workload class.

---

## Perspective: DeepSeek-V4 Pro (Frontier Code & Kernel Optimization Specialist)

## Architectural Review: Strix Halo Local Inference Deployment

Your current setup is already well-tuned. The 88.1 tok/s decode on Qwen3-Coder-30B-A3B is **~69% of the theoretical memory-bandwidth ceiling** for that model. There is still headroom, but the primary constraint is the 210 GB/s UMA bandwidth, not compute. The following recommendations target that bottleneck and add speculative/parallel techniques to push both raw tokens/s and intelligence density.

---

### 1. Bandwidth-First Analysis

For a 3.3B active-parameter MoE model at 4-bit:

- Active weights: 3.3B × 0.5 bytes = **1.65 GB**
- Theoretical max decode speed = 210 GB/s ÷ 1.65 GB = **127 tok/s**
- Your observed 88 tok/s → **69% efficiency**

The gap is caused by:
- Dequantization overhead in GGUF kernels
- Non-ideal memory access patterns (expert gather, KV cache, embeddings)
- Launch overhead and non-fused operations

**Target:** Reduce active bytes to ~1.2 GB via 3-bit experts, and improve kernel efficiency to 80–85%. That yields **~140–150 tok/s** before speculative decoding.

---

### 2. Speculative Decoding: NPU Draft Tree vs. Medusa/EAGLE

#### Option A: NPU Draft Tree → iGPU Parallel Verification

**Concept:**  
Run a small draft model (e.g., Qwen3-0.6B or 1.5B, 4-bit) on the XDNA2 NPU. The NPU generates a tree of candidate tokens (top-k at each step, depth 2–4). The iGPU verifies all candidates in **one forward pass** using tree attention masks.

**Expected speedup:**  
If draft acceptance is 60–70% and draft cost is low, speedup ≈ 1 / (1 − acceptance + draft_cost/verify_cost) ≈ **1.5–2.0×**.

**Caveats on Strix Halo:**
- XDNA2 NPU has limited local memory (~32 MB). A 0.5B 4-bit draft model (~250 MB) will **stream weights from UMA**, competing with iGPU for bandwidth.
- Cross-device synchronization (NPU → CPU → iGPU) adds latency, potentially negating the benefit for short sequences.
- Tree attention on iGPU requires custom block-sparse attention kernels.

**Verdict:** Possible, but not the first choice. Use only if NPU latency is < 5 ms per draft step and bandwidth contention is manageable.

#### Option B: Medusa / EAGLE Heads on iGPU (Recommended)

**Concept:**  
Attach small prediction heads to the existing model’s hidden states. These heads predict multiple future tokens in parallel. The iGPU verifies them in one pass.

**Advantages:**
- No separate draft model → no extra weight streaming.
- Runs entirely on iGPU, avoiding cross-device sync.
- Can be trained or fine-tuned for your specific model.

**Implementation:**
- Use **EAGLE** (Extrapolation Algorithm for Greater Language-model Efficiency) or **Medusa** heads.
- Integrate into llama.cpp via custom `llama_decode` with tree attention.
- Expected speedup: **1.4–1.8×** with 3–5 candidate heads.

**Recommendation:** Start with Medusa/EAGLE on iGPU. It is more practical and avoids NPU bandwidth contention.

---

### 3. Kernel-Level Optimizations for RDNA 3.5

#### a. Flash-Decoding for Long Context

- Enable `--flash-attn` in llama.cpp (HIP backend). This splits the KV cache across CUs and uses online softmax to reduce memory traffic.
- For 128k context, use **paged KV cache** and `--rope-scaling yarn` to avoid OOM and improve quality.
- Expected improvement: 10–20% on long-context decode, especially with large batch sizes.

#### b. Split-K Attention for Prefill

- During prompt processing, split the sequence length dimension across CUs to increase occupancy.
- Use `--split-mode layer` if using multiple devices, but on a single iGPU, custom split-k attention kernels can improve prefill throughput by 30–50%.

#### c. Custom MoE GEMM with rocWMMA

- RDNA 3.5 supports **WMMA (Wave Matrix Multiply Accumulate)** for FP16, BF16, and INT8. Use `rocwmma` to write custom MoE kernels that:
  - Gather only active expert weights (avoid reading all experts).
  - Use shared memory to cache router scores and expert indices.
  - Fuse dequantization with GEMM to reduce memory traffic.
- Repack GGUF weights to 16-byte aligned layouts for WMMA instructions.
- Expected improvement: 15–25% over stock GGUF MoE kernels.

#### d. Memory Management

- Use `--mlock` and `--no-mmap` to prevent page faults and swapping.
- On unified memory, ensure `HSA_XNACK=1` is set for proper page migration (though on APU it is less critical).
- Pin CPU cores for the iGPU driver to avoid scheduling jitter.

---

### 4. Quantization Improvements

#### MXFP4 vs. IQ3_XXS vs. NVFP4

- **NVFP4:** Blackwell-specific, **not applicable** to RDNA 3.5.
- **MXFP4:** Micro-scaling format with 32-element blocks. More accurate than GGUF Q4_K, but **no native hardware acceleration** on RDNA 3.5 WMMA. Emulation requires dequant to FP16, adding overhead that likely negates bandwidth savings.
- **IQ3_XXS:** 3-bit with 256-block scales. Active bytes for 3.3B ≈ **1.24 GB**. Theoretical max decode = 210 / 1.24 = **169 tok/s**. Dequant overhead is higher, but with custom fused kernels, real speed can reach **120–130 tok/s**.

**Recommended Quantization Strategy:**
- **Attention and shared layers:** Q4_K_M (good accuracy, moderate size)
- **MoE experts:** Q3_K_S or IQ3_XXS (aggressive size reduction)
- **Embeddings:** Q8_0 (small, negligible impact)
- Use **imatrix calibration** during quantization to preserve quality.

**Expected result:** Active bytes ~1.2 GB, decode speed **110–120 tok/s** before speculative decoding.

---

### 5. Heterogeneous Swarm Execution

#### a. Workload Partitioning

- **iGPU:** Primary decode for Qwen3-Coder-30B-A3B and gpt-oss-20b. Use HIP backend, not Vulkan.
- **CPU:** Large-context 128B model (Mistral-Medium) only when needed. Use AVX-512 VNNI with IQ3_XXS to reduce memory traffic.
- **NPU:** Keep for embedding, audio, and background indexing. Do **not** run draft models that stream weights from UMA during active decode.

#### b. Bandwidth Contention Management

- Use `taskset` to pin CPU cores: reserve 2–4 cores for OS and iGPU driver, assign remaining to CPU inference.
- Use `ionice` and `nice` to prioritize iGPU memory access.
- If running multiple models concurrently, schedule them in phases (e.g., NPU embedding during iGPU idle periods).

#### c. Continuous Batching

- If serving multiple users, enable **continuous batching** in llama.cpp server (`--parallel` slots). This reuses active weights across multiple sequences, increasing total throughput even if per-user latency rises.
- For a single stream, speculative decoding is more effective.

---

### 6. Concrete Action Plan

| Step | Action | Expected Gain |
|------|--------|---------------|
| 1 | Switch to HIP backend, enable `--flash-attn`, `--mlock`, `--no-mmap` | +10–15% decode speed |
| 2 | Re-quantize Qwen3-Coder-30B-A3B with Q4_K_M attention + Q3_K_S experts | +20–30% decode speed |
| 3 | Implement Medusa/EAGLE heads on iGPU | +40–80% decode speed |
| 4 | Custom MoE GEMM with rocWMMA and expert gather | +15–25% decode speed |
| 5 | Use split-k attention for prefill | +30–50% prefill throughput |
| 6 | Offload all non-critical tasks to NPU/CPU, pin cores | +5–10% stability |

**Combined potential:**  
- Decode: **88 → 150–180 tok/s** on Qwen3-Coder-30B-A3B  
- Prefill: **2–3× faster** on long contexts  
- Intelligence density: improved via better quantization and speculative verification without quality loss.

---

### Final Verdict

Yes, you can do significantly better. The key levers are:
1. **Reduce active bytes** via 3-bit experts.
2. **Add speculative decoding** with Medusa/EAGLE on iGPU.
3. **Optimize MoE kernels** for RDNA 3.5 WMMA.
4. **Avoid NPU draft streaming** due to bandwidth contention.

Your current setup is already near the practical limit for stock GGUF Vulkan. With these changes, you can push the Strix Halo to **150+ tok/s** on a 3B-active MoE, making it one of the fastest local inference deployments on this hardware.

---

