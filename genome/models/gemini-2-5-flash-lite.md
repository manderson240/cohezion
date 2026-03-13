---
title: "Model Card: Gemini 2.5 Flash-Lite"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, small-fast, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-2.5-flash-lite"
aspect: knower
neural:
  activation: 0.66
  stage: growing
  synapse_in: 1
  synapse_out: 3
---

# Model Card: Gemini 2.5 Flash-Lite

> [!abstract] Summary
> Gemini 2.5 Flash-Lite is the cheapest multimodal model in the Gemini 2.5 family — $0.10/MTok input with free tier and 1M context. Designed for budget-sensitive, high-volume tasks where speed and cost matter more than peak reasoning.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 2.5 Flash-Lite |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-2.5-flash-lite` |
| **Model Class** | small-fast |
| **Release Date** | 2025 (GA) |
| **Knowledge Cutoff** | ~Early 2025 |
| **System Card** | [Gemini 2.5 Flash-Lite Model Card (PDF)](https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Flash-Lite-Model-Card.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Budget quality |
| Extended thinking | No | No reasoning mode |
| Tool use | Yes | Basic function calling |
| Vision / multimodal | Yes | Text, image, video, audio |
| Code generation | Limited | Simple tasks |
| Agentic loops | Limited | Short chains only |
| Embeddings | No | Use `gemini-embedding-001` |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M |
| **Output tokens** | 64K |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $0.10 / MTok (text/image/video), $0.30 (audio) |
| **Output cost** | $0.40 / MTok |
| **Context caching** | $0.01 / MTok |
| **Tier** | Economy |
| **Free tier** | Unlimited tokens |
| **Batch discount** | 50% off |

> [!tip] Cost Comparison
> At $0.10 input / $0.40 output, this is 8x cheaper than Claude Haiku ($0.80 / $4.00) and 3x cheaper than Gemini 2.5 Flash ($0.30 / $2.50).

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Bulk text classification | Cheapest model with free tier | Claude Haiku (8x more) |
| Tag extraction at scale | Low cost per call | Gemini 3.1 Flash-Lite (newer) |
| Pre-filtering pipeline | Cheap first-pass filter | Gemini 2.5 Flash |

## Configuration in Cohezion

```json
{
  "model": "gemini-2.5-flash-lite",
  "maxOutputTokens": 2048,
  "temperature": 0.5
}
```

## Known Limitations

- No extended thinking / reasoning mode
- Superseded by Gemini 3.1 Flash-Lite
- Weakest reasoning in the Gemini family
- Not suitable for complex tasks

## Related

- [[gemini-3-1-flash-lite|Model Card: Gemini 3.1 Flash-Lite]] — Next generation
- [[gemini-2-5-flash|Model Card: Gemini 2.5 Flash]] — Higher quality
- [[claude-haiku-4-5|Model Card: Claude Haiku 4.5]] — Competitor (8x more expensive)

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
