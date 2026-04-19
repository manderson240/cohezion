# Luma AMD Speedrun — Leaderboard Scores (manderson240)
**Scraped:** 2026-04-05 04:05 UTC | **Deadline:** April 7, 2026 07:59 UTC (~2 days 3 hours remaining)

## Our Rankings (best-ever leaderboard scores)

| Kernel | Best Score | Rank | Total | Leader | Gap |
|--------|-----------|------|-------|--------|-----|
| **GEMM** (amd-mxfp4-mm) | **13.425µs** | ~126 / 391 | 391 | 4.354µs | 3.1x |
| **MoE** (amd-moe-mxfp4) | **154.183µs** | ~63 / 274 | 274 | 70.470µs | 2.2x |
| **MLA** (amd-mixed-mla) | **69.745µs** | ~96 / ? | ? | 19.484µs | 3.6x |

## Session 91 Leaderboard Submissions (ACTUAL ranked scores)

| Kernel | Submission | Score | vs Best | Result |
|--------|-----------|-------|---------|--------|
| **GEMM** | #730941 (v6 hybrid) | **23.987µs** | worse than 13.425µs | DID NOT improve rank |
| **GEMM** | #730122 (v5 custom) | **27.174µs** | worse than 13.425µs | DID NOT improve rank |
| **MoE** | #729992 (dispatch_policy=1) | **214.153µs** | worse than 154.183µs | DID NOT improve rank |
| **MLA** | #730281 (hybrid_v2) | **83.320µs** | worse than 69.745µs | DID NOT improve rank |
| **MLA** | #729824 (earlier) | **79.484µs** | worse than 69.745µs | DID NOT improve rank |
| **MLA** | #731234 (hybrid_v3) | test only, no score | rate limited | incomplete |

**CRITICAL FINDING: ALL session 91 leaderboard submissions scored WORSE than our existing bests.**
The benchmark improvements (13.3µs GEMM, 89µs MoE) did NOT translate to ranked scores
because ranked shapes are different and harder than benchmark shapes.

## Top 3 Per Kernel

### GEMM (amd-mxfp4-mm) — 391 entries
| Rank | User | Score |
|------|------|-------|
| 1 | bhagawan-yantrion | 4.354µs |
| 2 | mars-compute | 4.409µs |
| 3 | josusanmartin | 7.651µs |
| ~126 | **manderson240** | **13.425µs** |

### MoE (amd-moe-mxfp4) — 274 entries
| Rank | User | Score |
|------|------|-------|
| 1 | Danishlynx | 70.470µs |
| 2 | Maxwell Cipher | 107.345µs |
| 3 | shaw061434 | 108.412µs |
| ~63 | **manderson240** | **154.183µs** |

### MLA (amd-mixed-mla)
| Rank | User | Score |
|------|------|-------|
| 1 | josusanmartin | 19.484µs |
| 2 | Barry_zhang | 20.589µs |
| 3 | John Hahn | 29.218µs |
| ~96 | **manderson240** | **69.745µs** |

## Key Observations

1. **GEMM**: Our 13.425µs is the AITER BASELINE score (not our custom MFMA kernel).
   The v6 hybrid submission (#730941) may not have improved the ranked score because
   the ranked shapes differ from benchmark shapes. The leaderboard shows our OLD
   best score from a previous session.

2. **MoE**: Score shows 154.183µs — this is our OLD score, NOT the dispatch_policy=1
   submission (which benchmarked at 89-436µs). The leaderboard may use geometric mean
   across secret shapes, or our latest submission hasn't updated the score yet.

3. **MLA**: 69.745µs is our original score. The hybrid_v2 (23-104µs benchmark) and
   hybrid_v3 submissions may not have improved the RANKED score because ranked shapes
   are different/harder than benchmark shapes.

## Error Tolerances (from reference implementations)

| Kernel | rtol | atol | Implication |
|--------|------|------|-------------|
| **GEMM** | 1e-02 | 1e-02 | 1% — tight, must match aiter's quant closely |
| **MoE** | 5e-02 | 5e-02 | 5% — relaxed, allows approximate dispatch |
| **MLA** | 1e-01 | 1e-01 | 10% — very relaxed, enables aggressive FP8/approx |

**Key:** MLA's 10% tolerance means we can use aggressive approximations (lower-precision quant, approximate softmax) without failing correctness. MoE's 5% also leaves room. GEMM at 1% is tightest.

## Competition Details

- **Deadline:** April 7, 2026 07:59 UTC (~2 days remaining)
- **Scoring:** Geometric mean across secret ranked shapes (different from benchmark shapes)
- **GEMM ref:** `aiter.gemm_a4w4` with `dynamic_mxfp4_quant` + `e8m0_shuffle` + `bpreshuffle=True`
- **MoE ref:** `fused_moe` with `ActivationType.Silu`, `QuantType.per_1x32`, `doweight_stage1=False`
- **MLA ref:** `mla_decode_fwd` with FP8 Q+KV, `num_kv_splits=32`, `intra_batch_mode=True`

## Analysis: Why Rankings Don't Reflect Our Benchmark Improvements

The ranked score uses SECRET test shapes that differ from the benchmark shapes.
Our optimizations may improve benchmark shapes but not ranked shapes:
- GEMM: ranked shapes likely include large M×N×K where our 32×32 MFMA tiles are slow
- MoE: ranked shapes may have different expert counts than benchmark
- MLA: ranked shapes may have larger batch/kv combinations

**Next priority: optimize for the RANKED shapes, not benchmark shapes.**
