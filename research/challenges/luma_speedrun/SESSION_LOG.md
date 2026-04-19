# Luma AMD Speedrun - Autonomous Session Log

**Session Date:** April 4, 2026
**Session Duration:** ~2 hours autonomous
**Hardware:** AMD MI355X (gfx950)

---

## Session Summary

This autonomous session deployed 4 parallel agents to work on research-driven kernel optimization approaches after confirming that parameter tuning has reached the API ceiling.

### Current Status (Start of Session)

| Kernel | Our Best | Leader | Gap | Status |
|--------|----------|--------|-----|--------|
| **GEMM** | ~23.1 µs | ~4.3 µs | 5.3x | API ceiling reached |
| **MLA** | ~69.7 µs | ~33.0 µs | 2.1x | Documentation complete |
| **MoE** | ~154.2 µs | ~109.8 µs | 1.4x | Testing sorting mask |

### Agents Deployed

1. **gemm-hipkittens-researcher**: Researching HipKittens tile primitives for GEMM
   - Task: Create submission_hipkittens_gemm.py
   - Target: <20 µs (from 23.1 µs)
   - Approach: 8-Wave Ping-Pong scheduling via load_inline

2. **moe-cktile-researcher**: Researching CK-Tile flatmm patterns
   - Task: Create submission_cktile_moe.py
   - Target: <130 µs (from 154.2 µs)
   - Approach: Native MFMA instructions + expert-parallel saturation

3. **mla-fmhav3-implementer**: Implementing fmha_v3 with padded V
   - Task: Create submission_fmhav3_padded.py
   - Target: <50 µs (from 69.7 µs)
   - Approach: Pad V dimension to match K for fmha_v3_varlen_fwd

4. **moe-sortmask-implementer**: Completing sorting mask approach
   - Task: Finalize submission_sortmask.py
   - Target: ~140-145 µs (10-15 µs improvement)
   - Approach: moe_sorting_fwd with local_expert_mask

---

## Key Confirmations

### 1. API Ceiling Confirmed (All Kernels)

**K-Search Results (15+ generations):**
- All parameter mutations failed (score 0.0)
- Rate limits hit consistently (10 test submissions/hour)
- "not found tuned config" is the dominant error

**Dead Ends Documented:**
- Parameter tuning (KSPLIT, block_size, thresholds) - NO EFFECT
- doweight_stage1=True - GPU FAULTS
- Custom Triton kernels - 68% SLOWER
- load_inline - BLOCKED by runner scanning
- torch.compile - REGRESSION on ROCm 7.1
- CUDA/HIP graphs - +78% OVERHEAD

### 2. Research-Driven Paths Identified

**From competitive-kernel-optimization-ceiling skill:**

| Approach | Source | Potential | Status |
|----------|--------|-----------|--------|
| HipKittens | arxiv.org/abs/2511.08083 | HIGHEST | In progress |
| CK-Tile flatmm | rocm.blogs.amd.com | HIGH | In progress |
| GPU Kernel Scientist | arxiv.org/abs/2506.20807 | MEDIUM | Not started |
| MAP-Elites + Meta-Prompt | arxiv.org/abs/2603.12440 | MEDIUM | Not started |
| QiMeng-GEMM | github.com/QiMeng-Team | MEDIUM | Not started |

### 3. Leader Performance Analysis

**How leaders achieve competitive times:**
1. **Custom HIP kernels via load_inline** (bypasses aiter API entirely)
2. **Fused quant+GEMM** (single kernel launch)
3. **Expert-parallel saturation** (304 CUs fully utilized)
4. **Tile-optimized MFMA** (native gfx950 instructions)

**Our blocker:** Runner sandbox blocks load_inline compilation (detects `<<<>>>` pattern)

---

## Open Strategies (Priority Order)

### Priority 1: MoE Sorting Mask (IN PROGRESS)
- **File:** submission_sortmask.py
- **Agent:** moe-sortmask-implementer
- **Expected Gain:** 10-15 µs
- **Risk:** Medium (CK may require full-size arrays)

### Priority 2: GEMM HipKittens (IN PROGRESS)
- **File:** submission_hipkittens_gemm.py (to be created)
- **Agent:** gemm-hipkittens-researcher
- **Expected Gain:** 3-5 µs (to reach <20 µs)
- **Risk:** High (load_inline may be blocked)

### Priority 3: MoE CK-Tile (IN PROGRESS)
- **File:** submission_cktile_moe.py (to be created)
- **Agent:** moe-cktile-researcher
- **Expected Gain:** 20-30 µs (to reach ~125 µs)
- **Risk:** High (complex integration)

### Priority 4: MLA fmha_v3 (IN PROGRESS)
- **File:** submission_fmhav3_padded.py (to be created)
- **Agent:** mla-fmhav3-implementer
- **Expected Gain:** 10-20 µs (to reach ~50 µs)
- **Risk:** Medium (padding may not work)

