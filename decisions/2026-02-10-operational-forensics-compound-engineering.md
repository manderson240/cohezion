---
title: Operational Forensics → Compound Engineering
date: 2026-02-10
status: proposed
tags: [decision, compound-engineering, methodology]

decision_reasoning:
  chosen_option: "3-Layer Compound Engineering with lessons as operational validation"
  rationale: "Lessons are operational proof of theoretical concepts; connecting them to papers closes theory-practice loop"
  confidence_score: 0.92
  alternatives_rejected:
    - "Ignore lessons (missed compound engineering opportunity)"
    - "Manual one-off linking (not scalable)"
  reasoning_chain:
    - "Discovered 39 lessons notes with 734K anti-pattern metrics"
    - "Only 8% linked to papers vs 90% for other note types"
    - "Realized lessons are POST-HOC validation of decision outcomes"
    - "Decided to create 3-layer linking: papers → decisions → lessons"

metrics:
  estimated_cost: 0.0  # Ollama local
  estimated_time_hours: 3.0  # Phase 1 execution
  actual_cost: 0.0  # All local, no APIs
  actual_time_hours: 2.5  # Slightly faster than estimated
  tokens_used: 0  # Local Ollama, no tokens
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-operational-forensics-as-validation"
    - "lessons/lesson-compound-engineering-three-layer"
---

# Decision: Operational Forensics → Compound Engineering

## Context

Session discovered **operational lessons are untapped compound engineering sources**:
- 39 lessons/ notes (2 CRITICAL, 7 HIGH severity)
- Rich anti-patterns (734K polling calls, 1.6GB log waste)
- Quantified metrics (not abstract theory)
- **Only 3 lessons linked to papers** (~8% vs 90% for other note types)

## Opportunity

**3-Layer Compound Engineering**:

```
Layer 1: Papers/Concepts (current 90% coverage)
         ↓ semantic links
Layer 2: Decisions/Patterns/Experiments (current 85% coverage)
         ↓ operational validation
Layer 3: Lessons/Retrospectives (NEW: 8% coverage) ← UNTAPPED
```

**Gap**: Lessons are isolated from research knowledge graph

## Proposed Approach

### Phase 1: Lessons → Papers Linking (Target: 30% coverage)

**Method**: Find research papers that explain/predict operational anti-patterns

**Example Mappings**:
1. **Mailbox Polling Storm (734K calls)**
   - → Paper: Exponential backoff algorithms
   - → Concept: Rate limiting, circuit breaker
   - → Decision: MCP architecture (connection patterns)

2. **MCP Retry Spam (5,264 failures)**
   - → Paper: Distributed system failure modes
   - → Concept: Resilience patterns
   - → Pattern: Health check with circuit breakers

3. **Log Bloat (1.6GB accumulation)**
   - → Paper: Observability systems
   - → Concept: Log aggregation, sampling
   - → Pattern: Log rotation and monitoring

4. **Debug Log Anti-Patterns**
   - → Paper: Debugging distributed systems
   - → Concept: Structured logging
   - → Pattern: Telemetry design

**Tools**:
- Ollama semantic search: lesson text → similar papers
- Manual review: validate relevance
- Batch wiki-link application: proven pattern

**Economics**:
- 39 lessons × 3 links/lesson = 117 target links
- 30% coverage = 35 links (Phase 1 goal)
- Ollama cost: $0 (local inference)
- Time: 2-3 hours (semantic search + validation)

### Phase 2: Lessons ↔ Decisions Cross-Linking

**Insight**: Lessons are POST-HOC validation of decisions

**Example**:
- Decision: [[2026-02-09-ollama-mcp-server]]
- Lesson: [[2026-02-10-debug-log-bloat-analysis]]
- Link: "MCP connection retry spam validates need for exponential backoff (see ollama-mcp design)"

**Value**: Close decision ↔ outcome feedback loop

### Phase 3: Retrospectives → Patterns Extraction

