---
name: langchain-rag-tier
description: LangChain RAG pipeline as a TieredOrchestrator tier for document QA and retrieval-augmented generation. FAISS vectorstore + Ollama embeddings + CPU-local LLM. Route when output_type=rag_query.
category: inference
tags: [langchain, rag, retrieval, documents, tier, inference, faiss]
---

# SKILL: LANGCHAIN_RAG_TIER_PRIME

# Skill: LangChain RAG Tier

## Overview

Wraps a LangChain chain as a TieredOrchestrator tier. Best for:
- RAG (Retrieval-Augmented Generation) over vault/corpus documents
- Document question-answering with source attribution
- Multi-step reasoning with structured chain output

**Cost:** $0 when using local Ollama (phi3:mini embeddings + CPU LLM).
**Routing:** Use when `output_type=rag_query` or task requires document retrieval.

## Usage

```python
from cohezion.inference.langchain_tier import LangChainTier, build_rag_chain

# Simple passthrough (testing)
tier = LangChainTier()
text, metrics = tier.run_sync("What is HIHO stability?")

# Full RAG over documents
docs = [
    "HIHO stability: 4x(1-x) peaks at x=0.5...",
    "LENR: lattice-confined nuclear reactions...",
]
rag_tier = build_rag_chain(documents=docs)
text, metrics = rag_tier.run_sync("How does LENR relate to HIHO?")

# As async
import asyncio

result = asyncio.run(rag_tier.run("Explain ionic cluster equilibrium"))
print(result.text, result.source_documents)
```

## Routing Table

| Task type | Use LangChain? |
|-----------|---------------|
| `rag_query` | Yes — primary tier |
| Document QA over vault | Yes |
| Web search grounding | No — use GeminiCliTier |
| Code generation | No — use iGPU tier |
| Categorical routing | No — use NPU tier |

## Graceful Degradation

When `langchain_core` is not installed:
- Returns empty text + `{"error": "langchain not installed"}`
- Compound loop escalates to next tier automatically
- Does NOT raise exceptions

## Files

- Implementation: `src/cohezion/inference/langchain_tier.py`
- Factory: `build_rag_chain(documents, llm)` — FAISS + Ollama embeddings
- Default LLM: `phi3:mini` via Ollama (localhost:11434, free)
- Fallback: passthrough chain when LangChain not available


## DOMAIN EXPERTISE
Provides expert capabilities for Langchain Rag Tier Prime within the Cohezion AGI architecture.

## INSTRUCTION
1. Execute step-by-step verification.
2. Validate outcomes against AutoHarness policies.

## VERSION
v1.0


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for LANGCHAIN RAG TIER PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## SEE ALSO
- **AUTOHARNESS_POLICY_PRIME**
- **JOURNEY_TRACKING_PRIME**
