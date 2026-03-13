---
title: "Context Management"
date: 2026-02-07
tags: [concept, agentic-ai, agent-loop-architecture, prompt-engineering]
related_concepts: [agent-context, token-efficiency, semantic-search, compound-engineering, cloud-vault-mcp]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 69
  synapse_out: 21
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
- [[Autonomous-Context-Hooks-Guide]] — autonomous hooks that automate context loading before prompts and result saving after responses
- [[2026-02-19-token-limit-error-prevention-implemented|Token Limit Error Prevention]] — implements calculate_max_tokens and auto-retry to prevent context window overflow errors
- [[cognitive-science]] — working memory models from cognitive science directly inform context window design and attention management in AI systems
- [[ollama-context-management]] — concrete context management strategies for locally-served Ollama models

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations
- VAULT_MANIFEST — the agent orientation map providing directory routing rules and conventions that agents load at session start for context awareness

## Related Patterns

- [[sanitize-env-var-path-components]] — session IDs from environment variables are context artifacts requiring sanitization before filesystem use

## Related Lessons

- [[lesson-29-batch-cache-two-phase]] — batch cache two-phase pattern: check cache before compute; directly optimizes context retrieval at scale
- [[lesson-19-session-awareness-protocol]] — agents must explicitly load prior context at session start; context is not inherited between sessions automatically

## Relevance to Cohezion

Context management is core to Cohezion's ContextEngineeringInfrastructure, which manages a tool registry with MCP-integrated context retrieval through find_relevant_context. The SemanticCache provides multi-layer context optimization (exact hash, semantic similarity, vault persistence), while the CompoundExecutor uses vault-logged execution history and extracted patterns to dynamically assemble contextual information for each agent action.

## Session References

- [[session-50-handoff]] — SemanticCache L2 benefits from 10x faster FLUME queries for context retrieval

## Agent Outputs

- advanced_persistence_plan — Advanced Persistence Plan
- implementation_plan_context — Implementation Plan: Context management
- implementation_plan_mission — Implementation Plan: Mission context
- **Walkthrough: Recovering from Initial Memory Loss** — `Agents/Antigravity/30480d59-daec-4ea2-a981-eb404e8f78c5/walkthrough.md`

## Skills

- MEMORY_MCP_PRIME — Persistent memory across sessions
- PERSISTENT_UNIVERSE_PRIME — Institutional intelligence via stateful memory
- RECOVERY_PRIME — Session recovery and state hydration
- VAULT_CONTEXT_HOOKS_PRIME — Autonomous vault context hooks for pre-operation loading and post-operation saving across AI agents

## Plans
- [[2026-02-24-context-awareness-engine-improvements|Context Awareness Engine Improvements]] — plan for predictive context budget management
- [[2026-02-26-context-awareness-next-tier|Context Awareness Next Tier]] — plan for active budget management and phase transition gating
