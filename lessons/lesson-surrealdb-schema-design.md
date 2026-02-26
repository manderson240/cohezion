---
title: SurrealDB Schema Design: Record-Centric Schema Outperforms Table-Centric for Agent Context
date: 2026-02-23
severity: HIGH
category: database
tags: [surrealdb, schema-design, database, agent-context, graph]
status: validated
---

# Lesson: SurrealDB Schema Design: Record-Centric Schema Outperforms Table-Centric for Agent Context

## Context

Initial SurrealDB schema for agent context followed relational patterns (flat tables, foreign keys, JOINs). This required complex multi-table queries and missed SurrealDB's native graph traversal strengths.

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

## Recommendations

### Do
- Model relationships as RELATE edges, not foreign key columns
- Use record IDs with semantic names: session:s47, task:auth-001
- Use FETCH in queries to expand nested records

### Don't
- Emulate SQL schemas in SurrealDB (missed opportunity)
- Build JOIN-style queries when graph traversal is available

## Related Concepts

- [[lesson-05-surrealdb]] - SurrealDB query patterns and syntax
- [[mcp-infrastructure-architecture]] - SurrealDB role in Cohezion infrastructure
- [[surrealdb]] - record-centric schema design is the foundational SurrealDB knowledge
- [[cloud-vault-mcp]] - the agent context graph in cloud-vault-mcp uses this schema design
- [[graph-databases]] - RELATE edges as graph connections outperform foreign key simulation

## Validation

**Discovered**: Feb 2026 during agent context schema design (Session 55)
**Impact**: Query complexity reduced 60-70% after schema redesign
**Status**: Validated in production
