# Kimi-K2.6 Frontier Hardware Optimization Review

**Date**: 2026-08-21 11:17:17
**Target System**: AMD Ryzen AI MAX+ 395 (Strix Halo)

---

Here is how to push that Strix Halo deployment past its current ceiling. These four recommendations are purpose-built for the Ryzen AI MAX+ 395’s tri-silicon topology, 128 GB UMA pool, and the specific model mix you are running on Lemonade Server (`:1335`).

---

### 1. Speculative Decoding: Async NPU→iGPU Cascade with UMA Zero-Copy Ring Buffer
**Current state:** Qwen3-Coder-30B-A3B is decoding at 88 tok/s on RDNA 3.5. At 128k context, you are memory-bandwidth bound, not compute bound. Raising clocks will burn TDP for minimal gain.

**The move:** Pin a tiny draft model—your existing `waslmedia-4b` or a distilled 0.5B Qwen3 block—exclusively to the **XDNA2 NPU**. Configure it to generate 5–7 candidate tokens asynchronously while the iGPU is busy verifying the previous step. Leverage Strix Halo’s unified memory architecture to eliminate PCIe copies:

* Allocate a ring buffer in **HSA fine-grain UMA** (`hipMallocManaged` with `amdgpu` NUMA binding) and pin it with Linux CMA so the NPU’s DMA engine writes draft token IDs and hidden-state pointers directly into pages that the iGPU’s MMU already maps.
* On RDNA 3.5, use **async compute queue bifurcation**: Queue 0 runs the 30B target forward pass; Queue 1 runs a fused verification-and-acceptance kernel that compares draft logits against the target distribution using shared L2 scratch. Because RDNA 3.5 supports concurrent async compute, the draft verification overlaps with KV-cache attention for the next step.
* Enable **multi-token lookahead** on the NPU (exploit AIE spatial parallelism to predict tokens t+1 and t+2 in parallel) to push draft acceptance rates toward 70%.

**Expected impact:** 88 tok/s → **135–150 tok/s** sustained decode on Qwen3-Coder-30B-A3B without touching the iGPU clock or power limit, because the NPU drafts at <8 W.

---

### 2. Kernel Tuning: Persistent Wavefront Decode on RDNA 3.5 + Software-Defined AIE Prefetch for MoE
**Current state:** Per-step kernel launch overhead and KV-cache streaming are eating walls of time at 128k context, while the NPU stalls on irregular expert loading for `qwen3.6-moe-35b-a3b`.

**The move:** Replace dispatch-bound inference with **persistent HIP kernels** and treat the NPU’s control plane as a dataflow prefetcher.

* **iGPU (RDNA 3.5):** Launch a single persistent wavefront grid that stays resident across the 40 CUs for the entire decode sequence. Loop internally on a `volatile uint64_t` step counter in UMA. Inside the persistent kernel:
  * Fuse RoPE, causal mask, and sliding-window attention into one `decode_wave64` kernel.
  * Use `__builtin_nontemporal_load/store` for KV vectors >64 B to stream through L2 without polluting caches.
  * Force 64 VGPR usage to allow four waves per SIMD, maximizing occupancy on RDNA 3.5.
* **NPU (XDNA2):** MoE routing (`softmax(topk(gate))`) is control-divergent and hates AIE arrays. Offload the router to a single Zen 5 core (latency <1 µs). That CPU thread writes active expert IDs into an **HSA signal**. The XDNA2 DMA engine triggers on that signal to **double-buffer** expert weights into AIE local memory: Bank A executes while Bank B prefetches the next sparse expert. This turns unpredictable sparse access into a deterministic prefetch pipeline.

**Expected impact:** 20–25% decode latency reduction on the iGPU; 30–40% higher effective NPU throughput on MoE layers because experts are resident before the MAC array asks for them.

---

### 3. Quantization: Layer-Adaptive Tri-Silicon Quantization (MXFP6 | AIE-Block-INT4 | IQ2_XXS)
**Current state:** You are running BF16/FP16-class workloads on iGPU, INT8-ish on NPU, and IQ4_KT on CPU. You have headroom to trade precision for bandwidth and UMA capacity.

**The move:** Deploy heterogeneous precision formats native to each silicon domain.

