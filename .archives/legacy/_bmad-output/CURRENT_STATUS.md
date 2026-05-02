# R-Zero Challenger Framework - Current Status

**Last Updated:** 2026-03-18 (Session in progress)
**Current Phase:** Phase 2 - Validate Assumptions
**Mode:** Build (execution phase)

---

## Competition Overview

**Event:** Luma AMD Speedrun ($650K prize pool)
**Timeline:** March 16-30, 2026 (14 days total)
**Current Day:** Day 3 of 14
**Goal:** Top 10 on all three leaderboards

---

## Current Performance vs Targets

| Kernel | Current Best | Target | Leader | Gap | Status |
|--------|--------------|--------|--------|-----|--------|
| **GEMM** | 14.1µs | ≤10µs | 9.671µs | 45% slower | ❌ Not Top 10 |
| **MLA** | 67.84µs | ≤15µs | ~4.3µs | 15.8× slower | ❌ Not Top 10 |
| **MoE** | 155µs | ≤145µs | ~145µs | 7% slower | ❌ Not Top 10 |

**Overall Status:** Not yet in Top 10 on any kernel

---

## Phase 1 Complete: Critical Issues Addressed

### Submissions Made Today:

1. **GEMM Breakthrough** (ID: 583191)
   - File: `gemm_breakthrough.py`
   - Status: ✅ done
   - Strategy: Shape-adaptive kernel selection with aggressive split-K
   - Result: Pending score visibility

2. **MoE Breakthrough** (ID: 583190)
   - File: `moe_breakthrough.py`
   - Status: ✅ done
   - Strategy: Ultra-aggressive KSPLIT for sparse workloads
   - Result: Pending score visibility

3. **MLA Fixed v2** (ID: 583287)
   - File: `mla_fixed_v2.py`
   - Status: ✅ done
   - Strategy: Fixed tuple unpacking + metadata API
   - Result: Pending score visibility

### Key Fixes Applied:
- ✅ MLA: Fixed `kv_data["fp8"]` tuple unpacking `(tensor, scale)`
- ✅ MLA: Corrected `get_mla_metadata_v1` API call to match reference
- ✅ GEMM: Shape-adaptive kernel selection (32×128 to 256×128)
- ✅ MoE: Aggressive KSPLIT (up to 8 for sparse workloads)

---

## Existing Assets (Not Yet Integrated)

### Custom HIP Kernels:
- `gemm_final.hip` - Complete with 8-wave ping-pong, LDS swizzle, direct global→LDS
- `gemm_mfma_tuned.hip` - MFMA tile tuning
- `gemm_direct_lds.hip` - Direct global→LDS transfers
- `mla_top10.hip` - Fused flash-decode with MXFP4 LUT
- `mla_flash_attention.hip` - Full flash attention

### Compiled Libraries:
- `libfused_gemm.so` (52KB) - Compiled but not integrated into submissions

### Submission Variants Created:
- GEMM: 6 variants (v1-v6, breakthrough)
- MoE: 6 variants (v1-v6, breakthrough)
- MLA: 7 variants (v1-v6, breakthrough, fixed, fixed_v2)

---

## Knowledge Base (Vault + SurrealDB)

### Obsidian Vault Documentation:
- ✅ `cerebellum/amd-hip-kernel-development.md` - HIP development guide
- ✅ `cerebellum/luma-amd-speedrun-strategy.md` - Competition strategy
- ✅ `luma-amd-speedrun-kimi-k2-5/patterns/` - Successful patterns
- ✅ `luma-amd-speedrun-kimi-k2-5/failures/` - Documented failures
- ✅ `luma-amd-speedrun-kimi-k2-5/decisions/` - Key decisions

### SurrealDB Status:
- ⚠️ Database running but no Luma-specific records
- ❌ Tables exist but empty (learning, pattern, submission tables)
- ❌ Need to populate with actual results

---

## Critical Findings From Research

### What Actually Works:
1. **GEMM**: `gemm_a4w4` with proper calling convention (14.1µs)
2. **MLA**: Three-regime routing (67.84µs, still far off)
3. **MoE**: AITER `fused_moe` with env vars (155µs)

### What Doesn't Work:
1. ❌ Python parameter tuning hit ceiling (90+ variants, no breakthrough)
2. ❌ Triton-based experiments (syntax errors from `__future__` imports)
3. ❌ `doweight_stage1=True` (catastrophic failure)
4. ❌ Ultra-aggressive KSPLIT=8/16 (numerical overflow)

### API Constraints Discovered:
- MLA: `kv_data["fp8"]` returns tuple `(tensor, scale)`
- Submission: Wrapper injects code, breaking `__future__` imports
- Runner: Single file upload only

---

## Current Blocker

**Problem:** Cannot see actual scores from submissions
- CLI shows only "done" status, not performance metrics
- Need to check web leaderboard manually
- Cannot iterate effectively without feedback loop

**Workaround Options:**
1. Check web leaderboard at https://www.gpumode.com/leaderboard/
2. Submit many variants and see patterns
3. Focus on integrating custom HIP kernels

---

## Next Phase Options

### Option A: Check Leaderboard & Iterate
- Have user check web leaderboard for actual scores
- Create more variants based on winning patterns
- Continue rapid submission cycle

### Option B: Integrate Custom HIP Kernels
- Compile and integrate `gemm_final.hip`
- Test if custom kernels actually improve performance
- Scale to MLA if successful

### Option C: Document & Tutorial
- Create comprehensive walkthrough
- Document failures and what worked
- Enable replication by others

---

## Remaining Days (11 days left)

**Day 3 (Today):** Phase 2 - Validate assumptions
**Days 4-7:** Focus on highest-impact kernel (likely MLA)
**Days 8-10:** Integrate custom HIP if needed
**Days 11-14:** Final submissions and documentation

---

## Success Probability Assessment

**Current State:** Medium-Low
- Python parameter tuning reached ceiling
- 45% gap to leader on GEMM (closest)
- 15.8× gap on MLA (hardest)
- Custom HIP kernels exist but not tested

**Path to Success:**
1. Custom HIP kernels must work (unproven)
2. Need breakthrough on MLA (biggest gap)
3. Requires 11 days of intensive work

---

## What User Needs to Do

1. **Check web leaderboard** for actual scores from submissions 583191, 583190, 583287
2. **Decide:** Continue with Python or pivot to custom HIP integration
3. **Confirm:** Prioritize which kernel (recommend MLA - biggest opportunity)

---

## Files Created This Session

- `_bmad-output/planning-artifacts/prd.md` - Comprehensive PRD
- `_bmad-output/CURRENT_STATUS.md` - This file
- `hip-kernels-kimi-k2-5/submissions/gemm_breakthrough.py`
- `hip-kernels-kimi-k2-5/submissions/moe_breakthrough.py`
- `hip-kernels-kimi-k2-5/submissions/mla_fixed_v2.py`

---

## Next Actions Needed

**Immediate:**
- [ ] Get actual scores from web leaderboard
- [ ] Decide on Phase 2 strategy

**Short-term:**
- [ ] Integrate custom HIP kernels OR double down on Python
- [ ] Create 5-10 more variants of winning approach
- [ ] Document what actually worked

**Long-term:**
- [ ] Achieve Top 10 on all three kernels
- [ ] Create tutorial series
- [ ] Populate SurrealDB with learnings

---

**Status:** Awaiting user input to proceed
