---
title: 'Anti-pattern: HIHO coherence loss on batch mean'
date: '2026-02-24'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Batch-level statistics can be misleading. Two samples with means of 0.0 and 1.0 average to 0.5, passing the batch check while both individually violating HIHO. Per-sample regularization prevents this.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: HIHO coherence loss on batch mean'
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

**Anti-pattern:** Computing HIHO coherence regularization on the batch mean rather than per-sample.

Original implementation:
```python
batch_coherence = model(batch).coherence  # shape: (batch_size,)
loss = abs(batch_coherence.mean() - target)
```

The failure mode: two samples with coherence 0.0 and 1.0 produce batch mean = 0.5. A target of 0.5 is satisfied. But neither sample has achieved HIHO stability — one is fully incoherent, the other is fully coherent. The regularization passes despite both samples being individually at the extreme.

This creates a training dynamic where the model can satisfy coherence loss by maintaining bimodal distributions rather than genuine per-sample stability. The loss signal is misleading.

## Decision

Compute HIHO coherence loss per-sample:
```python
loss = abs(batch_coherence - target).mean()
```

This is `mean(abs(x - target))` not `abs(mean(x) - target)`. The operations don't commute.

## Chosen Option

Per-sample L1 loss, batch-averaged.

## Alternatives Considered

1. Batch-mean L1 (anti-pattern)
2. Batch-mean L2
3. Per-sample L1 (chosen)
4. Per-sample L2

## Decision Reasoning

### Why This Option?

Per-sample loss guarantees every sample contributes an honest gradient signal. The mathematical failure of batch-mean approaches (operations not commuting) is not fixable by tuning.

L1 preferred over L2: coherence values are bounded [0,1], and we want equal penalty for equal deviation rather than disproportionate penalty for large deviations.

### Alternatives Rejected

- **Any batch-mean variant** — Operations don't commute; cancellation failure is inherent.
- **Per-sample L2** — Acceptable alternative; de-emphasizes small deviations, which could hide gradual drift from target.

### Confidence Level

High. Mathematical certainty about non-commutativity. Empirically confirmed through training behavior analysis.

## Expected Outcomes

- Loss signal accurately reflects per-sample coherence quality
- No bimodal failure modes hidden by cancellation
- Training converges to genuinely stable per-sample coherence

## Metrics & Impact

### Estimated

- Fraction of samples within 0.1 of coherence target increases during training
- Bimodal coherence distributions eliminated

### Actual (Post-Implementation)

- HIHO loss now tracks per-sample coherence faithfully

## Related Decisions & Lessons

- [[2026-02-23-hiho-coherence-loss-must-target-per-sample-not-batch-mean]]
