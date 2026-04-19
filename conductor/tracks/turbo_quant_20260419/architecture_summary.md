# Turbo Quant Architecture Summary

## 1. Integration Boundaries
- **Lemonade Backend Extension**: The `lemonade` server (local private instance) will be the primary target for Turbo Quant. We will leverage its ROCm/HIP backend, specifically targeting the `gfx1151` architecture.
- **Unified Provider API**: The `LemonadeProvider` and `OllamaProvider` will be unified under a `LocalModelOrchestrator` that handles the `turbo_quant` flag.
- **Payload Specification**:
  ```json
  {
    "model": "Gemma-4-E2B",
    "turbo_quant": {
      "enabled": true,
      "precision": "mxfp4",
      "nodes": ["npu", "gpu"]
    }
  }
  ```

## 2. Hardware Distribution Logic (AMD Strix Halo)
- **NPU (XDNA 2)**: 
  - **Role**: Latent state projections and high-speed token encoding.
  - **Models**: Small models (<=4B) using FastFlowLM (FLM).
- **iGPU (Radeon 8060S)**:
  - **Role**: Primary compute for large-model inference (Gemma-4).
  - **Precision**: MXFP4 / 4-bit / Mixed Precision via Triton/HIP kernels.
- **CPU (Ryzen AI MAX+)**:
  - **Role**: KV-cache management, background data mesh operations, and INT4 ONNX fallback.

## 3. Coherence Guard & AutoHarness
- **Module**: `src/cohezion/flume/coherence_guard.py`.
- **Harness**: `TurboQuantHarness`.
- **Invariants**:
  1. **Numerical Parity**: MAE < 0.05 vs FP16 baseline.
  2. **HIHO Stability**: Manifold overlap at exactly 0.5 (±0.005 tolerance).
  3. **Token Throughput**: >= 30% improvement over standard ROCm GGUF.

## 4. Implementation Path
- **Step 1**: Synthesize the `CoherenceGuard` harness.
- **Step 2**: Implement Triton kernels for MXFP4 on `gfx1151`.
- **Step 3**: Integrate kernels into `lemonade` backend.
- **Step 4**: Update `HybridSwarmRouter` for explicit node allocation.