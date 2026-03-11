---
title: 'Lessons Graph Integration Plan'
date: 2026-02-09
tags: [daily]
aspect: doer
neural:
  activation: 0.404
  stage: growing
  cluster: daily
---
# Lessons Graph Integration Plan

**Date**: 2026-02-09
**Status**: Ready to execute
**Estimated Time**: 35 minutes total
**Cost**: $0 (uses local Ollama)

## Overview

Compound engineering plan to integrate 38 lessons into the 12D graph and create bidirectional vault links.

## Statistics

- **38 lessons** documented (2 CRITICAL, 7 HIGH, 29 MEDIUM severity)
- **0 graph nodes** currently (lessons not in SurrealDB)
- **0 backlinks** currently (lessons isolated)
- **Target**: 80%+ lessons linked to concepts/papers/patterns

## Five-Phase Plan

### Phase 1: Graph Schema Extension (5 min)
**Action**: Add `lesson` table to SurrealDB with relationship edges
**Files**: Execute SQL via `surrealdb_query()` MCP tool
**Output**: Schema ready for lesson import

### Phase 2: Semantic Analysis (15 min)
**Action**: Analyze each lesson with Ollama qwen3:8b to extract:
- Problem domains (git, testing, performance, security, etc.)
- Related concepts from vault
- Originating papers (if mentioned)
- Resulting patterns (if lesson led to pattern)

**Script**: `/tmp/analyze_lessons.py` (✓ READY)
**Prompts**: `/tmp/lesson_analysis_prompts.jsonl` (✓ GENERATED, 38 prompts)
**Output**: `/tmp/lesson_links.json` with semantic relationships

### Phase 3: Graph Population (5 min)
**Action**: Import lessons + edges to SurrealDB
**Script**: `/tmp/import_lessons.py` (TODO)
**Output**: 38 lesson nodes + ~100-150 relationship edges

### Phase 4: Vault Enrichment (10 min)
**Action**: Add bidirectional links:
- "Lessons Learned" sections in papers
- "Related Lessons" in concepts/patterns
- Backlinks in lesson files

**Script**: Reuse `/tmp/apply_links.py` pattern
**Output**: Enriched vault files with cross-references

### Phase 5: Compound Discovery (optional)
**Action**: Run graph queries to find:
- Lesson clusters (related lessons)
- High-lesson-density papers
- Concepts lacking lessons (blindspots)

**Output**: Discovery insights for future work

## Token Efficiency

| Approach | Cost | Time |
|----------|------|------|
| Cloud Sonnet (38 lessons × 2K tokens) | $2.28 | 15 min |
| Cloud Haiku (38 lessons × 2K tokens) | $0.61 | 10 min |
| **Local Ollama qwen3:8b** | **$0.00** | **15 min** |

**Winner**: Local Ollama (same quality, zero cost)

## Files Created

- ✓ `patterns/lessons-graph-integration.md` - Full pattern documentation
- ✓ `/tmp/analyze_lessons.py` - Semantic analysis script (READY)
- ✓ `/tmp/lesson_analysis_prompts.jsonl` - 38 prompts (GENERATED)
- ✓ `/tmp/lesson_links.json` - Metadata file (READY)
- ⏳ `/tmp/import_lessons.py` - Graph import script (TODO)
- ⏳ `/tmp/enrich_lessons.py` - Vault enrichment script (TODO)

## Compound Benefits

1. **Zero Cost**: Local Ollama, no API charges
2. **Graph Queries**: Lessons become explorable in 12D graph
3. **Bidirectional Links**: Papers↔Lessons↔Concepts
4. **Gap Analysis**: Find concepts/papers without lessons
5. **Reusable**: Same pattern for decisions/experiments

## Next Actions

**Option A: Full Automation (recommended)**
```bash
# Phase 1: Extend schema
# Phase 2: Run Ollama analysis (15 min)
# Phase 3: Import to graph (5 min)
# Phase 4: Enrich vault (10 min)
# Total: ~35 minutes, $0 cost
```

**Option B: Incremental**
1. Extend schema now (5 min)
2. Run semantic analysis later when needed
3. Import + enrich when analysis complete

## Success Criteria

- [ ] 38 lessons in SurrealDB graph
- [ ] 80%+ lessons linked to ≥1 concept/paper/pattern
- [ ] "Lessons Learned" sections in high-impact papers
- [ ] Graph queries working (e.g., "lessons about testing")
- [ ] Pattern documented in vault

## Related Work

- [[automated-concept-extraction]] - Similar extraction method
- [[google-sheets-vault-bridge]] - Batch processing pattern
- [[python-optimized-flume-pattern]] - Ollama integration
- [[2026-02-09-ollama-mcp-server]] - Local model infrastructure

---

**Ready to execute**: All preparation complete, awaiting user approval.