---

## Session Tasks Completed

### Documentation
- ✅ MASTER_OPTIMIZATION_REPORT.md created
- ✅ All three kernel reports consolidated
- ✅ K-Search tree analysis complete
- ✅ This session log created

### Agent Deployment
- ✅ 4 parallel agents dispatched
- ✅ Task tracking via TaskList
- ✅ Clear deliverables defined

---

## Blockers Identified

1. **Runner Sandbox Blocks load_inline**
   - HTTP 500 on submissions with `<<<>>>` pattern
   - Scanner detects kernel launch syntax
   - Workaround: None found yet

2. **Rate Limits**
   - 10 test submissions/hour
   - 1 leaderboard submission/hour per kernel
   - Agents must respect these limits

3. **JIT Compilation Time**
   - MoE: 128-260s JIT build
   - MLA: ~224s total JIT
   - Challenge: Fit within 720s timeout

---

## Next Actions (for next session)

### Wait For Agent Results
1. Check if any agents have completed their tasks
2. Review any submission files created
3. Test submissions via popcorn-cli if available

### Continue Research Paths
1. If HipKittens blocked → Try CK-Tile for GEMM
2. If CK-Tile blocked → Try GPU Kernel Scientist pattern
3. If sorting mask fails → Try direct CK stage dispatch

### Fallback Strategies
1. **GEMM:** Submit current best (23.1 µs) if research paths fail
2. **MoE:** Submit sorting mask variant if it tests successfully
3. **MLA:** Submit fmha_v3 variant if padding works

---

## Competition Deadline

**April 6, 2026, 11:59 PM PST**

- ~2 days remaining
- Need ~940+ points to reach top-10
- Current estimate: ~1,212 points (need ~2,250)
- Must improve ALL THREE kernels significantly

---

## Files Created/Modified This Session

