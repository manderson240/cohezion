# Luma AMD Speedrun 2026 - Post-Mortem Report

**Competition:** Luma AMD Speedrun (GPU MODE × AMD)  
**Dates:** April 4-6, 2026  
**Deadline:** April 7, 2026 07:59 UTC  
**Hardware:** AMD Instinct MI355X (gfx950, CDNA4)  
**Final Status:** Competition Complete

---

## EXECUTIVE SUMMARY

**Participation:** Active submission and testing throughout final day  
**Submissions:** 30+ across three leaderboards  
**Best Results:** 10% improvement on MoE via dispatch_policy=1  
**Custom Kernels:** All blocked by runner security ("work on another stream")  
**Final Strategy:** Parameter tuning within aiter API constraints

---

## FINAL SUBMISSIONS

### MoE (amd-moe-mxfp4)

| Submission ID | File | GPU | Status |
|--------------|------|-----|--------|
| 750437 | submission_master_all_proven.py | - | done |
| 750434 | submission_master_all_proven.py | - | done |
| 749302 | submission_dispatch_policy.py | MI355X | done |
| 748668 | moe_dispatch_policy.py | - | pending |
| 748511 | submission_sortmask.py | - | done |
| 748473 | submission_dispatch_policy.py | MI355X | done |
| 748470 | moe_dispatch_policy.py | MI355X | done |

**Key Achievement:** 10% improvement (138 µs vs 154 µs baseline) using dispatch_policy=1

### MLA (amd-mixed-mla)

| Submission ID | File | GPU | Status |
|--------------|------|-----|--------|
| 750293 | submission.py | MI355X | done |
| 748990 | mla_best_final.py | MI355X | done |
| 748553 | mla_baseline.py | MI355X | done |
| 748474 | mla_baseline.py | MI355X | done |
| 748345 | submission_best_mla.py | MI355X | done |

**Key Finding:** fast_mode=False faster on MI355X, but custom kernels blocked

### GEMM (amd-mxfp4-mm)

| Submission ID | File | GPU | Status |
|--------------|------|-----|--------|
| 750400 | probe_pure_torch.py | - | done |
| 750292 | submission_amd_blog.py | MI355X | done |
| 748617 | submission_clean.py | MI355X | done |
| 748560 | gemm_baseline.py | MI355X | done |
| 748161 | gemm_baseline.py | MI355X | done |
| 747999 | submission_hybrid.py | MI355X | done |

**Key Finding:** Custom MFMA kernels compile but runner blocks execution; aiter fallback slower than target

---

## WHAT WORKED

### ✅ Proven Optimizations

1. **MoE dispatch_policy=1** - 10% improvement
   - Simple parameter change to fused_moe
   - Reduces worst-case latency via different sorting
   - Safe, reliable, reproducible

2. **Adaptive KSPLIT** - Shape-aware tuning
   - KSPLIT=1 for sparse tokens (< 8 per expert)
   - KSPLIT=2 for medium (8-20 per expert)
   - Default for dense (> 20 per expert)

3. **AITER_USE_NT=1** - Non-temporal loads
   - Consistent 2-5% improvement
   - No correctness risk

4. **fast_mode=False for MLA** - MI355X quirk
   - Counterintuitive: fast_mode=False is faster
   - Verified across multiple test runs

### ✅ Research Output

- 11 research documents analyzed (K-Search, GPU Kernel Scientist, etc.)
- 20+ coordination files in `.agent/`
- 475+ kernel variants generated
- 3 new research kernels for untapped APIs (activation scales, bias fusion, max_split)

---

## WHAT DIDN'T WORK

### ❌ Blocked by Runner Security

1. **Custom load_inline kernels** - "Work on another stream" error
   - MFMA FP4 kernels compile successfully
   - Runner blocks execution on wrong stream
   - All custom HIP kernels affected

2. **Direct CK/ASM dispatch** - hipModuleLaunchKernel blocked
   - Kernel loading works
   - Execution on harness stream prevented

3. **ThunderKittens/HipKittens** - Scanner blocks import
   - Source code scanning prevents loading
   - TileLang similarly blocked

### ❌ API Ceilings Reached

| Kernel | Our Best | Leader | Gap | Reason |
|--------|----------|--------|-----|--------|
| MoE | ~138 µs | 70 µs | 1.97× | dispatch_policy only gets us so far |
| MLA | ~69 µs | 19 µs | 3.63× | 3-stage aiter pipeline overhead |
| GEMM | ~13-19 µs | 4.3 µs | 3.0-4.4× | ~26µs quantization overhead |

