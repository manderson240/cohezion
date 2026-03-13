---
title: SurrealDB Schema Design: Record-Centric Schema Outperforms Table-Centric for Agent Context
date: 2026-02-23
severity: HIGH
category: database
cost_of_forgetting: "60-70% higher query complexity from relational emulation; missed graph traversal capabilities"
tags: [surrealdb, schema-design, database, agent-context, graph]
status: validated
aspect: knower
neural:
  activation: 0.76
  stage: growing
  synapse_in: 8
  synapse_out: 7
---

# Lesson: SurrealDB Schema Design: Record-Centric Schema Outperforms Table-Centric for Agent Context

## Context

During Session 55 (February 2026), the Cohezion agent context schema was initially designed following relational database patterns because the team had extensive PostgreSQL experience. The schema used flat tables with foreign key columns to model relationships between sessions, tasks, artifacts, and observations. Queries required multi-table JOINs to traverse the agent context graph.

## Problem

The relational approach was a poor fit for SurrealDB's strengths:

1. **Complex queries**: A simple question like "What artifacts did session 47 produce?" required a 3-table JOIN with foreign key matching. In SurrealDB's native graph model, this is a single traversal: `SELECT ->contains->task->produced->artifact FROM session:s47`.
2. **Foreign key simulation**: SurrealDB has no foreign key constraint system like PostgreSQL. The team was manually maintaining referential integrity with columns like `session_id TEXT`, which was error-prone and provided no enforcement.
3. **Missed graph capabilities**: SurrealDB's `->` and `<-` graph traversal operators, `RELATE` for edge creation, and multi-hop queries were entirely unused. The team was using SurrealDB as a worse PostgreSQL.
4. **Query count explosion**: What should have been 1 query became 3-5 queries with intermediate result processing.

## Core Learning

**Design SurrealDB schemas around records as nodes and RELATE as edges. Avoid emulating relational schemas -- lean into the graph model.**

### Key Design Principles
```sql
-- Relational anti-pattern (avoid)
CREATE TABLE sessions;
CREATE TABLE tasks;
-- foreign key simulation with columns

-- SurrealDB native pattern
CREATE session:s47 SET name = "Session 47", started = time::now();
CREATE task:t001 SET description = "Implement auth";
RELATE session:s47 -> contains -> task:t001;

-- Querying with graph traversal (natural, efficient)
SELECT ->contains->task FROM session:s47;

-- Multi-hop traversal
SELECT ->contains->task->produced->artifact FROM session:s47;
```

## Solution

The schema was completely redesigned around SurrealDB's native capabilities:

1. **Records as nodes**: Every entity is a typed record with a semantic ID (e.g., `session:s47`, `task:auth-001`, `artifact:output-001`)
2. **RELATE as edges**: All relationships use `RELATE`, creating first-class edges that can carry metadata
3. **Graph traversal as queries**: Multi-hop queries replace multi-table JOINs
4. **FETCH for expansion**: Nested records are expanded with explicit FETCH clauses

The result: query complexity reduced 60-70%, query count reduced 3-5x, and the code became more readable because queries directly expressed the intent ("what did this session produce?") rather than the mechanics ("join sessions to tasks on session_id, then join tasks to artifacts on task_id").

## Prevention

- **Start with graph model**: When using SurrealDB, design the schema as a graph from day one
- **Use RELATE for all relationships**: Never model relationships with columns when RELATE is available
- **Read SurrealDB docs first**: Do not assume PostgreSQL patterns transfer (see [[lesson-05-surrealdb]])
- **Test queries early**: Write the queries you need before finalizing the schema; if they require JOINs, reconsider the schema

## Cost of Forgetting

- **60-70% more complex queries**: Relational emulation requires multiple queries where graph traversal needs one
- **Manual referential integrity**: Without RELATE, relationships are maintained by convention, not by the database
- **Missed SurrealDB value**: Using SurrealDB as a worse PostgreSQL wastes its graph-native strengths
- **Schema migration cost**: Switching from FK columns to RELATE later requires data migration

## Recommendations

### Do
- Model relationships as RELATE edges, not foreign key columns
- Use record IDs with semantic names: session:s47, task:auth-001
- Use FETCH in queries to expand nested records

### Don't
- Emulate SQL schemas in SurrealDB (missed opportunity)
- Build JOIN-style queries when graph traversal is available

## Related Concepts

- [[lesson-05-surrealdb]] - SurrealDB query patterns and syntax gotchas
- [[surrealdb]] - record-centric schema design is the foundational SurrealDB knowledge
- [[cloud-vault-mcp]] - the agent context graph in cloud-vault-mcp uses this schema design
- [[graph-databases]] - RELATE edges as graph connections outperform foreign key simulation
- [[schema-design-relational]] - contrast: relational schema design patterns that do not apply to SurrealDB
- [[knowledge-graph-systems]] - SurrealDB schema design directly supports knowledge graph construction
- [[graphrag-knowledge-graph-with-surrealdb]] - GraphRAG implementation builds on this schema design

## Validation

**Discovered**: Feb 2026 during agent context schema design (Session 55)
**Impact**: Query complexity reduced 60-70% after schema redesign
**Status**: Validated in production
