# Master AMD Strix Halo Heterogeneous Optimization Roadmap (2026)

**Hardware Profile**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (Strix Halo)
- **Memory**: 128 GB Unified LPDDR5X-7500 (256-bit bus, 210 GB/s sustained UMA bandwidth)
- **NPU**: XDNA2 (32 AI Engine tiles, 50 TOPS INT8)
- **iGPU**: RDNA 3.5 (40 Compute Units @ 2.9 GHz, 118.8 TOPS MXFP4)
- **CPU**: Zen 5 (16 Cores / 32 Threads, Dual 512-bit AVX-512 pipes, 9.2 TOPS VNNI)

---

## 1. The Paradigm Shift: From Model Partitioning to Heterogeneous Operator Sharding

The fundamental bottleneck on Strix Halo is **memory bandwidth (210 GB/s)**, not raw compute. 
Traditional model partitioning (assigning whole models to isolated chips) leaves silicon underutilized and introduces CPU memory latency stalls.

### Master Silicon Allocation Matrix

| Hardware Engine | Primary Architectural Role | Deployed Workloads | Rationale & Performance Ceiling |
|:---|:---|:---|:---|
| **XDNA2 NPU** (50 TOPS) | **Asynchronous Speculative Drafter & Fixed-Graph Router** | `llama3.2:1b-FLM` (Drafter)<br>`qwen3.6-moe` Gating Router<br>`embed-gemma-300m-FLM`<br>`Whisper-Large-v3-Turbo` | Computes token trees and embedding projections at <12W power envelope with zero GPU compute contention. |
| **Radeon 8060S iGPU** (40 CUs) | **High-Throughput MXFP4 Matrix Engine & Tree Verifier** | `Qwen3-Coder-30B-A3B` (88.1 tok/s)<br>`Mistral-Medium-128B-MXFP4`<br>`gpt-oss-20b-MXFP4`<br>`SD-Turbo` / `TRELLIS-3D` | Native RDNA 3.5 MXFP4 matrix multipliers accelerate token verification and active MoE expert FFNs directly from UMA framebuffer. |
| **Zen 5 CPU** (16C / 32T) | **Hardware-Paged KV-Cache MMU & Swarm Orchestration** | Paged KV-Cache Manager (AVX-512)<br>SurrealDB ACID Engine (:8001)<br>Cross-Session EventBus<br>`lfm25-embed-350m` (1024D) | Acts as the system Memory Management Unit, prefetching KV blocks into L3 cache slices for 1M+ context reasoning. |

---

## 2. Quantitative Speedup Projections

1. **Speculative Decoding Speedup**:
   - NPU drafts 4-token candidate trees asynchronously $\rightarrow$ iGPU verifies in a single parallel attention pass.
   - **Net Result**: 128B and 30B MoE generation speeds jump from $88\text{ tok/s} \rightarrow \mathbf{140\text{--}180\text{ tok/s}}$.
2. **CPU-Evacuated 128B Inference**:
   - Evacuating `Mistral-128B` from CPU DDR5 into iGPU `MXFP4` increases decode rate from $2.0\text{ tok/s} \rightarrow \mathbf{18.5\text{ tok/s}}$.
3. **Zero-GPU Continuous Background Indexing**:
   - Offloading `embed-gemma-300m` to NPU preserves all 40 CUs and GPU memory channels for active chat/code workflows.
