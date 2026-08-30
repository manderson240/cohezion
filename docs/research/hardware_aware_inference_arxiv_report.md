# Hardware-Aware Inference: arXiv 2025-2026 Synthesis

**Generated via Local Silicon**: `user.cohezion-hermes-router` (:13305)
**Execution Latency**: 32.35s | **Memory Headroom**: 62.03 GiB | **Cloud Cost**: $0.00

### **1. Phase-Split Heterogeneous Scheduling (NPU Prefill vs. iGPU/CPU Decode)**  
- **Why**: Compute-bound **prefill** (e.g., attention computation) benefits from NPUs’ parallelism and energy efficiency (35–70% energy savings vs. CPU/GPU), while memory-bound **decoding** (e.g., autoregressive token generation) thrives on iGPU/CPU’s high-bandwidth memory (HBM) and low-latency access. NPUs excel in dense matrix operations, whereas iGPU/CPU’s unified memory (e.g., 256-bit LPDDR5X-8533) optimizes for sequential memory access patterns.  
- **Implementation**: Cohezion’s `UnifiedHybridRouter` must **partition tasks dynamically** using **phase-aware scheduling** on AMD Strix Halo:  
  - **NPU prefill**: Offload token generation and attention layers via **NPU-specific kernels** (e.g., TensorRT-LLM optimizations).  
  - **iGPU/CPU decode**: Route token generation and beam search to **iGPU/CPU cores** with **shared memory coherence** (e.g., using **AMD ROCm** for cross-architecture synchronization).  
  - **Pipeline**: Use **asynchronous task queues** to overlap NPU prefill and iGPU/CPU decode phases, leveraging Strix Halo’s **heterogeneous compute fabric** (e.g., **Infinity Fabric 3** for low-latency inter-core communication).  

---

### **2. Cross-Layer Quantization & Memory Bandwidth Constraints**  
- **Why**: Real-world agentic inference prioritizes **memory bandwidth (GB/s)** over theoretical TOP