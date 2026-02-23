---
title: Ollama Latency Spikes: Cold Start and Model Load Times Must Be Budgeted
date: 2026-02-23
severity: MEDIUM
category: infrastructure
tags: [ollama, latency, model-loading, performance]
status: validated
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

## Validation

**Discovered**: Feb 2026 during pipeline optimization
**Status**: Validated in production
