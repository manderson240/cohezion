---
title: "Model Card: Claude Haiku 4.5"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, anthropic, small-fast, claude]
card_type: model
status: active
provider: anthropic
model_id: "claude-haiku-4-5-20251001"
aspect: knower
neural:
  activation: 0.451
  stage: growing
  cluster: specs
---

# Model Card: Claude Haiku 4.5

> [!abstract] Summary
> Claude Haiku 4.5 is Anthropic's fastest and most cost-effective model, designed for high-throughput tasks where latency and cost matter more than peak reasoning. In Cohezion, it's used for simple agent subagents, quick classification tasks, and high-volume operations where Sonnet/Opus would be wastefully expensive.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Claude Haiku 4.5 |
| **Provider** | Anthropic |
| **Model ID** | `claude-haiku-4-5-20251001` |
| **Model Class** | small-fast |
| **Release Date** | October 2025 |
| **Knowledge Cutoff** | Early 2025 |
| **System Card** | [Anthropic Haiku 4.5 System Card (PDF)](https://www-cdn.anthropic.com/7aad69bf12627d42234e01ee7c36305dc2f6a970.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Good quality for its class |
| Extended thinking | Yes | Available but limited budget |
| Tool use | Yes | Function calling supported |
| Vision / multimodal | Yes | Basic image understanding |
| Code generation | Yes | Adequate for simple tasks |
| Agentic loops | Limited | Best for single-step or short chains |
| Embeddings | No | Use dedicated embedding models |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 200K |
| **Output tokens** | 8K (standard) |
| **Effective context** | ~100K before significant quality drop |

## Benchmarks

> [!note] Source: Anthropic Haiku 4.5 System Card
> Haiku 4.5 is not benchmarked against the same suite as Opus/Sonnet on most agentic tasks.

| Benchmark | Haiku 4.5 | Notes |
|-----------|----------|-------|
| **MMMLU** | ~83% | Broad knowledge (estimated from card) |
| **Coding tasks** | Adequate | Not benchmarked on SWE-bench |
| **Safety evals** | Passed | Single-turn, multi-turn, bias evals |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $0.80 / MTok |
| **Output cost** | $4.00 / MTok |
| **Latency (TTFT)** | <1s |
| **Throughput** | Highest in Claude family |
| **Tier** | Economy |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Quick classification tasks | Lowest cost, fastest response | Sonnet if quality matters |
| Simple subagent operations | Parallel agents at low cost | Sonnet for complex analysis |
| Bulk note analysis | High throughput for vault-wide scans | Sonnet for individual deep analysis |
| Tag extraction | Simple structured output | Sonnet for nuanced tagging |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **AI Safety Level** | ASL-2 | Standard safety measures |
| **Harmlessness** | Evaluated | Single-turn and multi-turn |
| **Child safety** | Evaluated | Specific child safety testing |
| **Bias** | Evaluated | BBQ benchmark |

## Configuration in Cohezion

```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 4096,
  "temperature": 0.7
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| API | `api.anthropic.com` | Bearer token auth |
| Agent subagents | `model: "haiku"` | For quick, simple tasks |

## Known Limitations

- Significantly weaker reasoning than Sonnet/Opus — not for complex tasks
- Limited agentic capability — short chains only
- Earlier knowledge cutoff than 4.6 models
- Not suitable for /spec planning or verification

## Related

- [[claude-opus-4-6|Model Card: Claude Opus 4.6]] — Frontier tier
- [[claude-sonnet-4-6|Model Card: Claude Sonnet 4.6]] — Mid tier
- [[ai-safety-alignment]] — Safety and alignment concepts

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card from Anthropic System Card (Oct 2025) |
