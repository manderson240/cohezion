---
title: "Model Card: Gemini 3.1 Flash-Lite"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, small-fast, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-3.1-flash-lite-preview"
aspect: knower
neural:
  activation: 0.66
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Model Card: Gemini 3.1 Flash-Lite

> [!abstract] Summary
> Gemini 3.1 Flash-Lite is Google's fastest and most cost-efficient Gemini 3 model. At $0.25/MTok input and $1.50 output, it delivers impressive performance (86.9% GPQA Diamond, 76.8% MMMU-Pro) with 2.5x faster time-to-first-token than 2.5 Flash. Google's answer to Claude Haiku.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 3.1 Flash-Lite |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-3.1-flash-lite-preview` |
| **Model Class** | small-fast |
| **Release Date** | March 2026 (preview) |
| **Knowledge Cutoff** | ~Early 2026 |
| **System Card** | [Gemini 3.1 Flash-Lite Model Card](https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Fast and cost-efficient |
| Extended thinking | Limited | Lightweight reasoning |
| Tool use | Yes | Basic function calling |
| Vision / multimodal | Yes | Text, image, video, audio |
| Code generation | Yes | Adequate |
| Agentic loops | Limited | Short chains |
| Embeddings | No | Use `gemini-embedding-001` |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M |
| **Output tokens** | 64K |

## Benchmarks

| Benchmark | 3.1 Flash-Lite | Notes |
|-----------|---------------|-------|
| **GPQA Diamond** | 86.9% | Strong for economy tier |
| **MMMU-Pro** | 76.8% | Multimodal reasoning |
| **Arena Elo** | 1432 | Arena.ai leaderboard |
| **Speed vs 2.5 Flash** | 2.5x faster TTFT | 45% faster output |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $0.25 / MTok (text/image/video), $0.50 (audio) |
| **Output cost** | $1.50 / MTok |
| **Context caching** | $0.025 / MTok |
| **Latency** | Fastest in Gemini 3 family |
| **Tier** | Economy |
| **Free tier** | Unlimited tokens |
| **Batch discount** | 50% off |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Bulk classification | Cheapest + free tier | Claude Haiku ($0.80 input) |
| High-volume processing | Fastest TTFT in class | Gemini 2.5 Flash-Lite |
| Simple agent subtasks | Low cost per operation | Claude Haiku |

## Configuration in Cohezion

```json
{
  "model": "gemini-3.1-flash-lite-preview",
  "maxOutputTokens": 4096,
  "temperature": 0.7
}
```

## Known Limitations

- Preview status
- Not suitable for complex reasoning (use 3.1 Pro or 3 Flash)
- Lighter reasoning than full Flash models

## Related

- [[gemini-3-flash|Model Card: Gemini 3 Flash]] — Full Flash tier
- [[gemini-2-5-flash-lite|Model Card: Gemini 2.5 Flash-Lite]] — Previous generation
- [[claude-haiku-4-5|Model Card: Claude Haiku 4.5]] — Direct competitor

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
