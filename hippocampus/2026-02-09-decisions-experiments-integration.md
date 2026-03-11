---
title: 'Decisions & Experiments Integration - v2'
date: 2026-02-09
tags: [daily]
aspect: doer
neural:
  activation: 0.473
  stage: growing
  cluster: daily
---
# Decisions & Experiments Integration - v2

**Date**: 2026-02-09
**Method**: Selective v2 (30% threshold)
**Time**: ~15 minutes
**Cost**: $0

## Executive Summary

✅ **16 decisions** enriched with semantic metadata
✅ **2 experiments** enriched with semantic metadata
✅ **25 files** total modified (bidirectional links)
✅ **75 links** extracted (selective, high quality)

## Results

### Files Enriched

**Decisions** (16):
- All enriched with domains, categories, and related links
- Status: 7 proposed, 6 unknown, 2 implemented, 1 ready
- Top domains: infrastructure (13), integration (12), ai-ml (11)

**Experiments** (2):
- ai-research-agent-for-vault-notes
- phase-5b-production-readiness-validation

**Bidirectional Links Created**:
- 3 concepts → decisions/experiments
- 5 patterns → decisions/experiments
- 0 lessons → decisions (none explicitly referenced yet)

### Link Quality Comparison

| Metric | Lessons v1 | Decisions v2 | Improvement |
|--------|-----------|--------------|-------------|
| Files | 38 | 18 | - |
| Total links | 306 | 75 | **75% reduction** |
| Avg links/file | 8.1 | 4.2 | **Better selectivity** |
| Threshold | Any match | 30% match | **Quality filter** |
| Over-broad? | Yes (80%) | No | **v2 win** |

## v2 Methodology

### Selective Domain Scoring

```python
score = keyword_hits / total_keywords
matched = [d for d, s in scores.items() if s >= 0.3]
```

**Effect**: Only domains with 30%+ keyword presence are tagged

### Domain Categories

**Infrastructure**: architecture, performance, infrastructure, ai-ml, data, integration
**Decision-specific**: technical, strategic, operational

**Result**: More precise categorization

### Explicit Link Extraction

Only `[[wiki-links]]` actually present in content (no heuristic concept mapping)

**Effect**: High precision, low false positives

## Sample Enrichment

**Before**:
```markdown
# Ollama MCP Server Decision

[content]
```

**After**:
```markdown
# Ollama MCP Server Decision

[content]

## Related
**Domains**: ai-ml, architecture, data, infrastructure, integration, performance
**Categories**: strategic, technical
```

## Bidirectional Discovery

**Pattern → Decision**:
```markdown
# bmad-scale-adaptive-documentation.md

## Decisions & Experiments
- 📋 [[2026-02-08-bmad-framework-removal]] - BMAD framework removal
```

**Decision → Pattern**:
```markdown
# 2026-02-08-bmad-framework-removal.md

## Related
- [[bmad-scale-adaptive-documentation]]
- [[bmad-agent-persona-definition]]
- [[bmad-workflow-orchestration]]
```

## Cross-Vault Integration

**Now discoverable**:
- Decisions ↔ Patterns (5 bidirectional links)
- Decisions ↔ Concepts (3 bidirectional links)
- Experiments ↔ Patterns/Concepts
- All enriched with domain tags for filtering

**Obsidian queries possible**:
- "All infrastructure decisions"
- "Patterns referenced by decisions"
- "Proposed vs implemented decisions"
- "Strategic decisions about AI/ML"

## Lessons from v1 → v2

### What Improved
1. **Selectivity**: 30% threshold eliminates noise
2. **Explicit-only**: No heuristic concept guessing
3. **Quality > Quantity**: 75 precise links > 306 broad links
4. **Categories**: Decision-specific taxonomy added

### What Worked Well
1. **Fast execution**: ~15 min total (analysis + enrichment)
2. **Zero cost**: Pure heuristics, no API calls
3. **Bidirectional**: Automatic reverse index creation
4. **Reusable**: Same pattern, better tuning

### Next Iteration (v3)
- Add severity/priority tagging (like lesson CRITICAL/HIGH)
- Semantic clustering (group related decisions)
- Timeline analysis (decision evolution over time)
- Impact scoring (which decisions influenced most work)

## Files Created

**Scripts**:
- `/tmp/analyze_decisions_v2.py` - Selective semantic analyzer
- `/tmp/enrich_decisions_experiments.py` - Vault enrichment
- `/tmp/decisions_experiments_links.json` - 75 extracted links

**Vault**:
- `daily/2026-02-09-decisions-experiments-integration.md` (this file)
- 16 decisions enriched
- 2 experiments enriched
- 3 concepts with reverse links
- 5 patterns with reverse links

## Statistics

**By Domain**:
- Infrastructure: 13 files (72%)
- Integration: 12 files (67%)
- AI/ML: 11 files (61%)
- Architecture: 10 files (56%)
- Data: 9 files (50%)

**By Status** (decisions only):
- Proposed: 7 (44%)
- Unknown: 6 (38%)
- Implemented: 2 (13%)
- Ready: 1 (6%)

**By Category** (decisions only):
- Technical: ~60%
- Strategic: ~50%
- Operational: ~20%

## Next Applications

**Immediate**:
1. Add lesson references to decisions (manual curation)
2. Create decision → paper links (research backing)
3. Timeline view of decision evolution

**Future**:
1. Apply to 38 remaining papers (research integration)
2. Apply to patterns (cross-pattern relationships)
3. Apply to daily notes (session insights)

## Success Metrics

- ✅ 18/18 files enriched with v2 selective metadata
- ✅ 75 high-quality links (vs 306 noisy)
- ✅ Bidirectional discovery working in Obsidian
- ✅ 25 files modified (decisions + reverse links)
- ✅ Zero cost, 15-minute execution
- ✅ v2 methodology validated

## Related

**Patterns**: [[lessons-graph-integration]] (v1 → v2 evolution)

**Lessons**:
- **L1**: Selectivity > speed (30% threshold works)
- **L2**: Explicit > heuristic (for precision)
- **L3**: Domain-specific categories matter (decision taxonomy)
- **L4**: Reverse index creates discoverability

---

**Status**: ✅ COMPLETE
**Method**: v2 selective (refined from lessons retrospective)
**Next**: Manual lesson → decision curation, or apply to papers
