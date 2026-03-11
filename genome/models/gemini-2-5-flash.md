---
title: "Model Card: Gemini 2.5 Flash"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, mid-tier, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-2.5-flash"
aspect: knower
neural:
  activation: 0.442
  stage: growing
  cluster: specs
---

# Model Card: Gemini 2.5 Flash

> [!abstract] Summary
> Gemini 2.5 Flash is Google's stable workhorse model — best price-performance for reasoning tasks with a 1M token context window and hybrid thinking budgets. First model in the Gemini family with configurable reasoning depth. $0.30/MTok input with free tier. The Gemini equivalent of Claude Sonnet.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 2.5 Flash |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-2.5-flash` |
| **Model Class** | mid-tier |
| **Release Date** | June 2025 (GA) |
| **Knowledge Cutoff** | January 2025 |
| **System Card** | [Gemini 2.5 Flash Model Card (PDF)](https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Flash-Model-Card.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Good reasoning at speed |
| Extended thinking | Yes | Hybrid — configurable thinking budgets |
| Tool use | Yes | Native function calling |
| Vision / multimodal | Yes | Text, image, audio, video input |
| Code generation | Yes | Solid coding performance |
| Agentic loops | Yes | Multi-step workflows |
| Embeddings | No | Use `gemini-embedding-001` |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M |
| **Output tokens** | 64K |
| **Long context pricing** | 2x rate above 200K tokens |

## Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| **Intelligence Index** | 21 | Artificial Analysis (above 15 avg) |
| **vs Gemini 3 Flash** | -15% relative | Superseded by 3 Flash |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $0.30 / MTok (text/image/video), $1.00 (audio) |
| **Output cost** | $2.50 / MTok |
| **Context caching** | $0.03 / MTok |
| **Tier** | Standard |
| **Free tier** | Unlimited tokens |
| **Batch discount** | 50% off |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Cost-sensitive reasoning | Cheapest stable reasoning model | 2.5 Flash-Lite (even cheaper) |
| Long document processing | 1M context at low cost | Gemini 2.5 Pro (better quality) |
| High-volume agentic tasks | Free tier + good quality | Gemini 3 Flash (newer) |

## Configuration in Cohezion

```json
{
  "model": "gemini-2.5-flash",
  "maxOutputTokens": 8192,
  "temperature": 1.0
}
```

## Known Limitations

- Superseded by Gemini 3 Flash (15% improvement)
- Verbose output — token usage can be higher than expected
- Knowledge cutoff January 2025

## Related

- [[gemini-3-flash|Model Card: Gemini 3 Flash]] — Next generation (15% better)
- [[gemini-2-5-flash-lite|Model Card: Gemini 2.5 Flash-Lite]] — Budget version
- [[gemini-2-5-pro|Model Card: Gemini 2.5 Pro]] — Pro tier
- [[claude-sonnet-4-6|Model Card: Claude Sonnet 4.6]] — Competitor

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card |
