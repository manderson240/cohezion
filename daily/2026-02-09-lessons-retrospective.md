---
title: 'Lessons Integration Retrospective'
date: 2026-02-09
tags: [daily]
---
# Lessons Integration Retrospective

**Date**: 2026-02-09
**Duration**: 10 minutes (planned 35)
**Cost**: $0 (planned $0)

## What Worked ✅

1. **Heuristic speed**: 10 seconds vs 50+ minutes (Ollama ~80s/lesson)
2. **Vault-first approach**: Enrichment provides immediate value without graph
3. **Compound infrastructure**: Reused existing patterns (apply_links.py methodology)
4. **Pragmatic pivot**: Switched from Ollama to heuristics when latency blocked
5. **Phase independence**: Phase 4 succeeded despite Phase 3 auth issues

## What Didn't Work ❌

1. **Keyword matching too broad**: All lessons matched 4-5 domains (80% overlap)
2. **Concept mismatch**: Software concepts (testing, automation) ≠ research concepts (agentic-ai, compound-engineering)
3. **SurrealDB auth**: HTTP 403 blocked Phase 3 (needs MCP server)
4. **Ollama latency**: 80-90s per query unusable for 38 lessons
5. **No severity filtering**: CRITICAL lessons not surfaced distinctly

## Key Metrics

| Metric | Planned | Actual | Delta |
|--------|---------|--------|-------|
| Time | 35 min | 10 min | **-71%** ✅ |
| Cost | $0 | $0 | ✅ |
| Lessons | 38 | 38 | ✅ |
| Links | ~100-150 | 306 | **+100%** ⚠️ |
| Domain accuracy | High | Low | ⚠️ |

**Analysis**: Over-extraction (306 links) due to broad keywords. Quality < quantity.

## Lessons Learned

### L1: Keyword Selectivity Matters
**Problem**: Generic keywords (test, module, performance) appear everywhere
**Solution**: Use TF-IDF scoring or require 3+ keyword hits for domain match

### L2: Concept Spaces Are Domain-Specific
**Problem**: Software concepts ≠ research concepts
**Solution**: Build separate ontologies or use explicit vault references

### L3: Vault Enrichment > Graph Import
**Problem**: Graph adds complexity without immediate user value
**Solution**: Prioritize vault enrichment (Phase 4), defer graph (Phase 3)

### L4: Ollama Needs Batching
**Problem**: 80s latency per request = 50 min for 38 lessons
**Solution**: Use Ollama batch API or async processing (lesson-123-ollama-latency)

### L5: Auth Is Infrastructure
**Problem**: Direct HTTP failed, MCP would have worked
**Solution**: Always use MCP layer for authenticated services

## Refined Plan

### Phase 2.1: Selective Heuristics (5 min)

**Keyword scoring**:
```python
def score_domain(content: str, domain: str, keywords: list) -> float:
    hits = sum(1 for kw in keywords if kw in content.lower())
    return hits / len(keywords)  # 0.0-1.0

# Require 30%+ match instead of any match
matched = [d for d, score in scores.items() if score >= 0.3]
```

**Severity weighting**:
- CRITICAL lessons: Boost domain confidence by 20%
- HIGH lessons: Boost by 10%
- Surface in vault enrichment: `**⚠️ CRITICAL lesson**: ...`

### Phase 3.1: MCP-Based Import (10 min)

**When MCP server available**:
```python
# Use MCP tools instead of HTTP
from mcp_client import surrealdb_query

surrealdb_query(schema_sql)
surrealdb_query(import_sql)
```

**Benefits**:
- Auth handled by MCP
- Consistent with existing infrastructure
- Error handling built-in

### Phase 4.1: Targeted Enrichment (5 min)

**Enrich specific relationships**:
1. Research concepts → Lessons (manual curation needed)
2. CRITICAL lessons → All related notes (severity surfacing)
3. Pattern/decision → Lessons (explicit references only)

**Skip generic concepts** (testing, automation) unless manually validated

### Phase 5: Graph Queries (5 min)

**When Phase 3 complete**:
```sql
-- Lesson impact: papers citing lessons
SELECT paper.title, count(<-learned_from<-lesson) AS impact
FROM paper ORDER BY impact DESC LIMIT 10;

-- Knowledge gaps: concepts without lessons
SELECT concept.title FROM concept
WHERE count(<-relates_to_concept<-lesson) = 0;

-- Severity clusters: CRITICAL lesson domains
SELECT domains, count() FROM lesson
WHERE severity = 'CRITICAL' GROUP BY domains;
```

## Revised Methodology

### Token-Efficient Lessons Integration v2

**Phase 0: Severity Triage** (1 min)
- Filter by severity: CRITICAL (2) → HIGH (7) → MEDIUM (29)
- Process high-priority first

**Phase 1: Selective Analysis** (5 min)
- TF-IDF scored keyword matching (threshold: 30%)
- Explicit `[[wiki-link]]` extraction only
- Output: Fewer, higher-confidence links (~100-150 vs 306)

**Phase 2: MCP Graph Import** (10 min)
- Via MCP tools (auth handled)
- Import lessons + validated links only
- Skip if MCP unavailable (vault-first)

**Phase 3: Smart Enrichment** (5 min)
- CRITICAL lessons: Bold/warn formatting
- Research concepts: Manual curation hooks
- Generic concepts: Omit or tag as [auto]

**Phase 4: Validation** (3 min)
- Sample 5 CRITICAL/HIGH lessons
- Verify domain accuracy
- Adjust thresholds if needed

**Total: 24 minutes, $0**

## Reusable Patterns

### Fast Semantic Extraction
```python
def extract_domains_selective(content: str, threshold: float = 0.3):
    scores = {d: score_keywords(content, kws)
              for d, kws in DOMAIN_KEYWORDS.items()}
    return [d for d, s in scores.items() if s >= threshold]
```

### MCP-First Architecture
```python
try:
    surrealdb_query(sql)  # Via MCP
except MCPNotAvailable:
    vault_enrich_only()   # Fallback
```

### Severity-Aware Enrichment
```python
def format_lesson_link(lesson):
    prefix = "⚠️ " if lesson.severity == "CRITICAL" else ""
    return f"{prefix}[[{lesson.id}]] - {lesson.title}"
```

## Next Application

Apply refined methodology to:
1. **Decisions** (8 files) - Map to papers/concepts/patterns
2. **Experiments** (1 file) - Link to lessons/decisions
3. **Patterns** (8 files) - Cross-link patterns ↔ lessons

**Expected**: 50% fewer links, 3x higher accuracy, same speed

## Files

**Pattern**: `patterns/lessons-graph-integration.md` (original)
**Retrospective**: `daily/2026-02-09-lessons-retrospective.md` (this)
**Scripts**:
- `/tmp/analyze_lessons_heuristic.py` (v1 - broad)
- `/tmp/analyze_lessons_selective.py` (v2 - TODO)

---

**Key Insight**: Speed ≠ Quality. Fast heuristics need selectivity filters. Vault enrichment delivers immediate value, graph enables discovery. Prioritize vault, defer graph.
