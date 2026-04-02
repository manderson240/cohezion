# Luma AMD Speedrun — Kernel Optimization Rules

## HARD CONSTRAINT: load_inline ONLY

**ALL new kernel submissions MUST use `torch.utils.cpp_extension.load_inline()` for custom HIP C++ kernels.**

The Python API ceiling has been reached on all 3 kernels across 4 conductors and 200+ experiments:
- aiter `gemm_a4w4` / `fused_moe` / `mla_decode_fwd` — **EXHAUSTED**
- Parameter tuning (KSPLIT, block_size, sorting, thresholds) — **EXHAUSTED**
- Triton custom kernels — 68% slower than CK ASM baseline
- ctypes HIP dispatch — blocked by runner stream isolation
- CUDA graphs — blocked by runner sandbox

**The ONLY path to competitive times is `load_inline()`** — proven by Rank 1 (1us GEMM).

## Allowed Approaches

1. `torch.utils.cpp_extension.load_inline()` with HIP C++ kernels
2. HipKittens tile primitives via load_inline
3. CK-Tile composable primitives via load_inline
4. Untested aiter APIs (pa_ps_fwd_asm, fmha_v3_varlen_fwd) — test first, document results
5. K-Search (arXiv:2602.19128) guided mutations of load_inline kernels

## BANNED Approaches (API Ceiling Reached)

- Tuning aiter API parameters (KSPLIT, block_size, sorting, thresholds)
- Modifying fused_moe dispatch policy or weight stage
- Adjusting mla_decode_fwd num_kv_splits or fast_mode
- Any submission that only changes Python-level parameters

## Two Builders Pattern

- **Correctness Anchor**: Keep baseline aiter API submissions as reference
- **Performance Explorer**: All new work uses load_inline custom kernels
- Never modify the anchor — only add new explorer variants

## Benchmark-Driven Learning

- `popcorn --mode test` (correctness) and `--mode benchmark` (performance) have NO rate limit
- `popcorn --mode leaderboard` is limited to ~1/hour per kernel
- Maximize benchmarks between submissions (12 per hour target)
- Persist EVERY result to SurrealDB kernel_run table (even failures)

## Current Best Times

| Kernel | Our Best | Leader | Gap | Path |
|--------|----------|--------|-----|------|
| GEMM | 22.8us | 4.3us | 5.3x | load_inline + HipKittens/rocWMMA tiling |
| MLA | 69.7us | 33.0us | 2.1x | Untested APIs + load_inline attention |
| MoE | 154.2us | 109.8us | 1.4x | load_inline LDS bridge |

## Deadline: April 6, 2026, 11:59 PM PST
