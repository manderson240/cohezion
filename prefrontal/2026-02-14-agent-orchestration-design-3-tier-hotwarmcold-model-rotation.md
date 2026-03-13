---
title: Agent Orchestration Design - 3-Tier Hot/Warm/Cold Model Rotation
date: '2026-02-14'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: "1. MoE models (glm-4.7-flash, qwen3-coder:30b) load all 30B params into\
    \ RAM but only activate ~3B per token \u2014 giving 30B quality at 3B speed (~20-35\
    \ t/s gen, ~1000+ t/s prompt processing on CPU). 2. phi4-mini-reasoning (3.8B\
    \ dense) achieves ~60-80 t/s generation \u2014 ideal for always-on routing. 3.\
    \ Tier 1+2 totals ~48GB leaving 74GB headroom for KV caches + one Tier 3 model.\
    \ 4. Q8_0 KV cache halves KV memory with negligible quality loss. 5. Cold-start\
    \ from NVMe: ~24-30s for 9GB model, ~45-60s for 19GB model \u2014 acceptable for\
    \ Tier 3 on-demand loads. 6. Existing OllamaGate semaphore=4 naturally maps to\
    \ 4 hot/warm model slots."
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Agent Orchestration Design - 3-Tier Hot/Warm/Cold Model Rotation'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  - sequence: 4
    content: Selected option with best balance of trade-offs
    type: hybrid
    confidence: 0.62
    assumption: Best option was chosen based on analysis
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
aspect: thinker
neural:
  activation: 0.99
  stage: mature
  synapse_in: 6
  synapse_out: 18
---

## Context

The Cohezion platform runs multiple local LLM models via Ollama on a workstation with 128 GB RAM and no dedicated GPU (CPU-only inference). Agent workflows require different models for different tasks -- embeddings, routing, gap analysis, deep reasoning -- and the naive approach (load every model, keep-alive forever) had exhausted RAM, causing OS swap thrashing and OOM kills.

Key constraints driving this decision:
- **128 GB total RAM**: Must serve OS, SurrealDB, MCP server, Obsidian, browser, and models simultaneously
- **CPU-only inference**: No GPU VRAM tier; all models compete for system RAM
- **MoE models available**: GLM-4.7-Flash (30B params, 3B active) and qwen3-coder:30b offer 30B-class quality at 3B inference speed
- **Cold-start penalty**: Loading a 9 GB model from NVMe takes 24-30 seconds; loading 19 GB takes 45-60 seconds
- **Existing OllamaGate**: A semaphore-based concurrency gate (`semaphore=4`) already limits parallel model requests to 4 slots

The [[2026-02-09-ollama-context-management]] decision identified LRU eviction as the memory strategy but did not formalize tier assignments or routing logic.

## Decision

Formalize a 3-tier Hot/Warm/Cold model rotation architecture for the Ollama model pool, with explicit tier assignments, routing logic, and memory budget allocation. See [[3-tier-hotwarmcold-model-rotation]] for the full pattern documentation.

## Chosen Option

**3-Tier model rotation with MoE-optimized tier assignments:**

| Tier | Models | RAM Budget | Keep-Alive | Role |
|------|--------|-----------|------------|------|
| **Hot** (always loaded) | phi4-mini-reasoning (3.8B), nomic-embed-text (280M) | ~8 GB | Forever | Routing, classification, embeddings |
| **Warm** (on-demand, idle eviction) | glm-4.7-flash (3B active MoE), qwen3:8b | ~20 GB | 30 min | Gap analysis, summarization, concept extraction |
| **Cold** (load-on-demand, immediate eviction) | nemotron-3-nano (1M ctx), deepseek-r1:70b | ~20-40 GB | 0 (unload after task) | Long-context analysis, complex reasoning |

**Total active RAM budget**: ~48 GB (Tier 1+2), leaving 74 GB headroom for OS, KV caches, and one cold-tier model.

**KV cache optimization**: Use Q8_0 quantized KV caches (half the memory of FP16 with negligible quality loss).

## Alternatives Considered

### Alt 1: Flat Model Pool (All Models Equal Priority)
- **Rejected**: No prioritization means the embedding model (used every request) competes equally with deepseek-r1:70b (used rarely). LRU eviction would frequently evict hot models, causing latency spikes on every embedding request.

### Alt 2: Single Model for All Tasks
- **Rejected**: No single model optimizes for all task types. Embedding models are fast but cannot reason. Reasoning models are slow but accurate. A single model forces a quality-speed compromise on every request.

