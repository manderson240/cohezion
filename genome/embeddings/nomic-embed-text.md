---
title: "Embedding Card: nomic-embed-text"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, embedding-card, ollama, semantic-search]
card_type: embedding
status: active
provider: ollama
aspect: knower
neural:
  activation: 0.451
  stage: growing
  cluster: specs
---

# Embedding Card: nomic-embed-text

> [!abstract] Summary
> nomic-embed-text is Cohezion's primary embedding model, running locally via Ollama. It generates 768-dimensional vectors for vault notes, enabling semantic search across papers, concepts, and decisions through the Ollama MCP server. Open-weights, no API costs, fully offline-capable.

## Identity

| Field | Value |
|-------|-------|
| **Model** | nomic-embed-text |
| **Provider** | Nomic AI (via Ollama) |
| **Model ID** | `nomic-embed-text` |
| **Type** | embedding-model |
| **Dimensions** | 768 |
| **Max Input Tokens** | 8192 |
| **Training Data Cutoff** | ~2024 |

## Capabilities

| Task | Support | Notes |
|------|---------|-------|
| Semantic search | Yes | Primary use case in Cohezion |
| Clustering | Yes | Note grouping and topic discovery |
| Classification | Yes | Note type classification |
| Retrieval | Yes | Vault note retrieval |
| Reranking | Limited | Not specialized for reranking |
| STS | Yes | Semantic textual similarity |

## Architecture

| Parameter | Value |
|-----------|-------|
| **Base architecture** | BERT-variant (nomic-bert) |
| **Parameters** | 137M |
| **Quantization** | FP16 (default Ollama) |
| **Distance metric** | cosine |
| **Normalization** | Pre-normalized |

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **MTEB Average** | ~62.4 | Competitive for size class |
| **Retrieval (MTEB)** | ~52 | Good for general retrieval |
| **Embedding latency** | ~5-15ms per document | Local Ollama, depends on hardware |
| **Batch throughput** | ~100-200 docs/sec | GPU-accelerated |
| **Memory footprint** | ~274MB | Small enough for CPU-only |

## Index Configuration

> [!tip] How This Embedding Is Indexed
> Configured for SurrealDB HNSW vector search.

| Parameter | Value |
|-----------|-------|
| **Vector store** | SurrealDB 3.0 HNSW |
| **Index type** | HNSW |
| **Dimensions** | 768 |
| **Distance** | cosine |
| **Total vectors** | ~700+ (vault notes) |

## Use Cases in Cohezion

| Use Case | Collection | Query Pattern |
|----------|-----------|---------------|
| Vault semantic search | All vault `.md` notes | Natural language → top-K similar notes |
| Note deduplication | papers/, concepts/ | Find near-duplicate content |
| Topic clustering | All notes | Group by semantic similarity |
| Context loading | Task-relevant notes | "Find notes related to X" |

## Cost & Deployment

| Metric | Value |
|--------|-------|
| **Cost** | Free (local Ollama) |
| **Deployment** | Local — Ollama on `localhost:11434` |
| **GPU required** | No (faster with GPU) |
| **Disk footprint** | ~274MB |

## Known Limitations

- 768 dimensions is smaller than OpenAI ada-002 (1536) — slightly lower fidelity
- English-focused training data — may underperform on multilingual content
- 8K token limit — long documents need chunking
- MTEB scores below commercial embedding APIs (OpenAI, Cohere)

## Related

- [[mxbai-embed-large]] — Alternative embedding model (1024d, higher quality)
- [[ollama]] — System card for the Ollama server
- [[semantic-search]] — Concept note on semantic search approaches
- [[surrealdb]] — Vector index storage

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial embedding card |
