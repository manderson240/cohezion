---
title: "Model Card: Claude Opus 4.6"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, anthropic, frontier, claude]
card_type: model
status: active
provider: anthropic
model_id: "claude-opus-4-6"
aspect: knower
neural:
  activation: 0.77
  stage: growing
  synapse_in: 1
  synapse_out: 5
---

# Model Card: Claude Opus 4.6

> [!abstract] Summary
> Claude Opus 4.6 is Anthropic's most capable frontier model, excelling at agentic coding, complex reasoning, and long-horizon tasks. It is Cohezion's primary model for spec-driven development, plan verification, and complex research. Deployed under ASL-3 security with extended thinking enabled by default.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Claude Opus 4.6 |
| **Provider** | Anthropic |
| **Model ID** | `claude-opus-4-6` |
| **Model Class** | frontier |
| **Release Date** | February 2026 |
| **Knowledge Cutoff** | May 2025 |
| **System Card** | [Anthropic Opus 4.6 System Card (PDF)](https://www-cdn.anthropic.com/0dd865075ad3132672ee0ab40b05a53f14cf5288.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | State-of-the-art quality |
| Extended thinking | Yes | Adaptive thinking with variable budget |
| Tool use | Yes | Full function calling, MCP integration |
| Vision / multimodal | Yes | Image understanding |
| Code generation | Yes | Top-tier agentic coding (SWE-bench 80.8%) |
| Agentic loops | Yes | Multi-step autonomous execution |
| Embeddings | No | Use dedicated embedding models |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 200K |
| **Output tokens** | 32K (standard), 128K (extended) |
| **Effective context** | ~180K before quality degradation |

## Benchmarks

> [!note] Source: Anthropic Opus 4.6 System Card (Table 2.3.A)
> All scores are averages over 5 trials with adaptive thinking, max effort, default sampling.

| Benchmark | Opus 4.6 | Opus 4.5 | Sonnet 4.5 | Gemini 3 Pro | GPT-5.2 |
|-----------|----------|----------|------------|-------------|---------|
| **SWE-bench Verified** | 80.8% | 80.9% | 77.2% | 76.2% | 80.0% |
| **Terminal-Bench 2.0** | **65.4%** | 59.8% | 51.0% | 56.2% | 64.7% |
| **τ²-bench (Retail)** | **91.9%** | 88.9% | 86.2% | 85.3% | 82.0% |
| **τ²-bench (Telecom)** | **99.3%** | 98.2% | 98.0% | 98.0% | 98.7% |
| **MCP-Atlas** | 59.5% | **62.3%** | 43.8% | 54.1% | 60.6% |
| **OSWorld** | **72.7%** | 66.3% | 61.4% | — | — |
| **ARC-AGI-2 (Verified)** | **68.8%** | 37.6% | 13.6% | 45.1% | 54.2% |
| **GPQA Diamond** | **91.3%** | 87.0% | 83.4% | 91.9% | **93.2%** |
| **MMMU-Pro (no tools)** | **73.9%** | 70.6% | 63.4% | **81%** | 79.5% |
| **MMMLU** | **91.1%** | 90.8% | 89.5% | **91.8%** | 89.6% |
| **OpenRCA** | **34.9%** | 26.9% | 12.9% | — | — |

### Agentic Highlights

- **Cybench:** ~100% (pass@30) — saturated current evaluations
- **CyberGym:** 66% (pass@1)
- **ARC-AGI-2:** 68.8% — near-doubling vs Opus 4.5 (37.6%)
- **Terminal-Bench 2.0:** 65.4% — highest among all tested models
- Anthropic notes Opus 4.6 "saturated all current cyber evaluations"

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $15.00 / MTok |
| **Output cost** | $75.00 / MTok |
| **Latency (TTFT)** | ~2-5s (with thinking) |
| **Throughput** | Variable (thinking budget dependent) |
| **Tier** | Premium |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| /spec planning & implementation | Highest agentic coding capability | Claude Sonnet 4.6 |
| Complex research synthesis | Best reasoning (GPQA 91.3%) | Gemini 2.5 Pro |
| Plan verification agents | Deep analysis, catches subtle issues | Claude Sonnet 4.6 |
| Vault keeper full maintenance | Quality > speed for structural decisions | Claude Sonnet 4.6 |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **AI Safety Level** | ASL-3 | Deployed under ASL-3 security measures |
| **Autonomy** | Below AI R&D-4 threshold | Does not fully automate entry-level research engineering |
| **CBRN** | Below CBRN-4 threshold | "Slightly less helpful than Opus 4.5" in expert uplift trials |
| **Cyber** | Saturated current evaluations | ~100% Cybench, 66% CyberGym |
| **Agentic safety** | Evaluated | Prompt injection resistance, multi-turn safety |
| **Model welfare** | Assessed | Self-interaction studies, intrinsic interest experiments |

> [!warning] Evaluation Integrity Note
> Anthropic acknowledges that Opus 4.6 was used to debug its own evaluation infrastructure — a self-referential dynamic they are monitoring and developing mitigations for.

## Configuration in Cohezion

```json
{
  "model": "claude-opus-4-6",
  "max_tokens": 16384,
  "temperature": 1.0
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| API | `api.anthropic.com` | Bearer token auth |
| Claude Code | Default model | Primary IDE integration |
| MCP | Via Cloud Vault MCP | Agent context queries |

## Known Limitations

- Highest cost tier — reserve for complex tasks, use Sonnet 4.6 for routine work
- Extended thinking can produce very long outputs (token budget management critical)
- Knowledge cutoff May 2025 — may miss recent developments
- SWE-bench score slightly below Opus 4.5 (80.8% vs 80.9%) — within noise

## Related

- [[claude-sonnet-4-6|Model Card: Claude Sonnet 4.6]] — Mid-tier alternative
- [[claude-haiku-4-5|Model Card: Claude Haiku 4.5]] — Economy fast model
- [[ai-safety-alignment]] — Concept note on safety and alignment
- [[anthropic-disempowerment-patterns]] — Paper on alignment research
- [[agentic-ai]] — Concept note on agentic AI architecture

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card from Anthropic System Card (Feb 2026) |
