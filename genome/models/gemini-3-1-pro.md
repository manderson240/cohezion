---
title: "Model Card: Gemini 3.1 Pro"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, frontier, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-3.1-pro-preview"
aspect: knower
neural:
  activation: 0.74
  stage: growing
  synapse_in: 0
  synapse_out: 4
---

# Model Card: Gemini 3.1 Pro

> [!abstract] Summary
> Gemini 3.1 Pro is Google DeepMind's latest flagship reasoning model (February 2026), the most advanced in the Gemini family. It leads on GPQA Diamond (94.3%), Terminal-Bench (68.5%), and matches Claude Opus on SWE-bench (80.6%). Natively multimodal with 1M token context window and dynamic thinking.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 3.1 Pro |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-3.1-pro-preview` |
| **Model Class** | frontier |
| **Release Date** | February 2026 (preview) |
| **Knowledge Cutoff** | ~January 2026 |
| **System Card** | [Gemini 3.1 Pro Model Card](https://deepmind.google/models/model-cards/gemini-3-1-pro/) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | State-of-the-art reasoning |
| Extended thinking | Yes | Dynamic thinking + Deep Think mode |
| Tool use | Yes | Function calling, MCP via Gemini CLI |
| Vision / multimodal | Yes | Text, image, audio, video input |
| Code generation | Yes | SWE-bench 80.6%, Terminal-Bench 68.5% |
| Agentic loops | Yes | Gemini CLI agent mode |
| Embeddings | No | Use `gemini-embedding-001` |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M |
| **Output tokens** | 64K |
| **Effective context** | Strong at 128K (MRCR 84.9%), degrades at 1M (MRCR 26.3%) |

## Benchmarks

> [!note] Source: [Gemini 3.1 Pro Model Card](https://deepmind.google/models/model-cards/gemini-3-1-pro/) (February 2026)

| Benchmark | Gemini 3.1 Pro | Gemini 3 Pro | Claude Opus 4.6 | Notes |
|-----------|---------------|-------------|-----------------|-------|
| **GPQA Diamond** | **94.3%** | 91.9% | 91.3% | Scientific reasoning — Gemini leads |
| **SWE-bench Verified** | **80.6%** | 76.2% | 80.8% | Near-parity with Opus |
| **Terminal-Bench 2.0** | **68.5%** | — | 65.4% | Agentic coding — Gemini leads |
| **ARC-AGI-2** | **77.1%** | 45.1% | 68.8% | Abstract reasoning — Gemini leads |
| **MMMLU** | **92.6%** | 91.8% | 91.1% | Broad knowledge |
| **MMMU-Pro** | **80.5%** | 81% | 73.9% | Multimodal reasoning |
| **MRCR v2 (128K)** | 84.9% | — | — | Long context |
| **LiveCodeBench Pro** | 2887 Elo | — | — | Competitive coding |

> [!tip] Key Insight
> Gemini 3.1 Pro now leads or matches Claude Opus 4.6 across nearly all benchmarks, including the coding-focused ones that were previously Claude territory.

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $2.00 / MTok (≤200K), $4.00 (>200K) |
| **Output cost** | $12.00 / MTok (≤200K), $18.00 (>200K) |
| **Context caching** | $0.20 / MTok (≤200K), $0.40 (>200K) |
| **Tier** | Premium |
| **Free tier** | Not available |
| **Batch discount** | 50% off via Batch API |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Complex reasoning tasks | Highest GPQA (94.3%) and ARC-AGI-2 (77.1%) | Claude Opus 4.6 |
| Agentic coding | Terminal-Bench leader (68.5%) | Claude Opus 4.6 |
| Long document analysis | 1M token context window | Claude (200K limit) |
| Cross-validation | Second opinion against Claude outputs | Claude Opus 4.6 |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **Safety Framework** | Google Frontier Safety Framework | All CCLs unbreached |
| **CBRN** | Below CCL | Cannot provide novel threat instructions |
| **Cyber** | Below CCL | Capability increase but below threshold |
| **Harmful Manipulation** | Below CCL | Max odds ratio 3.6x |
| **ML R&D** | Below CCL | RE-Bench score 1.27 |
| **Misalignment** | Below CCL | Nearly 100% on stealth challenges |

## Configuration in Cohezion

```json
{
  "model": "gemini-3.1-pro-preview",
  "maxOutputTokens": 8192,
  "temperature": 1.0
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| Gemini API | `generativelanguage.googleapis.com` | API key auth |
| Gemini CLI | `gemini` command | Agent mode |
| Google AI Studio | Browser | Interactive |
| Vertex AI | Google Cloud | Enterprise |

## Known Limitations

- Preview status — may change before GA
- Long context degrades significantly at 1M tokens (MRCR drops from 84.9% at 128K to 26.3% at 1M)
- More expensive than Gemini 2.5 Pro ($2.00 vs $1.25 input)
- No free tier (unlike 2.5 Pro)

## Related

- [[gemini-2-5-pro|Model Card: Gemini 2.5 Pro]] — Previous generation, stable
- [[gemini-3-flash|Model Card: Gemini 3 Flash]] — Flash tier counterpart
- [[claude-opus-4-6|Model Card: Claude Opus 4.6]] — Primary competitor
- [[ide-and-model-providers]] — Integration points

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card from Google model card (Feb 2026) |
