---
title: "Graph Databases"
date: 2026-02-19
tags: [concept, surrealdb, knowledge-graph-systems, compound-engineering]
related_concepts: [surrealdb, knowledge-graph-systems, graphrag-knowledge-graph-with-surrealdb, semantic-search, agent-context]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 24
  synapse_out: 21
---
## Definition

Graph databases store data as nodes (entities) and edges (relationships) rather than rows and tables. This structure makes traversal queries natural and efficient: finding all papers that cite a concept, or all agent sessions that produced a particular decision type, requires following edges rather than executing expensive JOIN operations across tables. The schema models the domain's actual relationship structure rather than forcing it into flat tables.

For AI agent systems, graph databases are uniquely well-suited because agent knowledge is inherently relational. Decisions reference prior decisions; experiments depend on patterns; sessions produce artifacts that link to concepts. These dependencies form a graph that relational databases model awkwardly (many-to-many join tables) and document databases model poorly (embedded arrays with no traversal). Graph databases make these relationships first-class, enabling the multi-hop queries that power systems like [[graphrag-knowledge-graph-with-surrealdb]].

In Cohezion, [[surrealdb]] serves as the graph database, leveraging its multi-model capability: nodes are stored as typed records, edges are created with RELATE syntax, and vector fields on each node enable embedding-based [[semantic-search]] alongside graph traversal. This unified model eliminates the need for separate graph and vector stores.

## Key Properties

- **Node-edge model**: Entities are nodes; relationships are first-class edges with typed semantics
- **Traversal-native**: Graph path queries (A->B->C) replace multi-table JOINs
- **Flexible schema**: New relationship types can be added without schema migrations
- **Bidirectional traversal**: Edges can be traversed in both directions (forward links and backlinks)
- **Compound queries**: Graph traversal can be combined with filters and aggregations

## Related Papers

- [[12d-graph-implementation]]
- [[2026-02-09-12d-graph-next-steps]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-10-EXECUTION-COMPLETE]]
- [[3d-graph-plugin-selection]]

## Related Concepts

- [[surrealdb]] — Cohezion's graph database implementation
- [[knowledge-graph-systems]] — graph databases as knowledge infrastructure
- [[graphrag-knowledge-graph-with-surrealdb]] — Cohezion's GraphRAG system built on a graph database
- [[semantic-search]] — vector search layer that complements graph traversal
- [[cloud-vault-mcp]] — the MCP server exposing graph database tools

- [[surrealdb-sync-pattern]] — the sync pattern addresses graph consistency challenges during batched writes to graph databases

## Related Decisions

- [[2026-02-14-graphrag-verification-and-integration-session]] — GraphRAG verification demonstrating graph database integration with compound engineering
- [[surrealdb-graph-databases]] — research paper surveying SurrealDB's graph database capabilities and multi-model architecture
- [[knowledge-graph-semantic-relationships]] — semantic relationship patterns that graph databases model natively
- [[knowledge-graphs-semantic-web]] — the broader semantic web context for graph database technology

## Related Lessons

- [[lesson-05-surrealdb]] — SurrealDB graph database gotchas: record IDs are typed, graph traversal (-> and <-) replaces JOINs, FETCH required for nested records
- [[lesson-surrealdb-schema-design]] — design graph database schemas around records as nodes and RELATE as edges; emulating SQL schemas misses graph model strengths
- [[force-directed-graph]] — the visualization technique for rendering graph database contents as interactive 3D layouts
- [[knowledge-graph-densification]] — densification increases the useful edge density stored in the graph database

## Relevance to Cohezion

SurrealDB is Cohezion's graph database, running locally at `ws://localhost:8000`. The 12D graph system stores papers, concepts, decisions, and agent sessions as typed nodes with RELATE edges encoding semantic relationships. The graph database enables the multi-hop queries that power GraphRAG context retrieval: given a new agent task, traverse from relevant concepts to related papers to prior decisions, surfacing the full chain of accumulated knowledge. The [[cloud-vault-mcp]] server's `surrealdb_query` tool exposes this capability to agents via MCP.

## Skills

- DATABASE_PRIME — Graph database systems for AI
- KNOWLEDGE_GRAPH_INTEGRATION_PRIME — RDF and property graph models
- SURREALDB_MCP_PRIME — Multi-model database capabilities
- SURREALDB_OPTIMIZER_PRIME — Complex graph relationship optimization
- VECTOR_STORE_PRIME — Vector stores including FAISS and Chroma

## Documentation
- [[SURREALDB_SETUP|SurrealDB Setup Guide]] — setup guide for graph database decision analysis
- [[TRACK_C_IMPACT_API|Track C: Impact API]] — impact and dependency analysis using graph algorithms