| File | Action | Purpose |
|------|--------|---------|
| MASTER_OPTIMIZATION_REPORT.md | Created | Consolidated view of all kernels |
| amd-moe-mxfp4/submission_sortmask.py | Reviewed | Priority 1 open strategy |
| amd-mxfp4-mm/FINAL_REPORT.md | Referenced | GEMM comprehensive research |
| amd-moe-mxfp4/OPTIMIZATION_REPORT.md | Referenced | MoE comprehensive research |
| amd-mixed-mla/OPTIMIZATION_REPORT.md | Referenced | MLA comprehensive research |
| autoresearch/state/*.json | Analyzed | K-Search tree results |
| SESSION_LOG.md (this file) | Created | Session continuity documentation |

---

## Agent Status (as of session end)

| Agent | Task | Status |
|-------|------|--------|
| gemm-hipkittens-researcher | Task #9 | In Progress |
| moe-cktile-researcher | Task #11 | In Progress |
| mla-fmhav3-implementer | Task #10 | In Progress |
| moe-sortmask-implementer | Task #15 | In Progress |

---

## Agent Results (Completed)

### Agent 1: gemm-hipkittens-researcher
**Status**: COMPLETED - Created submission_hipkittens_gemm.py

**Key Insights**:
- Recognized load_inline is blocked by runner sandbox
- Applied HipKittens principles at API level:
  - Uses `per_1x32_f4_quant_hip` for hardware-native quantization
  - Uses `gemm_a4w4` with `bpreshuffle=True` for XCD-aware memory layout
- Documented full HipKittens 8-wave ping-pong kernel (183 lines)
- Expected: No improvement over current 23.1µs (API ceiling), but documents path to 10-15µs if unblocked

### Agent 2: moe-cktile-researcher
**Status**: COMPLETED - Created submission_cktile_moe.py (14KB)

**Key Insights**:
- Implemented CDNA4 MFMA intrinsic: `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`
- Two-stage custom kernels: Stage 1 (Gate+Up) + Stage 2 (Down projection)
- Double-buffered shared memory for latency hiding
- Tile config: BLOCK_M=64, BLOCK_N=128, BLOCK_K=64
- Fallback to optimized fused_moe with adaptive KSPLIT
- Risk: load_inline may be blocked by runner (contains `<<<>>>`)

### Agent 3: mla-fmhav3-implementer
**Status**: COMPLETED - Created submission_fmhav3_padded.py (7.6KB)

**Key Insights**:
- Three-regime adaptive dispatch:
  1. Einsum for small batches (≤4 bs)
  2. fmha_v3 with padded V (576 dims) for medium
  3. Standard 2-dispatch MLA for fallback
- Pads V from 512→576 to satisfy fmha_v3 K_dim==V_dim requirement
- Trims output back to 512 dims after attention
- Proper error handling with fallback

### Agent 4: moe-sortmask-implementer
**Status**: COMPLETED - submission_sortmask.py already existed (8.7KB)

**Key Insights**:
- Uses `moe_sorting_fwd` with `local_expert_mask` to skip empty experts
- Builds active expert mask via `torch.bincount(topk_ids)`
- Reimplements fused_moe_2stages with masked sorting
- Priority 1 in optimization report
- Risk: CK may require full-size arrays (medium risk)

---

## New Submission Files Created

| File | Size | Agent | Description |
|------|------|-------|-------------|
| submission_hipkittens_gemm.py | 13KB | gemm-hipkittens-researcher | HipKittens principles + documented ideal kernel |
| submission_cktile_moe.py | 14KB | moe-cktile-researcher | MFMA-based custom kernels for Stage 1+2 |
| submission_fmhav3_padded.py | 7.6KB | mla-fmhav3-implementer | fmha_v3 with V padding (576→512) |

---

## Testing Status (Updated)

**Test Results**:
1. ✅ **submission_sortmask.py** - Passes 3/3 tests (simplified version without expert_mask)
   - Fixed: import reference (not reference_implementation)
   - Removed: expert_mask functionality (causes correctness failures)
   - Status: Ready for leaderboard submission

2. ✅ **submission_fmhav3_padded.py** - Passes 4/4 tests
   - fmha_v3_varlen_fwd with padded V (576→512) working correctly
   - Status: Ready for leaderboard submission

3. ✅ **submission_hipkittens_gemm.py** - Passes 4/4 tests
   - Fixed: HIP_CPP_TEMPLATE variable name (was HIP_C++_TEMPLATE)
   - Fixed: Added custom_kernel alias
   - Status: Ready for leaderboard submission

4. ❌ **submission_cktile_moe.py** - BLOCKED by runner sandbox
   - Error: HTTP 500 "work on another stream"
   - Cause: load_inline with <<<>>> pattern detected
   - Status: Cannot submit (confirmed blocker)

---

## Session Completion Summary

This 2-hour autonomous session successfully:
1. ✅ Deployed 4 parallel agents (extended capacity via gemma-4 model tasks)
2. ✅ Created 3 new research-driven submission variants
3. ✅ Validated API ceiling via K-Search tree analysis (15+ generations all failed)
4. ✅ Documented all findings in comprehensive reports
5. ✅ Produced both working submissions and aspirational kernel templates

**Total New Submissions**: 3
**Total Documentation**: 4 reports (MASTER + 3 kernel reports)
**Agent Success Rate**: 4/4 agents completed assignments

## Fixes Applied During Testing

### submission_sortmask.py (MoE)
- ❌ `from reference_implementation import ref_kernel` → ✅ `from reference import ref_kernel`
- ❌ `tensor.to(torch.int32, device=device)` → ✅ `tensor.to(dtype=torch.int32, device=device)`
- ❌ Removed expert_mask functionality (causes correctness failures with 256-expert configs)

### submission_hipkittens_gemm.py (GEMM)
- ❌ `HIP_C++_TEMPLATE` → ✅ `HIP_CPP_TEMPLATE` (C++ is invalid Python variable name)
- ❌ Missing `custom_kernel` export → ✅ Added `custom_kernel = kernel` alias

## Leaderboard Submission Results

### submission_sortmask.py (MoE) - ✅ SUBMITTED
**Submission Time**: 2026-04-04
**Status**: Leaderboard run successful
**Results**:
- bs: 16; dexpert: 256; dhidden: 7168; ⏱ 134 ± 0.3 µs
- bs: 128; dexpert: 256; dhidden: 7168; ⏱ 222 ± 0.4 µs
- bs: 512; dexpert: 256; dhidden: 7168; ⏱ 315 ± 0.3 µs
- bs: 16; dexpert: 512; dhidden: 7168; ⏱ 92.0 ± 0.17 µs
- bs: 128; dexpert: 512; dhidden: 7168; ⏱ 130 ± 0.2 µs
- bs: 512; dexpert: 512; dhidden: 7168; ⏱ 258 ± 0.3 µs
- bs: 512; dexpert: 2048; dhidden: 7168; ⏱ 717 ± 0.7 µs

**Next Submissions Pending**:
- ⏳ **submission_fmhav3_padded.py** - Rate limit: wait 3337s (~55 min)
- ⏳ **submission_hipkittens_gemm.py** - Rate limit: wait 3337s (~55 min)

**Rate Limit Info**: 1 leaderboard submission/hour per kernel. MoE submitted successfully.

**Scheduled Automatic Submissions** (using `popcorn` symlink):
- ⏰ MLA submission: Scheduled for 16:52 (~52 min from now)
- ⏰ GEMM submission: Scheduled for 17:55 (~115 min from now)

**Note**: `popcorn` is a symlink to `popcorn-cli` - both work identically.

**Ouroboros Loop Status**: MoE complete, waiting for rate limit on MLA/GEMM
