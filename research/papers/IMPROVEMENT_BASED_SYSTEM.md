# 📈 IMPROVEMENT-BASED SUBMISSION SYSTEM

## Principle: Only Submit If Better Than Baseline

**Time**: $(date)
**Strategy**: Smart A/B testing, not blind submissions

---

## Step 1: Establish Baselines

First, check current best scores:

```bash
# Get current baselines
popcorn submissions list --leaderboard amd-mixed-mla | head -10
popcorn submissions list --leaderboard amd-moe-mxfp4 | head -10
popcorn submissions list --leaderboard amd-mxfp4-mm | head -10

# Extract best known times
grep -E "µs|ms" /tmp/overnight_*.log 2>/dev/null || echo "No timing data yet"
```

**Current Baselines (from our knowledge):**
- MLA: ~69.7µs (from code comments) / Rank 1: ~26µs
- MoE: ~93µs / Rank 1: ~70µs
- GEMM: ~13µs / Rank 1: ~4.3µs

---

## Step 2: Hypothesis-Driven Optimization

Before submitting any variant, document:

```markdown
### Hypothesis Template
- **Parameter Changed**: block_size 128→256
- **Expected Improvement**: +15% throughput
- **Risk**: May increase register pressure
- **Test First?**: Yes, use --mode benchmark
```

---

## Step 3: A/B Testing Protocol

```bash
# Test new variant WITHOUT submitting to leaderboard
cd /kernel/dir
timeout 300 popcorn-cli submit variant_v2.py \
  --mode benchmark \
  --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  --no-tui

# Compare:
# - Baseline: 93.4µs
# - Variant V2: ???µs

# Only if V2 < 93.4µs:
timeout 300 popcorn-cli submit variant_v2.py \
  --mode leaderboard ...
```

---

## Step 4: Variant Library System

Each kernel should have variants ranked by expected performance:

```
amd-moe-mxfp4/
├── submission.py              # Current best (93µs baseline)
├── submission_v1_aggressive.py # Hypothesis: 85µs expected
├── submission_v2_conservative.py # Hypothesis: 90µs expected
└── submission_v3_breakthrough.py # Hypothesis: 70µs (high risk)
```

**Rule**: Only submit variants where Expected < Current_Best

---

## Step 5: Automated Intelligence

System should:
1. ✅ Track all past results
2. ✅ Learn which changes help
3. ✅ Generate new hypotheses
4. ✅ Only submit promising variants
5. ✅ Stop if no improvement detected

```python
# Pseudo-code for intelligent submission
if variant_expected_time < current_best_time * 0.95:  # 5% improvement threshold
    submit_to_leaderboard(variant)
else:
    log("Rejected: expected %.2fµs vs current %.2fµs" % (expected, current))
```

---

## Current Gap Analysis

| Kernel | Current | Rank 1 | Gap | Next Hypothesis |
|--------|---------|--------|-----|-----------------|
| MLA | 69.7µs | 26µs | 2.7x | fmha_v3 optimization |
| MoE | 93µs | 70µs | 1.3x | Direct CK dispatch |
| GEMM | 13µs | 4.3µs | 3x | 8-wave + MFMA |

**Focus**: MoE (closest to Rank 1)

---

## Immediate Action

STOP current blind submissions.

START improvement-based system:
1. Test benchmark mode first
2. Compare to baseline
3. Only submit if improvement confirmed
4. Track results systematically

---

**Status**: Switching to intelligent optimization mode.
