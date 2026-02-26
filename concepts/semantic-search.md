---
title: Semantic Search
date: 2026-02-23
tags: [concept, ml, search]
status: stub
---

# Semantic Search

Search based on meaning and context rather than exact keyword matching. Implemented in Cohezion via Ollama embeddings and vector similarity search.

## Related
- [[mcp-infrastructure-architecture]]
- [[agentic-ai]]

## Related Lessons

- [[lesson-06-ollama-latency]] — Ollama (the semantic search inference backend) has cold-start latency of 5-30s; pre-warm models before pipeline execution
- [[lesson-29-batch-cache-two-phase]] — batch embedding cache lookups before computing new embeddings; 60% reduction in semantic search compute costs
