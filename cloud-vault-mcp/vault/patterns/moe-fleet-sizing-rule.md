---
date: 2026-06-15
source_project: cohezion
tags: [pattern, local-inference, fleet, moe, hardware, amd, strix-halo]
---
# MoE Fleet Sizing Rule (Strix Halo / 128GB)

## Problem
MoE models advertise "active parameters" (compute cost per token) which look small and fleet-compatible, while total parameters (which determine RAM) are 10-20x larger. Evaluating models on active params alone leads to attempting to load models that cannot fit in RAM.

## Solution
**Primary gating criterion = total params x bytes-per-param at target quantization.**

For the Strix Halo fleet (128GB unified RAM, ~115GB usable after OS/process overhead):

| Quant | Bytes/param | Max viable total params |
|-------|------------|------------------------|
| Q8   | ~1.0B       | ~115B                  |
| Q4_K_M | ~0.55B    | ~210B                  |
| Q2_K | ~0.28B     | ~410B                  |

Even at Q2_K, a 428B model consumes ~107GB — leaving only ~8GB for KV cache and process overhead at 16K ctx. **Rule: total x Q2 bytes must be <= 100GB to be viable** (leaves 15GB headroom).

Active params determine inference speed and quality, not whether the model fits. A 1T/32B-active model is computationally similar to a 32B dense model per token but requires 1T-param weight in RAM.

## Example
```
# Kimi K2.7 Code: 1T total / 32B active
1,000B x 0.28 bytes = 280GB at Q2 -> SKIP (2.4x over limit)

# MiniMax M3: 428B total / 23B active
428B x 0.28 bytes = 107GB at Q2 -> SKIP (no headroom)

# Qwen3-235B-A22B: 235B total / 22B active
235B x 0.28 bytes = 66GB at Q2 -> VIABLE (fits, leaves 49GB)

# Gemma-4-31B: 31B total / 31B dense
31B x 0.55 bytes = 17GB at Q4_K_M -> STRONG FIT (iGPU/CPU)
```

## When to Use
- Evaluating any MoE model for the Strix Halo local fleet
- Deciding between iGPU (4-8B GGUF), CPU-medium (14-35B), or skip tiers

## When NOT to Use
- Cloud inference (RAM not the constraint)
- Machines with higher RAM (scale the threshold accordingly)

## Related Decisions
- 2026-06-15 digest: Kimi K2.7 Code and MiniMax M3 both skipped under this rule
- Current fleet: Gemma-4-31B (CPU), Qwen3-235B-A22B (CPU), Granite-4.1-8B (iGPU), llama3.2-1b-FLM (NPU)