* **iGPU (RDNA 3.5):** Convert Qwen3-Coder-30B-A3B from BF16 to **per-layer adaptive MXFP6** (Microscaling FP6). Write custom HIP intrinsics that unpack a 2-bit shared exponent per 32-element tile and broadcast it prior to the WMMA multiply. This saves ~25% memory bandwidth versus INT8 and preserves code-model accuracy. For the 128k context, add **dynamic per-head scaling** to prevent outlier drift across long documents. Keep `gpt-oss-20b` at MXFP4, but implement per-tile exponent rebasing every 1,024 tokens to stabilize long-context generation.
* **NPU (XDNA2):** Re-quantize `qwen3.6-moe-35b-a3b` experts to **XDNA2-native INT4** with **64×1 block tiling** aligned to the AIE multiply-and-accumulate spatial units. Keep the shared routing layer in INT8. Because AIE local memory is tiny, interleave two experts’ weights in banked memory so the switch fabric can change experts in sub-cycle time.
* **CPU (Zen 5):** Drop Mistral-Medium-128B from IQ4_KT to **IQ2_XXS** (~2.25 bpw). Zen 5’s wide AVX-512 frontend can sustain the dequant throughput, and you will reclaim roughly **35 GB of UMA**. Repurpose that space for KV-cache expansion or keep a second 30B-class model hot-swappable.

**Expected impact:** iGPU bandwidth headroom to increase batch size or context length; NPU doubles active expert capacity; CPU model footprint shrinks by ~40%, freeing the UMA pool for the iGPU’s 128k KV cache.

---

### 4. Heterogeneous Multi-Silicon Orchestration: Fabric-Aware Task Graph with Cross-Domain KV Tiering
**Current state:** Your four workloads (NPU text+vision, iGPU code+OSS, CPU text+embed, audio pipeline) are likely scheduled as independent processes. Strix Halo’s value is the unified fabric; you are probably leaving concurrency and thermal headroom on the table.

**The move:** Build a **unified HSA task graph** inside Lemonade Server that treats the CPU, iGPU, and NPU as a single asymmetric NUMA machine.

* **Cross-Domain KV Tiering:** For Qwen3-Coder-30B-A3B’s 128k context, do not store the entire KV cache in iGPU-preferred coarse-grained pages. Instead:
  * **Hot tier:** Pin the active 32k context window in iGPU-preferred UMA (fast RDNA 3.5 path).
  * **Cold tier:** Spill the trailing 96k to CPU-mapped fine-grained UMA. Use Zen 5 background threads to asynchronously compress cold KV blocks with **Q5_K** or Zstd.
  * When the sliding attention window shifts, the CPU decompresses and streams the recovered blocks back into the iGPU hot tier via `nontemporal` bulk copies across the on-die fabric.
* **Thermal-Aware Work Stealing:** Strix Halo shares a single die TDP. Use `amd-smi` (or SMU mailbox writes) to enforce a **15 W NPU floor** for always-on audio (Whisper-Turbo + kokoro-v1) and an **80 W iGPU ceiling** for Qwen decode bursts. When the iGPU is idle between chat turns, immediately steal that TDP headroom to run larger `waslmedia-4b` batches or Whisper encoder slices on the NPU.
* **Zero-Copy Audio Pipeline:** Map the Whisper encoder output and Kokoro mel-spectrogram buffers into the same HSA allocation used by the text pipeline, so the audio path never triggers a page migration or `memcpy`.

**Expected impact:** You eliminate the last remaining “copy” stalls between CPU, iGPU, and NPU; sustain full concurrent load on all four models without thermal throttling; and effectively turn the 128 GB UMA into a single-tier memory pool rather than three separate heaps.

---

### Bottom Line
Your current deployment is already aggressive, but it is still scheduled like a discrete-GPU server. Strix Halo wins when you treat the NPU as a **low-power draft/pre-fetch accelerator**, the iGPU as a **persistent kernel decode engine**, and the CPU as a **compression/router/scheduler co-processor**—all sharing one physical memory pool. Implement the four recommendations above in this order (speculative decode first for immediate tok/s gain, then orchestration for sustained concurrency) and you will push Qwen3-Coder past **130 tok/s** at 128k context while running the full audio and embedding stack in parallel.