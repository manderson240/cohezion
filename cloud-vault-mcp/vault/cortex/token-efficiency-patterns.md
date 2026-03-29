---
title: Token Efficiency Patterns
date: 2026-02-23
tags: [token-efficiency, compound-engineering, patterns, meta-learning]
related_concepts: [token-efficiency, compound-engineering, meta-learning, context-management, semantic-search]
status: active
aspect: knower
neural:
  activation: 0.96
  stage: mature
  synapse_in: 18
  synapse_out: 16
---

# Token Efficiency Patterns

Token efficiency patterns are concrete, reusable techniques for reducing LLM token consumption in agentic workflows without sacrificing output quality. They translate the abstract [[token-efficiency]] principle into specific implementation choices: when to batch, when to cache, how to scope context reads, when to delegate to cheaper models, and when to use local inference instead of cloud APIs.

These patterns emerged from empirical retrospectives across Cohezion sessions. The Kyutai postmortem (61K tokens wasted on infrastructure before validation) produced the implementation-first pattern. The Sheets research pipeline (4 parallel Haiku agents with batch updates) produced the parallel-delegation and batch-operations patterns. The GraphRAG sessions produced the two-phase cache pattern. Each pattern has a measured ROI that justifies the overhead of following it.

Applied together, these patterns compound: a session that uses the right model, batches operations, caches results, loads only relevant context, and validates before scaling can achieve 10-20x token efficiency compared to naive approaches — making previously cost-prohibitive automation economically feasible.

## Key Patterns

### 1. Batch Cache Two-Phase
Check cache before computing. Load cached embeddings in one batch, compute only misses. Delivers 60% reduction in semantic search compute costs.
- [[lesson-29-batch-cache-two-phase]]

### 2. Team Agent Threshold
Single agents outperform teams for tasks under ~2 hours of work. Coordination overhead (2-5K tokens per handoff) exceeds benefits at low task complexity.
- [[lesson-11-team-agent-efficiency]]

### 3. Experience-Guided Loading
Load semantically relevant vault context at session start rather than a fixed system prompt. Grounds new work in prior decisions without loading everything.
- [[lesson-37-experience-guided-execution-works-new]]

### 4. Implementation-First Validation
Build one working feature before writing infrastructure, tests, or documentation. Prevents 61K-token infrastructure investments in unvalidated concepts.
- [[implementation-first-infrastructure-later|implementation-first-infrastructure-later]]

### 5. Model Delegation by Task Type
- Haiku: web research, JSON extraction, simple classification (1/3 Sonnet cost)
- Sonnet: code writing, architecture, debugging (balanced)
- Opus: novel reasoning, strategic planning (5x Sonnet cost)
- Local Ollama: embeddings, classification, batch inference ($0 API cost)

### 6. Scoped Context Reads
Use `vault_find_relevant_context(query)` to fetch only semantically relevant notes rather than loading the full vault. Combined with [[semantic-search]], this targets the 5-10 most relevant notes for any given task.

## Related
- [[token-efficiency]] — the principle these patterns implement
- [[compound-engineering]] — the methodology these patterns serve
- [[meta-learning]] — the process by which these patterns were discovered and validated
- [[context-management]] — the broader discipline of context optimization
- [[semantic-search]] — the retrieval mechanism enabling scoped context reads
- [[ADOPTION_CHECKLIST]] — team adoption checklist that operationalizes these token efficiency patterns into repeatable workflows
- [[2026-02-19-token-limit-error-prevention-implemented|Token Limit Error Prevention]] — a complementary error prevention pattern that guards against token limit violations at runtime
- [[canvas-driven-manual-linking]] — a concrete token-efficient vault enrichment pattern using canvas-driven linking instead of algorithmic approaches
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success]] — empirical validation of token-efficient compound engineering yielding production results
- [[2026-02-10-token-efficient-compound-engineering-roadmap]] — the strategic roadmap that established token efficiency as a compound engineering principle
- [[2026-02-10-compound-engineering-meta-learning]] — meta-learning decision that identified token efficiency patterns through retrospective analysis
- [[2026-02-10-claude-log-mining-architecture]] — log mining architecture that surfaces token usage patterns from session histories

## Agent Outputs

- **High Complexity Targets Analysis** — `Agents/Antigravity/42233b97-45f7-4a48-bd44-7a7be04e48c9/high_complexity_targets.md`

## Skills

- TOKEN_EFFICIENCY_PRIME — Batching, caching, and pruning patterns
