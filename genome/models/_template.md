---
title: "Model Card: [Model Name]"
date: YYYY-MM-DD
version: 1
last_revised: YYYY-MM-DD
tags: [spec, model-card]
card_type: model
status: active
provider: [anthropic | google | openai | meta | ollama]
model_id: "[exact API model ID]"
---

# Model Card: [Model Name]

> [!abstract] Summary
> One-paragraph description of the model, its class (frontier/mid/small), and primary use case within Cohezion.

## Identity

| Field | Value |
|-------|-------|
| **Model** | [Display name] |
| **Provider** | [Anthropic / Google / OpenAI / Meta / Ollama] |
| **Model ID** | `[exact API string]` |
| **Model Class** | frontier / mid-tier / small-fast / embedding |
| **Release Date** | [Date] |
| **Knowledge Cutoff** | [Date] |
| **System Card** | [Link to provider's official system card if available] |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes/No | |
| Extended thinking | Yes/No | Chain-of-thought reasoning |
| Tool use | Yes/No | Function calling |
| Vision / multimodal | Yes/No | Image understanding |
| Code generation | Yes/No | |
| Agentic loops | Yes/No | Multi-step autonomous |
| Embeddings | Yes/No | |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | [Max input] |
| **Output tokens** | [Max output] |
| **Effective context** | [Practical limit before degradation] |

## Benchmarks

> [!note] Cohezion-Relevant Benchmarks
> Scores most relevant to our use cases (agentic coding, knowledge management, research).

| Benchmark | Score | Notes |
|-----------|-------|-------|
| SWE-bench Verified | [Score] | Agentic coding |
| GPQA Diamond | [Score] | Expert-level reasoning |
| MMMLU | [Score] | Broad knowledge |
| [Custom benchmark] | [Score] | [Why relevant] |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $[X] / MTok |
| **Output cost** | $[X] / MTok |
| **Latency (TTFT)** | [Time to first token] |
| **Throughput** | [Tokens/sec] |
| **Tier** | [Cost tier: premium / standard / economy] |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| [Use case 1] | [Why it's the best fit] | [Fallback model] |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **AI Safety Level** | [ASL-2 / ASL-3 / N/A] | [Provider's safety classification] |
| **Harmlessness** | [Summary] | |
| **Agentic safety** | [Summary] | |
| **Prompt injection resistance** | [Summary] | |

## Configuration in Cohezion

```json
{
  "model": "[model_id]",
  "max_tokens": 8192,
  "temperature": 0.7
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| API | [Endpoint] | [Auth method] |
| MCP | [Server name] | [How it's used via MCP] |
| Local | [Ollama model name] | [If local deployment] |

## Known Limitations

- [Limitation 1]
- [Limitation 2]

## Related

- [[related-model-card]]
- [[related-concept]]

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | YYYY-MM-DD | Initial card |
