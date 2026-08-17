# Post-Mortem Consultation & Architectural Recommendations: AMD Strix Halo Memory Aperture Collision

**Oracle Model**: `deepseek-v4-pro:cloud` (Tier 2 Cloud Senior Kernel & Systems Architect)  
**Date Grounded**: August 17, 2026  
**Hardware Context**: AMD Ryzen AI MAX+ 395 (Strix Halo APU, 128GB LPDDR5X UMA, GFX1151 / RDNA 3.5, XDNA 2 NPU)

---

## 1. Post-Mortem Review & Clarifications

### Accurate Diagnosis & Corrections
1. **Causal Chain**: The SIGSEGV in `amd::Command::enqueue` (`libamdhip64.so`) was caused by **memory aperture exhaustion and uncoordinated multi-process GPU context allocation** between Lemonade's resident GPU models (`llamacpp-rocm`) and PyTorch's attempted asynchronous `hipMemcpyWithStream`.
2. **Hardware Invariants**:
   - Processor Architecture: **Zen 5** (16-core, 32-thread with 512-bit native AVX-512 datapath).
   - Memory Substrate: **128GB LPDDR5X unified UMA**.
3. **Safety of CPU Workaround**: Pinning the fine-tuning task to `device="cpu"` successfully bypassed the ROCm aperture collision and allowed gradient descent to execute cleanly across 128GB RAM with zero VRAM contention.

---

## 2. Long-Term Recommendations for Safe GPU/NPU/CPU Co-Existence

### A. Workload Engine Separation (Primary Rule)
To avoid aperture collisions on APUs:
- **NPU (XDNA 2)**: Dedicate to Lemonade inference (`FLM` / ONNX Runtime Vitis AI).
- **Radeon iGPU (RDNA 3.5)**: Dedicate to heavy GPU inference (`Qwen3-Coder-30B`) OR isolated PyTorch training under exclusive lock.
- **CPU (Zen 5 AVX-512)**: Dedicate to background fine-tuning pipelines and deterministic AST verification.

### B. FleetLock Serialization for GPU Operations
Never allow concurrent uncoordinated GPU initialization. All model loads and PyTorch GPU training runs must acquire our existing `FleetLock("modelload")` or `FleetLock("gpu_training")` helper.

### C. PyTorch Memory Allocator Configuration
When running ROCm GPU operations on UMA:
```bash
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
export HSA_XNACK=1
```
This prevents large contiguous block reservations that collide with APU driver-pinned apertures.
