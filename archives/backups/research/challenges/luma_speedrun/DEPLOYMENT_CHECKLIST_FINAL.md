# FINAL DEPLOYMENT CHECKLIST - Luma AMD Speedrun Sprint

**Sprint Date:** 2026-04-06  
**Target Hardware:** AMD MI355X (gfx950)  
**Competition:** Luma AMD Speedrun (April 2026)  

---

## 1. PRE-DEPLOYMENT CHECKLIST

### 1.1 Validation
- [ ] All kernel files pass syntax check (`python -m py_compile`)
- [ ] No hardcoded local paths in submission files
- [ ] Import statements reference correct modules
- [ ] No debug print statements left in code
- [ ] All required dependencies listed in `requirements.txt`

### 1.2 Runner Verification
- [ ] SSH access to Popcorn CLI runner confirmed
- [ ] `popcorn-cli` command responds without error
- [ ] ROCm environment loads correctly
- [ ] GPU visible via `rocm-smi` or `torch.cuda.is_available()`

### 1.3 Submission Package
- [ ] All 3 kernels have submission files ready:
  - [ ] `submission_gemm.py` (MXFP4 GEMM)
  - [ ] `submission_moe.py` (Mixture-of-Experts)
  - [ ] `submission_mla.py` (MLA Decode)
- [ ] Each submission matches reference output (local test passed)
- [ ] Leaderboard names confirmed:
  - [ ] `amd-mxfp4-mm`
  - [ ] `amd-moe-mxfp4`
  - [ ] `amd-mla-decode`

---

## 2. DEPLOYMENT ORDER (Priority Ranking)

### Tier 1: BREAKTHROUGH CANDIDATES (Deploy First)
| Kernel | Status | Reason |
|--------|--------|--------|
| MoE | ⬜ | At API ceiling (~155µs vs leader 145µs, 1.07x gap). Parameter tuning exhausted. Custom kernel needed. |
| MLA | ⬜ | 22.9x gap to leader. Flash Attention approach may be breakthrough. |

**Strategy:** These are highest risk/highest reward. Deploy first when fresh.

### Tier 2: BEST VARIANTS (Deploy Second)
| Kernel | Variant | Expected µs | Notes |
|--------|---------|-------------|-------|
| GEMM | aiter gemm_a4w4 baseline | 13.4 | API ceiling reached. Only fused quant can beat. |
| MoE | fused_moe w/ policy=1 | 154-436 | Reduces worst-case by 37%. |
| MLA | Three-regime routing | 67.8 | Hybrid: matmul + aiter a16w8 + aiter a8w8. |

**Strategy:** These have highest probability of incremental improvement.

### Tier 3: EXPERIMENTAL (Deploy Last)
| Approach | Status | Risk |
|----------|--------|------|
| HIP kernel via load_inline | ⬜ | High - register layout bugs likely |
| Triton FP4 with tl.dot_scaled | ⬜ | High - BLOCK_K>=128 mandatory |
| CK-Tile direct dispatch | ⬜ | Medium - calling convention issues |

**Strategy:** Only if Tier 1/2 exhausted or as time permits.

---

## 3. TEST PROTOCOL

### Phase 1: Correctness Check (Mandatory)
```bash
popcorn run submission.py --mode test --leaderboard <name>
```
- [ ] Output matches reference (PASS/FAIL)
- [ ] If FAIL: Stop. Go to Iteration Workflow.
- [ ] If PASS: Proceed to Phase 2

### Phase 2: Benchmark Run (If Pass)
```bash
popcorn run submission.py --mode benchmark --leaderboard <name>
```
- [ ] Record timing (µs) for each shape
- [ ] Compare to baseline (previous best)
- [ ] If improved: Proceed to Phase 3
- [ ] If no improvement: Try next variant

### Phase 3: Leaderboard Submit (If Improve)
```bash
popcorn run submission.py --mode leaderboard --leaderboard <name>
```
- [ ] Record ranked score
- [ ] Compare to benchmark (expect ±10% variance)
- [ ] Document final rank

