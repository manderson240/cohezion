---
title: SurrealDB Agent Context Schema Design Decision
date: 2026-02-11
status: proposed
tags: [decision, architecture, surrealdb, agent-context, knowledge-graph, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: SurrealDB Agent Context Schema Design Decision'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 11
  synapse_out: 18
---

# SurrealDB Agent Context Schema Design

## Status
**Proposed** - Design complete, awaiting Phase 1 implementation approval

## Context

The Cohezion vault currently contains:
- **84 research papers** with 79% concept wiki-links
- **21 core concepts** with primary sources
- **38 lessons** (2 CRITICAL, 7 HIGH, 29 MEDIUM)
- **12D graph** in development (8/12 dimensions complete)
- **SurrealDB** instance at http://localhost:8000 with 148 relationships

**Problem**: Agent work (design decisions, implementations, validations) exists outside the knowledge graph. We cannot answer:
- Which research papers influenced a specific architectural decision?
- Did an agent's work validate or challenge existing lessons?
- Where is agent reasoning misaligned with established research?
- How did architectural decisions cascade or block each other?
- How should agent context feed into Dimension 12 (Agent Affinity) of the 12D graph?

## Decision

Implement a comprehensive agent context schema in SurrealDB with:

### 1. Five Node Types
| Node | Purpose | Rationale |
|------|---------|-----------|
| **agent_session** | Wrapper for entire agent task (start/end, model, tokens, cost) | Enables resource tracking + efficiency metrics |
| **agent_decision** | Architectural/feature/refactor decision with reasoning | Captures "why" for every decision |
| **agent_reasoning** | HOW decision was made (research vs intuition vs pattern) | Enables misalignment detection |
| **agent_context** | Agent state at point in time (active concepts, domains, goals) | Enables "what was agent thinking" queries |
| **agent_outcome** | Closure node - learnings + validation + metrics | Completes feedback loop |

### 2. Eight Relationship Types
| Edge | Connects | Purpose |
|------|----------|---------|
| **APPLIED_RESEARCH** | decision → paper | Research lineage: which papers influenced decision |
| **VALIDATES_LESSON** | outcome → lesson | Lesson validation: agent's work confirms/refutes/refines lessons |
| **CHALLENGES_LESSON** | reasoning → lesson | Misalignment detection: reasoning contradicts research |
| **INFLUENCED_BY_CONCEPT** | decision → concept | Concept application: cross-cutting concepts used in decision |
| **IMPLEMENTS_PATTERN** | decision → pattern | Pattern reuse: decision follows established patterns |
| **RELATES_TO_DECISION** | decision → decision | Decision cascade: how decisions block/enable/refine each other |
| **EXPLORES_DOMAIN** | context → domain | Domain focus: which research areas agent prioritized |
| **INFORMS_AGENT** | reasoning → context | Context shaping: what information influenced agent state |

### 3. Implementation Approach
- **Phase 1** (2-3 days): agent_session + agent_decision + APPLIED_RESEARCH + VALIDATES_LESSON
  - Unlocks research lineage tracking
  - Low-risk MVP validates approach
- **Phase 2** (1 day): agent_reasoning + CHALLENGES_LESSON + decision cascades
  - Detects misalignment with research
- **Phase 3** (1 day): agent_context snapshots + relevance snapshots
  - Enables retrospective analysis
- **Phase 4** (2 days): agent_outcome + metrics + 12D integration
  - Full strategic learning capabilities

## Consequences

### Positive
1. **Research Lineage**: Every architectural decision traced to papers/concepts that influenced it
   - Enables audit trail for decision quality
   - Validates that agent work is evidence-based

2. **Lesson Validation**: Agent outcomes automatically validate or challenge vault lessons
   - Creates feedback loop: vault lessons → agent decisions → lessons refined
   - Surfaces which lessons are most/least validated by practice

3. **Misalignment Detection**: Query layer can flag reasoning that contradicts research
   - Early warning for systemic biases in agent decision-making
   - Guides training/refinement

4. **Decision Dependencies**: Capture cascading effects of architectural choices
   - Understand which decisions block/enable/refine others
   - Retrospective learning from decision sequences

5. **12D Graph Integration**: Agent context feeds Dimension 12 (Agent Affinity)
   - Visualization shows papers relevant to agent's current goals
   - Dynamic graph based on agent state

### Negative
1. **Explicit Tracking Required**: Agent code must actively record decisions, reasoning, outcomes
   - Requires discipline + tool support
   - Incomplete tracking = incomplete lineage

2. **Reasoning Capture Overhead**: Explicit chain-of-thought increases token usage
   - Phase 2 will add ~10-20% to agent token budget
   - Mitigated by Haiku's lower cost

3. **SurrealDB Query Complexity**: Graph queries can be complex for analysis
   - Requires SurrealQL expertise
   - Mitigated by query templates + MCP tools

4. **Maintenance Burden**: Schema evolution if new decision types discovered
   - Foreseeable (new decision_type enum values)
   - Backward-compatible schema design mitigates

### Trade-offs

**Option A** (Selected): Full agent context schema (5 node types, 8 edges)
- **Pro**: Complete lineage + strategic learning
- **Pro**: Integrates with existing 12D graph
- **Con**: Higher implementation complexity
- **Con**: Requires explicit agent instrumentation

**Option B** (Alternative): Minimal decision-only schema (1 node type: agent_decision, 1 edge: APPLIED_RESEARCH)
- **Pro**: Simpler, faster implementation
- **Pro**: Answers "which papers influenced this decision"
- **Con**: Misses lesson validation, reasoning depth, cascade analysis
- **Con**: Can't detect misalignment

**Option C** (Alternative): No schema - use vault notes only
- **Pro**: Zero implementation cost
- **Con**: Not queryable, no structured analysis
- **Con**: Misses integration with 12D graph

**Decision**: Select Option A (full schema)
- Research lineage is table-stakes requirement
- Lesson validation closes feedback loop (critical for Cohezion's compound engineering vision)
- Misalignment detection enables systematic improvement
- Phased implementation reduces risk

## Alternatives Considered

### 1. GraphQL API vs SurrealQL
- **Decision**: Use SurrealQL (native to SurrealDB)
- **Rationale**: Simpler queries, no extra layer, better graph performance

### 2. Real-time Subscriptions vs Polling
- **Decision**: Use SurrealDB's native LIVE queries
- **Rationale**: Real-time graph updates without polling overhead

### 3. Embeddings for Similarity vs Keyword Matching
- **Decision**: Hybrid - use existing embeddings from Ollama MCP for semantic similarity
- **Rationale**: Already have local embedding capability, no API cost

### 4. Agent Tracking at MCP Level vs Application Level
- **Decision**: MCP level (Cloud Vault MCP tools)
- **Rationale**: Centralized, reusable across all agents, consistent recording

## Success Criteria

1. **Phase 1 Complete** (✓ Design, ⏳ Implementation)
   - [ ] agent_session + agent_decision nodes created
   - [ ] APPLIED_RESEARCH edges populated with >= 80% of decisions
   - [ ] Research lineage queries functional
   - [ ] Query: "Which papers influenced this decision?" returns ranked results

2. **Phase 2 Complete** (⏳ Implementation)
   - [ ] agent_reasoning nodes capture chain-of-thought
   - [ ] CHALLENGES_LESSON edges identify misalignment
   - [ ] Query: "Where is agent reasoning misaligned?" returns contradictions

3. **Phase 3 Complete** (⏳ Implementation)
   - [ ] agent_context snapshots track state over time
   - [ ] Retrospective analysis possible: "what was agent thinking at time T?"

4. **Phase 4 Complete** (⏳ Implementation)
   - [ ] agent_outcome validates lessons
   - [ ] Dimension 12 (Agent Affinity) integrated into 12D graph
   - [ ] Strategic questions answerable

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Agents don't record decisions consistently | High | Medium | Tool support + templates + examples |
| SurrealDB queries become bottleneck | High | Low | Index optimization + caching + pagination |
| Schema requires frequent changes | Medium | Low | Design for extensibility (enums, metadata objects) |
| Token cost for reasoning capture | Medium | Low | Phase 2 can be optional, Haiku mitigates cost |
| Lesson validation conflicts with research | Low | Low | Handle via validation_type ("contradicts", "refines") |

## Implementation Plan

### Phase 1: Core Lineage (Target: 2026-02-13)
```
Week 1: Design + Core Nodes
  ├── Define agent_session + agent_decision schema
  ├── Define APPLIED_RESEARCH + VALIDATES_LESSON edges
  ├── Create SurrealDB tables + indexes
  ├── Implement MCP tools: track_session(), record_decision(), record_outcome()
  └── Add 5 test sessions with decisions

Week 1: Validation
  ├── Query: research papers influencing decisions
  ├── Query: lessons validated by sessions
  ├── Verify relationship integrity
  └── Prepare Phase 2 design
```

### Phase 2: Reasoning Depth (Target: 2026-02-14)
- agent_reasoning + CHALLENGES_LESSON
- Chain-of-thought capture
- Misalignment detection queries

### Phase 3: Context Snapshots (Target: 2026-02-15)
- agent_context + snapshot tracking
- Retrospective analysis queries

### Phase 4: Advanced Integration (Target: 2026-02-17)
- agent_outcome full implementation
- Metrics computation
- 12D graph integration

## Next Steps

### Immediate (This Session)
1. ✅ Design complete (this document)
2. ✅ Pattern documented (`patterns/surrealdb-agent-context-schema.md`)
3. ⏳ Review + approval from team lead
4. ⏳ Begin Phase 1 implementation

### Short-term (This Week)
- Implement Phase 1 (agent_session + agent_decision)
- Create MCP tools for session/decision tracking
- Validate research lineage queries

### Medium-term (Next Week)
- Implement Phases 2-4
- Integrate with 12D graph
- Create visualization dashboards

## Related Decisions

- **2026-02-09-12d-graph-surrealdb-integration**: Parent decision for 12D graph architecture
- **2026-02-11-adopt-graphrag-for-vault-knowledge-graph**: Alternative approach being evaluated
- **2026-02-10-compound-engineering-meta-learning**: Strategic vision for continuous learning

## References

- Pattern: `patterns/surrealdb-agent-context-schema.md`
- SurrealDB Docs: https://surrealdb.com/docs
- Query Examples: See pattern document Section 3
- Metrics Definition: See pattern document Section 4

---

## Approval

**Status**: Awaiting team lead review + Phase 1 implementation approval

**Questions for Approval**:
1. Does the 5 node type + 8 edge type schema align with strategic vision?
2. Is Phase 1 (research lineage only) the right MVP?
3. Should we prioritize Phase 2 (misalignment detection) or Phase 4 (12D integration) first?
4. Who should validate agent outcomes (human vs automated)?

**Domains**: architecture, data, infrastructure, knowledge-management

**Categories**: strategic, technical

---

**Author**: Data Graph Specialist
**Date**: 2026-02-11
**Status**: Proposed

[[surrealdb]], [[knowledge-graph-systems]], [[agent-context]], [[12d-graph-implementation]]

## Related Lessons

- [[lesson-31-operation-specific-modulation]] (operational validation)

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

- [[lesson-11-team-agent-efficiency]] (operational validation)

## Related Concepts

- [[surrealdb-agent-context-schema]] — the pattern that implements this schema design decision
- [[agent-context]] — the concept note defining the agent context data this schema stores
- [[graph-databases]] — graph database concepts that inform the schema's node-edge model
- [[surrealdb-graph-databases]] — the SurrealDB graph database paper providing the backend capabilities
- [[3d-graph-plugin-selection]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
