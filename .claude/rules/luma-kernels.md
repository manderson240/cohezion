# Luma AMD Speedrun — Post-Competition Reference (April 2026)

**Competition ended: April 7, 2026, 07:59 UTC**

## Final Results

| Kernel | Our Best | Leader | Final Gap | Submissions |
|--------|----------|--------|-----------|-------------|
| GEMM | 13.4µs | 4.3µs | 3.1x | ~20 leaderboard |
| MLA | 69.7µs | 19.5µs | 3.6x | ~8 leaderboard |
| MoE | 154µs | 70.5µs | 2.2x | ~10 leaderboard |

## What Worked

1. **aiter API baseline** (gemm_a4w4, fused_moe, mla_decode_stage1_asm_fwd) — best ranked scores
2. **load_inline custom MFMA kernels** — compile and pass correctness on MI355X runners
3. **Fused quant+GEMM** — inline BF16→FP4 quantization proven correct (0.0 error)
4. **K-Search compound loop** — Ollama synthesis → popcorn eval → tree learning (operational)
5. **TDD for GPU kernels** — local verification of data flow before remote submission

## What Didn't Work

1. **per_1x32_f4_quant_hip** — silent incompatibility with gemm_a4w4 (L265)
2. **Triton GEMM (gemm_afp4wfp4)** — autotuner exceeds 12-min runner timeout
3. **Scalar FP4 quantization in fused kernel** — 4-50x slower than CK ASM pipeline
4. **dispatch_policy=1 for MoE** — helped benchmark, hurt ranked (warm JIT caches)
5. **MLA leaderboard submissions** — 8 shapes consistently exceed 12-min timeout

## Key Architecture Lessons

- **12-minute runner timeout** is the binding constraint for custom kernels (L266)
- **Pre-compiled .co files** (CK ASM) have zero JIT overhead — hard to beat with JIT
- **Ranked mode ≠ benchmark mode** — warm caches change everything
- **Popcorn CLI**: `popcorn submit <file> --mode <mode> --leaderboard <name> --no-tui`
- **Rate limits**: 1 leaderboard/hour, 1 test/hour per kernel (as of April 2026)
