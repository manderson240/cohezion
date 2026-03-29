# WHITE-PAPER: Blackwell G4 & Nemotron Hybrid MoE Orchestration

## 1. Executive Summary
This paper details the engineering breakthroughs required to successfully orchestrate the **NVIDIA Nemotron-3-Nano-30B-A3B** model on **NVIDIA Blackwell (G4)** hardware within the Kaggle competition environment. It addresses critical hurdles in hardware locking, hybrid architecture fine-tuning, and numerical precision strategies.

## 2. Hardware: The Blackwell sm_120 Mandate
The NVIDIA Blackwell (RTX 6000 Blackwell Server Edition) introduces the **sm_120** compute capability. Standard "GPU" requests in standard cloud runners often fallback to sm_60 (P100) or sm_90 (Hopper), which lack the VRAM or instruction sets required for 30B parameter hybrid models.

### 2.1 Hardware Locking (Kaggle G4)
Accessing the G4 instances programmatically requires a specific metadata handshake:
*   **machine_shape**: Must be set exactly to `"NvidiaRtxPro6000"`.
*   **docker_image**: Requires the private URI `gcr.io/kaggle-private-byod/python@sha256:9fa0da194fad2241d3f01a80581cbecbd3a258b4d1b695e2cbbbc62a0fd205ac`.
*   **Triton JIT**: Blackwell requires a specialized PTX assembler. The `ptxas-blackwell` binary must be copied to a writable `/tmp` directory and granted execute permissions.

## 3. Architecture: Nemotron Hybrid MoE (A3B)
The Nemotron-3-Nano-30B-A3B is an "Active 3B" model. It leverages a Mixture-of-Experts (MoE) strategy where only ~3.2B parameters are active per token.

### 3.1 Interleaved Mechanisms
The model's 52 layers consist of:
*   **23 Mamba-2 Layers**: For sequential efficiency and 1M token context.
*   **23 MoE Layers**: Utilizing 128 experts with top-6 routing.
*   **6 GQA Attention Layers**: Acting as factual retrieval anchors.

### 3.2 Fine-Tuning Strategy
LoRA targeting for this hybrid architecture must move beyond standard `q_proj/v_proj` patterns. The optimal target modules are the linear projections within the Mamba blocks:
*   **Regex**: `r".*\.(in_proj|out_proj|up_proj|down_proj)$"`
*   **Rank**: Max rank `r=32` is recommended for reasoning tasks.

## 4. Forward-Looking: FP4 Micro-Tensor Scaling
Blackwell's **Transformer Engine 2.0** introduces native **FP4** support. To achieve maximum throughput (up to 4x BF16), Cohezion agents should transition from standard `bitsandbytes` quantization to **Micro-Tensor Scaling** via the `NVFP4BlockScaling` recipe.

## 5. Protocol: The Ralph Loop
To prevent regression and ensure stability on high-end hardware, all Cohezion implementations now follow the **Ralph Loop**:
`[Benchmark -> Gate -> Propose -> Apply -> Verify]`
No solution is finalized until it achieves ≥0.5 HIHO coherence through automated `pytest` and diagnostic verification.

---
**Date**: 2026-03-24  
**Project**: Cohezion  
**Status**: Codified Standard  
