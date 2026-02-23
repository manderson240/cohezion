---
title: SurrealDB Query Patterns and Schema Design Gotchas
date: 2026-02-23
severity: MEDIUM
category: database
tags: [surrealdb, database, schema, query-patterns]
status: validated
---

# Lesson: SurrealDB Query Patterns and Schema Design Gotchas

## Context

SurrealDB uses a SQL-like syntax with significant differences from PostgreSQL and SQLite. Schema design decisions have non-obvious consequences for query performance and correctness.

## Core Learning

**SurrealDB record IDs are first-class -- design schemas around them. Use RELATE for graph edges, not foreign key columns.**

### Why This Matters
- SurrealDB query syntax diverges from SQL in ways that cause silent failures
- Record IDs like agent:session-47 are typed and must match at query time
- Graph traversal (-> and <-) replaces JOINs -- don't emulate SQL patterns
- FETCH is required to expand nested records (lazy loading by default)

### Pattern
```sql
-- Create typed records
CREATE agent:session-47 SET name = "Session 47", created = time::now();

-- Create a relation (graph edge)
RELATE agent:session-47 -> produced -> artifact:output-001;

-- Query with graph traversal
SELECT ->produced->artifact FROM agent:session-47 FETCH artifact;
```

## Recommendations

### Do
- Use RELATE for all inter-record connections
- Fetch related records explicitly with FETCH clause
- Test queries on small datasets before production use

### Don't
- Use foreign key columns for relations (use RELATE instead)
- Assume SQL syntax transfers directly to SurrealDB

## Related Concepts

- [[mcp-infrastructure-architecture]] - SurrealDB is core to the Cohezion context graph
- [[agentic-ai]] - Agent context persistence relies on correct SurrealDB patterns

## Validation

**Discovered**: Feb 2026 during agent context schema design
**Status**: Validated in production Cohezion pipeline
