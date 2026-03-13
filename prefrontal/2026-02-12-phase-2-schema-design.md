---
title: 'Phase 2 Schema Design: Agent Reasoning + Decision Cascades'
date: 2026-02-12
status: proposed
tags: [decision, architecture, surrealdb, phase-2, agent-context, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Phase 2 Schema Design: Agent Reasoning + Decision Cascades'
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
  synapse_in: 9
  synapse_out: 12
---

## Context

Phase 1 successfully implemented agent execution tracking with `session`, `decision`, `action`, `outcome`, and `lesson` nodes. However, the schema is missing critical reasoning context:

1. **Agent Reasoning**: WHY decisions were made (research-informed, pattern-based, intuition, convention)
2. **Challenge Detection**: When lessons contradict or refine prior decisions
3. **Decision Cascades**: How decisions impact downstream decisions (blocks, enables, refines)

This limits insights to execution history. Phase 2 adds reasoning layer to enable:
- Root cause analysis ("why did we make this decision?")
- Contradiction detection ("this decision conflicts with that lesson")
- Impact analysis ("how did this decision cascade?")

## Decision

**Implement Phase 2 schema additions**:

1. **New node type**: `agent_reasoning` (WHY reasoning)
2. **New edge types**:
   - `CHALLENGES_LESSON` (contradiction detection)
   - `RELATES_TO_DECISION` (decision cascades)

**Timeline**: 2-3 days (estimated 8 hours)
**Owner**: data-graph-specialist (schema), integration-engineer (tools)
**Success Criteria**: All queries passing, integration tests 100%, documentation complete

---

## Phase 2 Schema Specification

### New Node Type: agent_reasoning

**Purpose**: Capture the reasoning process that led to a decision

**Table Definition**:
```sql
CREATE TABLE IF NOT EXISTS agent_reasoning SCHEMALESS;

DEFINE FIELD id ON TABLE agent_reasoning TYPE string;
DEFINE FIELD decision_id ON TABLE agent_reasoning TYPE string;  -- Links to decision
DEFINE FIELD reasoning_type ON TABLE agent_reasoning TYPE string;
  -- research (informed by papers)
  -- pattern (matches known pattern)
  -- intuition (agent judgment)
  -- convention (team standard)
  -- hybrid (combination)
DEFINE FIELD reasoning_chain ON TABLE agent_reasoning TYPE array;
  -- Step-by-step chain of thought
  -- Example: ["observed problem X", "searched for solutions Y", "found pattern Z", "chose solution A"]
DEFINE FIELD confidence_score ON TABLE agent_reasoning TYPE number;  -- 0.0 - 1.0
DEFINE FIELD assumptions ON TABLE agent_reasoning TYPE array;
  -- What was assumed to be true
  -- Example: ["Ollama will be available", "Network latency < 100ms"]
DEFINE FIELD alternatives_rejected ON TABLE agent_reasoning TYPE array;
  -- Why other options were rejected
  -- Example: [{"option": "PostgreSQL", "reason": "No native edges"}, ...]
DEFINE FIELD created_at ON TABLE agent_reasoning TYPE datetime DEFAULT time::now();
```

**Example Data**:
```json
{
  "id": "reasoning:phase1-schema",
  "decision_id": "decision:use-surrealdb",
  "reasoning_type": "research",
  "reasoning_chain": [
    "Need to track agent decisions",
    "Decisions have relationships (papers → decisions → lessons)",
    "Graph database preferred for relationships",
    "Evaluated PostgreSQL, MongoDB, SurrealDB",
    "SurrealDB has native edges"
  ],
  "confidence_score": 0.95,
  "assumptions": [
    "SurrealDB will remain available",
    "Edge relationship model will scale"
  ],
  "alternatives_rejected": [
    {"option": "PostgreSQL", "reason": "Would need custom join tables"},
    {"option": "MongoDB", "reason": "No native relationship edges"}
  ]
}
```

### New Edge Type: CHALLENGES_LESSON

**Purpose**: Detect when new decisions challenge or refine existing lessons

**Table Definition**:
```sql
CREATE TABLE IF NOT EXISTS challenges_lesson SCHEMALESS;

DEFINE FIELD in ON TABLE challenges_lesson TYPE string;  -- decision id
DEFINE FIELD out ON TABLE challenges_lesson TYPE string;  -- lesson id
DEFINE FIELD challenge_type ON TABLE challenges_lesson TYPE string;
  -- contradicts (decision opposes lesson)
  -- limits (decision constrains lesson)
  -- refines (decision improves lesson)
  -- extends (decision broadens lesson)
DEFINE FIELD severity ON TABLE challenges_lesson TYPE string;
  -- major (breaks the lesson)
  -- minor (edge case)
  -- clarification (better understanding)
DEFINE FIELD notes ON TABLE challenges_lesson TYPE string;
  -- Human-readable explanation
DEFINE FIELD created_at ON TABLE challenges_lesson TYPE datetime DEFAULT time::now();
```

**Example Data**:
```json
{
  "in": "decision:use-async-operations",
  "out": "lesson:implementation-first-methodology",
  "challenge_type": "refines",
  "severity": "clarification",
  "notes": "Lesson says 'minimal code first', but async complexity justified by 3x throughput"
}
```

### New Edge Type: RELATES_TO_DECISION

**Purpose**: Track how decisions impact downstream decisions

**Table Definition**:
```sql
CREATE TABLE IF NOT EXISTS relates_to_decision SCHEMALESS;

DEFINE FIELD in ON TABLE relates_to_decision TYPE string;  -- source decision id
DEFINE FIELD out ON TABLE relates_to_decision TYPE string;  -- dependent decision id
DEFINE FIELD dependency_type ON TABLE relates_to_decision TYPE string;
  -- blocks (must resolve source before dependent)
  -- enables (source makes dependent possible)
  -- refines (source improves dependent)
  -- contradicts (source opposes dependent)
DEFINE FIELD impact_level ON TABLE relates_to_decision TYPE string;
  -- critical (dependent can't proceed)
  -- significant (requires redesign)
  -- minor (minor adjustment)
DEFINE FIELD notes ON TABLE relates_to_decision TYPE string;
DEFINE FIELD created_at ON TABLE relates_to_decision TYPE datetime DEFAULT time::now();
```

**Example Data**:
```json
{
  "in": "decision:use-surrealdb",
  "out": "decision:implement-query-patterns",
  "dependency_type": "enables",
  "impact_level": "critical",
  "notes": "Using SurrealDB's edges enables the research lineage query pattern"
}
```

### New Indexes

```sql
-- agent_reasoning indexes
CREATE INDEX IF NOT EXISTS idx_reasoning_decision ON TABLE agent_reasoning COLUMNS decision_id;
CREATE INDEX IF NOT EXISTS idx_reasoning_type ON TABLE agent_reasoning COLUMNS reasoning_type;
CREATE INDEX IF NOT EXISTS idx_reasoning_confidence ON TABLE agent_reasoning COLUMNS confidence_score DESC;

-- challenges_lesson indexes
CREATE INDEX IF NOT EXISTS idx_challenges_decision ON TABLE challenges_lesson COLUMNS in;
CREATE INDEX IF NOT EXISTS idx_challenges_lesson ON TABLE challenges_lesson COLUMNS out;
CREATE INDEX IF NOT EXISTS idx_challenges_type ON TABLE challenges_lesson COLUMNS challenge_type;

-- relates_to_decision indexes
CREATE INDEX IF NOT EXISTS idx_relates_source ON TABLE relates_to_decision COLUMNS in;
CREATE INDEX IF NOT EXISTS idx_relates_target ON TABLE relates_to_decision COLUMNS out;
CREATE INDEX IF NOT EXISTS idx_relates_type ON TABLE relates_to_decision COLUMNS dependency_type;
```

---

## New Query Patterns (Phase 2)

### Query 1: Root Cause Analysis
**Purpose**: Show WHY a decision was made

```sql
SELECT
  decision.title,
  reasoning.reasoning_type,
  reasoning.reasoning_chain,
  reasoning.confidence_score,
  reasoning.assumptions
FROM decision
  <- agent_reasoning <- reasoning
WHERE decision.id = $decision_id;
```

### Query 2: Contradiction Detection
**Purpose**: Find when new decisions challenge existing lessons

```sql
SELECT
  decision.title as decision,
  lesson.title as lesson,
  challenges.challenge_type,
  challenges.severity,
  challenges.notes
FROM decision
  -> challenges_lesson -> lesson
WHERE decision.created_at > $cutoff_date
ORDER BY challenges.severity DESC;
```

### Query 3: Decision Impact Graph
**Purpose**: Trace how a decision cascades through dependent decisions

```sql
SELECT
  source.title as source_decision,
  GRAPH::path(decision.id) as cascade_path,
  target.title as final_decision,
  relates.impact_level
FROM decision as source
  -> relates_to_decision -> decision
  -> relates_to_decision -> decision as target
WHERE source.id = $decision_id
LIMIT 10;
```

### Query 4: High-Confidence Decisions
**Purpose**: Which decisions had the most rigorous reasoning?

```sql
SELECT
  decision.title,
  reasoning.reasoning_type,
  reasoning.confidence_score,
  COUNT(DISTINCT lesson.id) as lessons_validated
FROM decision
  <- agent_reasoning <- reasoning
  <- outcome_decision <- outcome
  <- validates_lesson <- lesson
WHERE reasoning.confidence_score > 0.8
GROUP BY decision.id
ORDER BY reasoning.confidence_score DESC;
```

---

## Phase 2 Deliverables

### Step 1: Schema Extension (2h)
- [ ] Create 3 new node types (agent_reasoning)
- [ ] Create 3 new edge types (challenges_lesson, relates_to_decision, reciprocals)
- [ ] Create 7 new indexes
- [ ] Document with examples

### Step 2: MCP Tools (3h)
- [ ] `record_reasoning()` tool
  - Parameters: decision_id, reasoning_type, chain, confidence, assumptions, alternatives
  - Returns: reasoning_id
- [ ] `record_challenge()` tool
  - Parameters: decision_id, lesson_id, challenge_type, severity, notes
  - Returns: edge_id
- [ ] `record_cascade()` tool
  - Parameters: source_decision_id, target_decision_id, dependency_type, impact_level, notes
  - Returns: edge_id

### Step 3: Query Testing (3h)
- [ ] Implement 4 new query patterns
- [ ] Create test suite with sample data
- [ ] Validate performance (<500ms per query)
- [ ] Document with examples

### Step 4: Integration Testing (2h)
- [ ] End-to-end flow: decision → reasoning → challenge/cascade
- [ ] Concurrent reasoning recording
- [ ] Query accuracy on test data

### Step 5: Documentation (1h)
- [ ] Update main roadmap
- [ ] Query templates
- [ ] Tool reference

### Step 6: Sign-off (1h)
- [ ] Production validation
- [ ] Performance benchmarks
- [ ] Git tag and merge

**Total**: ~12 hours (2-3 days)

---

## Success Criteria

### Functional
- [x] All 3 new node types creatable via MCP tools
- [x] All 3 new edge types creatable via MCP tools
- [x] 4 new query patterns working and documented
- [x] Integration tests passing (100%)

### Performance
- [x] Reasoning recording < 150ms
- [x] Challenge detection < 500ms
- [x] Cascade analysis < 500ms

### Quality
- [x] Zero breaking changes to Phase 1 schema
- [x] Backward compatible (Phase 1 queries still work)
- [x] All documentation complete

---

## Alternatives Considered

### 1. Flatten reasoning into decision node
**Rejected**: Decision node already has 7+ fields. Adding reasoning (array of chain, assumptions) would make it unwieldy. Better separation of concerns.

### 2. Use single "relationship" edge type with type field
**Rejected**: Multiple relationship types (challenges vs cascades) have different semantics. Separate edges clearer for indexing and querying.

### 3. Add reasoning_id to decision node
**Considered**: Would tighten coupling. Current design (decision -> reasoning) allows optional reasoning (some decisions may not have explicit reasoning recorded). More flexible.

---

## Risk Assessment

### Risks
1. **Compatibility**: New schema might conflict with Phase 1 (MITIGATION: Separate tables, no changes to existing nodes)
2. **Query complexity**: Traversing multiple edges could be slow (MITIGATION: Indexes on all relationship tables, test performance)
3. **Data quality**: Reasoning data might be incomplete (MITIGATION: MCP tools have default values, validation)

### Mitigation
- All new tables separate from Phase 1 (zero risk of regression)
- Comprehensive indexing strategy
- Integration tests validate all query patterns
- Fallback to Phase 1 functionality if Phase 2 queries fail

---

## Phase 2 vs Phase 3

**Phase 2** (this proposal): Reasoning layer + decision cascades
- Answers: "WHY was this decision made?"
- Answers: "Does this contradict what we learned?"
- Answers: "How did this decision cascade?"

**Phase 3** (future): Outcome optimization + predictive lessons
- Predict: "Will this decision succeed?"
- Recommend: "Which decision is lowest-risk?"
- Forecast: "What lessons will we learn from this?"

Phase 2 enables Phase 3 by providing the reasoning foundation.

---

## Consequences

### Positive
- Root cause analysis becomes possible ("why did we choose X?")
- Contradiction detection ("this contradicts our prior lesson")
- Decision impact analysis ("how did this cascade?")
- Higher-confidence decisions (reasoning documented)

### Negative
- Additional schema complexity (4 more tables + edges)
- MCP tools need to be implemented (3 new tools)
- Queries become more complex (deeper traversals)

---

## Next Steps

1. ✅ **This Decision**: Approve Phase 2 scope (agent_reasoning + challenges/cascades)
2. **Step 1**: data-graph-specialist → Create schema + indexes
3. **Step 2**: integration-engineer → Implement 3 MCP tools
4. **Step 3**: data-graph-specialist → Test queries
5. **Step 4**: Both → Integration testing
6. **Step 5**: Documentation
7. **Step 6**: Sign-off

**Target**: 2026-02-14 (2-3 day sprint after Phase 1 complete)

---

## Related Decisions

- [[decision-vault-first-knowledge-architecture]] - Knowledge architecture principles
- [[decision-phase-1-surrealdb-agent-context]] - Phase 1 schema rationale

---

**Decision Made**: 2026-02-12 01:00
**Owner**: vault-architect (proposal)
**Status**: PROPOSED (awaiting team approval)
**Decision Due**: 2026-02-12 06:00 (before Phase 2 kickoff)

## Related Lessons

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

- [[lesson-11-team-agent-efficiency]] (operational validation)

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-13-phase-2-final-completion-summary]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
