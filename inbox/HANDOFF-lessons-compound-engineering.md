---
title: HANDOFF - Lessons Compound Engineering
date: 2026-02-10
tags: [handoff, compound-engineering, next-session]
status: ready
---

# Lessons Compound Engineering - Session Handoff

## Quick Context

**Discovery**: 39 lessons with rich operational data, but only **8% linked to research** (vs 90% for papers).

**Opportunity**: Add lessons as **Layer 3 validation layer** in compound engineering.

## What's Ready

### Artifacts Created This Session
1. `decisions/2026-02-10-operational-forensics-compound-engineering.md` - Complete plan
2. `lessons/2026-02-10-debug-log-bloat-analysis.md` - Rich example (734K metrics)
3. `patterns/log-rotation-and-monitoring.md` - Operational pattern
4. `retrospectives/2026-02-10-log-mining-retrospective.md` - Meta-process

### Key Statistics
- **39 lessons** total (2 CRITICAL, 7 HIGH, 29 MEDIUM)
- **~3 lessons** linked to papers (8% coverage)
- **Target**: 35+ links (30% coverage in Phase 1)
- **Method**: Ollama semantic search + manual validation
- **Cost**: $0 (local inference)
- **Time**: 2-3 hours

## Execution Plan (Ready to Run)

### Phase 1: Semantic Search (1 hour)
```bash
# Extract lesson embeddings
cd /tmp
cat > link_lessons_to_papers.py << 'EOF'
import ollama
import json
from pathlib import Path

VAULT = Path("/home/mike-anderson/vaults/cohezion-vault")
lessons = list((VAULT / "lessons").glob("*.md"))
papers = list((VAULT / "papers").glob("*.md"))

# Compute embeddings for all lessons + papers
# Find cosine similarity > 0.3
# Output: [{"lesson": "...", "papers": ["...", "..."]}]
EOF

python3 link_lessons_to_papers.py > lesson_paper_links.json
```

### Phase 2: Validation (1 hour)
- Manual review of candidates
- Filter false positives (expect 20%)
- Identify high-value cross-links

### Phase 3: Application (30 min)
- Batch apply wiki-links (proven `/tmp/apply_links.py` pattern)
- Update SurrealDB
- Commit to vault

## High-Value Example Mappings

| Lesson | Severity | Should Link To |
|--------|----------|----------------|
| debug-log-bloat-analysis | HIGH | Observability papers, distributed systems |
| telemetry-corruption-fix | MEDIUM | Log aggregation, JSONL format papers |
| token-waste-postmortem | CRITICAL | AI cost optimization, prompt engineering |
| ollama-context-management | HIGH | LLM context window papers |

## Tools Available

1. **Ollama MCP** - Local embeddings (`nomic-embed-text`)
2. **`/tmp/apply_links.py`** - Batch wiki-link application (proven)
3. **SurrealDB sync** - Graph import (when online)
4. **Canvas view** - Visual validation

## Success Criteria

**Phase 1 Complete** when:
- [ ] 35+ lessons ↔ papers links added
- [ ] 30% lessons coverage achieved
- [ ] 10+ lessons ↔ decisions cross-links
- [ ] SurrealDB updated (or queued if offline)
- [ ] Committed to vault git

## Why This Matters

**Current State**: Theory (papers) ↔ Practice (decisions) gap
**New State**: Theory ↔ Practice ↔ **Validation (lessons)**

**Example Value Chain**:
1. Paper: "Exponential backoff reduces retry storms"
2. Decision: "Implement backoff in MCP client"
3. Lesson: "Found 734K polling calls without backoff → 474MB log"
4. **Insight**: Theory validated, anti-pattern quantified

**Compound Effect**: Each lesson becomes a data point validating or refuting research claims.

## Next Session Prompt

```
Review: decisions/2026-02-10-operational-forensics-compound-engineering.md
Execute: Phase 1 (Ollama semantic search for lessons → papers)
Goal: 35+ links, 30% coverage
Method: Hybrid (automated + manual validation)
Tools: Ollama MCP + apply_links.py
Time: 2-3 hours
```

## Related Context

- Current compound coverage: 90% (papers/concepts)
- Lessons are newest note type (not in original 12D graph)
- Canvas view supports visual validation
- Pattern proven in `2026-02-10-canvas-driven-compound-engineering-refined`

---

**Ready to execute** - all tools, patterns, and decision docs in place. Just needs Ollama semantic search run + validation.
