---
title: Agent Orchestration Design - 3-Tier Hot/Warm/Cold Model Rotation
date: '2026-02-14'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: "1. MoE models (glm-4.7-flash, qwen3-coder:30b) load all 30B params into\
    \ RAM but only activate ~3B per token \u2014 giving 30B quality at 3B speed (~20-35\
    \ t/s gen, ~1000+ t/s prompt processing on CPU). 2. phi4-mini-reasoning (3.8B\
    \ dense) achieves ~60-80 t/s generation \u2014 ideal for always-on routing. 3.\
    \ Tier 1+2 totals ~48GB leaving 74GB headroom for KV caches + one Tier 3 model.\
    \ 4. Q8_0 KV cache halves KV memory with negligible quality loss. 5. Cold-start\
    \ from NVMe: ~24-30s for 9GB model, ~45-60s for 19GB model \u2014 acceptable for\
    \ Tier 3 on-demand loads. 6. Existing OllamaGate semaphore=4 naturally maps to\
    \ 4 hot/warm model slots."
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Agent Orchestration Design - 3-Tier Hot/Warm/Cold Model Rotation'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  - sequence: 4
    content: Selected option with best balance of trade-offs
    type: hybrid
    confidence: 0.62
    assumption: Best option was chosen based on analysis
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
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

- [[3-tier-hotwarmcold-model-rotation|Pattern: 3-Tier Hot/Warm/Cold Model Rotation]] — the pattern that operationalizes this decision
- [[runbook-ollama-mcp-operations]]
- [[2026-02-09-ai-model-strategy]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[lesson-06-ollama-latency]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]

## Scientific Foundation

- [[agentic-ai-memory-hierarchies]] — the hot/warm/cold tier design directly implements the paper's call for "intelligent memory management software" that decides which context parts reside in fastest memory. Hot = HBM/VRAM (always loaded, nanosecond access); Warm = DRAM (loaded on first request, microsecond access); Cold = NVMe (load on demand, seconds). This decision IS the memory management software the paper calls for.
- [[superfluid-to-supersolid-transition]] — the model tier system undergoes phase transitions analogous to the superfluid-to-supersolid transition: at high request density (like high exciton density), all models are in the hot fluid tier (fast, flexible flow); at lower demand, models crystallize into the cold tier (solid, structured storage). The density parameter that drives the quantum phase transition maps to the request-rate threshold that drives model tier assignment. Phase transitions between agent tiers follow the same non-linear threshold behavior.
