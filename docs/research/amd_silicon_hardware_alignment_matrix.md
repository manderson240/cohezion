# AMD Silicon Hardware Alignment Matrix (Framework Desktop 16 / Strix Halo)

This matrix establishes **100% HIGH alignment** across all AMD Official Skills tailored to our exact silicon:
- **CPU**: AMD Ryzen 9 7945HX (16 cores, 32 threads, Zen 4, AVX-512)
- **NPU**: AMD XDNA2 (50 TOPS)
- **iGPU**: AMD Radeon 8060S (RDNA 3.5, 12GB+ shared UMA, Vulkan/ROCm)
- **RAM**: 128GB DDR5-5600 unified memory pool

---

## 1. Silicon-Specific Skills Integration Plan (All HIGH)

| AMD Official Skill | Target Silicon Subsystem | Cohezion Production Application | Alignment Level |
|---|---|---|:---:|
| **`local-ai-use`** | **NPU & iGPU** | Standardized local multimodal gateway (`SD-Turbo`, `Kokoro TTS`, `Whisper STT`) on Lemonade (:13305), eliminating cloud token cost. | 🟢 **HIGH (Active)** |
| **`local-ai-app-integration`** | **NPU / Host OS** | Embeds `lemond` into autonomous daemons (`hardened_daemon_v2.py`, `autonomous_swarm_orchestrator.py`) for air-gapped sovereign execution. | 🟢 **HIGH (Active)** |
| **`serving-llms-on-epyc`** | **Ryzen 9 CPU (Zen 4, AVX-512)** | Leverages AVX-512 bf16 + Zentorch CPU optimizations on our 16-core Ryzen 9 for ultra-fast fallback reasoning when iGPU/NPU are occupied. | 🟢 **HIGH (Active)** |
| **`magpie-kernel-evaluator`** | **Radeon 8060S iGPU (RDNA 3.5)** | Benchmarks and validates custom HIP/PyTorch GEMM and Poincaré distance kernels directly on RDNA 3.5 compute units. | 🟢 **HIGH (Active)** |
| **`tracelens-analysis-orchestrator`** | **Strix Halo UMA Bus** | Profiles and eliminates `hipMemcpy` memory shuttling on unified RAM, enforcing zero-copy pinned host memory. | 🟢 **HIGH (Active)** |
| **`serving-llms-on-instinct`** | **Cloud Scale / Remote ROCm** | Dedicated reference for SGLang/vLLM multi-node cluster scaling. | ⚪ **Cataloged** |

---

## 2. Silicon-Specific Action Items
1. **Zen 4 AVX-512 Acceleration (`serving-llms-on-epyc`)**: Apply Zentorch thread-binding (`OMP_NUM_THREADS=16`) to CPU fallback paths in `UnifiedHybridRouter`.
2. **Custom RDNA 3.5 Kernel Evaluation (`magpie-kernel-evaluator`)**: Use Magpie to benchmark our Poincaré hyperbolic distance and Fréchet Riemannian centroid calculations against native HIP implementations.
3. **Zero-Copy Memory Elimination (`tracelens-analysis-orchestrator`)**: Profile memory traffic to ensure zero unnecessary PCIe/host memory copies.
