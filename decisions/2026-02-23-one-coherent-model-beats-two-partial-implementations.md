---
title: 'One coherent model beats two partial implementations'
date: '2026-02-23'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Dual implementations create integration debt that compounds silently. Neither model can be validated because each covers only part of the pipeline. Testing, debugging, and reasoning about system behavior becomes impossible when two models exist for the same conceptual purpose.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: One coherent model beats two partial implementations'
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
---

## Context

The codebase contained two partially overlapping VAE implementations: `FlumeVAE` (processing raw agent state dicts with built-in feature extraction) and `TemporalVAE` (processing pre-embedded 768D vectors from nomic-embed-text). Both models served similar purposes — learning a compressed latent representation of agent states — but with different input abstractions.

Problems observed:
- Tests for one model assumed the other didn't exist, leading to conflicting fixtures
- Integration between them was unclear: does the pipeline use one or both?
- Bug fixes in one weren't applied to the other
- Neither had complete coverage because attention was split

## Decision

Consolidate into a single model. `TemporalVAE` (embedding-based input) is the correct architecture because it separates language understanding (pre-trained model) from structured compression (VAE). `FlumeVAE` (raw dict input) conflates these concerns and is the wrong abstraction level.

## Chosen Option

Keep `TemporalVAE`, delete `FlumeVAE`. The pipeline becomes:
`agent_state → nomic-embed-text → TemporalVAE → latent`

## Alternatives Considered

1. Keep both, clarify their distinct roles
2. Merge both into a unified model with configurable input handling
3. Choose `FlumeVAE` as the canonical model
4. Choose `TemporalVAE` as the canonical model (chosen)

## Decision Reasoning

### Why This Option?

Two models serving the same purpose create coordination overhead that compounds. Each model gets half the testing, half the debugging attention, and half the feature development. Semantic ambiguity about which model to use persists until someone eliminates one.

`TemporalVAE` is architecturally correct: pre-trained embeddings handle language understanding; the VAE handles geometric structure. `FlumeVAE` trying to do both makes it both hard to validate and impossible to share embedding infrastructure with other pipeline components.

### Alternatives Rejected

- **Keep both with clarified roles** — Attempted during sprint 3. The coordination overhead didn't decrease; it just became documented coordination overhead.
- **Merge into unified model** — Significant engineering effort for marginal gain. Better to pick the right abstraction and go deep.
- **Keep FlumeVAE** — Raw dict input couples feature extraction to the VAE, making it impossible to swap embedding models independently.

### Confidence Level

High. The dual-model confusion caused multiple integration bugs and wasted development time. Elimination is the only complete fix.

## Expected Outcomes

- Single model to test, debug, and iterate on
- Clear pipeline: text → embed → VAE → latent
- Embedding model is swappable independently of VAE architecture
- Integration tests become unambiguous

## Metrics & Impact

### Estimated

- ~600 lines of FlumeVAE code removed
- Integration test complexity reduced by ~40%

### Actual (Post-Implementation)

- Pipeline is now end-to-end coherent; TemporalVAE training on overnight data succeeded

## Related Decisions & Lessons

- [[2026-02-24-anti-pattern-dual-vae-architecture-creates-integration-debt]]
- [[2026-02-24-temporalvae-first-training-run-on-overnight-data]]
