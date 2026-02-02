# RETROSPECTIVE: Phase 18 - Semantic Vector Caching

**Date**: 2026-02-01
**Topic**: HNSW Vector Search & Latent Space Acceleration
**Phase**: S18 (Semantic Caching)

## 1. The Challenge
Traditional caching (Exact Hash) has a hit rate of <5% in conversational agents because users never type the exact same thing twice (e.g., "Status?" vs "Give me status"). We needed a way to cache *ideas*, not just strings.

## 2. Issues Encountered & Solutions

### A. VRAM Contention
**Problem**: Initial implementation imported `FlumeEncoder` (PyTorch + Transformers), which allocated ~1GB VRAM for CUDA context. On an already stressed system (90% VRAM load), this triggered the **Emergency Circuit Breaker**.
**Solution**: **Lightweight Encoder Pattern**.
- We refactored `SemanticCache` to use a nested `LightweightEncoder` class that calls Ollama's HTTP API directly (`nomic-embed-text`) instead of loading local weights. This reduced VRAM overhead to near zero (client-side).

### B. SurrealDB Vector Syntax
**Problem**: Determining the correct syntax for HNSW ordering and similarity scoring was non-trivial.
**Solution**:
- **Ordering**: `ORDER BY embedding <|4|> $vec ASC` (KNN Search).
- **Scoring**: `vector::similarity::cosine(embedding, $vec)` (Returns 0.0-1.0).
- **Threshold**: We set a baseline of `0.95` for "Semantically Identical".

## 3. Metrics & Validation
- **Integration Test**: `scripts/caching/test_agent_integration.py` confirmed `BaseAgent` successfully retrieves cached responses for paraphrased queries.
- **Latency**: Semantic Hit ~30ms vs LLM Generation ~2000ms.
- **Efficiency**: Zero VRAM footprint for the caching client.

## 4. Key Takeaways
- **Avoid PyTorch Imports if Possible**: If you have an inference server (Ollama), use it. Importing `torch` is expensive.
- **KNN is a Filter**: In SurrealDB, `<|4|>` effectively acts as a filter *and* sorter.
- **Compound Value**: This phase not only speeds up the swarm but significantly reduces the token load on the `70B` models.
