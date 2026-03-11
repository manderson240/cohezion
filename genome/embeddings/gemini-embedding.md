---
title: "Embedding Card: Gemini Embedding"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, embedding-card, google, gemini, semantic-search]
card_type: embedding
status: active
provider: google
aspect: knower
neural:
  activation: 0.430
  stage: growing
  cluster: specs
---

# Embedding Card: Gemini Embedding

> [!abstract] Summary
> Gemini Embedding (`gemini-embedding-001`) is Google's native embedding model for the Gemini API ecosystem. It generates high-dimensional vectors for semantic search, text classification, and RAG systems. API-based (not local like Ollama embeddings), with $0.15/MTok pricing and a free tier.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini Embedding |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-embedding-001` |
| **Type** | embedding-model |
| **Dimensions** | 768 (default), configurable |
| **Max Input Tokens** | 8192 |
| **Training Data Cutoff** | ~2025 |

## Capabilities

| Task | Support | Notes |
|------|---------|-------|
| Semantic search | Yes | Primary use case |
| Clustering | Yes | Document grouping |
| Classification | Yes | Text classification |
| Retrieval | Yes | RAG systems |
| Reranking | Limited | |
| STS | Yes | Semantic textual similarity |

## Architecture

| Parameter | Value |
|-----------|-------|
| **Base architecture** | Gemini-derived transformer |
| **Parameters** | Undisclosed (proprietary) |
| **Quantization** | N/A (API-served) |
| **Distance metric** | cosine |
| **Normalization** | Pre-normalized |

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Quality** | Competitive | Google's production embedding |
| **Embedding latency** | ~20-50ms | API call (network dependent) |
| **Batch support** | Yes | Multiple documents per request |

## Cost & Deployment

| Metric | Value |
|--------|-------|
| **Cost** | $0.15 / MTok input |
| **Free tier** | Unlimited input tokens |
| **Deployment** | API only (cloud) |
| **GPU required** | No (server-side) |
| **Offline capable** | No (requires internet) |

## Use Cases in Cohezion

| Use Case | Collection | Notes |
|----------|-----------|-------|
| Cloud-based search | When Ollama is unavailable | Fallback to API embeddings |
| High-quality embeddings | Production RAG | Higher quality than local models |
| Batch processing | Large document sets | Free tier for experimentation |

## Known Limitations

- API-only — requires internet, can't run offline
- Proprietary — no visibility into model architecture
- Not currently integrated into Cohezion's primary pipeline (using Ollama locally)
- Latency higher than local Ollama embeddings

## Related

- [[nomic-embed-text]] — Primary local embedding (768d, Ollama)
- [[mxbai-embed-large]] — Alternative local embedding (1024d, Ollama)
- [[gemini-2-5-pro|Model Card: Gemini 2.5 Pro]] — Same provider
- [[semantic-search]] — Concept note

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
