---
title: "Model Card: Gemini 3 Flash"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, mid-tier, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-3-flash-preview"
aspect: knower
neural:
  activation: 0.455
  stage: growing
  cluster: specs
---

# Model Card: Gemini 3 Flash

> [!abstract] Summary
> Gemini 3 Flash delivers frontier-class performance rivaling larger models at a fraction of the cost. It offers 15% improvement over Gemini 2.5 Flash across benchmarks, with configurable thinking levels, tool use, and 1M token context. Google's direct competitor to Claude Sonnet 4.6.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 3 Flash |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-3-flash-preview` |
| **Model Class** | mid-tier |
| **Release Date** | 2026 (preview) |
| **Knowledge Cutoff** | ~Early 2025 |
| **System Card** | [Gemini 3 Flash](https://deepmind.google/models/gemini/flash/) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Strong reasoning at speed |
| Extended thinking | Yes | Configurable levels: minimal, low, medium, high |
| Tool use | Yes | Native function calling |
| Vision / multimodal | Yes | Text, image, audio, video |
| Code generation | Yes | Strong coding and instruction-following |
| Agentic loops | Yes | Optimized for agentic workflows |
| Embeddings | No | Use `gemini-embedding-001` |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M |
| **Output tokens** | 64K |
| **Effective context** | Good across full range |

## Benchmarks

| Metric | Gemini 3 Flash | vs Gemini 2.5 Flash | Notes |
|--------|---------------|---------------------|-------|
| **Overall accuracy** | — | +15% relative | Significant improvement |
| **Intelligence Index** | Rank #11 globally | — | Artificial Analysis benchmark |
| **Coding** | Strong | Improved | Agentic coding focus |
| **Instruction following** | Excellent | Improved | Configurable thinking |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $0.50 / MTok (text/image/video), $1.00 (audio) |
| **Output cost** | $3.00 / MTok |
| **Context caching** | $0.05 / MTok (text/image/video) |
| **Latency** | Fast — optimized for speed |
| **Tier** | Standard |
| **Free tier** | Unlimited tokens |
| **Batch discount** | 50% off via Batch API |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| High-volume analysis | Free tier + fast throughput | Gemini 2.5 Flash (cheaper) |
| Agentic workflows | Optimized for agent loops | Claude Sonnet 4.6 |
| Cross-validation | Alternative to Claude at low cost | Gemini 2.5 Flash |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **Safety Framework** | Google Frontier Safety Framework | Standard evaluations |
| **Harmlessness** | Google Gen AI policies | Content safety |

## Configuration in Cohezion

```json
{
  "model": "gemini-3-flash-preview",
  "maxOutputTokens": 8192,
  "temperature": 1.0
}
```

## Known Limitations

- Preview status
- Still behind Gemini 3.1 Pro on complex reasoning tasks
- More expensive than 2.5 Flash ($0.50 vs $0.30 input)

## Related

- [[gemini-3-1-pro|Model Card: Gemini 3.1 Pro]] — Pro tier counterpart
- [[gemini-2-5-flash|Model Card: Gemini 2.5 Flash]] — Previous generation Flash
- [[gemini-3-1-flash-lite|Model Card: Gemini 3.1 Flash-Lite]] — Budget Flash
- [[claude-sonnet-4-6|Model Card: Claude Sonnet 4.6]] — Primary competitor

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
