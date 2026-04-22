---
title: "Decision Phase 1 Surrealdb Agent Context"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.69
  stage: growing
  synapse_in: 2
  synapse_out: 7
---
## Definition

The Phase 1 SurrealDB Agent Context decision was an architectural decision record (ADR) that selected SurrealDB as the persistence layer for Cohezion's agent context graph and defined the scope of the first implementation phase. The decision chose SurrealDB over alternatives (PostgreSQL with graph extensions, Neo4j, pure file-based storage) because its multi-model capability (graph + document + vector) eliminated the need for multiple databases to serve the agent context use case.

## Key Properties

- **Single-database strategy**: SurrealDB serves graph traversal, document storage, and vector search in one system, avoiding operational complexity of multiple databases
- **Schema-first design**: Phase 1 began with schema definition before any application code, ensuring data model clarity
- **Record-centric over table-centric**: The decision favored SurrealDB's record-link model over traditional relational table joins, reducing query complexity by 60-70%
- **Local-first**: SurrealDB runs locally (`ws://localhost:8000`) with zero cloud dependency, matching Cohezion's local-first philosophy
- **MCP exposure**: Agent context queries are exposed via the Cloud Vault MCP server, making them accessible to Claude Code agents

## Examples

- Choosing RELATE edges (`RELATE session->produced->artifact`) over foreign key joins for agent-artifact relationships
- Defining typed record IDs that encode both table and identity in a single reference

## Related Papers

- [[2026-02-12-phase-2-schema-design]]
- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]]
- [[lesson-11-team-agent-efficiency]]

## Related Concepts

- [[surrealdb]] — the database selected by this decision
- [[phase-1-implementation]] — the implementation phase this decision scoped
- [[decision-vault-first-knowledge-architecture]] — the broader architecture decision that this builds upon
- [[knowledge-graph-systems]] — the graph paradigm this decision instantiates

## Relevance to Cohezion

This decision established SurrealDB as the backbone of Cohezion's agent memory system. The multi-model choice proved correct: subsequent phases leveraged graph traversal for session retrospectives, document storage for agent logs, and vector fields for semantic search, all without introducing additional database infrastructure.
