---
title: 'HIHO coherence loss must target per-sample not batch mean'
date: '2026-02-23'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Batch-level regularization doesn't ensure per-sample coherence. A batch where half the samples are at 0.0 and half at 1.0 has a batch mean of 0.5 but no individual sample achieves HIHO stability.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: HIHO coherence loss must target per-sample not batch mean'
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

HIHO (High-In High-Out) coherence loss was designed to enforce that agents with high input coherence produce high output coherence. The original implementation computed:

```python
loss = abs(mean(batch_coherence) - target)
```

During analysis of training behavior, it was found that this allows cancellation: a batch where half the samples are at coherence 0.0 and half at 1.0 produces batch mean = 0.5, which can satisfy target = 0.5 while no individual sample achieves HIHO stability. The loss was masking individual failures behind batch statistics.

## Decision

HIHO coherence loss must be computed per-sample:

```python
loss = mean(abs(coherence_per_sample - target))
```

This ensures every sample is individually penalized for deviation, not just the batch as a whole.

## Chosen Option

Per-sample L1 loss against target coherence value, averaged across the batch.

## Alternatives Considered

1. Batch-mean L1 loss (status quo)
2. Batch-mean squared loss
3. Per-sample squared loss
4. Per-sample L1 loss (chosen)

## Decision Reasoning

### Why This Option?

Per-sample L1 loss directly penalizes each sample's deviation from the target. It is simple, interpretable, and prevents the cancellation failure mode. L1 is preferred over L2 here because coherence values are bounded [0, 1] and we care about magnitude of deviation, not squared magnitude.

### Alternatives Rejected

- **Batch-mean variants** — All batch-mean approaches allow individual sample failures to cancel. The cancellation failure is fundamental, not a hyperparameter issue.
- **Per-sample L2** — Acceptable alternative, but L1 penalizes all deviations equally. L2 would de-emphasize small deviations, which may hide gradual drift.

### Confidence Level

High. The mathematical failure mode of batch-mean regularization is clear. The fix is straightforward.

## Expected Outcomes

- Every sample individually penalized for HIHO coherence deviation
- No hiding of bimodal failure modes behind batch statistics
- Training signal is honest about per-sample coherence quality

## Metrics & Impact

### Estimated

- Fraction of samples with coherence within 0.1 of target increases during training
- Loss surface becomes more informative (correlated with per-sample behavior)

### Actual (Post-Implementation)

- HIHO loss now accurately reflects per-sample coherence distribution

## Related Decisions & Lessons

- [[2026-02-24-anti-pattern-hiho-coherence-loss-on-batch-mean]]
- [[latent-coherence-stability-predictor-lcsp]] — LCSP measures whether per-sample coherence is stable over training; this decision ensures the loss signal supports that goal
- [[failure-mode-test-priority]] — bimodal coherence failure is a silent failure mode; tests should verify per-sample coherence distribution not just batch mean
