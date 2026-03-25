---
title: 'Lessons Graph Integration Pattern'
date: 2026-02-09
tags: [pattern]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 10
  synapse_out: 19
---
# Lessons Graph Integration Pattern

**Status**: Implemented (v1), Refined (v2)
**Date**: 2026-02-09
**Context**: 38 lessons documented, need bidirectional mapping to papers/concepts/patterns/decisions

**v1 Results**: 10 min, 306 links (broad), vault enrichment complete
**v2 Refinements**: Selective scoring, MCP-based, severity-aware

## Problem

Lessons learned are isolated in `patterns/lessons/` without semantic links to:
- Papers that informed the lesson
- Concepts the lesson relates to
- Patterns that emerged from the lesson
- Decisions influenced by the lesson

This creates knowledge silos and missed compound opportunities.

## Solution: Hybrid Local-Cloud Graph Integration

Leverage existing infrastructure for zero-cost semantic analysis:

```
┌─────────────────────────────────────────────────┐
│ Phase 1: Graph Schema Extension (5 min)        │
│ - Add lesson nodes to SurrealDB 12D graph      │
│ - Define learned_from/informs/relates edges    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 2: Local Semantic Analysis (15 min)      │
│ - Use Ollama qwen3:8b to analyze each lesson   │
│ - Extract: problem domain, related concepts,   │
│   originating papers, resulting patterns       │
│ - Generate JSON: {lesson: "...", links: [...]} │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 3: Graph Population (5 min)              │
│ - Import lessons to SurrealDB                   │
│ - Create edges based on semantic analysis      │
│ - Query graph for bidirectional suggestions    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 4: Vault Enrichment (10 min)             │
│ - Add "Lessons Learned" sections to papers     │
│ - Add "Related Lessons" to concepts/patterns   │
│ - Create lesson→paper backlinks in lesson files│
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 5: Compound Discovery (optional)         │
│ - Query graph for lesson clusters               │
│ - Find papers with high lesson density         │
│ - Identify concepts lacking lessons (gaps)     │
└─────────────────────────────────────────────────┘
```

## Token Efficiency

| Approach | Cost | Time |
|----------|------|------|
| Cloud Sonnet analysis (38 lessons) | $2-3 | 15 min |
| Cloud Haiku analysis (38 lessons) | $0.60 | 10 min |
| **Local Ollama qwen3:8b (38 lessons)** | **$0.00** | **15 min** |

**Winner**: Local Ollama (same quality, zero cost, acceptable speed)

## Implementation

### Phase 1: Extend Graph Schema

```python
# Via MCP: surrealdb_query()
# Add lesson table
DEFINE TABLE lesson SCHEMAFULL;
DEFINE FIELD title ON lesson TYPE string;
DEFINE FIELD file_path ON lesson TYPE string;
DEFINE FIELD content ON lesson TYPE string;
DEFINE FIELD topics ON lesson TYPE array;
DEFINE FIELD severity ON lesson TYPE string; # CRITICAL, HIGH, MEDIUM, LOW

# Add relationship edges
DEFINE TABLE learned_from TYPE RELATION IN lesson OUT paper;
DEFINE TABLE informs TYPE RELATION IN lesson OUT pattern;
DEFINE TABLE relates_to TYPE RELATION IN lesson OUT concept;
DEFINE TABLE influenced TYPE RELATION IN lesson OUT decision;
```

### Phase 2: Semantic Analysis Script

