---
title: SurrealDB Query Patterns and Schema Design Gotchas
date: 2026-02-23
severity: MEDIUM
category: database
cost_of_forgetting: "Silent query failures and 60-70% higher query complexity from relational anti-patterns in a graph database"
tags: [surrealdb, database, schema, query-patterns]
status: validated
aspect: knower
neural:
  activation: 0.77
  stage: growing
  synapse_in: 10
  synapse_out: 8
---

# Lesson: SurrealDB Query Patterns and Schema Design Gotchas

## Context

During the Cohezion agent context schema design in February 2026, the team adopted SurrealDB as the graph database for agent context persistence. The initial schema followed familiar relational patterns (flat tables, foreign key columns, JOIN-style queries) since the developers had PostgreSQL and SQLite backgrounds. SurrealDB's SQL-like syntax made this approach feel natural, but it silently undermined the database's core strengths.

## Problem

SurrealDB's syntax similarity to SQL is a trap. Key divergences caused three categories of failures:

1. **Silent query failures**: Record IDs like `agent:session-47` are typed. Queries using string comparison (`WHERE session_id = "session-47"`) instead of record ID syntax (`WHERE id = agent:session-47`) returned empty results with no error.
2. **Missed graph capabilities**: Using foreign key columns for relationships instead of RELATE meant graph traversal operators (`->`, `<-`) could not be used. This forced complex multi-query patterns where a single traversal query would have sufficed.
3. **Lazy loading surprises**: SurrealDB returns record IDs by default for nested records. Without explicit FETCH clauses, queries returned opaque IDs instead of expanded objects, causing downstream parsing failures.

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

## Solution

The schema was redesigned around SurrealDB's native graph model:

- **Records as nodes**: Every entity (session, task, artifact, observation) is a typed record with a semantic ID
- **RELATE as edges**: All relationships use RELATE, enabling natural graph traversal
- **Explicit FETCH**: Every query that needs nested data includes FETCH clauses
- **Record ID consistency**: All code uses record ID syntax, never string comparison for identity

This redesign reduced query complexity by 60-70% (see [[lesson-surrealdb-schema-design]]).

## Prevention

- **Read SurrealDB docs before writing queries**: Do not assume SQL knowledge transfers -- check the SurrealQL reference first
- **Use RELATE from day one**: Never model relationships with foreign key columns in SurrealDB
- **Test queries on small datasets**: Verify query results before building application logic on top
- **Always include FETCH**: Default to FETCH for any query that returns nested records

## Cost of Forgetting

- **Silent query failures**: Queries return empty results instead of errors when using wrong ID syntax
- **60-70% more complex queries**: Relational emulation requires multiple queries where graph traversal needs one
- **Missed performance**: SurrealDB's graph engine optimizes traversal queries; relational patterns bypass this optimization
- **Schema migration cost**: Switching from FK columns to RELATE requires data migration, not just query changes

## Recommendations

### Do
- Use RELATE for all inter-record connections
- Fetch related records explicitly with FETCH clause
- Test queries on small datasets before production use

### Don't
- Use foreign key columns for relations (use RELATE instead)
- Assume SQL syntax transfers directly to SurrealDB

## Related Concepts

- [[surrealdb]] - this lesson contains the essential SurrealDB query patterns and syntax gotchas
- [[surrealdb-graph-databases]] - Reference paper for SurrealDB's graph-native data model and SurrealQL traversal syntax
- [[lesson-surrealdb-schema-design]] - Deeper dive: record-centric schema design outperforms relational emulation
- [[cloud-vault-mcp]] - the cloud-vault-mcp SurrealDB tools depend on these query patterns
- [[graph-databases]] - SurrealDB's graph traversal replaces SQL JOINs; RELATE creates edges
- [[agentic-ai]] - Agent context persistence relies on correct SurrealDB patterns
- [[knowledge-graph-systems]] - SurrealDB schema design directly informs knowledge graph query patterns
- [[graphrag-knowledge-graph-with-surrealdb]] - GraphRAG implementation depends on these query patterns for knowledge retrieval

## Validation

**Discovered**: Feb 2026 during agent context schema design
**Status**: Validated in production Cohezion pipeline
