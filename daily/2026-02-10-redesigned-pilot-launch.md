---
title: Redesigned Pilot Study - Launch
date: 2026-02-10
tags: [execution, log-mining, pilot-study]
status: phase-1-in-progress
---

## Decision

✅ **PROCEEDING with Redesigned Pilot Study** (Alternative 3 from adversarial review)

**Rationale**: Accept data limitations (98 sessions vs 647), extract 3-5 validated hypotheses with honest caveats, build foundation for future work.

## Execution Plan

### Phase 1: Manual Labeling (8 hours, $0) 🏃 **IN PROGRESS**

**Tool Created**: `/tmp/label_sessions_interactive.py`

**Task**: Manually review all 98 sessions, label based on ACTUAL outcomes (not automated error counts)

**Labels**:
- Success: Task completed efficiently
- Partial: Task done but inefficient OR partially complete
- Failure: Task not completed
- Unknown: Can't remember outcome

**Timeline**: 2-3 days (20-25 sessions per sitting)

**Output**: `/tmp/session_index_labeled.json`

**How to Start**:
```bash
python3 /tmp/label_sessions_interactive.py
```

**Features**:
- Interactive CLI with keyboard shortcuts (s/p/f/u/q)
- Auto-saves after each label (safe to quit anytime)
- Progress tracking (X/98 complete)
- Resume capability
- Optional notes per session

**Alternative**: HTML batch review
```bash
python3 /tmp/label_sessions_interactive.py --html
# Opens: /tmp/session_review.html
```

---

### Phase 2: Fixed Extraction (30 min, $0) ⏳ READY

**Tasks**:
1. Fix error counting (filter non-fatal)
2. Apply SurrealDB schema
3. Import labeled sessions with correct labels
4. Verify distribution

**Triggers after**: Phase 1 complete

---

### Phase 3: Pattern Hypotheses (45 min, $0.40) ⏳ AGENTS READY

**Tasks**:
1. Spawn 2 parallel Haiku agents:
   - agent-success-patterns: Top 10 successful → 3-5 hypotheses
   - agent-failure-patterns: Top 10 failed → 3-5 anti-patterns
2. Human validates each hypothesis
3. Mark as validated/uncertain/rejected

**Output**: 3-5 validated hypotheses with evidence

**Triggers after**: Phase 2 complete

---

### Phase 4: Documentation (30 min, $0) ⏳ READY

**Tasks**:
1. Create `patterns/prompt-optimization-hypotheses.md`
2. Label as "PILOT STUDY - NOT VALIDATED AT SCALE"
3. Document limitations (98 sessions, single labeler, recency bias)
4. Update `MEMORY.md` with findings

**Triggers after**: Phase 3 complete

---

## Why Redesign?

**Original Plan Issues** (from adversarial review):

1. ❌ **Sample size catastrophe**: Claimed 647, only 98 exist (85% missing)
2. ❌ **Broken classifier**: 71% "failure" rate is absurd
3. ❌ **Error count noise**: Averaging 42.6 non-fatal errors per session
4. ❌ **Haiku hallucination risk**: Can't extract 10-15 patterns from 3 mislabeled sessions
5. ❌ **Cost underestimation**: $0.75 → $2.40 (3.2x over)

**Redesign Fixes**:

✅ Accept 98 sessions (not 647)
✅ Manual labeling (not automated classifier)
✅ Extract 3-5 hypotheses (not 10-15 patterns)
✅ Human validation required
✅ Label as pilot study (not validated patterns)
✅ Cheaper ($0.40 vs $2.40)
✅ Honest about limitations

---

## Expected Deliverable

`patterns/prompt-optimization-hypotheses.md`:

- 3-5 success hypotheses with evidence
- 3-5 failure anti-patterns with evidence
- Confidence scores (0.0-1.0)
- Supporting session IDs
- Limitations section (small sample, single labeler, etc.)
- Status: "PILOT STUDY - NOT VALIDATED AT SCALE"

**NOT claiming**:
- ❌ These are established patterns
- ❌ These work at scale
- ❌ These are statistically significant

**Claiming**:
- ✅ These are preliminary hypotheses
- ✅ These are worth investigating further
- ✅ These provide foundation for future validation

---

## Timeline

| Day | Phase | Hours | Output |
|-----|-------|-------|--------|
| 1 | Phase 1 (part 1) | 4 | ~45 sessions labeled |
| 2 | Phase 1 (part 2) | 4 | ~53 remaining labeled |
| 3 | Phases 2-4 | 2 | Hypotheses documented |

**Total**: ~10 hours over 2-3 days

---

## Meta-Lesson Applied

**From MEMORY.md**:
> "NEVER build test infrastructure before proving the concept works"
> "Validate in Phase 1 (8K tokens, 2-3h): Copy template → Implement ONE feature → Write 5 real tests"

**Lesson Applied**:
- ✅ Ran log indexer FIRST (discovered 98 sessions, not 647)
- ✅ Redesigned based on reality
- ✅ Reduced scope to what's actually achievable
- ✅ Honest about limitations

**What we avoided**:
- ❌ Building full 4-wave system on bad assumptions
- ❌ Extracting fake patterns from mislabeled data
- ❌ MCP tool that gives misleading advice
- ❌ Wasting $2.40 on hallucinated patterns

---

## Files Created

### Architecture & Review
1. `decisions/2026-02-10-claude-log-mining-architecture.md` (680 lines) - Original plan (flawed)
2. `decisions/2026-02-10-log-mining-adversarial-review.md` (520 lines) - Critical flaws identified
3. `/tmp/ADVERSARIAL_REVIEW_SUMMARY.md` (140 lines) - Executive summary

### Execution Tools
4. `/tmp/log_indexer.py` (239 lines) ✅ Functional - Revealed data issues
5. `/tmp/label_sessions_interactive.py` (320 lines) ✅ Ready - Phase 1 tool
6. `/tmp/import_to_surrealdb.py` (142 lines) ✅ Ready - Phase 2 tool
7. `/tmp/surrealdb_prompt_schema.surql` (60 lines) ✅ Ready - DB schema

### Guides
8. `/tmp/REDESIGNED_PILOT_QUICKSTART.md` (287 lines) - Full execution guide
9. `/tmp/EXECUTION_SUMMARY.md` (140 lines) - Original plan summary
10. `daily/2026-02-10-claude-log-mining-design.md` (240 lines) - Design retrospective

### Data
11. `/tmp/session_index.json` (98 sessions) - Auto-labeled (incorrect)
12. `/tmp/session_stats.json` - Statistics revealing issues

---

## Next Action

**START PHASE 1 NOW**:

```bash
python3 /tmp/label_sessions_interactive.py
```

**Or explore in HTML first**:
```bash
python3 /tmp/label_sessions_interactive.py --html
# Then open: file:///tmp/session_review.html
```

**Timeline**: Label 20-25 sessions per sitting (~2 hours each)

**Phase 1 complete when**: `/tmp/session_index_labeled.json` exists with 98 manual labels

---

**Status**: 🏃 Phase 1 in progress - User labeling sessions
