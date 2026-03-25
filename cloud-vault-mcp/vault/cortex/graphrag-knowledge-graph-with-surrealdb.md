---
title: "Graphrag Knowledge Graph With Surrealdb"
date: 2026-02-19
tags: [concept, knowledge-graph-systems, surrealdb, semantic-search, compound-engineering]
related_concepts: [knowledge-graph-systems, surrealdb, semantic-search, compound-engineering, cloud-vault-mcp]
aspect: knower
neural:
  activation: 0.91
  stage: mature
  synapse_in: 22
  synapse_out: 28
---
## Definition

GraphRAG (Graph-augmented Retrieval Augmented Generation) extends standard RAG by using a knowledge graph as the retrieval substrate instead of a flat vector index. Rather than simply finding semantically similar documents, GraphRAG traverses typed relationships — "this concept implements that pattern," "this session references that decision" — enabling multi-hop reasoning that surfaces contextually adjacent knowledge unreachable by vector similarity alone.

Cohezion's GraphRAG implementation uses [[surrealdb]] as both the graph database and the vector store. SurrealDB's native RELATE syntax models typed edges between nodes (papers, concepts, decisions, agent sessions), while its vector field support stores Ollama-generated embeddings alongside structured metadata. Queries can combine graph traversal with vector similarity in a single SurrealQL statement, enabling hybrid search: "find concepts semantically similar to X that are linked to papers published after 2025."

The implementation was developed across sessions 56-57, progressing through four phases: schema design, data import, query validation, and GraphRAG proof-of-concept. Phase 2 Track A added agent context reasoning — storing agent session data as nodes so the graph captures not just research knowledge but also the agent execution history that produced it. This closes the loop between knowledge graph and [[agent-journey-tracking]].

## Key Properties

- **Hybrid retrieval**: Combines vector similarity search with graph traversal in single queries
- **Typed relationships**: Edges carry semantic meaning (cites, implements, contradicts, derived-from)
- **Agent context integration**: Agent sessions stored as graph nodes, linking executions to knowledge
- **SurrealDB-native**: SurrealQL RELATE syntax + vector fields handle both graph and vector operations
- **Incremental indexing**: New papers and concepts are added to the graph without rebuilding indexes

## Related Papers

- [[2026-02-10-phase4-universe-simulation-complete]]
- [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-12-graphrag-phase-1-sql-syntax-errors-block-imports]]
- [[2026-02-12-phase-2-track-a-surrealdb-agent-reasoning-complete]]
- [[2026-02-12-phase2-prioritization-decision]]
- [[2026-02-12-session-57-graphrag-complete-phases-1-4-delivered]]
- [[2026-02-13-next-10-phases-graphrag-roadmap]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-2-track-a-complete]]
- [[2026-02-14-phase-4-implementation-progress]]
- [[2026-02-14-track-a-sign-off-approved]]

## Related Concepts

- [[knowledge-graph-systems]] — the broader category GraphRAG belongs to
- [[surrealdb]] — the database implementing the graph and vector layers
- [[semantic-search]] — the vector similarity component of hybrid search
- [[compound-engineering]] — the methodology whose knowledge the graph stores
- [[cloud-vault-mcp]] — the MCP server exposing graph query tools
- [[vault-knowledge-graph-densification|Vault Knowledge Graph Densification]] — the project to systematically densify the SurrealDB graph by auditing papers, concepts, and wiki-links

- [[CascadeTimeline]] — the cascade timeline visualizes temporal decision chains from the GraphRAG data
- [[DecisionHealthDashboard]] — the decision health dashboard renders decision metadata stored in the GraphRAG backend
- [[knowledge-graph-densification]] — densification increases edge density in the GraphRAG graph, improving retrieval quality
- [[force-directed-graph]] — the 3D visualization of the GraphRAG graph structure

## Relevance to Cohezion

The GraphRAG knowledge graph is Cohezion's long-term memory layer, encoding 84 papers, 22+ concepts, 150+ decisions, and growing agent session history as a queryable graph. When an agent needs context for a new task, `vault_find_relevant_context` runs a hybrid GraphRAG query: vector similarity narrows the candidate set, graph traversal surfaces related decisions and experiments. This is orders of magnitude more effective than keyword search alone — enabling compound knowledge retrieval that scales with the vault's growth.

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[PHASE-3-COMPLETION-VERIFIED-2026-02-14]]
- [[PHASE-2-DEPLOYMENT-COMPLETION-2026-02-14]]
