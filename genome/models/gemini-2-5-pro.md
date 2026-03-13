---
title: "Model Card: Gemini 2.5 Pro"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, google, frontier, gemini]
card_type: model
status: active
provider: google
model_id: "gemini-2.5-pro"
aspect: knower
neural:
  activation: 0.73
  stage: growing
  synapse_in: 0
  synapse_out: 4
---

# Model Card: Gemini 2.5 Pro

> [!abstract] Summary
> Gemini 2.5 Pro is Google DeepMind's frontier reasoning model, built on a sparse Mixture-of-Experts (MoE) Transformer architecture. It supports text, audio, images, video, and code input. In Cohezion, it's available via Gemini CLI and API for tasks where multi-modal reasoning or alternative perspective is valuable.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Gemini 2.5 Pro |
| **Provider** | Google DeepMind |
| **Model ID** | `gemini-2.5-pro` |
| **Model Class** | frontier |
| **Release Date** | June 2025 (GA) |
| **Knowledge Cutoff** | Early 2025 |
| **System Card** | [Google Gemini 2.5 Pro Model Card (PDF)](https://storage.googleapis.com/model-cards/documents/gemini-2.5-pro.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | Strong reasoning, competitive with Opus |
| Extended thinking | Yes | "Deep Think" variant available |
| Tool use | Yes | Function calling, MCP via Gemini CLI |
| Vision / multimodal | Yes | Text, image, audio, video input |
| Code generation | Yes | Competitive on coding benchmarks |
| Agentic loops | Yes | Via Gemini CLI agent mode |
| Embeddings | No | Use Gemma embedding models |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 1M+ |
| **Output tokens** | 64K |
| **Effective context** | Very long context — entire codebases |

## Benchmarks (vs Claude Family)

> [!note] Source: Anthropic Opus 4.6 System Card (Table 2.3.A) — third-party comparison

| Benchmark | Gemini 3 Pro | Opus 4.6 | Sonnet 4.6 | Notes |
|-----------|-------------|----------|-----------|-------|
| **SWE-bench Verified** | 76.2% | 80.8% | — | Agentic coding |
| **Terminal-Bench** | 56.2% | 65.4% | — | Terminal tasks |
| **τ²-bench (Retail)** | 85.3% | 91.9% | — | Customer service |
| **ARC-AGI-2** | 45.1% | 68.8% | — | Abstract reasoning |
| **GPQA Diamond** | 91.9% | 91.3% | — | Expert reasoning — Gemini leads |
| **MMMU-Pro** | 81% | 73.9% | — | Multimodal — Gemini leads |
| **MMMLU** | 91.8% | 91.1% | — | Broad knowledge — Gemini leads |

> [!tip] Gemini Strengths
> Gemini 3 Pro leads on GPQA Diamond (91.9%), MMMU-Pro (81%), and MMMLU (91.8%) — strong in multimodal and broad knowledge. Claude leads on agentic/coding tasks.

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $1.25 / MTok (≤128K), $2.50 / MTok (>128K) |
| **Output cost** | $10.00 / MTok |
| **Latency (TTFT)** | ~2-4s |
| **Throughput** | Competitive |
| **Tier** | Standard-to-Premium |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Very long context analysis | 1M+ token window | Claude (200K limit) |
| Multimodal research | Best MMMU-Pro scores | Claude Opus |
| Alternative perspective | Cross-validate Claude outputs | Claude Opus |
| Gemini CLI workflows | Native Gemini CLI integration | Claude Code |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **Safety Framework** | Google Frontier Safety Framework | CCLs not reached |
| **Harmlessness** | Google Generative AI policies | Standard safety measures |
| **Known limitations** | Hallucinations, knowledge cutoff | Common to all LLMs |

## Configuration in Cohezion

```json
{
  "model": "gemini-2.5-pro",
  "maxOutputTokens": 8192,
  "temperature": 1.0
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| Gemini API | `generativelanguage.googleapis.com` | API key auth |
| Gemini CLI | `gemini` command | Agent mode with tools |
| Vertex AI | Google Cloud | Enterprise deployment |

## Known Limitations

- Not the primary model for Cohezion — Claude Code ecosystem is primary
- Gemini CLI lacks the hook system of Claude Code
- Slightly weaker on agentic coding (SWE-bench 76.2% vs Claude 80.8%)
- Google model card format is less detailed than Anthropic system cards

## Related

- [[claude-opus-4-6|Model Card: Claude Opus 4.6]] — Primary Cohezion model
- [[ide-and-model-providers]] — How Gemini CLI connects to the vault
- [[gemini-cli-ai-employees-agent-factory]] — Paper on Gemini CLI capabilities
- [[grok4-ai-benchmarks]] — Benchmark comparison across providers

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card from Google Model Card + Anthropic cross-comparison |
