---
title: "Embedding Card: mxbai-embed-large"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, embedding-card, ollama, semantic-search]
card_type: embedding
status: active
provider: ollama
aspect: knower
neural:
  activation: 0.68
  stage: growing
  synapse_in: 4
  synapse_out: 4
---

# Embedding Card: mxbai-embed-large

> [!abstract] Summary
> mxbai-embed-large is Cohezion's higher-fidelity embedding alternative, producing 1024-dimensional vectors via Ollama. It offers better retrieval quality than nomic-embed-text at the cost of slightly larger vectors and slower inference. Used when embedding quality matters more than speed.

## Identity

| Field | Value |
|-------|-------|
| **Model** | mxbai-embed-large |
| **Provider** | mixedbread.ai (via Ollama) |
| **Model ID** | `mxbai-embed-large` |
| **Type** | embedding-model |
| **Dimensions** | 1024 |
| **Max Input Tokens** | 512 |
| **Training Data Cutoff** | ~2024 |

## Capabilities

| Task | Support | Notes |
|------|---------|-------|
| Semantic search | Yes | Higher quality than nomic |
| Clustering | Yes | Better separation with 1024d |
| Classification | Yes | |
| Retrieval | Yes | Strong retrieval performance |
| Reranking | Limited | |
| STS | Yes | |

## Architecture

| Parameter | Value |
|-----------|-------|
| **Base architecture** | BERT-large |
| **Parameters** | 335M |
| **Quantization** | FP16 (default Ollama) |
| **Distance metric** | cosine |
| **Normalization** | Pre-normalized |

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **MTEB Average** | ~64.7 | Higher than nomic-embed-text |
| **Retrieval (MTEB)** | ~54 | Better retrieval quality |
| **Embedding latency** | ~10-25ms per document | Slightly slower than nomic |
| **Batch throughput** | ~60-120 docs/sec | |
| **Memory footprint** | ~335MB | Moderate |

## Index Configuration

| Parameter | Value |
|-----------|-------|
| **Vector store** | SurrealDB 3.0 HNSW |
| **Index type** | HNSW |
| **Dimensions** | 1024 |
| **Distance** | cosine |

## Use Cases in Cohezion

| Use Case | Collection | Query Pattern |
|----------|-----------|---------------|
| High-fidelity search | Critical queries needing precision | When nomic results are too noisy |
| Research paper matching | papers/ collection | Find semantically similar research |
| Cross-domain discovery | All notes | Find unexpected connections |

## Cost & Deployment

| Metric | Value |
|--------|-------|
| **Cost** | Free (local Ollama) |
| **Deployment** | Local — Ollama on `localhost:11434` |
| **GPU required** | Recommended |
| **Disk footprint** | ~335MB |

## Known Limitations

- 512 token max input — more aggressive chunking needed than nomic (8K)
- Larger vectors (1024 vs 768) — more storage and slightly slower search
- 335M parameters — heavier memory footprint
- Still below commercial embeddings (OpenAI ada-002, Cohere embed-v3)

## Related

- [[nomic-embed-text]] — Primary embedding model (768d, faster)
- [[ollama]] — System card for the Ollama server
- [[semantic-search]] — Concept note on semantic search
- [[surrealdb]] — Vector index storage

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial embedding card |