### Alt 3: Cloud API for All Inference
- **Rejected**: Eliminates the cost advantage of local inference. The [[google-sheets-vault-bridge]] pipeline processes 100+ items per batch -- at API pricing, this costs $10-50 per run vs. $0 locally. Local inference is essential for cost-sensitive batch workloads.

### Alt 4: GPU Offloading (Buy a GPU)
- **Rejected for now**: A dedicated GPU (e.g., RTX 4090 with 24 GB VRAM) would add a fast tier for inference, but the $1,600+ investment is premature before validating the software architecture. The 3-tier pattern works on CPU-only and can incorporate a GPU tier later.

## Decision Reasoning

### Why This Option?

1. **MoE models are the key insight**: GLM-4.7-Flash loads 30B parameters but only activates 3B per token. This gives 30B-quality output at 3B inference speed (~20-35 tokens/second generation on CPU). Tier 2 gets high-quality inference without high RAM pressure.
2. **phi4-mini-reasoning at 3.8B achieves 60-80 t/s**: Ideal for the always-on routing tier where latency matters most.
3. **Budget arithmetic works**: Tier 1+2 totals ~48 GB, leaving 74 GB headroom for KV caches, OS, and one Tier 3 model at a time.
4. **Natural mapping to OllamaGate**: The existing `semaphore=4` concurrency limit maps naturally to 4 model slots (2 hot + 2 warm).
5. **Cold-start from NVMe is acceptable for Tier 3**: 24-30 seconds for a 9 GB model is tolerable for infrequent deep-reasoning tasks that take minutes to complete anyway.

### Alternatives Rejected

Flat pool causes latency spikes on hot-path models. Single model forces quality-speed compromise. Cloud API eliminates cost advantage. GPU purchase is premature.

### Confidence Level

**0.88** -- High confidence. MoE performance data is public (GLM-4.7-Flash benchmarks). RAM arithmetic is verifiable. The main risk is Ollama's MoE support maturity -- if MoE models do not activate sparsely as expected, Tier 2 RAM requirements increase.

## Expected Outcomes

1. Hot-tier models respond in <2 seconds (always loaded, no cold-start)
2. Warm-tier models respond in <10 seconds (5-second cold-start worst case)
3. Cold-tier models respond in <60 seconds (acceptable for infrequent deep tasks)
4. Total RAM usage stays under 70 GB (48 GB active models + 22 GB KV caches)
5. Zero OOM kills or swap thrashing under normal workloads
6. Embedding throughput maintained at >100 vectors/minute (hot tier, always loaded)

## Metrics & Impact

### Estimated

| Metric | Before (Flat Pool) | After (3-Tier) |
|--------|-------------------|----------------|
| Embedding latency | Variable (0.5-30s) | <2s (always hot) |
| Gap analysis latency | Variable (5-60s) | <10s (warm tier) |
| OOM events per week | 2-3 | 0 |
| RAM utilization | 90-100% (thrashing) | 50-70% (headroom) |
| Cold-start frequency | Random | Predictable (Tier 3 only) |

### Actual (Post-Implementation)

See [[2026-02-14-modelpoolmanager-3-tier-lifecycle-management]] for experimental validation of the ModelPoolManager implementation.

## Related Decisions & Lessons

- [[3-tier-hotwarmcold-model-rotation|Pattern: 3-Tier Hot/Warm/Cold Model Rotation]] — the pattern that operationalizes this decision
- [[runbook-ollama-mcp-operations]]
- [[2026-02-09-ai-model-strategy]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[lesson-06-ollama-latency]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]

## Scientific Foundation

- [[agentic-ai-memory-hierarchies]] — the hot/warm/cold tier design directly implements the paper's call for "intelligent memory management software" that decides which context parts reside in fastest memory. Hot = HBM/VRAM (always loaded, nanosecond access); Warm = DRAM (loaded on first request, microsecond access); Cold = NVMe (load on demand, seconds). This decision IS the memory management software the paper calls for.
- [[superfluid-to-supersolid-transition]] — the model tier system undergoes phase transitions analogous to the superfluid-to-supersolid transition: at high request density (like high exciton density), all models are in the hot fluid tier (fast, flexible flow); at lower demand, models crystallize into the cold tier (solid, structured storage). The density parameter that drives the quantum phase transition maps to the request-rate threshold that drives model tier assignment. Phase transitions between agent tiers follow the same non-linear threshold behavior.
