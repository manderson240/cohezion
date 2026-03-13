---
title: "Model Card: Claude Sonnet 4.6"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, model-card, anthropic, mid-tier, claude]
card_type: model
status: active
provider: anthropic
model_id: "claude-sonnet-4-6"
aspect: knower
neural:
  activation: 0.71
  stage: growing
  synapse_in: 1
  synapse_out: 3
---

# Model Card: Claude Sonnet 4.6

> [!abstract] Summary
> Claude Sonnet 4.6 is Anthropic's balanced performance-to-cost model, combining strong agentic coding with faster throughput and lower cost than Opus. It is Cohezion's workhorse model for routine development, research summarization, and vault maintenance. Fast mode in Claude Code uses this same model with faster output.

## Identity

| Field | Value |
|-------|-------|
| **Model** | Claude Sonnet 4.6 |
| **Provider** | Anthropic |
| **Model ID** | `claude-sonnet-4-6` |
| **Model Class** | mid-tier |
| **Release Date** | February 2026 |
| **Knowledge Cutoff** | May 2025 |
| **System Card** | [Anthropic Sonnet 4.6 System Card (PDF)](https://www-cdn.anthropic.com/78073f739564e986ff3e28522761a7a0b4484f84.pdf) |

## Capabilities

| Capability | Support | Notes |
|-----------|---------|-------|
| Text generation | Yes | High quality, faster than Opus |
| Extended thinking | Yes | Adaptive thinking |
| Tool use | Yes | Full function calling, MCP integration |
| Vision / multimodal | Yes | Image understanding |
| Code generation | Yes | Strong agentic coding (SWE-bench 72.7%) |
| Agentic loops | Yes | Multi-step autonomous execution |
| Embeddings | No | Use dedicated embedding models |

## Context Window

| Parameter | Value |
|-----------|-------|
| **Input tokens** | 200K |
| **Output tokens** | 16K (standard), 64K (extended) |
| **Effective context** | ~180K before quality degradation |

## Benchmarks

> [!note] Source: Anthropic Sonnet 4.6 System Card
> Scores from Anthropic's evaluations with adaptive thinking, max effort.

| Benchmark | Sonnet 4.6 | Opus 4.6 | Notes |
|-----------|-----------|----------|-------|
| **SWE-bench Verified** | 72.7% | 80.8% | Agentic coding |
| **Terminal-Bench 2.0** | 57.7% | 65.4% | Terminal/CLI tasks |
| **τ²-bench (Retail)** | 88.3% | 91.9% | Customer service agent |
| **τ²-bench (Telecom)** | 96.2% | 99.3% | Technical support agent |
| **MCP-Atlas** | 44.7% | 59.5% | MCP tool orchestration |
| **OSWorld** | 55.6% | 72.7% | Computer use tasks |
| **ARC-AGI-2 (Verified)** | 24.8% | 68.8% | Abstract reasoning |
| **GPQA Diamond** | 84.0% | 91.3% | Expert-level science |
| **MMMU-Pro** | 65.2% | 73.9% | Multimodal reasoning |
| **MMMLU** | 89.1% | 91.1% | Broad knowledge |
| **HLE** | 22.1% | — | Humanity's Last Exam |

## Cost & Performance

| Metric | Value |
|--------|-------|
| **Input cost** | $3.00 / MTok |
| **Output cost** | $15.00 / MTok |
| **Latency (TTFT)** | ~1-3s (with thinking) |
| **Throughput** | ~2-3x faster than Opus |
| **Tier** | Standard |

## Use Cases in Cohezion

| Use Case | Why This Model | Alternative |
|----------|---------------|-------------|
| Daily development tasks | Best cost/performance ratio | Opus for complex tasks |
| Vault keeper quick checks | Speed over depth for routine audits | Opus for full runs |
| Research paper summarization | Good reasoning at 5x lower cost | Opus for synthesis |
| Code review & verification agents | Fast enough for iteration loops | Haiku for simple checks |
| Claude Code fast mode | Same model, faster output | — |

## Safety & Alignment

| Assessment | Level | Notes |
|-----------|-------|-------|
| **AI Safety Level** | ASL-3 | Standard Anthropic safety measures |
| **Harmlessness** | Evaluated | Single-turn, multi-turn, ambiguous context |
| **Agentic safety** | Evaluated | Prompt injection resistance |
| **Bias** | Evaluated | BBQ benchmark, demographic fairness |

## Configuration in Cohezion

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 8192,
  "temperature": 1.0
}
```

### Access Method

| Method | Config | Notes |
|--------|--------|-------|
| API | `api.anthropic.com` | Bearer token auth |
| Claude Code | Fast mode (`/fast`) | Primary for routine tasks |
| Agent subagents | `model: "sonnet"` | Default for verification agents |

## Known Limitations

- Significantly weaker on ARC-AGI-2 (24.8% vs Opus 68.8%) — complex abstract reasoning benefits from Opus
- MCP-Atlas gap (44.7% vs Opus 59.5%) — tool orchestration at scale favors Opus
- Knowledge cutoff May 2025

## Related

- [[claude-opus-4-6|Model Card: Claude Opus 4.6]] — Frontier tier
- [[claude-haiku-4-5|Model Card: Claude Haiku 4.5]] — Economy tier
- [[ai-safety-alignment]] — Safety and alignment concepts

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial card from Anthropic System Card (Feb 2026) |
