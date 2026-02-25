---
title: 'Anti-pattern: Training VAE on random noise (SyntheticFlumeDataset)'
date: '2026-02-24'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'A VAE trained on random noise learns Gaussian structure, not semantic structure. The model becomes a fancy identity function over random distributions. Always validate that training data distribution matches the target deployment distribution.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: Training VAE on random noise (SyntheticFlumeDataset)'
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

**Anti-pattern:** Using `SyntheticFlumeDataset` — which sampled features from `N(0.5, 0.15)` — as training data for the FLUME VAE.

The motivation: get integration tests running quickly without waiting for real agent data from simulation. Reasonable for unit tests. Catastrophic when used for model training.

A VAE is a universal function approximator for distributions. Given `N(0.5, 0.15)` as training data, it will faithfully learn to model `N(0.5, 0.15)`. It achieves excellent ELBO on this synthetic data — which looks like training success but measures nothing useful. When connected to real agent state data (which has very different distributional properties), reconstruction quality collapses.

This created a false confidence loop: great ELBO → ship model → use on real data → catastrophic failure.

## Decision

Delete `SyntheticFlumeDataset`. Never use random noise as a proxy for real data in model training. Integration tests that require a dataset should use a small sample of real data or a domain-realistic generator.

## Chosen Option

Use the overnight simulation pipeline output (5.5M trajectories) as the training dataset. For fast integration tests, use a 1000-sample subset of real data.

## Alternatives Considered

1. SyntheticFlumeDataset from N(0.5, 0.15) (anti-pattern)
2. Domain-realistic synthetic generator (e.g., correlated features from known agent behavior distributions)
3. Small subset of real simulation data
4. Full overnight simulation dataset

## Decision Reasoning

### Why This Option?

The overnight simulation pipeline already exists and produces real agent trajectory data. Using a small real-data subset for integration tests is better than any synthetic generator: it's guaranteed to match the deployment distribution.

### Alternatives Rejected

- **Random noise** — Trains the model on the wrong distribution; provides false success signal.
- **Domain-realistic synthetic generator** — Better than random noise but requires its own validation to ensure it matches real data. Additional complexity for marginal benefit given real data availability.

### Confidence Level

High. The failure mode (model learns synthetic distribution, fails on real data) was directly observed. The fix is straightforward.

## Expected Outcomes

- Model learns actual agent state distribution
- ELBO on training data correlates with real-world reconstruction quality
- No distribution mismatch between training and deployment

## Metrics & Impact

### Estimated

- Reconstruction quality on real agent data: from collapsed (>5.0 reconstruction loss) to <0.5

### Actual (Post-Implementation)

- TemporalVAE trained on overnight data produces meaningful semantic clusters

## Related Decisions & Lessons

- [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]]
- [[2026-02-24-flume-vae-v2-training-results]]
