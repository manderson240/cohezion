---
title: 'Hash-based journey tracking produces meaningless 12D trajectories'
date: '2026-02-23'
status: accepted
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'The purpose of journey tracking is to observe semantic relationships between agent actions. Hash-based tracking destroys these relationships by design. FLUME embeddings preserve semantic similarity, enabling meaningful trajectory analysis.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Hash-based journey tracking produces meaningless 12D trajectories'
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
  activation: 0.68
  stage: growing
  synapse_in: 8
  synapse_out: 5
---

## Context

`JourneyTracker` was computing 12D positions by taking the first 12 bytes of `SHA-256(agent_state_string)` and normalizing to floats. This produced positions that were numerically valid and internally consistent — the same state always mapped to the same position — but semantically random.

Consequences observed:
- Trajectories showed no continuity: semantically adjacent states mapped to distant positions
- Drift detection produced false positives on every step (random walk in 12D)
- Anomaly detection was unusable (everything was anomalous relative to random walk)
- Cluster analysis found no meaningful clusters

## Decision

Journey tracking must use FLUME latent vectors as 12D positions. The 12D universe is only meaningful if positions reflect semantic proximity of agent states.

## Chosen Option

`agent_state → nomic-embed-text (768D) → FLUME VAE encoder → latent (12D projected)`

The FLUME latent space becomes the coordinate system for the 12D universe. Semantically similar agent states occupy nearby regions.

## Alternatives Considered

1. SHA-256 hash bytes (status quo)
2. Random projection of agent state features
3. PCA of raw state features
4. FLUME semantic embeddings

## Decision Reasoning

### Why This Option?

The entire purpose of the 12D universe is to enable geometric reasoning about agent behavior — drift detection, anomaly identification, trajectory prediction. These require that distance in 12D corresponds to semantic distance in agent reasoning. Only trained semantic embeddings provide this correspondence.

### Alternatives Rejected

- **SHA-256** — Avalanche effect makes it semantically meaningless by design.
- **Random projection** — Preserves no semantic structure; positions are arbitrary.
- **PCA** — Captures variance in raw features but not semantic meaning. May work as a fallback if FLUME is unavailable.

### Confidence Level

High. The failure of hash-based tracking was directly observed in trajectory visualizations. The fix follows directly from first principles.

## Expected Outcomes

- Trajectories show smooth geometric continuity in 12D space
- Drift detection identifies genuine reasoning drift, not random walk
- Cluster analysis reveals meaningful agent behavior modes
- Anomaly detection catches genuine semantic outliers

## Metrics & Impact

### Estimated

- Trajectory smoothness (average step distance) decreases from ~1.4 (random walk expectation in 12D) to <0.3 for coherent agent reasoning

### Actual (Post-Implementation)

- Trajectories now show interpretable geometric structure in visualization

## Related Decisions & Lessons

- [[2026-02-23-never-use-sha-256-hashes-as-semantic-embeddings]]
- [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning]]
- [[agent-journey-tracking]] — journey tracking requires FLUME latent vectors as 12D positions; hash-based positions destroy semantic structure
- [[semantic-search]] — semantic proximity in latent space is the foundation for meaningful journey analysis, just as it is for search
- [[anomaly-detection]] — hash-based trajectories produce false positive anomalies because random walk in 12D is indistinguishable from genuine anomalies
