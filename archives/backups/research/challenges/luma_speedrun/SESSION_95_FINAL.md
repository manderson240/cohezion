# Session 95 — DEFINITIVE FINAL STATUS

**Date**: 2026-04-05/06 (12+ hours of continuous work)
**Deadline**: April 6, 2026 11:59 PM PST (~17 hours remaining)

## Rankings (UNCHANGED)
- GEMM: 13.425µs (rank ~126/391)
- MoE: 154.183µs (rank ~63/274)  
- MLA: 69.745µs (rank ~96)

## What Was Built (20+ correct custom kernels)
- MFMA v1/v2/v3 (26-31µs) — verified FP4 32×32×64 intrinsic
- Triton dotscaled v1/v2/split-K (22-23µs) — BLOCK_K>=128 constraint discovered
- Fused parallel/prologue (89-163µs) — correct but quant overhead dominates
- AMD blog 8-wave ping-pong v1/v2 (22.6µs) — all AMD CDNA4 intrinsics verified working
- Hybrid split-K v2 with lazy Triton (22.7µs) — lazy import didn't fix ranked gap
- MLA a16w16 BF16 decode (100µs) — correct but 2x slower (bandwidth)
- MoE blockscale v1/v2/v3 — all failed (double quant error)

## Why Nothing Improved Ranked Score
The pure aiter baseline (13.4µs) uses `dynamic_mxfp4_quant` + `e8m0_shuffle` + `gemm_a4w4`.
On the ranked runner, this pipeline is ALREADY optimal because:
1. JIT compilation is cached after first call
2. Tensor memory is reused across invocations
3. The CK ASM kernel (`32x128`) is hand-tuned by AMD kernel engineers
4. ANY modification to the Python code adds measurable overhead on ranked

Custom MFMA/Triton kernels are 2x slower because:
- Our MFMA tiles lack software pipelining (8-wave ping-pong helps 14% but not 2x)
- Triton JIT adds per-launch overhead that CK ASM avoids
- The quant+shuffle overhead is ~2-5µs that can't be fused (parallel quant is slower)

## What the Leaders Do Differently (4.3µs)
- `v78_splitk0.py` = 78 iterations with log2_k_split=0
- Likely a fully fused load_inline kernel with AMD ISA-level memory scheduling
- Their GEMM runs ~3-4µs (vs aiter's 6-8µs GEMM-only from tuning CSV)
- This requires months of AMD ISA expertise we don't have

## Skills Created (5)
1. `amd-load-inline-hip-kernel` v2.0.0
2. `amd-gfx950-tl-dot-scaled-constraints` v1.0.0
3. `multi-model-kernel-optimization` v1.0.0
4. `popcorn-benchmark-vs-ranked-scoring` v2.0.0
5. `popcorn-runner-api-inventory` (updated with .co inventory)

## Tools Installed
- GEAK at `/home/mike-anderson/dev/geak/` with Ollama cloud backend
- `ollama_kernel_iterate.sh` for automated iteration
- Complete runner .co inventory (67 kernels mapped)

## Files for Future Sessions
All in `luma_speedrun/amd-mxfp4-mm/`:
- `submission_amd_blog_v2.py` — best custom kernel (22.6µs, 8-wave ping-pong)
- `submission_triton_splitk.py` — correct split-K (32µs on M=16)
- `submission_hybrid_splitk_v2.py` — lazy Triton import hybrid
- `LEADER_ANALYSIS.md` — 338-line analysis of leader patterns
- `RUNNER_INVENTORY.md` — complete .co tile inventory
