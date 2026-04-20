---
title: Semantic Search
date: 2026-02-23
tags: [concept, ml, search, agent-context, knowledge-graph-systems]
related_concepts: [knowledge-graph-systems, context-management, agent-context, mcp-infrastructure-architecture, token-efficiency-patterns]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 67
  synapse_out: 21
---

# Semantic Search

Semantic search retrieves documents based on meaning and conceptual similarity rather than exact keyword matching. Instead of asking "does this document contain these words?", it asks "is this document about the same concept, even if different words are used?" The implementation uses embedding models to convert text into high-dimensional vectors where semantically related content clusters together, then finds nearest neighbors via cosine similarity.

For AI agents, semantic search is the primary mechanism for relevant context retrieval. When an agent needs to find prior decisions, patterns, or experiments relevant to its current task, keyword search fails on paraphrasing and terminology variations. Semantic search over vault embeddings surfaces the right notes even when the agent's query uses different terminology than the stored content — enabling robust, context-aware retrieval across large knowledge bases.

In Cohezion, semantic search is implemented using Ollama's `nomic-embed-text` embedding model (local, zero API cost) combined with cosine similarity ranking. The two-phase batch cache pattern (see [[token-efficiency-patterns]]) pre-warms embeddings for known vault content, making incremental searches fast. The `vault_find_relevant_context` tool in [[cloud-vault-mcp]] wraps this search, accepting a natural language query and returning the most relevant vault notes for injection into agent context.

## Key Properties

- **Embedding-based**: Text is converted to vectors; similarity is computed as cosine distance
- **Language-agnostic**: Finds similar content regardless of terminology variation or phrasing
- **Scalable**: Vector indices (e.g., FAISS, SurrealDB vector fields) enable sub-millisecond search at scale
- **Cold-start latency**: First Ollama query triggers model load (5-30s); pre-warm before pipeline execution
- **Batch-friendly**: Embed multiple documents at once to amortize model loading overhead

## Related
- [[mcp-infrastructure-architecture]] — the infrastructure hosting Ollama embeddings
- [[knowledge-graph-systems]] — the graph layer complementing vector search
- [[context-management]] — the broader discipline semantic search serves
- [[agent-context]] — what semantic search retrieves and assembles
- [[token-efficiency-patterns]] — patterns for making semantic search cost-effective
- [[natural-language-processing]] — NLP embeddings power the vector-based retrieval underlying semantic search
- [[FLUME-Architecture]] -- FLUME latent space enables semantic similarity search over agent trajectories
- [[VAE-Encoder]] -- VAE latent spaces enable semantic similarity search via distance in latent space
- [[2026-02-24-anti-pattern-dual-vae-architecture-creates-integration-debt|Anti-pattern: Dual VAE]] — TemporalVAE uses pre-trained semantic embeddings, connecting to the semantic search pipeline
- [[2026-02-24-anti-pattern-character-level-tokenizer-for-semantic-embeddings|Anti-pattern: Character-Level Tokenizer]] — pre-trained embeddings are the correct foundation for semantic search
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories|Hash-Based Journey Tracking Failure]] — semantic proximity in latent space is foundational for meaningful analysis
- [[2026-02-09-rust-flume-python313-incompatibility|Rust FLUME Incompatibility]] — FLUME encoding is in the hot path for semantic cache queries
- [[2026-02-20-session-59-compound-engineering-complete|Session 59: Compound Engineering Complete]] — HIHO-stabilized semantic cache improves hit stability
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification Complete]] — denser wiki-link graphs improve semantic search traversal paths

- [[decision-linker]] — the decision linker uses semantic similarity search to find and connect related decision notes
- [[knowledge-graph-densification]] — embedding-based similarity drives automated link prediction in densification
- [[bidirectional-linking]] — semantic search helps identify note pairs that should be bidirectionally linked
- [[ollama-context-management]] — context management for the Ollama models powering semantic embeddings

## Related Lessons

- [[lesson-06-ollama-latency]] — Ollama (the semantic search inference backend) has cold-start latency of 5-30s; pre-warm models before pipeline execution
- [[lesson-29-batch-cache-two-phase]] — batch embedding cache lookups before computing new embeddings; 60% reduction in semantic search compute costs

## Agent Outputs

- **Nexus Research Miner Implementation** — `Agents/Antigravity/1cfa5e45-49e4-46cc-88b3-b0ed12938d3a/implementation_plan.md`

## Skills

- DATABASE_PRIME — Vector stores for semantic retrieval
- embedding_strategy — Embedding strategies for semantic retrieval
- FLUME_METHODOLOGY_PRIME — Semantic interpolation techniques
- KNOWLEDGE_GRAPH_INTEGRATION_PRIME — Semantic linking of skills and concepts
- MEMORY_MCP_PRIME — Semantic vector storage
- REDUCER_PRIME — Semantic compression and distillation
- semantic_algebra — Vector arithmetic on semantic concepts
- semantic_analysis — Vector similarity and clustering
- SEMANTIC_CACHING_PRIME — Vector similarity for cache matching
- VECTOR_STORE_PRIME — Persistent vector storage for retrieval
