# Submission Strategy Map (CONFIDENTIAL)

**Last Updated**: 2026-03-16
**Classification**: Internal Use Only
**Purpose**: Map public submission filenames to actual strategies

---

## Naming Convention

**Public Filenames**: Generic versioning only
- ✅ `submission.py` - Baseline
- ✅ `submission_v2.py` through `submission_v99.py` - Iterations
- ❌ NEVER: `ksplit`, `expert`, `aggressive`, `optimized`, `splitk`

**Internal Tracking**: This document maps public names to strategies

---

## MoE Submissions (amd-moe-mxfp4)

| Public Name | Actual Strategy | KSPLIT | Expert-Aware | Status | Results | Notes |
|-------------|-----------------|--------|--------------|--------|---------|-------|
| submission_v4.py | Balanced baseline | 6/3/2/default | No | ✅ Working | ~155µs | Sweet spot found |
| submission_v5.py | Ultra-aggressive | 8/4/2/1 | Partial | 🔄 Testing | Pending | May overflow |
| submission_v6.py | Adaptive fine-tune | 6/4/2/1 | Yes | 🔄 Testing | Pending | Shape-specific |
| submission_v7.py | Aggressive sparse | 8/6/4/2 | Yes | 🔄 Testing | Pending | Max parallelism |
| submission_v8.py | KSPLIT sweep A | 8/4/2 | No | 🔄 Testing | Pending | Test high values |
| submission_v9.py | KSPLIT sweep B | 6/3/2 | No | 🔄 Testing | Pending | Conservative |
| submission_v10.py | Expert-aware dispatch | 4/2/1 | Yes | 🔄 Testing | Pending | E=257 vs E=33 |
| submission_v11.py | Uniform KSPLIT=4 | 4 | No | 🔄 Testing | Pending | All sparse |
| submission_v12.py | Uniform KSPLIT=2 | 2 | No | 🔄 Testing | Pending | All sparse |

**Key Insights** (DO NOT EXPOSE):
- KSPLIT sweet spot: 6/3/2 better than 8/4/2
- E=257 can handle more parallelism than E=33
- Very sparse (est_m < 8) benefits from KSPLIT=6-8
- Dense shapes (est_m > 80) should use default

---

## GEMM Submissions (amd-mxfp4-mm)

| Public Name | Actual Strategy | Split-K | Kernel | Status | Results | Notes |
|-------------|-----------------|---------|--------|--------|---------|-------|
| submission_v1.py | HIP fused baseline | Default | 32x128/192x128 | ✅ Working | ~13-14µs | 35% improvement |
| submission_v2.py | Shape-aware split-K | Adaptive | Auto-select | 🔄 Testing | Pending | Per-shape tuning |
| submission_v3.py | Aggressive split-K | Max | Auto-select | 🔄 Testing | Pending | M≤4→split_k=4 |
| submission_v4.py | Split-K sweep A | Aggressive | Auto-select | 🔄 Testing | Pending | High parallelism |
| submission_v5.py | Split-K sweep B | Conservative | Auto-select | 🔄 Testing | Pending | Low overhead |

**Key Insights** (DO NOT EXPOSE):
- HIP quantization bypasses Python overhead
- Small M (≤4) benefits from split_k=4
- Large M (≥128) should use split_k=0 or 1
- Kernel 32x128 for M<64, 192x128 for M≥64

---

## MLA Submissions (amd-mixed-mla)

| Public Name | Actual Strategy | Routing | Status | Results | Notes |
|-------------|-----------------|---------|--------|---------|-------|
| submission_v1.py | Hybrid three-regime | Einsum→a16w8→a8w8 | ✅ Working | ~69µs | Baseline |
| submission_v2.py | HIP flash-decode | Custom kernel | 🔄 Testing | Pending | Optimized parallelism |

**Key Insights** (DO NOT EXPOSE):
- Three-regime routing based on qseqlen and total_kv
- Persistent kernels critical for decode
- num_kv_splits: 1, 4, 8, 16, 32 based on size

---

## Competition Intelligence

### Top Performers Analysis

**John Hahn** (Rank #1 MoE, #1 GEMM):
- Submission counts: 44 (MoE), 812 (GEMM), 173 (MLA)
- Filenames: Generic (`submission.py`, `submission_v115.py`)
- Strategy: Selective, high-quality submissions
- **Lesson**: Quality over quantity, stealth naming

**josusanmartin** (Heavy iteration):
- Submission counts: 1000+ per kernel
- Filenames: Revealing (`v491_v396_split_shared_route46_raw_e33_bs128.py`)
- Strategy: Brute force parameter sweep
- **Lesson**: They don't care about hiding strategies

**parcadei** (Consistent across kernels):
- Submission counts: ~700-1200 per kernel
- Filenames: Generic (`submission.py`)
- Strategy: Systematic exploration
- **Lesson**: Stealth naming is standard for pros

### What We Should Copy

✅ **Stealth naming** (John Hahn, parcadei)
✅ **Selective submissions** (John Hahn - 44 submissions vs 1000+)
✅ **Version tracking** (v115 suggests 115 iterations)

❌ **Avoid**: Revealing filenames (josusanmartin style)

---

## Operational Security Checklist

### Filename Rules
- [x] Never include: `ksplit`, `expert`, `splitk`, `aggressive`, `optimized`
- [x] Use generic: `submission_v{N}.py`
- [x] Randomize submission order (don't submit v1, v2, v3 sequentially)

### Code Comments
- [x] Remove strategy hints from docstrings
- [x] Use generic comments: "Optimized variant" not "KSPLIT=8 variant"
- [x] Keep detailed notes in THIS FILE only

### Git Commits
- [x] Generic messages: "Update submission v8" not "Add KSPLIT=8 variant"
- [x] No strategy details in commit messages

### External Communication
- [x] Slack: Use code names ("Project Alpha" not "KSPLIT tuning")
- [x] Forums: Share only after winning
- [x] README: Generic descriptions only

---

## Code Name Reference

For internal communication:

| Code Name | Actual Strategy | Kernel |
|-----------|-----------------|--------|
| Project Alpha | KSPLIT tuning | MoE |
| Project Beta | Expert-aware dispatch | MoE |
| Project Gamma | Split-K optimization | GEMM |
| Project Delta | Three-regime routing | MLA |
| Project Epsilon | HIP kernel fusion | All |

---

## Next Actions

1. ✅ Rename existing submissions to generic names
2. ✅ Update README with generic descriptions
3. ✅ Store this map in SurrealDB for querying
4. ⏳ Submit future variants with stealth names
5. ⏳ Track results internally, not in filenames

---

**Remember**: The competition can see submission filenames on the leaderboard. Don't give away our edge! 🎯
