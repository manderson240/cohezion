---
title: 'Never use SHA-256 hashes as semantic embeddings'
date: '2026-02-23'
status: accepted
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Cryptographic hashes are designed to maximize distance between similar inputs. Semantic embeddings are designed to minimize distance between similar meanings. Using hashes where semantics matter is an anti-pattern that makes the entire downstream pipeline (VAE, cache, journey tracking) semantically meaningless.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Never use SHA-256 hashes as semantic embeddings'
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
  activation: 0.64
  stage: growing
  synapse_in: 2
  synapse_out: 3
---

## Context

FLUME's feature encoding was using `hashlib.sha256(state_str.encode()).digest()[:32]` to produce 32-byte "embeddings" for agent states. These bytes were fed into the VAE as the input representation. The logic was: a consistent hash gives a consistent vector, so similar states get similar vectors.

This is wrong. SHA-256 is designed with the avalanche effect: a single-bit change in input causes ~50% of output bits to flip. "Agent found food" and "agent located food" — semantically near-identical — produce hash values with no relationship whatsoever.

## Decision

Remove all SHA-256 hash-based encoding from the FLUME pipeline. Use actual semantic embedding models (nomic-embed-text or equivalent) for all state representations.

## Chosen Option

Replace `hashlib.sha256(state).digest()[:32]` with `embed(state)` using a pre-trained embedding model that preserves semantic similarity.

## Alternatives Considered

1. Keep SHA-256 but normalize to unit sphere
2. Use SHA-256 as a seeded random vector (deterministic lookup)
3. Character-level learned embeddings
4. Pre-trained semantic embedding model

## Decision Reasoning

### Why This Option?

Pre-trained embedding models directly encode semantic similarity — their entire training objective is to place semantically similar text close together. This is exactly what FLUME needs. The avalanche property of hashes is irreconcilable with semantic similarity requirements.

### Alternatives Rejected

- **Normalized SHA-256** — Normalization doesn't fix the underlying distribution; semantically similar inputs still map to unrelated points.
- **Seeded random vectors** — Same problem. Consistent but semantically meaningless.
- **Character-level learned embeddings** — Requires training from scratch on domain data; can't compete with pre-trained models encoding billions of tokens of context.

### Confidence Level

High. The mathematical incompatibility between hash avalanche effect and semantic proximity is fundamental, not a tuning issue.

## Expected Outcomes

- Semantically similar agent states map to nearby points in embedding space
- VAE receives meaningful input signal to learn from
- Journey tracking, drift detection, and anomaly identification become meaningful
- FLUME pipeline becomes end-to-end semantically coherent

## Metrics & Impact

### Estimated

- Semantic similarity of reconstructed states improves from ~random to >0.8 cosine similarity for near-identical inputs

### Actual (Post-Implementation)

- Downstream trajectory analysis now produces interpretable clusters

## Related Decisions & Lessons

- [[2026-02-23-character-level-tokenizers-are-inadequate-for-semantic-embeddings]]
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories]]
- [[2026-02-24-anti-pattern-sha-256-as-semantic-embedding]]
