---
title: "MLA Attention & MoE Trends — 2026 Q2"
date: 2026-06-15
tags: [concept, architecture, moe, attention, mla, local-inference, llama.cpp]
---
# MLA Attention & MoE Architecture Trends (2026 Q2)

## MLA (Multi-head Latent Attention)

Originally from DeepSeek-V2/V3/R1. Now adopted by Kimi K2.7 Code (Moonshot AI) as of June 2026.

**Key idea:** Compress key/value projections into a low-rank latent space. During inference, KV cache stores compressed latents rather than full K/V tensors — dramatically smaller KV cache for long contexts.

**Why it matters for fleet:** Reduces per-token KV memory ~5-13x vs standard MHA. For a 256K ctx model, this is the difference between feasible and impossible on a 128GB machine — *if* the model's total weights fit.

**Models using MLA (as of June 2026):**
- DeepSeek-V2/V3/R1
- Kimi K2.7 Code (1T/32B-active)

## Cohere2MoE / North Architecture

Cohere's North family uses a MoE architecture ("Cohere2MoE" in llama.cpp). As of llama.cpp b9626 (June 13, 2026), full GGUF support landed:
- b9626: Initial arch support (tensor mapping, sliding window, expert selection)
- b9637: Dedicated parser for North Code

**North Mini Code 1.0** is the compact member of this family. Likely iGPU-tier (4-8B). Pending size confirmation — evaluate against Granite-4.1-8B and Gemma-4-E4B for the iGPU slot.

## MiniMax M3 MSA (MiniMax Sparse Attention)

MiniMax M3 (428B/23B-active) introduces MSA — a high-performance sparse attention operator targeting million-token contexts with:
- 9x prefill speedup vs M2 at 1M context
- 15x decode speedup
- Per-token compute reduced to 1/20 of M2

Not fleet-viable at 428B total (too large for 128GB), but the sparse attention operator concept is worth watching — similar goals to MLA (reduce KV memory and attention compute at long ctx).

## AI Policy Event (June 13, 2026)

US government issued export control order suspending Anthropic's Claude Fable 5 globally, citing a demonstrated code-analysis-based safety bypass. An unreleased model "Mythos 5" was also suspended. Other Anthropic models unaffected. Compliance was immediate (~90 minutes from directive to access cut).

This is the first known US government-mandated suspension of a frontier model's public access.

## Tracking

- llama.cpp Cohere2MoE support: b9626+ confirmed
- North Mini Code 1.0 evaluation: **Pending**
- Kimi K2.7 Code fleet status: **Skip** (1T total too large)
- MiniMax M3 fleet status: **Skip** (428B total too large)
