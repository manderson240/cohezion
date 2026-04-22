---
title: "Surrealdb"
date: 2026-02-19
tags: [concept, graph-databases, knowledge-graph-systems, agent-context]
related_concepts: [graphrag-knowledge-graph-with-surrealdb, knowledge-graph-systems, cloud-vault-mcp, agent-context, semantic-search]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 0
  synapse_out: 36
---
## Definition

SurrealDB is a multi-model database that combines graph database capabilities, document storage, relational queries, and vector fields in a single system accessed through SurrealQL — a SQL-inspired query language with graph-native extensions. Unlike traditional databases that force a choice between document, relational, or graph models, SurrealDB handles all three simultaneously, making it well-suited for agent context graphs that need structured schema, relationship traversal, and vector similarity search.

SurrealDB's key differentiator for agent systems is its RELATE syntax for typed edges. Rather than encoding relationships as foreign keys in relational tables (which loses semantic meaning) or as adjacency lists in document fields (which makes traversal expensive), RELATE creates first-class edge records: `RELATE paper_a->cites->paper_b SET strength = 0.9`. These edges are queryable, typed, and traversable with graph path syntax. Combined with native vector field support for embedding storage, SurrealDB handles both the graph and vector layers of Cohezion's [[graphrag-knowledge-graph-with-surrealdb]] implementation.

The SurrealDB agent context schema stores agent sessions, tasks, decisions, and artifacts as interconnected records. Session nodes link to task nodes link to artifact nodes, enabling queries like "find all decisions made during sessions that produced high-coherence artifacts" — retrospective analytics that feed the [[experience-feedback-loop]]. The record-centric schema (as captured in [[lesson-surrealdb-schema-design]]) outperforms table-centric approaches by 60-70% in query complexity.

## Key Properties

- **Multi-model**: Document, relational, graph, and vector operations in one system
- **RELATE syntax**: First-class typed edge records with queryable metadata
- **SurrealQL**: SQL-familiar with graph path traversal and CONTAINS/SELECT FETCH extensions
- **Record IDs are typed**: IDs must match declared type at query time — a common source of bugs
- **Runs locally**: `ws://localhost:8000` with no cloud dependency; zero operational cost

## Related Papers

- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-step1-schema-complete]]
- [[2026-02-11-surrealdb-agent-context-schema-design]]
- [[2026-02-11-phase1-step1-schema-complete]]
- [[surrealdb-agent-context-phase1-step3-execution-plan]]
- [[surrealdb-agent-context-phase1-step3-query-testing]]

## Navigation

- [[MOC-platform-infrastructure]] — Map of Content for platform infrastructure including MCP, SurrealDB, and CI/CD

## Related Concepts

- [[graphrag-knowledge-graph-with-surrealdb]] — Cohezion's GraphRAG implementation built on SurrealDB
- [[knowledge-graph-systems]] — the broader category SurrealDB serves
- [[cloud-vault-mcp]] — the MCP server exposing SurrealDB tools
- [[agent-context]] — the agent session data stored in SurrealDB
- [[semantic-search]] — implemented via SurrealDB vector fields and Ollama embeddings
- [[2026-02-12-phase-0-foundation-complete|Phase 0 Foundation Complete]] — SurrealDB was integrated as part of the Phase 0 foundation
- [[vault-knowledge-graph-densification|Vault Knowledge Graph Densification]] — project to densify the SurrealDB graph with systematic paper/concept cross-linking and re-import

- [[surrealdb-sync-pattern]] — the pattern for batched writes, conflict resolution, and graph consistency when syncing to SurrealDB

## Related Lessons

- [[lesson-05-surrealdb]] — SurrealDB query syntax diverges from SQL in ways that cause silent failures; record IDs are typed and must match at query time
- [[lesson-surrealdb-schema-design]] — record-centric schema with RELATE edges outperforms table-centric for agent context; 60-70% query complexity reduction after redesign

## Projects

- [[2026-03-05-vault-surrealdb-sync-pipeline]] — PRD for real-time vault↔SurrealDB sync pipeline with change journal and sync daemon
- [[2026-03-05-vault-surrealdb-architecture]] — Architecture decision for three-layer compound sync pattern

## Missions

- README — HNSW vector search backend for the Anthropic portfolio knowledge graph

## Relevance to Cohezion

SurrealDB is the persistent graph backbone of Cohezion's knowledge infrastructure. It runs locally at `ws://localhost:8000`, stores all agent context data (sessions, tasks, artifacts, decisions), and serves as the query layer for the [[graphrag-knowledge-graph-with-surrealdb]] system. The [[cloud-vault-mcp]] server's `surrealdb_query`, `surrealdb_import_papers`, and `surrealdb_import_concepts` tools provide MCP-accessible interfaces for agent use. Key operational lessons: typed record IDs must be handled carefully (see [[lesson-05-surrealdb]]), and record-centric schema design dramatically reduces query complexity versus table-centric approaches.

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[SESSION-61-COMPLETE-SUMMARY]]
- [[SESSION-60-COMPLETION-SUMMARY]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[SESSION-2026-02-10-WORK-SUMMARY]]
- [[PHASE-2-FINAL-COMPLETION-VERIFIED-2026-02-14]]
- [[PHASE-2-DEPLOYMENT-COMPLETION-2026-02-14]]
- [[2026-02-14-wave-1-status-snapshot]]
- [[2026-02-14-wave-1-delivery-complete]]
- [[2026-02-14-phase-7-preparation-complete]]
- [[2026-02-14-phase-7-execution-complete]]
- [[2026-02-14-phase-6b-final-report]]
- [[2026-02-14-phase-6b-execution-complete]]

## Agent Outputs

- RETROSPECTIVE_PHASE_17_SURREALDB — Retrospective phase 17: SurrealDB mass ingestion
- persistence_implementation_plan — Persistence implementation plan

## Skills

- DATABASE_PRIME — Hybrid database approaches
- RECOVERY_PRIME — Recovery via SurrealDB substrate
- RELIABILITY_FALLBACK_PRIME — Fallback when SurrealDB is offline
- SURREALDB_MCP_PRIME — SurrealDB as MCP tool for agents
- SURREALDB_OPTIMIZER_PRIME — SurrealDB performance tuning

## Documentation
- [[SURREALDB_SETUP|SurrealDB Setup Guide]] — setup guide for the Phase 5-7 decision analysis system
- [[TRACK_A_GRAPHRAG_API|Track A: GraphRAG API]] — API documentation for GraphRAG reasoning engine using SurrealDB
- [[TRACK_C_IMPACT_API|Track C: Impact API]] — API documentation for impact and dependency analysis using graph algorithms
