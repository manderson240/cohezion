---
name: popcorn-ranked-score-validation
description: |
  MANDATORY validation: benchmark improvements do NOT guarantee ranked score improvements
  in Popcorn CLI kernel competitions. Use when: (1) about to submit to leaderboard,
  (2) benchmark shows improvement over baseline, (3) ANY kernel optimization session.
  HARD RULE: run --mode leaderboard BEFORE committing a submission as "improved".
  Session 91 proof: ALL 5 "improved" submissions scored WORSE on ranked leaderboard
  (GEMM 24µs vs 13.4µs best, MoE 214µs vs 154µs best, MLA 83µs vs 70µs best).
author: Claude Code (Session 91)
version: 1.0.0
---

# Popcorn Ranked Score Validation

## Problem

Benchmark mode (`--mode benchmark`) uses KNOWN shapes. Ranked mode (`--mode leaderboard`)
uses SECRET shapes with geometric mean scoring. Optimizations that improve benchmark
can REGRESS ranked performance because:

1. **Different shape distribution** — ranked shapes weight large/hard cases more heavily
2. **Geometric mean** — one bad shape tanks the entire score
3. **Routing changes** — switching between paths (custom vs API) can help benchmark shapes
   while hurting ranked shapes
4. **Threshold tuning** — adjusting thresholds (e.g., einsum vs ASM boundary) optimizes
   for visible shapes but may be wrong for secret shapes

## Session 91 Evidence

| Submission | Benchmark | Ranked | Δ vs Best | Verdict |
|-----------|-----------|--------|-----------|---------|
| GEMM v6 (hybrid MFMA+aiter) | 13.3µs best shape | 23.987µs | +78% worse | REGRESSION |
| GEMM v5 (custom MFMA only) | 13.3µs best shape | 27.174µs | +102% worse | REGRESSION |
| MoE dispatch_policy=1 | 89µs best shape | 214.153µs | +39% worse | REGRESSION |
| MLA hybrid_v2 (wider einsum) | 23µs best shape | 83.320µs | +19% worse | REGRESSION |

## Mandatory Submission Process

```
1. --mode test      → ALL tests must pass (correctness gate)
2. --mode benchmark → Record per-shape times (informational only)
3. --mode leaderboard → GET THE ACTUAL RANKED SCORE  ← THIS IS CRITICAL
4. Compare: new_score < current_best_score?
   - YES → Submit as new best, update LEADERBOARD_SCORES.md
   - NO  → DO NOT submit. Analyze why benchmark ≠ ranked.
5. Scrape leaderboard via browser to confirm rank change
```

**Step 3 costs 1 leaderboard submission per hour. Budget wisely.**

## How to Check Ranked Score

### Via CLI
```bash
popcorn-cli submit --no-tui --mode leaderboard --gpu MI355X \
  --leaderboard amd-mxfp4-mm submission.py 2>&1 | grep -E "μs|score"
```

### Via Browser (Playwright)
```javascript
// Navigate to submission tab, expand the submission, read the leaderboard score
await page.goto('https://www.gpumode.com/leaderboard/763?tab=submission');
// Evaluate to find scores
const scores = document.body.innerText.match(/leaderboard[\s\S]{0,50}μs/g);
```

## Current Best Ranked Scores (manderson240)

| Kernel | Best Ranked | Submission | Date |
|--------|------------|------------|------|
| GEMM | 13.425µs | aiter baseline | Pre-session 91 |
| MoE | 154.183µs | default fused_moe | Pre-session 91 |
| MLA | 69.745µs | original einsum+ASM hybrid | Pre-session 91 |

**Update this table when a NEW ranked best is achieved.**

## Anti-Patterns (DO NOT)

1. ❌ "Benchmark improved → submit to leaderboard" (benchmark ≠ ranked)
2. ❌ "Custom kernel beats API on some shapes → use it for all shapes" (regression on others)
3. ❌ "dispatch_policy=1 improves worst-case → submit" (hurts ranked average)
4. ❌ "Expand einsum threshold → captures more small shapes" (hurts ranked large shapes)
5. ❌ Submitting without checking ranked score first

## Safe Patterns (DO)

1. ✅ Run `--mode leaderboard` before EVERY submission decision
2. ✅ Only submit if ranked score < current best
3. ✅ Keep the proven baseline file untouched as fallback
4. ✅ Test optimizations that improve ALL shapes uniformly (not just some)
5. ✅ Profile ranked shapes by submitting instrumented code