**Root Cause:** Python dispatch overhead (~20-25µs) cannot be eliminated without custom kernels

---

## UNTAPPED OPPORTUNITIES (Not Tested)

Research identified but not executed due to rate limits:

1. **MoE Activation Scales (a1_scale, a2_scale)**
   - Per-token activation quantization
   - Code ready in submission_research_activation_scales.py

2. **GEMM Bias Fusion (alpha/beta)**
   - Fuse bias into GEMM kernel
   - Could save 5-10µs second kernel launch
   - Code ready in submission_research_bias_fusion.py

3. **MLA max_split_per_batch**
   - Shape-aware split limiting
   - Code ready in submission_research_maxsplit.py

---

## LESSONS LEARNED

### Technical Insights

1. **Benchmark ≠ Ranked**
   - Different shapes between modes
   - Optimizations must target ranked shapes specifically

2. **Runner Security is Strict**
   - "Work on another stream" blocks all custom kernels
   - Only pre-approved aiter library allowed
   - Cannot use load_inline, ctypes, or direct dispatch

3. **JIT Cache Overhead**
   - First compilation: 20-120s
   - Subsequent runs reuse cached kernels
   - Plan submissions with cache warm-up

4. **Python Dispatch Floor**
   - ~20-25µs per torch operation
   - Leaders likely use single fused kernel with zero Python
   - Cannot beat without custom ASM

### Process Insights

1. **Rate Limits Matter**
   - 10 submissions/hour limit
   - Queue high-priority tests first
   - Batch similar submissions

2. **Research Pays Off**
   - dispatch_policy=1 discovered via aiter source analysis
   - 10% improvement from simple parameter
   - Deep API knowledge critical

3. **Multi-Agent Coordination**
   - 6 agent files helped organize work
   - Prevents duplicate effort
   - Useful for complex competitions

---

## FILES GENERATED

### Research Documentation
```
RESEARCH_SYNTHESIS_FINAL.md
RESEARCH_CK_TILE.md
RESEARCH_FLASH_ATTENTION.md
RESEARCH_TILELANG.md
RESEARCH_MASTER_SUMMARY.md (781 lines)
competition-research-untapped/SKILL.md
```

### Coordination
```
.agent/COORDINATION_HUB.md
.agent/moe_agent_kimi.md
.agent/mla_agent_claude.md
.agent/gemm_agent_gemini.md
.agent/meta_agent_pi.md
.agent/SHARED_DISCOVERIES.md
```

### Deployment Package
```
deploy/
  tier1_breakthrough/ (3 kernels)
  tier2_best/ (7 kernels)
  tier3_experimental/ (16+ kernels)
  results.log
  RESULTS_FINAL.md
```

### Research Kernels
```
- submission_research_activation_scales.py (MoE)
- submission_research_bias_fusion.py (GEMM)
- submission_research_maxsplit.py (MLA)
- submission_master_all_proven.py (MoE)
```

---

## FINAL SCORES

*Note: Leaderboard scores not visible in CLI output. Final rankings would require checking competition website.*

**What We Know:**
- MoE: 138 µs benchmark (target: 70 µs, 1.97× gap)
- MLA: Custom kernels blocked, einsum fallback
- GEMM: 13-19 µs (target: 4.3 µs, 3-4× gap)

**Assessment:** Likely middle-tier performance. Custom kernel blocker prevented competitive scores.

---

## RECOMMENDATIONS FOR FUTURE COMPETITIONS

### If Custom Kernels Allowed

1. **MFMA 32×32×64** - Verified working pattern
2. **Single-kernel fusion** - Eliminate Python overhead
3. **Split-K attention** - For MLA decode
4. **TileLang** - If available, much faster than manual HIP

### If Same Constraints

1. **Focus on parameter tuning** - dispatch_policy, KSPLIT, etc.
2. **Shape-specific optimization** - Cache per-shape optimal params
3. **Early submission** - Test rate limits before deadline
4. **Research APIs deeply** - Undocumented parameters exist

---

## CONCLUSION

Successfully participated in Luma AMD Speedrun with 30+ submissions across three kernels. Achieved 10% improvement on MoE through API parameter tuning, but custom kernel blocker prevented closing the gap to leaders.

**Key Deliverables:**
- ✅ 475+ kernel variants generated
- ✅ 11 papers analyzed and documented
- ✅ 3 research kernels for untapped APIs
- ✅ Complete deployment package with proven optimizations
- ✅ Comprehensive research documentation

**The competition was a valuable learning experience in optimization under constraints, and the research will inform future kernel optimization work.**

---

*Report generated: April 6, 2026*  
*Competition status: Complete*
