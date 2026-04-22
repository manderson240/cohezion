---
title: "SurrealDB Agent Context - Quick Reference Card"
date: 2026-02-11
status: proposed
tags: [pattern, surrealdb, agent-context, cheatsheet, reference]
aspect: thinker
neural:
  activation: 0.79
  stage: mature
  synapse_in: 4
  synapse_out: 12
---

# Agent Context Schema - Quick Reference

One-page cheat sheet for the agent context schema.

---

## 5 Node Types (CRUD Summary)

| Node | Create | Read | Use Case |
|------|--------|------|----------|
| **agent_session** | `track_session(agent_id, goals)` | "Show all sessions" | Work boundary + resource tracking |
| **agent_decision** | `record_decision(session_id, type, reasoning, papers)` | "Which papers influenced D001?" | Architectural decisions |
| **agent_reasoning** | `record_reasoning(decision_id, chain_of_thought, assumptions)` | "How was D001 decided?" | Decision reasoning depth |
| **agent_context** | `track_context(session_id, concepts, domains, goals)` | "What was agent thinking at T?" | Agent state snapshots |
| **agent_outcome** | `record_outcome(session_id, lessons, metrics)` | "What did agent learn?" | Session closure + learnings |

---

## 8 Edge Types (Query Reference)

| Edge | From → To | Query Example | Answer |
|------|-----------|---------------|--------|
| **APPLIED_RESEARCH** | decision → paper | `SELECT ->APPLIED_RESEARCH->paper` | Which papers influenced this? |
| **VALIDATES_LESSON** | outcome → lesson | `SELECT ->VALIDATES_LESSON->lesson` | Did this validate lessons? |
| **CHALLENGES_LESSON** | reasoning → lesson | `SELECT ->CHALLENGES_LESSON->lesson` | Does reasoning contradict lessons? |
| **INFLUENCED_BY_CONCEPT** | decision → concept | `SELECT ->INFLUENCED_BY_CONCEPT->concept` | Which concepts were applied? |
| **IMPLEMENTS_PATTERN** | decision → pattern | `SELECT ->IMPLEMENTS_PATTERN->pattern` | Did this follow patterns? |
| **RELATES_TO_DECISION** | decision → decision | `SELECT ->RELATES_TO_DECISION->decision` | How did decisions cascade? |
| **EXPLORES_DOMAIN** | context → domain | `SELECT ->EXPLORES_DOMAIN->domain` | Which domains focused on? |
| **INFORMS_AGENT** | reasoning → context | `SELECT ->INFORMS_AGENT->context` | What shaped agent state? |

---

## Core Metrics

```python
# Token efficiency (Haiku vs Sonnet)
token_efficiency_ratio = output_value / total_tokens

# Decision quality
decision_validation_rate = validated_decisions / total_decisions

# Research alignment
research_alignment_score = avg(APPLIED_RESEARCH.relevance_score)

# Learning capture
lesson_integration_score = lessons_validated / available_lessons

# Breadth vs depth
domain_exploration_entropy = Shannon_entropy(domain_distribution)
```

---

## 5 Most Important Queries

### 1. Research Lineage
```sql
SELECT agent_decision, ->APPLIED_RESEARCH->paper
WHERE session_id = $s
ORDER BY ->APPLIED_RESEARCH.relevance_score DESC
-- Answer: "Which papers influenced decisions?"
```

### 2. Lesson Validation
```sql
SELECT agent_outcome, ->VALIDATES_LESSON->lesson
WHERE session_id = $s
ORDER BY ->VALIDATES_LESSON.alignment_score DESC
-- Answer: "What lessons did agent validate?"
```

### 3. Misalignment Detection
```sql
SELECT agent_reasoning, ->CHALLENGES_LESSON->lesson
WHERE decision_id->session_id = $s
  AND ->CHALLENGES_LESSON.challenge_type = "contradicts"
-- Answer: "Where is reasoning misaligned?"
```

### 4. Decision Cascade
```sql
SELECT agent_decision,
  <-RELATES_TO_DECISION<-agent_decision,
  ->RELATES_TO_DECISION->agent_decision
WHERE session_id = $s
ORDER BY timestamp ASC
-- Answer: "How did decisions block/enable/refine?"
```

### 5. Session Metrics
```sql
SELECT session.*,
  COUNT(<-RELATES_TO_DECISION<-agent_decision),
  AVG(<-RELATES_TO_DECISION<-agent_decision->confidence_score),
  <-RELATES_TO_DECISION<-agent_outcome.metrics
WHERE id = $session_id
-- Answer: "Overall session success + efficiency?"
```

---

## Node Field Summary

**agent_session**
```
├─ id, agent_id, start_time, end_time
├─ model_used, total_tokens, cost_usd
├─ phase, status, goals, outcome_summary
```

**agent_decision**
```
├─ id, session_id (→), timestamp
├─ decision_type, reasoning, confidence_score
├─ validation_status, implementation_status, metadata
```

**agent_reasoning**
```
├─ id, decision_id (→), timestamp
├─ reasoning_type, chain_of_thought
├─ source_notes (array), assumptions (array)
```

**agent_context**
```
├─ id, session_id (→), timestamp
├─ active_concepts, active_domains, current_goals
├─ token_budget_remaining, decision_history (array)
├─ relevance_snapshot (12D coordinates)
```

**agent_outcome**
```
├─ id, session_id (→), timestamp
├─ outcome_type, metrics (object)
├─ lessons_learned (array), validated_by, next_recommendations (array)
```

---

## MCP Tools (Once Implemented)

```python
# Session tracking
track_session(agent_id, goals) → session_id
track_context(session_id, concepts, domains, goals) → context_id

# Decision recording
record_decision(session_id, type, reasoning, papers, confidence) → decision_id
record_reasoning(decision_id, chain_of_thought, assumptions) → reasoning_id

# Outcome closure
record_outcome(session_id, lessons, metrics) → outcome_id
```

---

## 4-Phase Rollout Timeline

**Phase 1** (2-3d): `agent_session` + `agent_decision` + `APPLIED_RESEARCH` + `VALIDATES_LESSON`
→ "Which papers influenced this decision?"

**Phase 2** (1d): `agent_reasoning` + `CHALLENGES_LESSON` + decision cascades
→ "Where is agent misaligned with research?"

**Phase 3** (1d): `agent_context` snapshots + `relevance_snapshot`
→ "What was agent thinking at time T?"

**Phase 4** (2d): Full `agent_outcome` + metrics + 12D integration
→ Complete strategic learning framework

---

## Key Insights

1. **Research Lineage**: Every decision traced to papers
2. **Lesson Loop**: Agent work validates vault knowledge
3. **Misalignment Alerts**: Reasoning flagged against research
4. **Decision Deps**: Cascading effects captured
5. **Agent Affinity**: Feeds 12D graph Dimension 12

---

## Performance Tips

- Use relationships for traversal (faster than multiple SELECTs)
- Add LIMIT for large results
- GROUP BY before returning metrics
- CACHE dimension snapshots
- BATCH update relevance scores

---

## Related

- **Full spec**: `patterns/surrealdb-agent-context-schema.md`
- **Visual guide**: `patterns/surrealdb-agent-context-visual-guide.md`
- **Decision**: `decisions/2026-02-11-surrealdb-agent-context-schema-design.md`

## Related

- [[surrealdb-agent-context-visual-guide]]
- [[surrealdb-agent-context-phase1-implementation-checklist]]
- [[surrealdb-agent-context-schema]]
- [[2026-02-11-surrealdb-agent-context-schema-design]]

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
