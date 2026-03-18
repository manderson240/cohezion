# Benchmark Results: GEMM Iterations

**Date:** 2026-03-17  
**Kernel:** amd-mxfp4-mm (MXFP4 GEMM)  
**Leader:** 9.671 µs  
**Target:** 9.7 µs

---

## Benchmark Status

| Iteration | Technique | Geomean (µs) | Improvement | Status |
|-----------|-----------|--------------|-------------|--------|
| 1 | Fused baseline | TBD | — | ⏳ Running |
| 2 | 8-wave ping-pong | TBD | -11% expected | ⏳ Running |
| 3 | LDS swizzle | TBD | -6% expected | ⏳ Queued |
| 4 | Direct LDS | TBD | -5% expected | ⏳ Queued |
| 5 | MFMA tuning | TBD | -4% expected | ⏳ Queued |
| 6 | Combined all | TBD | -10% expected | ⏳ Queued |

---

## Expected Results

**Performance Path:**
- Iteration 1: 14.1 µs (baseline)
- Iteration 2: 12.5 µs (-11%)
- Iteration 3: 11.8 µs (-6%)
- Iteration 4: 11.2 µs (-5%)
- Iteration 5: 10.8 µs (-4%)
- Iteration 6: 9.7 µs (-10%)

**Total:** 14.1 → 9.7 µs (-31%)

---

## Leaderboard Comparison

| Rank | Time (µs) | Kernel |
|------|-----------|--------|
| 1 | 9.671 | parcadei (leader) |
| 2-10 | 9.8-10.5 | Top 10 threshold |
| **Target** | **9.7** | **Our goal** |
| Current | 14.1 | Baseline |
| Gap | 1.45× | To close |

---

## Next Actions

1. **Benchmark results** → Compare actual vs expected
2. **Select best iteration** → Submit to leaderboard
3. **Top 10 check** → If ranked, proceed to MoE
4. **If not Top 10** → Further optimization needed

---

**Status:** Benchmark running (JIT builds + queue pressure expected)
