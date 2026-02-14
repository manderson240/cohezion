---
title: "Agent Orchestration Design - 3-Tier Hot/Warm/Cold Model Rotation"
date: "2026-02-14"
status: proposed
tags: [decision]

# NEW FIELDS FOR OBSERVABILITY
decision_reasoning:
  chosen_option: "{{chosen_option}}"
  rationale: "1. MoE models (glm-4.7-flash, qwen3-coder:30b) load all 30B params into RAM but only activate ~3B per token — giving 30B quality at 3B speed (~20-35 t/s gen, ~1000+ t/s prompt processing on CPU). 2. phi4-mini-reasoning (3.8B dense) achieves ~60-80 t/s generation — ideal for always-on routing. 3. Tier 1+2 totals ~48GB leaving 74GB headroom for KV caches + one Tier 3 model. 4. Q8_0 KV cache halves KV memory with negligible quality loss. 5. Cold-start from NVMe: ~24-30s for 9GB model, ~45-60s for 19GB model — acceptable for Tier 3 on-demand loads. 6. Existing OllamaGate semaphore=4 naturally maps to 4 hot/warm model slots."
  confidence_score: 0.0  # 0-1 scale
  alternatives_rejected:
    - "{{alt1}}"
    - "{{alt2}}"
  reasoning_chain: []  # List of steps in reasoning process

metrics:
  estimated_cost: 0.0  # USD
  estimated_time_hours: 0.0
  actual_cost: 0.0  # USD (fill after implementation)
  actual_time_hours: 0.0  # Fill after implementation
  tokens_used: 0  # If applicable
  cost_per_lesson: 0.0  # Lessons generated ÷ actual cost
  lessons_generated: []  # Links to lesson notes
---

## Context

## Decision

## Chosen Option

## Alternatives Considered

## Decision Reasoning

### Why This Option?

### Alternatives Rejected

### Confidence Level

## Expected Outcomes

## Metrics & Impact

### Estimated

### Actual (Post-Implementation)

## Related Decisions & Lessons
