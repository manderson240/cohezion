# Experiment Design: Turbo Quant Multi-Node Validation

## 1. Objectives
This study aims to scientifically verify the "Turbo Quant Unlock" on AMD Strix Halo (128GB UMA) across three dimensions:
1.  **Throughput Scalability**: Performance gains across NPU, iGPU, and CPU.
2.  **Memory Compression Efficiency**: Reduction in KV-cache footprint for 128k context windows.
3.  **Semantic Integrity (HIHO)**: Coherence stability during aggressive 3.5-bit quantization.

## 2. Hypotheses
- **H1**: Wave32 alignment on the iGPU will yield >2x throughput vs. standard Wave64 libraries.
- **H2**: TurboQuant 3.5-bit will maintain HIHO stability within ±0.001 of the FP16 baseline.
- **H3**: Swarm routing (NPU+iGPU) will improve total system tokens/sec by >= 40% compared to iGPU-only execution.

## 3. Methodology
- **Node A (NPU)**: Execute 100 iterations of Qwen3.5-4b-FLM on port 13306.
- **Node B (iGPU)**: Execute 100 iterations of TurboKVKernel (Wave32) using synthetic 32k-128k context payloads.
- **Node C (CPU)**: Execute 100 iterations of TurboQuantCPU (Vectorized) for baseline parity checks.
- **Verification**: All results filtered through `TurboQuantHarness` invariants.

## 4. Expected Results
- **iGPU**: ~47-50 TPS
- **NPU**: ~110-115 TPS
- **Memory**: 40GB KV-cache (FP16) -> 8GB KV-cache (TurboQuant)
- **Coherence**: Stability locked at 0.5.
