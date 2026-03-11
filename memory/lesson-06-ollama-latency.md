---
title: Ollama Latency Spikes: Cold Start and Model Load Times Must Be Budgeted
date: 2026-02-23
severity: MEDIUM
category: infrastructure
tags: [ollama, latency, model-loading, performance]
status: validated
aspect: knower
neural:
  activation: 0.409
  stage: growing
  cluster: lessons
---

# Lesson: Ollama Latency Spikes: Cold Start and Model Load Times Must Be Budgeted

## Context

Ollama serves local LLM models. First-request latency (cold start) can be 5-30 seconds per model. Production pipelines that call Ollama without latency budgets silently stall.

## Core Learning

**Always budget for Ollama cold-start latency. Pre-warm models before pipeline execution.**

### Why This Matters
- Cold starts can exceed HTTP timeout defaults (10s) causing silent failures
- Batch inference workflows stall if the first call times out
- 38+ models loaded simultaneously degrades response times

### Pattern
```python
def warm_model(model_name: str, timeout: int = 60):
    response = requests.post("http://localhost:11434/api/generate",
        json={"model": model_name, "prompt": "ping", "stream": False},
        timeout=timeout)
    return response.status_code == 200

assert warm_model("llama3.2"), "Ollama model not ready"
```

## Recommendations

### Do
- Pre-warm critical models before starting long pipelines
- Set HTTP timeouts to 60s+ for Ollama calls
- Monitor Ollama health at http://localhost:11434/api/tags

### Don't
- Use default HTTP timeouts (10s) for Ollama calls
- Assume Ollama is warm between pipeline runs

## Related Concepts

- [[mcp-infrastructure-architecture]] - Ollama is a core inference backend
- [[concept-optimization]] - cold-start latency budgeting and model pre-warming are key optimization techniques
- [[semantic-search]] - Ollama is the inference backend for semantic search embeddings; cold starts affect pipeline reliability

## Scientific Context

- [[agentic-ai-memory-hierarchies]] — the 5-30 second cold-start latency here is the observed manifestation of the PCIe bandwidth bottleneck the paper describes: loading a 9GB model from NVMe to VRAM traverses the exact memory hierarchy the paper identifies as the primary agentic AI constraint. Pre-warming models keeps them in VRAM (hot tier), eliminating the bandwidth-limited load path entirely.
- [[llm-training-methodology-changes]] — the "efficient post-training" movement documented there is the long-term architectural fix for cold-start latency: smaller, more capable models (from smarter post-training) load faster. A model with identical quality at 2GB vs 9GB has 4-5x lower cold-start time. The efficiency gains the paper describes translate directly to lower operational latency.
- [[3-tier-hotwarmcold-model-rotation]] — the pattern that converts this lesson's insight into a systematic architecture: keep critical models pre-warmed (hot tier), load on-demand for less frequent ones (warm tier), accept cold-start only for rarely-used large models (cold tier)

## Validation

**Discovered**: Feb 2026 during pipeline optimization
**Status**: Validated in production
