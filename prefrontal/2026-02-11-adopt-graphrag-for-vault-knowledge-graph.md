---
title: "Adopt GraphRAG for Vault Knowledge Graph"
date: "2026-02-11"
status: proposed
tags: [decision]

decision_reasoning:
  chosen_option: "Adopt GraphRAG pattern for vault knowledge graph construction"
  rationale: "GraphRAG provides structured methodology for connecting papers, concepts, and lessons; enables advanced queries and analysis"
  confidence_score: 0.82
  alternatives_rejected:
    - "Continue manual canvas-driven linking (not scalable)"
    - "Implement custom LLM-based linking (reinventing wheel)"
  reasoning_chain:
    - "Recognized need for systematic knowledge graph approach"
    - "Canvas-driven linking works but requires manual effort"
    - "GraphRAG pattern provides proven methodology"

metrics:
  estimated_cost: 5.0
  estimated_time_hours: 8.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    []
aspect: thinker
neural:
  activation: 0.633
  stage: mature
  cluster: decisions
---

## Context

The Cohezion vault had accumulated 80+ research papers, dozens of architectural decisions, and numerous concept notes, but cross-linking between these documents was sparse and manually maintained. Obsidian's canvas view provided visual exploration, but creating connections required a human to read both documents and manually add wiki-links. This approach did not scale: with N documents, the potential connections grow as O(N^2), making manual linking increasingly impractical.

[Microsoft's GraphRAG](https://microsoft.github.io/graphrag/) introduced a structured methodology for building knowledge graphs from text corpora. The approach extracts entities and relationships from documents, builds community hierarchies, and generates summaries that enable both local (specific entity) and global (thematic) queries. [Research published in April 2024](https://arxiv.org/abs/2404.16130) demonstrated substantial improvements over baseline RAG for comprehensiveness and diversity of answers, particularly for global sensemaking questions over datasets in the 1M token range.

The vault's existing [[surrealdb|SurrealDB]] infrastructure provided a native graph database backend, making GraphRAG implementation more natural than with a traditional relational store. The question was whether to adopt GraphRAG's methodology for systematic knowledge graph construction or continue with ad hoc manual linking.

## Decision

Adopt the GraphRAG pattern for vault knowledge graph construction, implemented on top of [[graphrag-knowledge-graph-with-surrealdb|SurrealDB]] as the graph storage layer.

The implementation follows Microsoft's methodology adapted for Obsidian vault content:

1. **Entity extraction**: Parse all vault documents to extract entities (papers, concepts, decisions, patterns, experiments) and their relationships (cites, implements, extends, contradicts, validates).
2. **Community detection**: Cluster related entities into thematic communities (e.g., "quantum physics papers", "agent architecture decisions", "ML optimization patterns").
3. **Hierarchical summarization**: Generate summaries at each community level, enabling queries at different abstraction levels.
4. **Wiki-link materialization**: Convert discovered relationships into Obsidian wiki-links, making the graph navigable in the native vault interface.
5. **Incremental updates**: New documents trigger entity extraction and community re-evaluation, not a full graph rebuild.

## Consequences

- **Positive**: Knowledge graph density increased dramatically. Phases 1-4 delivered in [[2026-02-12-session-57-graphrag-complete-phases-1-4-delivered|Session 57]] added hundreds of new cross-links that would have taken weeks to create manually.
- **Positive**: [[semantic-search]] queries over the vault improved significantly. Instead of keyword matching, queries can now traverse entity relationships to find contextually relevant documents.
- **Positive**: The graph structure enables [[compound-engineering]] -- each new document automatically inherits connections to related existing content, making the vault more valuable with each addition.
- **Negative**: Initial graph construction required significant compute (entity extraction over 80+ papers). Subsequent incremental updates are much cheaper.
- **Negative**: Some extracted relationships are spurious (false positives). The [[adversarial-review]] process catches most of these, but manual curation remains necessary for high-confidence edges.
- **Risk**: Dependence on SurrealDB as the graph backend. If SurrealDB development stalls, migration to an alternative graph store would require re-implementing the storage layer.

## Alternatives Considered

- **Continue manual canvas-driven linking** -- Maintain the existing approach of reading documents and manually adding wiki-links in Obsidian's canvas view. Rejected because it does not scale with vault growth and relies on a single person's ability to hold the entire vault's content in memory.
- **Implement custom LLM-based linking** -- Build a bespoke system that uses LLM prompts to suggest connections between documents. Rejected as reinventing the wheel -- GraphRAG provides a proven, researched methodology that addresses the same problem.
- **Use a vector-only approach (traditional RAG)** -- Embed all documents and use cosine similarity for discovery. Rejected because vector similarity misses structural relationships (A cites B, B contradicts C) that are essential for knowledge graph navigation. As the [GraphRAG research](https://arxiv.org/abs/2404.16130) shows, graph-based retrieval catches multi-hop connections that vector similarity alone cannot.
- **Neo4j instead of SurrealDB** -- Use Neo4j as the graph database. Rejected because SurrealDB was already deployed in the Cohezion infrastructure and provides both document and graph capabilities in a single system.

## See Also

- [[graphrag-knowledge-graph-with-surrealdb]] -- the technical implementation combining GraphRAG with SurrealDB
- [[compound-engineering]] -- the principle that motivated systematic knowledge graph construction
- [[knowledge-graph-systems]] -- broader context of knowledge graph approaches
- [[graph-databases]] -- the underlying technology enabling graph queries
- [[semantic-search]] -- query capability enabled by the knowledge graph
- [[canvas-driven-manual-linking]] -- the predecessor approach this decision replaces
- [[surrealdb-agent-context-schema]] -- the SurrealDB schema used for storing graph data
- [[lessons-graph-integration]] -- pattern this decision instantiates for connecting vault nodes
- [[2026-02-13-next-10-phases-graphrag-roadmap]] -- the roadmap that builds on this decision
- [[2026-02-12-session-57-graphrag-complete-phases-1-4-delivered]] -- first delivery under this decision
- [[2026-02-14-graphrag-verification-and-integration-session]] -- later verification and fixes

## Primary Sources

- [From Local to Global: A Graph RAG Approach to Query-Focused Summarization (arXiv, April 2024)](https://arxiv.org/abs/2404.16130) -- the foundational GraphRAG paper
- [Microsoft GraphRAG Project](https://www.microsoft.com/en-us/research/project/graphrag/) -- Microsoft Research project page
- [GraphRAG GitHub Repository](https://github.com/microsoft/graphrag) -- open-source implementation
- [Graph Retrieval-Augmented Generation: A Survey (ACM TOIS)](https://dl.acm.org/doi/10.1145/3777378) -- comprehensive academic survey of GraphRAG approaches
- [GraphRAG Explained: Enhancing RAG with Knowledge Graphs](https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1) -- accessible overview of the approach
