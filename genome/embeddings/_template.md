---
title: "Embedding Card: [Model/Index Name]"
date: YYYY-MM-DD
version: 1
last_revised: YYYY-MM-DD
tags: [spec, embedding-card]
card_type: embedding
status: active
provider: [ollama | anthropic | openai | huggingface]
neural:
  activation: 0.41
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Embedding Card: [Model/Index Name]

> [!abstract] Summary
> One-paragraph description of the embedding model or index, what it encodes, and how it's used in Cohezion.

## Identity

| Field | Value |
|-------|-------|
| **Model** | [Model name] |
| **Provider** | [Ollama / OpenAI / Anthropic / HuggingFace] |
| **Model ID** | `[exact model identifier]` |
| **Type** | embedding-model / vector-index / hybrid |
| **Dimensions** | [Vector dimensions — e.g., 768, 1024, 1536] |
| **Max Input Tokens** | [Maximum tokens per embedding request] |
| **Training Data Cutoff** | [Date or description] |

## Capabilities

| Task | Support | MTEB Score | Notes |
|------|---------|------------|-------|
| Semantic search | Yes/No | [Score] | |
| Clustering | Yes/No | [Score] | |
| Classification | Yes/No | [Score] | |
| Retrieval | Yes/No | [Score] | |
| Reranking | Yes/No | [Score] | |
| STS (Semantic Textual Similarity) | Yes/No | [Score] | |

## Architecture

| Parameter | Value |
|-----------|-------|
| **Base architecture** | [Transformer variant, BERT, etc.] |
| **Parameters** | [Model size] |
| **Quantization** | [None / Q4 / Q8 / FP16] |
| **Distance metric** | cosine / euclidean / dot-product |
| **Normalization** | [Pre-normalized / requires normalization] |

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **MTEB Average** | [Score] | [Rank if known] |
| **Embedding latency** | [ms per document] | |
| **Batch throughput** | [docs/sec] | |
| **Memory footprint** | [RAM usage] | |

## Index Configuration

> [!tip] How This Embedding Is Indexed
> Configuration for the vector store that holds these embeddings.

| Parameter | Value |
|-----------|-------|
| **Vector store** | SurrealDB HNSW / FAISS / Chroma / custom |
| **Index type** | HNSW / IVF / flat |
| **ef_construction** | [HNSW build parameter] |
| **ef_search** | [HNSW query parameter] |
| **M** | [HNSW max connections] |
| **Total vectors** | [Current count] |

## Use Cases in Cohezion

| Use Case | Collection | Query Pattern |
|----------|-----------|---------------|
| [Use case 1] | [Which data is embedded] | [How queries are formed] |

## Cost & Deployment

| Metric | Value |
|--------|-------|
| **Cost** | [$ per MTok or free (local)] |
| **Deployment** | local (Ollama) / API / self-hosted |
| **GPU required** | Yes/No |
| **Disk footprint** | [Model file size] |

## Known Limitations

- [Limitation 1 — e.g., "English-only training data"]
- [Limitation 2 — e.g., "Degrades on documents >512 tokens"]

## Related

- [[related-model-card]]
- [[semantic-search]]
- [[surrealdb]]

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | YYYY-MM-DD | Initial card |
