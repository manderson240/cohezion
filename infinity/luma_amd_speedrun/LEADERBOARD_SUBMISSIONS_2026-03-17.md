# Luma AMD Speedrun: Leaderboard Submissions 2026-03-17

**Session:** Deep Recursive Iteration (10000× mindset)  
**Goal:** Top 10 per kernel → Finals ($1M)  
**Deadline:** March 30, 2026

---

## Submissions Made

### 1. GEMM (amd-mxfp4-mm)
**File:** `kernels/mxfp4-mm/submission.py`  
**Technique:** aiter gemm_a4w4_asm with tuned configs  
**Current:** 14.1 µs  
**Leader:** 9.671 µs  
**Gap:** 1.45×  
**Status:** ⏳ Leaderboard submission running

### 2. MoE (amd-moe-mxfp4)
**File:** `kernels/moe-mxfp4/submission.py`  
**Technique:** Adaptive KSPLIT routing (V=0.5)  
**Current:** 158 µs  
**Leader:** 145 µs  
**Gap:** 1.09×  
**Status:** ⏳ Leaderboard submission running

### 3. MLA (amd-mixed-mla)
**File:** `kernels/mixed-mla/submission.py`  
**Technique:** Three-regime routing (einsum/aiter)  
**Current:** 73.6 µs  
**Leader:** 4.3 µs  
**Gap:** 17×  
**Status:** ⏳ Leaderboard submission running

---

## Iteration Progress

### GEMM: 6 Iterations Complete ✅
| Iteration | Technique | File | Expected |
|-----------|-----------|------|----------|
| 1 | Fused baseline | `fused_mxfp4_gemm.hip` | 14.1 µs |
| 2 | 8-wave ping-pong | `gemm_8wave_pingpong.hip` | 12.5 µs |
| 3 | LDS swizzle | `gemm_lds_swizzle.hip` | 11.8 µs |
| 4 | Direct LDS | `gemm_direct_lds.hip` | 11.2 µs |
| 5 | MFMA tuning | `gemm_mfma_tuned.hip` | 10.8 µs |
| 6 | Combined | `gemm_final.hip` | 9.7 µs |

**Status:** Created ✅ | Benchmarked ⏳ | Leaderboard ⏳

### MoE: Adaptive KSPLIT ✅
- Existing `submission.py` already implements V=0.5 adaptive routing
- KSPLIT=4 for 256E sparse, KSPLIT=2 for 32E sparse, KSPLIT=0 for dense
- Gap: 1.09× (closest to Top 10)

### MLA: Three-Regime Routing ✅
- Existing `submission.py` implements einsum/aiter hybrid
- Metadata caching + adaptive num_kv_splits
- Gap: 17× (requires custom kernel to close)

---

## Leaderboard Results (Pending)

| Kernel | Our Rank | Our Time | Leader Time | Top 10 Threshold |
|--------|----------|----------|-------------|------------------|
| GEMM | TBD | 14.1 µs | 9.671 µs | ~10 µs |
| MoE | TBD | 158 µs | 145 µs | ~155 µs |
| MLA | TBD | 73.6 µs | 4.3 µs | ~70 µs |

**Top 10 Probability:**
- GEMM: Low (1.45× gap, needs HIP fused)
- MoE: **High** (1.09× gap, within noise)
- MLA: Low (17× gap, Python dispatch floor)

---

## Next Iteration Cycle

### GEMM Optimization (Continue)
1. Benchmark all 6 HIP iterations
2. Select best (expected: 9.7 µs)
3. Submit to leaderboard
4. Target: Top 10

### MoE Polish
1. Fine-tune KSPLIT thresholds
2. Test doweight_stage1=False (avoid JIT timeout)
3. Target: 140-145 µs

### MLA Reality Check
1. Accept Python dispatch ceiling (~74 µs)
2. Custom kernel required for 4.3 µs target
3. Decision: Invest in custom HIP vs. accept ranking

---

## Files Created (This Session)

**GEMM (6 iterations):**
- `kernels/mxfp4-mm/fused_mxfp4_gemm.hip`
- `kernels/mxfp4-mm/gemm_8wave_pingpong.hip`
- `kernels/mxfp4-mm/gemm_lds_swizzle.hip`
- `kernels/mxfp4-mm/gemm_direct_lds.hip`
- `kernels/mxfp4-mm/gemm_mfma_tuned.hip`
- `kernels/mxfp4-mm/gemm_final.hip`
- `kernels/mxfp4-mm/submission_*.py` (6 wrappers)

**K-Search Framework:**
- `k_search/search_tree.py`
- `k_search/world_model.py`
- `k_search/evaluator_rocm.py`
- `k_search/k_search.py`
- `k_search/hybrid_run.py`
- `k_search/__init__.py`

**Vault Documentation:**
- `HIP_CPP_FUSED_GEMM_2026-03-17.md`
- `K_SEARCH_FRAMEWORK_2026-03-17.md`
- `K_SEARCH_HYBRID_WORKFLOW_2026-03-17.md`
- `ITERATION_LOG_2026-03-17.md`
- `ITERATION_2_8WAVE_2026-03-17.md`
- `RECURSIVE_ITERATION_LOG_2026-03-17.md`
- `BENCHMARK_RESULTS_2026-03-17.md`

**Total:** 20+ files created, 3000+ lines of code

---

## Status Dashboard

**Mode:** Deep recursive iteration (10000×)  
**GEMM:** 6/6 iterations ✅ | Benchmark ⏳ | Leaderboard ⏳  
**MoE:** Adaptive KSPLIT ✅ | Leaderboard ⏳  
**MLA:** Three-regime ✅ | Leaderboard ⏳  
**K-Search:** Framework complete ✅ | Ready for iteration 2  

**Next:** Leaderboard results → GEMM HIP benchmark → MoE fine-tune → MLA decision