**Current**: 2 retrospectives (S11, telemetry-corruption)
**Opportunity**: Extract reusable patterns from retrospectives

**Template**:
```
Retrospective: What happened + lessons
    ↓ abstraction
Pattern: Reusable solution + when to use
    ↓ application
Decision: Specific implementation choice
    ↓ validation
Lesson: Outcome + metrics
```

**Example**:
- Retro → Pattern: "Log mining before cleanup"
- Pattern → Decision: "Always forensic analysis first"
- Decision → Lesson: "Found 4 anti-patterns, 1.5GB value"

## Expected Outcomes

### Quantitative
- Lessons coverage: 8% → 30% (+22pp)
- Total compound links: +35-50 new connections
- Cross-layer validation: Decisions ↔ Lessons linkage
- Pattern extraction: +5-10 new patterns from retros

### Qualitative
- **Bidirectional learning**: Theory ↔ Practice
- **Validation loop**: Predictions → Outcomes → Refinement
- **Pattern library**: Proven operational solutions
- **Learning culture**: "Always extract value before cleanup"

## Trade-offs

### Option A: Automated Ollama Linking (2 hours, $0)
**Pros**: Fast, scalable, proven tech
**Cons**: 20% false positives, needs validation
**Best for**: Initial 30% coverage

### Option B: Manual Semantic Linking (4 hours, $0)
**Pros**: 100% accuracy, deeper insights
**Cons**: Slow, doesn't scale
**Best for**: CRITICAL/HIGH severity lessons

### Option C: Hybrid (3 hours, $0)
**Pros**: Balance speed + quality
**Cons**: More complex workflow
**Best for**: RECOMMENDED

**Recommended**: Option C
1. Ollama semantic search → candidates
2. Manual review → filter false positives
3. Batch application → proven pattern

## Success Metrics

**Phase 1** (2 weeks):
- [ ] 35+ lessons ↔ papers links
- [ ] 30% lessons coverage achieved
- [ ] 10+ lessons ↔ decisions links
- [ ] SurrealDB updated with new links

**Phase 2** (1 month):
- [ ] 5+ new patterns extracted from retrospectives
- [ ] Decision ↔ Lesson validation loop documented
- [ ] Compound engineering methodology updated

## Implementation Plan

### Week 1: Semantic Search Setup
1. Extract all lesson text + metadata
2. Run Ollama embedding on lessons
3. Compute similarity to papers (cosine >0.3)
4. Generate candidate links JSON

### Week 2: Validation + Application
1. Manual review of candidates (filter false positives)
2. Identify high-value cross-links (lessons ↔ decisions)
3. Batch apply wiki-links to vault
4. Update SurrealDB with new relationships

### Week 3: Pattern Extraction
1. Review retrospectives for reusable patterns
2. Extract 5+ operational patterns
3. Link patterns ↔ lessons ↔ decisions
4. Document compound engineering methodology v2

## Related Work

- [[2026-02-10-canvas-driven-compound-engineering-refined]] - Manual linking approach
- [[canvas-driven-manual-linking]] - Proven methodology
- [[2026-02-10-debug-log-bloat-analysis]] - Example rich lesson
- [[2026-02-10-claude-log-mining-architecture]] - Meta-learning process

## Decision

**Adopt 3-Layer Compound Engineering** with lessons as operational validation layer.

**Next Steps**:
1. Create `inbox/phase-lessons-compound-engineering.md` handoff
2. Schedule Ollama semantic search (2026-02-17)
3. Allocate 3 hours for Phase 1 execution

---

**Key Insight**: Operational lessons are the missing validation layer in compound engineering. They prove which theories work in practice and reveal anti-patterns theory misses.

## Related Patterns

- [[log-lifecycle-management]] — the log lifecycle pattern that operationalizes the forensic analysis approach decided here
- [[canvas-driven-manual-linking]] — the canvas-driven approach used to visually organize the operational lessons discovered

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