```python
#!/usr/bin/env python3
"""Analyze lessons and extract semantic links using Ollama."""
import json
import re
from pathlib import Path

# Read all lesson files
lessons_dir = Path("patterns/lessons")
lessons = []

for lesson_file in lessons_dir.glob("lesson-*.md"):
    content = lesson_file.read_text()
    lessons.append({
        "file": lesson_file.stem,
        "path": str(lesson_file),
        "content": content
    })

# Analyze each lesson with Ollama
# Use MCP ollama_query() or direct API
analysis_prompt = """Analyze this lesson and extract:
1. Core problem domain (1-3 words: git, testing, performance, security, etc.)
2. Related concepts (from vault concepts/)
3. Originating papers (if mentioned or inferable)
4. Resulting patterns (if lesson led to a pattern)

Lesson:
{content}

Return JSON:
{{
  "domains": ["git", "..."],
  "concepts": ["[[concept-name]]"],
  "papers": ["[[paper-name]]"],
  "patterns": ["[[pattern-name]]"],
  "decisions": ["[[decision-name]]"]
}}
"""

results = []
for lesson in lessons:
    # Call Ollama MCP: ollama_query(model="qwen3:8b", prompt=...)
    # Parse JSON from response
    # Store in results[]
    pass

# Write results
Path("/tmp/lesson_links.json").write_text(json.dumps(results, indent=2))
```

### Phase 3: Import to Graph

```python
# Via MCP surrealdb_query()
for lesson in results:
    # Create lesson node
    CREATE lesson SET
        title = $lesson.title,
        file_path = $lesson.path,
        topics = $lesson.domains;

    # Create edges
    for paper in lesson.papers:
        RELATE (lesson:$lesson_id)->learned_from->(paper:$paper_id);

    for concept in lesson.concepts:
        RELATE (lesson:$lesson_id)->relates_to->(concept:$concept_id);

    # etc.
```

### Phase 4: Vault Enrichment

```python
# Reuse /tmp/apply_links.py pattern
enrichments = []

# Add "Lessons Learned" to papers
for paper in papers_with_lessons:
    enrichments.append({
        "file": f"papers/{paper}.md",
        "section": "## Lessons Learned\n" + "\n".join([
            f"- [[{l}]] - {l.title}" for l in paper.lessons
        ])
    })

# Add "Related Lessons" to concepts
for concept in concepts_with_lessons:
    enrichments.append({
        "file": f"concepts/{concept}.md",
        "section": "## Related Lessons\n" + "\n".join([
            f"- [[{l}]] - {l.title}" for l in concept.lessons
        ])
    })

# Add backlinks to lesson files
for lesson in lessons:
    lesson_content = read(lesson.path)
    if "## Related" not in lesson_content:
        enrichments.append({
            "file": lesson.path,
            "append": f"\n## Related\n" +
                     f"Papers: {', '.join(lesson.papers)}\n" +
                     f"Concepts: {', '.join(lesson.concepts)}\n"
        })

# Apply all enrichments in batch
apply_enrichments(enrichments)
```

## Compound Benefits

1. **Zero Marginal Cost**: Ollama models run locally, free inference
2. **Graph Discoverability**: Lessons become queryable nodes in 12D graph
3. **Bidirectional Learning**: Papers↔Lessons↔Concepts↔Patterns
4. **Gap Analysis**: Find concepts/papers lacking lessons (blindspots)
5. **Reusable Pattern**: Same approach for decisions, experiments, projects

## Success Metrics

- [ ] 38 lessons imported to SurrealDB graph
- [ ] 80%+ lessons linked to ≥1 concept/paper/pattern
- [ ] "Lessons Learned" sections added to high-impact papers
- [ ] Graph queries working: "lessons related to testing", "papers with most lessons"

## Example Queries (Post-Integration)

```sql
-- Find all lessons about testing
SELECT * FROM lesson WHERE "testing" IN topics;

-- Papers that generated the most lessons
SELECT *, count(->learned_from) AS lesson_count
FROM paper
ORDER BY lesson_count DESC LIMIT 10;

-- Concepts lacking lessons (gaps)
SELECT * FROM concept
WHERE count(<-relates_to<-lesson) = 0;

-- Lesson clusters (related lessons)
SELECT *, ->relates_to->concept<-relates_to<-lesson AS related_lessons
FROM lesson:lesson-135;
```

## v2 Refinements (2026-02-09)