---

## 4. ITERATION WORKFLOW

### Path A: Test Fails
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Test FAIL  │───▶│ Analyze Log │───▶│  Fix Issue  │
└─────────────┘    └─────────────┘    └──────┬──────┘
       ▲                                      │
       └──────────────────────────────────────┘
                    Redeploy
```

**Common Failure Modes:**
| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `KeyError: 'float4_e2m1fn_x2'` | Using aiter MXFP4 API | Use tritonblas or delegate to ref_kernel |
| Silent wrong results (80% match) | Triton JIT callsite issue | Match reference.py call pattern exactly |
| `doweight_stage1` NaN | Correctness-breaking flag | Set `doweight_stage1=False` |
| Column 0 correct, col 1+ wrong | MFMA register layout | Use column-major output mapping |

### Path B: Benchmark No Improvement
```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│ No Improve  │───▶│ Next Variant    │───▶│ Redeploy    │
│             │    │ (per Tier list) │    │             │
└─────────────┘    └─────────────────┘    └─────────────┘
```

**Decision Matrix:**
- Time remaining > 2 hours: Try next variant
- Time remaining < 1 hour: Document results, handoff
- All variants exhausted: Switch to research mode

### Path C: Ranked Worse Than Benchmark
```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│ Ranked Worse│───▶│ Verify warm     │───▶│ Document &  │
│ (Session 91)│    │ cache vs benchmark│   │ Move On     │
└─────────────┘    └─────────────────┘    └─────────────┘
```
**CRITICAL:** Benchmark ≠ Ranked. Ranked has warm JIT. Don't chase benchmark-only gains.

---

## 5. SUCCESS CRITERIA

### Minimum (Must Achieve)
- [ ] At least 1 kernel passes correctness test
- [ ] No regressions from previous session

### Target (Aim For)
- [ ] 3+ kernels show improvement over baseline
- [ ] At least 1 kernel in top 20

### Stretch (Aspire To)
- [ ] Top 10 ranking on any kernel
- [ ] Breakthrough on MoE or MLA (custom kernel)

---

## 6. POST-DEPLOYMENT

### 6.1 Document Results
```
Results Log Template:

Kernel: <name>
Variant: <description>
Test: PASS/FAIL
Benchmark: <µs> (baseline: <µs>)
Leaderboard: <rank> @ <µs>
Notes: <any insights>
```

### 6.2 Update Coordination Hub
- [ ] Update `luma_speedrun/README.md` with latest results
- [ ] Add findings to `AMD_SPEEDRUN_RESEARCH_BASELINE.md`
- [ ] Update skill files if breakthrough discovered

### 6.3 Handoff to Next Session
**Create handoff document with:**
- [ ] Current status of each kernel
- [ ] What was tried and results
- [ ] Next candidate approaches (ranked by priority)
- [ ] Any blockers or issues encountered
- [ ] Files changed and their purpose

---

## QUICK REFERENCE

### Commands
```bash
# Test mode (correctness)
popcorn run submission_<kernel>.py --mode test --leaderboard amd-<kernel>

# Benchmark mode
time popcorn run submission_<kernel>.py --mode benchmark --leaderboard amd-<kernel>

# Leaderboard mode (FINAL)
popcorn run submission_<kernel>.py --mode leaderboard --leaderboard amd-<kernel>
```

### Leaderboard Names
- `amd-mxfp4-mm` (GEMM)
- `amd-moe-mxfp4` (MoE)
- `amd-mla-decode` (MLA)

### Key Constraints
- BLOCK_K >= 128 for Triton FP4 (mandatory)
- `doweight_stage1=False` for MoE correctness
- `fast_mode=False` for MLA (faster on MI355X)
- Do NOT use ctypes kernel dispatch (blocked)
- Benchmark ≠ Ranked score (warm JIT effects)

---

**Session Lead:** _______________  
**Start Time:** _______________  
**Estimated Completion:** _______________
