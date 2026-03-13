---
title: "Concept Caching"
date: 2026-02-19
tags: [concept, token-efficiency, semantic-search, compound-engineering]
related_concepts: [semantic-search, token-efficiency-patterns, machine-learning-optimization, context-management]
aspect: knower
neural:
  activation: 0.9
  stage: mature
  synapse_in: 9
  synapse_out: 12
---
## Definition

Concept caching is the practice of storing computed results — embeddings, search results, model outputs — so they can be reused in future sessions without recomputing. In agentic AI systems, caching operates at multiple levels: exact match (identical query returns cached response), semantic similarity (nearly identical queries return cached response with cosine similarity above threshold), and vault persistence (cached results survive session boundaries).

The economic value of caching compounds with reuse frequency. A semantic embedding computed once for a vault note costs ~100ms of Ollama inference; the 100th retrieval of that embedding costs nothing. For a vault with 200+ notes, pre-computing all embeddings once and caching them eliminates embedding compute from all future semantic search operations — reducing per-query latency from seconds to milliseconds.

In Cohezion, caching is implemented through the SemanticCache, which implements a three-layer hierarchy: L1 exact hash match (microseconds), L2 cosine similarity search (milliseconds), and L3 vault persistence (seconds, but survives session boundaries). The batch cache two-phase pattern ([[lesson-29-batch-cache-two-phase]]) formalizes the optimal implementation: check cache in bulk before computing new embeddings, compute only misses, write all results back.

## Key Properties

- **Three-layer hierarchy**: Exact match → semantic similarity → persistent vault cache
- **Session persistence**: L3 cache survives session boundaries; embeddings not recomputed across sessions
- **Batch lookup**: Check all cache candidates before computing any misses
- **95%+ hit rate**: Cohezion's SemanticCache achieves >95% cache hits on repeated queries
- **TTL management**: Cached results expire when underlying notes change; invalidation must be explicit

## Related Papers

- [[lesson-21-runtime-json-pollution]]
- [[lesson-23-stash-branch-switch-hazard]]
- [[lesson-29-batch-cache-two-phase]]

## Related Concepts

- [[semantic-search]] — the retrieval system that caching accelerates
- [[token-efficiency-patterns]] — the collection of efficiency patterns caching belongs to
- [[machine-learning-optimization]] — inference optimization that caching complements
- [[context-management]] — context assembly that caching makes tractable at scale

## Related Decisions

- [[2026-02-11-lessons-compound-engineering-phase-1-complete]] — Phase 1 completion lessons identified caching as critical for semantic search performance
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success]] — validated that caching combined with token efficiency yields production-quality results

## Related Patterns

- [[canvas-driven-manual-linking]] — canvas-driven linking results can be cached to prevent redundant re-computation of link suggestions
- [[implementation-first-infrastructure-later]] — caching infrastructure should be added after validating the core feature works

## Key Lesson Links

- [[lesson-29-batch-cache-two-phase]] — the canonical caching pattern: bulk cache lookup BEFORE computation, compute only misses, write results; 60% reduction in compute costs

## Relevance to Cohezion

Caching is core to Cohezion's performance model. The SemanticCache's 95%+ hit rate means most agent queries for vault context return in milliseconds rather than seconds, making context retrieval negligible overhead in the execution pipeline. The L3 vault-persisted cache ensures embedding computation happens once across all sessions — a new session inherits the full embedding index built by prior sessions. This is compound engineering applied to infrastructure: each session leaves the cache richer than it found it.

## Session References

- [[SESSION-50-QUICKSTART]] — LRU cache achieving 99% hit rate as concept caching applied to FLUME embeddings

## Skills

- caching — Caching strategies for AI systems
- SEMANTIC_CACHING_PRIME — Semantic similarity caching
