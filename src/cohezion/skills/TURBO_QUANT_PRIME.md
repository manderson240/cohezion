# SKILL: TURBO_QUANT_PRIME

## DOMAIN EXPERTISE
Expertise in high-fidelity KV-cache compression and hardware-aware kernel optimization for AMD silicon (Strix Halo/gfx1151). Specializes in PolarQuant, Quantized Johnson-Lindenstrauss (QJL), and Wave32 matrix alignment.

## KEY TEXTS & CONCEPTS
- **PolarQuant**: MSE-optimal polar coordinate transformation for state vector compression.
- **Wave32 Alignment**: Bypassing the "Binary Hard-Lock" on RDNA 3.5 by forcing 32-thread wavefronts (`-mwavefrontsize32`).
- **Mean-Preserving Correction**: Chunked centroid alignment to prevent latent drift during de-quantization.
- **HIHO Stability**: Maintaining exactly 0.5 coherence overlap on the 12D manifold.

## INSTRUCTION
1. **Initialize Hardware-Aware Kernel**:
   ```python
   from cohezion.flume.kernels.turbo_kv import TurboKVKernel
   kernel = TurboKVKernel() # Automatically forces Wave32 on gfx1151
   ```
2. **Execute PolarQuant Compression**:
   ```python
   from cohezion.flume.turbo_quant import TurboQuantCPU
   tq = TurboQuantCPU(head_dim=128)
   compressed = tq.compress_kv(original_tensor) # Achieves ~3.76x reduction
   ```
3. **Verify Manifold Integrity**:
   ```python
   from cohezion.flume.coherence_guard import TurboQuantHarness
   harness = TurboQuantHarness()
   metrics = harness.verify_quantization(original, recovered)
   assert metrics['stability_delta'] <= 0.005 # Ensure HIHO-Lock
   ```

## VERSION
v1.0 (April 2026 Breakthrough)

## SEE ALSO
- **FLUME_METHODOLOGY_PRIME**
- **TRIUNE_SUBSTRATE_PRIME**
