---
title: 3-Tier Hot/Warm/Cold Model Rotation for Local LLM Orchestration
date: 2026-02-23
tags: [pattern, ollama, performance, model-selection]
status: stub
aspect: thinker
neural:
  activation: 0.82
  stage: growing
  synapse_in: 14
  synapse_out: 9
---

# 3-Tier Hot/Warm/Cold Model Rotation for Local LLM Orchestration

## Problem

Local LLM orchestration via Ollama faces a fundamental tradeoff: loading a model into GPU VRAM (or system RAM) takes 5-30 seconds, but keeping all models loaded simultaneously exhausts memory. A naive approach -- loading whatever model is needed on demand -- causes unpredictable latency spikes when the requested model is cold. Conversely, keeping every model always-loaded (the "keep-alive forever" approach) works only until RAM is full, then triggers OOM kills or OS swap thrashing.

Agent workflows exacerbate this: a single session might need embeddings (small model, high frequency), gap analysis (mid-size model, moderate frequency), and deep reasoning (large model, low frequency) -- each requiring a different model at different times.

## Solution

Apply a tiered rotation strategy inspired by CPU cache hierarchies:

- **Hot tier** (always loaded, <2 GB RAM): Small models for high-frequency, low-latency tasks like classification, routing, and embeddings. These stay in GPU VRAM or pinned RAM with `keep-alive: forever`.
- **Warm tier** (loaded on demand, 4-16 GB RAM): Mid-size models for standard inference tasks like summarization, concept extraction, and gap analysis. These are loaded when needed and evicted after a configurable idle timeout (e.g., 30-60 minutes).
- **Cold tier** (slow startup, 16+ GB RAM): Large models for complex reasoning, code generation, or multi-step analysis. These are loaded only on explicit request, used for the duration of the task, and immediately unloaded.

### Tier Assignment

```yaml
hot_tier:    # Always loaded, <2s response
  - nomic-embed-text          # 280 MB, embeddings
  - snowflake-arctic-embed    # 480 MB, MRL embeddings
  - phi3:mini                 # 2.2 GB, routing/classification

warm_tier:   # 5-10s cold start, 30min idle eviction
  - glm-4.7-flash            # ~5 GB (MoE, 3B active), gap analysis
  - phi4-mini-reasoning       # ~4 GB, structured reasoning
  - qwen3:8b                 # ~5 GB, general tasks

cold_tier:   # 15-30s cold start, immediate eviction after task
  - nemotron-3-nano           # ~8 GB, 1M context tasks
  - deepseek-r1:70b           # ~40 GB, complex reasoning (if GPU available)
```

### Routing Logic

```python
def select_tier(task_type: str, content_length: int) -> str:
    if task_type in ("embed", "classify", "route"):
        return "hot"
    elif task_type in ("summarize", "extract", "gap_analysis"):
        return "warm"
    elif task_type in ("reason", "code_gen", "long_context"):
        return "cold"
    # Content length override: >200K tokens always needs cold tier
    if content_length > 200_000:
        return "cold"
    return "warm"  # default
```

## When to Use

- Running multiple Ollama models on a single machine with limited RAM (16-64 GB)
- Agent workflows that mix high-frequency small tasks with occasional large tasks
- Any system where model cold-start latency impacts user experience or pipeline throughput
- Environments where GPU VRAM is the bottleneck (consumer GPUs with 8-24 GB)

## When NOT to Use

- Single-model deployments (only one model needed -- just keep it loaded)
- Cloud API inference (latency is network-bound, not model-loading-bound)
- Systems with unlimited RAM/VRAM (e.g., multi-GPU server clusters where all models fit simultaneously)

## Examples

**Agent session flow:**
1. Session starts -- hot tier models already loaded (embeddings, classifier)
2. User asks for concept extraction from 5 papers -- warm tier `glm-4.7-flash` loaded (~5s), processes all 5, stays loaded for 30 min
3. User asks for deep reasoning on a complex architecture question -- cold tier `deepseek-r1:70b` loaded (~25s), processes task, immediately evicted
4. 35 minutes pass with no warm-tier requests -- `glm-4.7-flash` evicted automatically
5. New embedding request arrives -- hot tier `nomic-embed-text` responds in <100ms (always loaded)

## Key Design Decisions

- **LRU eviction for warm tier**: Least Recently Used eviction matches actual usage patterns -- models used recently are likely to be used again soon
- **Immediate eviction for cold tier**: Large models consume too much RAM to justify keeping loaded on the chance of reuse
- **Hot tier models must fit in <4 GB total**: This ensures hot tier never competes with warm/cold for memory
- **Tier assignment is task-based, not model-based**: The same model could be hot for one deployment and warm for another depending on usage frequency

## Related

- [[lesson-06-ollama-latency]]
- [[mcp-infrastructure-architecture]]
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation|Decision: Agent Orchestration Design — 3-Tier Hot/Warm/Cold Model Rotation]]
- [[2026-02-09-ai-model-strategy|Decision: AI Model Strategy]]
- [[2026-02-09-ollama-mcp-server|Decision: Ollama MCP Server]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]] — SOTA model selection that determined which models fill each tier (GLM-4.7-Flash as hot/warm, phi4-mini-reasoning as routing tier)
- [[2026-02-14-modelpoolmanager-3-tier-lifecycle-management|Experiment: ModelPoolManager 3-Tier Lifecycle Management]] — experimental validation of the implementation

## Scientific Foundation

- [[agentic-ai-memory-hierarchies]] — the hardware KV-cache hierarchy problem described there (HBM → DRAM → PCIe bottleneck) is exactly what this Hot/Warm/Cold pattern solves at the software layer: hot models stay in GPU VRAM (fast tier), warm models in system RAM (medium tier), cold models on NVMe (slow tier). This pattern is a direct software implementation of the memory hierarchy principles the paper identifies as the critical constraint for agentic AI. The "intelligent memory management software" the paper calls for IS this pattern.
- [[lesson-29-batch-cache-two-phase]] — the two-phase cache lookup (check before compute) is the micro-level equivalent of the tier-selection logic: always query the hottest available tier before descending to a slower one. Both prevent unnecessary cold-start latency.
