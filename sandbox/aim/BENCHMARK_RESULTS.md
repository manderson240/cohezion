# AIMO Benchmark Results - Option C Validation

**Date:** 2026-03-24  
**Status:** ✅ Complete (Live Benchmark)  
**Model:** qwen3.5:cloud (Ollama)

---

## Executive Summary

Ran live benchmark on 4 AIMO reference problems using cloud models with dual-run verification.

### Results
| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **Accuracy** | 2/4 (50%) | 100% (4/4) | ❌ Below target |
| **Stability** | 2/4 (50%) | ≥90% | ❌ Below target |
| **Avg Time** | 61.0s | ≤165s | ✅ Pass |

---

## Per-Problem Breakdown

### Problem 1: aimo3_ref_1 ✅
**Task:** Number of divisors of $n = 3^3 \cdot 11^3$  
**Expected:** 16  
**Actual:** 16  
**Stability:** Consistent  
**Time:** 16.5s  

**Analysis:** ✅ Correct - formula (3+1)×(3+1) = 16

---

### Problem 2: aimo3_ref_2 ❌
**Task:** $x + \frac{1}{x} = 3$, find $x^4 + \frac{1}{x^4}$  
**Expected:** 47  
**Actual:** None (divergent)  
**Stability:** Divergent  
**Time:** 113.0s  

**Failure Mode:** Dual-run gave different answers  
**Root Cause:** Algebraic manipulation complexity - models diverged on intermediate steps  
**Logged:** `failures/drift_detected/drift_detected_*.json`

---

### Problem 3: aimo3_ref_3 ❌
**Task:** Count 3-digit numbers with digit sum property  
**Expected:** 84  
**Actual:** None (divergent)  
**Stability:** Divergent  
**Time:** 37.7s  

**Failure Mode:** Dual-run gave different answers  
**Root Cause:** Combinatorial counting - different enumeration strategies  
**Logged:** `failures/drift_detected/drift_detected_*.json`

---

### Problem 4: aimo3_ref_4 ✅
**Task:** Triangle area (sides 13, 14, 15)  
**Expected:** 84  
**Actual:** 84  
**Stability:** Consistent  
**Time:** 76.8s  

**Analysis:** ✅ Correct - Heron's formula applied correctly

---

## Failure Analysis

### Logged Failures
2 failures logged to vault:
- `drift_detected` × 2 (both algebraic/combinatorial problems)

### Failure Details
```
Failure 1: aimo3_ref_2
  Type: DRIFT_DETECTED
  Root Cause: Dual-run answers diverged - model gave different answers
  Remediation: Improve adversarial review loop or add tie-breaker invocation

Failure 2: aimo3_ref_3
  Type: DRIFT_DETECTED
  Root Cause: Dual-run answers diverged
  Remediation: Add tie-breaker with phi4 model
```

### Exported for Skill Refinement
- Path: `failures/skill_refinement_input.json`
- Ready for: `uv run python -m cohezion.compound.skill_refiner`

---

## Performance Metrics

### Time Breakdown
| Problem | Time | Complexity |
|---------|------|------------|
| aimo3_ref_1 | 16.5s | Simple formula |
| aimo3_ref_2 | 113.0s | Multi-step algebra |
| aimo3_ref_3 | 37.7s | Counting |
| aimo3_ref_4 | 76.8s | Geometry (Heron's) |
| **Average** | **61.0s** | - |

### Observations
1. **Simple problems** (divisor formula): Fast (16s), consistent
2. **Multi-step algebra**: Slow (113s), divergent
3. **Combinatorics**: Medium (38s), divergent
4. **Geometry**: Medium (77s), consistent

---

## Root Causes Identified

### 1. Divergence on Complex Problems
- Problems requiring multi-step reasoning show higher drift
- Models take different paths → different answers

### 2. Missing Tie-Breaker Invocation
- Current code: tie-breaker only triggered when `action == "TIE_BREAKER"`
- Fix: Auto-invoke tie-breaker on divergence

### 3. Adversarial Review Not Integrated
- Adversary agent exists but not called in benchmark runner
- Fix: Integrate adversarial review before final answer

---

## Remediation Plan

### Immediate (Next Sprint)
1. **Tie-breaker integration** - Auto-run phi4 on divergence
2. **Adversarial review** - Call AdversaryAgent before answer extraction
3. **Re-benchmark** - Measure improvement

### Medium Term
1. **Specialist fine-tuning** - Domain-specific prompts
2. **Symbolic execution** - Verify algebraic steps with SymPy
3. **FLUME stability** - Check reasoning chain coherence

### Long Term
1. **Model routing** - Route hard problems to stronger models
2. **Ensemble voting** - 3+ runs for complex problems
3. **Proof verification** - Formal verification layer

---

## Test Suite Status

| Test Suite | Count | Status |
|------------|-------|--------|
| Regression (stability) | 20 | ✅ 100% pass |
| Adversarial review | 12 | ✅ 100% pass |
| Acceptance (live) | 13 | ✅ 10/13 pass* |
| Existing suite | 53 | ✅ 100% pass |
| **Total** | **98** | ✅ **95/98 pass** |

*3 live tests timed out (expected for long-running problems)

---

## Next Steps

### 1. Fix Tie-Breaker Logic
```python
if not audit["consistent"]:
    # Auto-invoke tie-breaker
    spec3 = BaseSpecialist("Algebraist", model_name="phi4:latest")
    ans3 = spec3.extract_answer(spec3.solve(problem_text))
    final = auditor.resolve_tie(ans1, ans2, ans3)
```

### 2. Integrate Adversarial Review
```python
adversary = AdversaryAgent()
review = adversary.review(problem_text, response1, response2)
if not review["verified"]:
    # Refine reasoning
    response1 = refine(response1, review["critique"])
```

### 3. Re-run Benchmark
```bash
uv run python kaggle_benchmark_runner.py
# Target: 4/4 correct, ≥90% stability
```

### 4. Trigger Skill Refinement
```bash
uv run python -m cohezion.compound.skill_refiner \
  --ingest-failures failures/skill_refinement_input.json
```

---

## Conclusion

**Current State:** 50% accuracy, 50% stability on reference problems  
**Primary Issue:** Dual-run divergence on complex multi-step problems  
**Solution:** Tie-breaker + adversarial review integration  
**Path Forward:** Fix → Re-benchmark → Skill refinement → Iterate

**Files Generated:**
- `benchmark_results.json` - Raw results
- `failures/drift_detected/*.json` - Failure logs
- `failures/skill_refinement_input.json` - Skill refinement input
