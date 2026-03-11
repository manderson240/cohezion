---
title: 'Anti-pattern: Dual VAE architecture creates integration debt'
date: '2026-02-24'
status: accepted
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Two models operating on different input spaces creates integration debt that compounds silently. Each model makes assumptions about the other's output format, and neither gets enough attention to be production-quality.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: Dual VAE architecture creates integration debt'
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
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
aspect: thinker
neural:
  activation: 0.477
  stage: growing
  cluster: decisions
---

## Context

**Anti-pattern:** Maintaining two VAE implementations that serve partially overlapping purposes.

The FLUME codebase had both:
- `FlumeVAE`: took raw agent state dicts, did internal feature extraction, produced 256D latent
- `TemporalVAE`: took pre-embedded 768D vectors from nomic-embed-text, produced 256D latent

Integration consequences:
- Tests assumed one or the other was canonical; fixtures conflicted
- Bug fixes applied to one were missed in the other
- Integration path unclear: which model does the compound execution pipeline use?
- Neither model reached production quality because attention was split 50/50

The pattern: each model was ~80% of what was needed. Together they were 80% of one system, not 160% of capability.

## Decision

Pick one model, delete the other. `TemporalVAE` is the correct architecture; `FlumeVAE` conflates language understanding with geometric compression.

## Chosen Option

`TemporalVAE` as the single canonical VAE. `FlumeVAE` deleted.

## Alternatives Considered

1. Keep both, document distinct roles
2. Merge into a unified model with input mode flag
3. Delete `TemporalVAE`, keep `FlumeVAE`
4. Delete `FlumeVAE`, keep `TemporalVAE` (chosen)

## Decision Reasoning

### Why This Option?

`TemporalVAE` has the correct architectural separation: pre-trained model handles language understanding; VAE handles structured compression. This separation allows independent component improvement.

`FlumeVAE`'s dict-based input couples feature extraction to the VAE. Swapping embedding models requires modifying the VAE.

The "keep both with clarified roles" approach was attempted and failed — coordination overhead doesn't decrease when you document it, only when you eliminate one side.

### Alternatives Rejected

- **Keep both** — Attempted; integration confusion persisted.
- **Merge with mode flag** — `if input_mode == "dict"` paths compound over time; eventually one path is untested.
- **Keep FlumeVAE** — Wrong abstraction level; would require migrating back to dict-based input everywhere.

### Confidence Level

High. The dual-model integration bugs were directly observed and traced to architecture ambiguity.

## Expected Outcomes

- Single model to test, maintain, and iterate
- Clear pipeline: text → embed → VAE → latent
- Embedding model independently swappable
- Integration tests unambiguous

## Metrics & Impact

### Estimated

- ~600 lines removed (FlumeVAE + tests)
- Integration test fixtures simplified
- Zero ambiguity about which model the pipeline uses

### Actual (Post-Implementation)

- TemporalVAE successfully trained on overnight data end-to-end

## Related Decisions & Lessons

- [[2026-02-23-one-coherent-model-beats-two-partial-implementations]]
- [[2026-02-24-temporalvae-first-training-run-on-overnight-data]]
- [[integration-first-definition-of-done]] — dual models are an integration-debt failure; integration-first would have forced model selection earlier
- [[failure-mode-test-priority]] — conflicting fixtures from dual models are a test-infrastructure failure mode this anti-pattern creates
- [[neural-network-architecture]] — VAE architecture choices (FlumeVAE vs TemporalVAE) are neural network architecture decisions with downstream integration consequences
- [[machine-learning]] — the anti-pattern illustrates how ML model proliferation creates compounding technical debt
- [[semantic-search]] — TemporalVAE uses pre-trained semantic embeddings (nomic-embed-text), connecting this decision to the semantic search pipeline
