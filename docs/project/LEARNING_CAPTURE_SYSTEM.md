# 📚 Learning Capture & Breakthrough Research System

**Purpose**: Systematically document all experiments to accelerate breakthroughs.

**Time**: $(date)
**Status**: ACTIVATED

---

## 🔬 The Scientific Method

### 1. Hypothesis → 2. Experiment → 3. Results → 4. Analysis → 5. Iterate

---

## 📋 Hypothesis Log Template

```markdown
### Hypothesis #[ID]: [Title]
**Date**: YYYY-MM-DD
**Kernel**: MLA/MoE/GEMM
**Author**: system/user

**Current Baseline**: X.XX µs
**Hypothesis**: Changing [parameter] from [A] to [B] will improve by [expected%]
**Mechanism**: [Why we think this will work]
**Risk**: [What could go wrong]
**Expected Result**: X.XX µs

**Test Plan**:
1. Create variant [submission_vN.py]
2. Test in benchmark mode
3. Measure timing
4. Compare to baseline

**Status**: [PENDING|TESTING|FAILED|SUCCEEDED]
```

---

## 📊 Results Database

### Successful Patterns

| # | Kernel | What We Changed | Old | New | Improvement | Date |
|---|--------|------------------|-----|-----|--------------|------|
| 1 | MLA | Fixed API call | Broken | Working | ∞ | 2026-04-03 |
| 2 | MLA | Used fmha_v3 | Unknown | Has LB run | First success | 2026-04-04 |

### Failed Attempts

| # | Kernel | What We Tried | Why It Failed | Lesson Learned | Date |
|---|--------|---------------|---------------|----------------|------|
| 1 | MLA | load_inline complexity | Stream error | Keep submissions simple | 2026-04-04 |
| 2 | GEMM | 8-wave without testing | Never validated | Test before leaderboard | 2026-04-04 |

### Current Working Hypotheses

1. **MoE Direct CK Dispatch** (HIGH PRIORITY)
   - Hypothesis: Bypassing fused_moe via direct CK kernel dispatch will save 20-30µs
   - Expected: 93µs → 70µs
   - Status: PENDING - Need to implement

2. **MLA SDPA Fusion** (MEDIUM)
   - Hypothesis: Using F.scaled_dot_product_attention for small shapes instead of custom ASM
   - Expected: 69µs → 50µs
   - Status: PENDING - Test variant

3. **GEMM MFMA Optimization** (HIGH RISK)
   - Hypothesis: Direct MFFA instructions with 8-wave ping-pong will achieve Rank 1
   - Expected: 13µs → 4.3µs
   - Status: PENDING - Requires complex implementation

---

## 🎯 Breakthrough Scoreboard

Track progress toward Rank 1:

```
Kernel       Current     Target      Gap         Strategy              Confidence
MLA          69.7µs      26µs        -43.7µs     fmha_v3, SDPA         MEDIUM
MoE          93.4µs      70µs        -23.4µs     Direct CK dispatch      HIGH
GEMM         13µs        4.3µs       -8.7µs      MFMA 8-wave             LOW
```

---

## 🔍 Research Directions

### From Successful Submissions

**What MLA 720690 Taught Us**:
- ✅ File directives work (`#!POPCORN leaderboard ...`)
- ✅ Simple implementations pass pipeline
- ✅ fmha_v3 is the path forward

**Critical Discovery - Popcorn CLI Usage**:
- Must use `--mode leaderboard` for official scores
- Score column only populates after full pipeline
- Rate limit: 1/hour per kernel for leaderboard mode

### Open Questions

1. Can we achieve MoE breakthrough first? (Closest to goal)
2. What's the actual MLA 720690 timing? (Waiting for Score column)
3. Does SDPA actually help or hurt? (Need A/B test)

---

## 🧪 Active Experiments

| ID | Kernel | Experiment | Status | Started | Expected Result |
|----|--------|------------|--------|---------|-----------------|
| 1 | MoE | Direct CK dispatch | NOT STARTED | - | 70µs |
| 2 | MLA | SDPA vs ASM | NOT STARTED | - | 50µs |
| 3 | All | Intelligent optimizer | RUNNING | Now | Baseline tracking |

---

## 📈 Knowledge Graph

```
[MLA optimization]
    ├── fmha_v3 [SUCCESS - has LB run]
    ├── SDPA fusion [PENDING]
    └── load_inline [FAILED - stream issue]

[MoE optimization]
    ├── fused_moe [CURRENT BASELINE - 93µs]
    ├── Direct CK [BREAKTHROUGH HYPOTHESIS]
    └── Block size tuning [PENDING]

[GEMM optimization]
    ├── gemm_a4w4 [CURRENT]
    ├── 8-wave [UNTESTED]
    └── MFMA [BREAKTHROUGH NEEDED]
```

---

## 🎯 Breakthrough Criteria

Define what constitutes a breakthrough:

1. **Minor Improvement**: 5-10% faster → Document, continue iterating
2. **Significant Improvement**: 20%+ faster → Submit immediately
3. **Breakthrough**: >50% improvement OR reaching Rank 1 → STOP and celebrate

---

## 🔄 Continuous Learning

### Daily Review (Auto-generated)
```bash
# Run at end of each day:
./scripts/generate_learning_summary.sh > docs/LEARNING_$(date +%Y%m%d).md
```

### Weekly Synthesis
- Review all hypotheses tested
- Analyze patterns in successes/failures
- Generate new hypotheses based on gaps
- Update breakthrough strategy

---

## 🚀 Current Status

**Active Breakthrough Research**: YES
**Learning Capture**: Systematic
**Iterations**: Continuous
**Rank 1 Progress**: IN PROGRESS

### Most Promising Path

**MoE** is our best shot:
- ✅ Working baseline (93µs)
- 🎯 Close to Rank 1 (70µs)
- 💡 Clear hypothesis (Direct CK)
- 🔥 Ready to implement

---

**Status**: Learning system activated - BREAKTHROUGH MODE ON 🧠🔬
