---
title: "Knowledge Graph Systems"
date: 2026-02-19
tags: [concept, graph-databases, semantic-search, compound-engineering]
related_concepts: [graphrag-knowledge-graph-with-surrealdb, surrealdb, semantic-search, compound-engineering, mcp-infrastructure-architecture]
aspect: knower
neural:
  activation: 0.98
  stage: mature
  synapse_in: 57
  synapse_out: 38
---
## Definition

Knowledge graph systems represent information as a network of entities and relationships rather than flat documents or relational tables. Each node is a concept, paper, decision, or agent session; edges encode typed relationships (cites, implements, contradicts, is-related-to). This structure enables graph traversal queries that discover indirect connections — finding all papers that share a concept, or tracing how a decision influenced downstream experiments — that flat search cannot express.

For AI agents, knowledge graphs serve as externalized associative memory. Where a vector database returns semantically similar documents, a knowledge graph can follow relationship paths to surface contextually adjacent knowledge: “this concept was last used in session 57, which also produced pattern X, which is referenced in decision Y.” This multi-hop reasoning capability is the core insight behind GraphRAG approaches, which combine graph traversal with retrieval-augmented generation.

In Cohezion, the knowledge graph is built on [[surrealdb]] and stores papers, concepts, decisions, experiments, and agent sessions as typed records with RELATE edges. The graph is accessible via the [[cloud-vault-mcp]] server's `surrealdb_query` tool, and visualized through the 3D graph Obsidian plugin. Cross-linking via `[[wiki-links]]` in vault notes forms a parallel human-readable graph layer that Obsidian renders interactively.

## Key Properties

- **Entity typing**: Nodes carry types (paper, concept, decision, session) enabling type-filtered queries
- **Relationship semantics**: Typed edges (cites, implements, related_to) carry meaning beyond simple links
- **Graph traversal**: Multi-hop queries follow paths that flat search cannot express
- **Incremental growth**: Graphs compound in value as nodes and edges accumulate over time
- **Dual representation**: Machine-readable graph (SurrealDB) + human-readable graph (Obsidian wiki-links)

## Related Papers

- [[knowledge-graph-semantic-relationships]] — semantic relationship modeling in knowledge graphs
- [[knowledge-graphs-semantic-web]] — broader semantic web context for knowledge graph technology
- [[surrealdb-graph-databases]] — SurrealDB's multi-model architecture as knowledge graph backend
- [[12d-graph-implementation]]
- [[2026-02-09-12d-graph-next-steps]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-10-EXECUTION-COMPLETE]]
- [[3d-graph-plugin-selection]]
- [[lesson-11-team-agent-efficiency]]

## Navigation

- [[MOC-vault-architecture]] — Map of Content for the vault architecture topic area

## Related Concepts

- [[graphrag-knowledge-graph-with-surrealdb]] — Cohezion's specific GraphRAG implementation
- [[surrealdb]] — the graph database powering Cohezion's knowledge graph
- [[semantic-search]] — the vector similarity layer that complements graph traversal
- [[compound-engineering]] — the methodology that the knowledge graph serves
- [[cloud-vault-mcp]] — the MCP server exposing graph query tools
- [[2026-02-12-phase-0-foundation-complete|Phase 0 Foundation Complete]] — the knowledge graph foundation established in Phase 0
- [[2026-02-10-phase3a-3d-graph-validation|Phase 3A: 3D Graph Validation]] — validated 3D graph visualization of 84 nodes and 575 wiki-link edges from the knowledge graph
- [[vault-knowledge-graph-densification|Vault Knowledge Graph Densification]] — the project to systematically densify the vault's wiki-link graph by auditing papers and concepts
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification Complete]] — parallel agent teams densified the graph to 1,458 link edges and ~16 avg links/paper
- [[2026-03-03-vault-state-assessment|Vault State Assessment March 2026]] — external assessment of graph density (1,458 links, ~14 links/node) and strategic recommendations for deepening AI Architecture clusters
- [[2026-03-03-vault-hidden-contributions-assessment|Hidden Contributions Assessment]] — identifies a topology problem: many graph links are co-occurrence rather than semantic, overstating genuine knowledge connections

- [[decision-linker]] — the decision linker agent creates typed edges between decision nodes in the knowledge graph
- [[research-lineage]] — research lineage chains are encoded as traversable paths in the knowledge graph
- [[CascadeTimeline]] — the cascade timeline visualizes temporal decision chains stored in the knowledge graph
- [[12D-Projection]] — connectivity and domain clustering dimensions in the 12D projection are computed from knowledge graph structure
- [[query-testing]] — knowledge graph queries require testing for correct traversal, edge semantics, and multi-hop result accuracy
- [[knowledge-graph-densification]] — the systematic process of increasing edge density in the knowledge graph
- [[bidirectional-linking]] — the linking convention that ensures all graph edges are navigable in both directions
- [[force-directed-graph]] — the 3D visualization technique used to render the knowledge graph
- [[12D-Manifold]] — the 12-dimensional scoring space computed from knowledge graph structure
- [[agents-as-exotic-vacuum-objects]] — the knowledge graph is the apparatus through which agent EVOs propagate

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations

## Relevance to Cohezion

The Cohezion knowledge graph is the structural backbone of compound learning. Every paper ingested, concept defined, decision logged, and experiment recorded becomes a node in the graph. The 12D graph system (implemented in Phase 2 and extended with GraphRAG in sessions 56-57) adds dimensional embeddings to each node, enabling both keyword search (SurrealDB queries) and semantic similarity (Ollama embeddings). The graph's value compounds nonlinearly: 84 papers + 22 concepts + 150 decisions create a web with thousands of implicit connections that surface relevant context for any new agent task.

## Daily References

- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[PHASE-3-COMPLETION-VERIFIED-2026-02-14]]

### Indigenous Cosmology Cross-Validation

- [[indigenous-cosmologies-toe-synthesis]] — knowledge graphs pre-date computers: Whakapapa (Māori DAG genealogy), Songlines (Aboriginal traversal paths), Ifá (Yoruba 256-node oracle graph)
- [[maori-cosmology-and-toe]] — Whakapapa IS a directed acyclic graph: genealogical ontology where identity = position in the graph

## Agent Outputs

- MULTIMODAL_REGISTRY — Multimodal registry (visual artifact catalog)
- pillar_deep_dives — Pillar deep dives
- vault_integration_plan — Vault integration plan (structured + Obsidian persistence)

## Skills

- KNOWLEDGE_GRAPH_INTEGRATION_PRIME — Knowledge graph representation
- KNOWLEDGE_HARVESTING_PRIME — Recovering semantic value from artifacts
- knowledge_mining — Reusable pattern mining
- OBSIDIAN_MCP_INTEGRATION_PRIME — Knowledge graph queries
- OBSIDIAN_VAULT_INTEGRATION_PRIME — Knowledge graph health
- RECOVERY_PRIME — Context sync via knowledge graph
