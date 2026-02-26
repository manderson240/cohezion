---
title: "Context Management"
date: 2026-02-07
tags: [concept, agentic-ai, agent-loop-architecture, prompt-engineering]
---

## Definition

Systematic strategies for optimizing information payloads delivered to AI systems, transcending simple prompt design to encompass context retrieval, generation, and processing. Formalized by Devaria et al.'s 2024 survey analyzing 1400+ papers, covering retrieval-augmented generation (RAG), memory systems, tool-integrated reasoning, and multi-agent collaboration frameworks.

## Key Properties

- Encompasses context retrieval, generation, processing, and active management as integrated system
- Performance of LLMs fundamentally determined by contextual information quality and relevance
- Integrates RAG, memory systems, and tool-integrated reasoning
- Enables multi-agent collaboration through shared context and persistent information states
- Models excel at context understanding but struggle with long-form output generation

## Examples

- RAG systems dynamically fetching relevant documents to augment LLM prompts, improving factuality
- Chain-of-Agents framework enabling multiple LLMs to collaborate on long-context tasks in training-free manner

## Primary Sources

- Devarshi et al. (2024). *A Survey of Context Engineering for Large Language Models*. [https://arxiv.org/abs/2507.13334](https://arxiv.org/abs/2507.13334)
- Google Research (2024). *Chain of Agents: Large language models collaborating on long-context tasks*. [https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/)
- JetBrains Research (2025). *Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents*. [https://blog.jetbrains.com/research/2025/12/efficient-context-management/](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)

## Related Papers

- [[agentic-ai-memory-hierarchies]]
- [[langchain-deep-agents-context-management]]
- [[llm-in-sandbox-agentic-intelligence]]
- [[openai-codex-agent-loop]] — the Codex inner/outer loop and prompt caching strategy are concrete implementations of context management for agentic coding
- [[scaling-agent-systems]] — quantitative scaling findings show how context management directly affects error amplification in multi-agent systems
- [[data-engineering-ai-era-2026]] — "context engineering" as described for data pipelines is the data-infrastructure layer of context management: embedding machine-readable semantic, temporal, and provenance context alongside data for agent consumption
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF's AGENTS.md convention standardizes the context handoff format across agents, making cross-vendor context management interoperable

## Related Concepts

- [[agentic-ai]]
- [[agent-loop-architecture]]
- [[prompt-engineering]]
- [[ollama-context-management]] — a concrete implementation of context management for Ollama-served local models, covering truncation, chunking, and LRU-based budget tracking

## Related Lessons

- [[lesson-29-batch-cache-two-phase]] — batch cache two-phase pattern: check cache before compute; directly optimizes context retrieval at scale
- [[lesson-19-session-awareness-protocol]] — agents must explicitly load prior context at session start; context is not inherited between sessions automatically

## Relevance to Cohezion

Context management is core to Cohezion's ContextEngineeringInfrastructure, which manages a tool registry with MCP-integrated context retrieval through find_relevant_context. The SemanticCache provides multi-layer context optimization (exact hash, semantic similarity, vault persistence), while the CompoundExecutor uses vault-logged execution history and extracted patterns to dynamically assemble contextual information for each agent action.
