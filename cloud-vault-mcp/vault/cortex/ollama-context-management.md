---
title: Ollama Context Management
date: 2026-02-23
tags: [infrastructure, ollama, performance, context-management]
status: active
aspect: knower
neural:
  activation: 0.82
  stage: growing
  synapse_in: 7
  synapse_out: 7
---

# Ollama Context Management

Strategies for managing context windows in locally-served Ollama models, including truncation, summarization, context budget tracking, and automatic chunking. This concept addresses the practical challenges of running LLMs locally where context window limits, VRAM constraints, and latency trade-offs differ significantly from cloud-hosted API models.

## Definition

Ollama context management encompasses the techniques used to maximize the effective use of a local model's context window while staying within hardware constraints. Unlike cloud APIs with large (128K+) context windows, locally-served models typically operate with 2K-8K context windows, making efficient context usage critical.

## Key Strategies

### Truncation

The simplest approach: when input exceeds the model's context window, truncate from the beginning (oldest content removed first). Fast but lossy — important early context may be silently dropped.

### Summarization

Before context overflow, summarize earlier conversation turns into a compressed representation that preserves key facts. More expensive computationally but retains critical information. The Model Wrangler extension implements this as a pre-processing step.

### Context Budget Tracking

Monitor token usage in real-time and alert when approaching limits. The Cohezion platform uses `cz context --json` to report percentage usage and trigger handoff protocols at 80% and 90% thresholds.

### Automatic Chunking

For large inputs (e.g., vault documents fed to embedding models), automatically split content into context-sized chunks, process each independently, then aggregate results. The Ollama MCP server implements this for batch embedding operations.

## Key Properties

- **Model-dependent:** Different Ollama models have different context window sizes (Llama 3 supports 8K, Mistral 7B supports 8K, some fine-tunes support 32K+)
- **VRAM-bound:** Larger context windows require proportionally more GPU memory; a model that fits in 8GB VRAM at 4K context may not fit at 32K
- **Latency-sensitive:** Context processing time scales roughly linearly with context length for prefill and quadratically for attention computation

## Sources

- [Ollama Documentation](https://ollama.com/)
- [Ollama GitHub — Context Window Settings](https://github.com/ollama/ollama)

## Related

- [[lesson-06-ollama-latency]] — lessons learned about Ollama latency characteristics and their impact on context management
- [[mcp-infrastructure-architecture]] — the infrastructure layer where Ollama context management operates
- [[2026-02-09-ollama-context-management]] — the ADR defining the Model Wrangler extension strategy
- [[2026-02-09-ollama-mcp-server]] — decision to elevate Ollama management to infrastructure via dedicated MCP server
- [[context-management]] — parent concept; Ollama context management is a concrete implementation for local LLMs
- [[token-efficiency]] — efficient token use is the goal of context management strategies
- [[semantic-search]] — the Ollama MCP server provides embedding-based semantic search that depends on proper context chunking

## Relevance to Cohezion

Ollama context management is critical infrastructure for the Cohezion platform's local AI capabilities. The Ollama MCP server (port 11434) provides embedding generation and vector search that power the vault's semantic search, decision linking, and concept similarity features. Effective context management ensures these operations complete within VRAM and latency budgets, especially during batch operations like knowledge graph densification sprints that process hundreds of vault documents.