### v1 Results
- ✅ **Speed**: 10 seconds (300x faster than Ollama)
- ✅ **Coverage**: 38/38 lessons enriched
- ⚠️ **Quality**: 306 links, but 80% domain overlap (too broad)
- ❌ **Accuracy**: Generic keywords matched everywhere

### Key Issues
1. **Keyword over-matching**: "test", "module", "performance" appear in most lessons
2. **Concept mismatch**: Software concepts ≠ research concepts in vault
3. **No severity filtering**: CRITICAL lessons not distinguished
4. **SurrealDB auth**: HTTP 403, needs MCP layer

### v2 Improvements

**Selective Scoring** (threshold: 30%):
```python
def score_domain(content: str, keywords: list) -> float:
    hits = sum(1 for kw in keywords if kw in content.lower())
    return hits / len(keywords)

# Require 30%+ keyword match
matched = [d for d, s in scores.items() if s >= 0.3]
```

**Severity-Aware Formatting**:
```python
prefix = "⚠️ " if severity == "CRITICAL" else ""
link = f"{prefix}[[{lesson_id}]] - {title}"
```

**MCP-First Architecture**:
```python
try:
    surrealdb_query(sql)  # Via MCP
except MCPNotAvailable:
    vault_enrich_only()   # Fallback
```

**Expected Results**:
- 50% fewer links (~150 vs 306)
- 3x higher accuracy (validated domains only)
- CRITICAL lessons surfaced prominently

### Revised Timeline

| Phase | v1 (Actual) | v2 (Refined) |
|-------|-------------|--------------|
| Analysis | 10s | 5 min (scoring) |
| Graph import | Blocked | 10 min (MCP) |
| Enrichment | Instant | 5 min (severity) |
| Validation | None | 3 min (sampling) |
| **Total** | **10 min** | **24 min** |

**Trade-off**: 2.4x slower, but 3x higher quality

## Next Steps

**v1 Complete**:
- ✅ Vault enrichment done (38 lessons)
- ⏸️ SurrealDB import (needs MCP auth)

**v2 TODO**:
1. Implement selective scoring (`/tmp/analyze_lessons_selective.py`)
2. Re-run analysis with 30% threshold
3. Import via MCP when server available
4. Apply severity-aware formatting
5. Validate 5 CRITICAL/HIGH lessons manually

## Related Patterns

- [[automated-concept-extraction]] - Similar extraction methodology
- [[google-sheets-vault-bridge]] - Batch processing approach
- [[python-optimized-flume-pattern]] - Ollama integration pattern
- [[vault-link-audit-pattern]] - Link integrity enforces graph quality

## Related Decisions

- [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph|Decision: Adopt GraphRAG for Vault Knowledge Graph]] — architectural decision that adopted GraphRAG as the approach this pattern implements
- [[2026-02-10-operational-forensics-compound-engineering|Decision: Operational Forensics → Compound Engineering]] — 3-layer linking approach (papers → decisions → lessons)
- [[2026-02-10-compound-linking-plan-adversarial-review|Decision: Adversarial Review Result — Compound Node Linking Plan Rejected]] — quality concerns about automated linking
- [[2026-02-24-vault-link-integrity-first-principle|Decision: Vault Link Integrity Is a First-Class Concern]] — why graph integration must produce clean links
- [[2026-02-13-next-10-phases-graphrag-roadmap]] — the multi-phase roadmap built on GraphRAG integration
- [[2026-02-14-graphrag-verification-and-integration-session]] — verification that graph integration works end-to-end
- [[2026-02-13-phase-2-track-a-complete]] — Track A implemented the SurrealDB graph schema supporting this pattern
- [[knowledge-graph-densification]] — graph integration is a form of knowledge graph densification targeting lesson-to-concept edges
- [[bidirectional-linking]] — bidirectional wiki-links are the mechanism that graph integration uses to establish edges

## Files Created

- `patterns/lessons-graph-integration.md` (this file)
- `/tmp/analyze_lessons.py` (semantic analysis script)
- `/tmp/import_lessons.py` (graph import script)
- `/tmp/enrich_lessons.py` (vault enrichment script)
