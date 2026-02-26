---
title: 'Anti-pattern: Character-level tokenizer for semantic embeddings'
date: '2026-02-24'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Character-level models must learn word boundaries, morphology, and semantics from scratch. Pre-trained models (nomic-embed-text) already encode semantic knowledge from billions of tokens of training data.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: Character-level tokenizer for semantic embeddings'
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

**Anti-pattern:** Training a character-level model from scratch to produce semantic embeddings for agent state descriptions.

The appeal: full control over the embedding process, no external model dependencies, domain-specific vocabulary. In practice: a 74-character vocabulary trained on a small domain corpus cannot learn semantic similarity. The model must learn word boundaries, morphology, word meaning, and compositional semantics simultaneously — tasks that pre-trained models have already solved using orders of magnitude more data.

Observed failure: "search for food" and "find food source" had cosine similarity <0.3 with character-level embeddings.

## Decision

Use pre-trained embedding models. Do not train character-level models for semantic tasks.

## Chosen Option

nomic-embed-text (or equivalent) for semantic text representation.

## Alternatives Considered

1. Character-level LSTM (anti-pattern)
2. Word-level BoW
3. Pre-trained embedding model (chosen)

## Decision Reasoning

### Why This Option?

The capability gap between character-level models and pre-trained models is not a training data quantity issue — it's a knowledge transfer issue. Pre-trained models encode linguistic knowledge that cannot be learned from a domain corpus of hundreds of thousands of examples. The investment required to close this gap (massive data collection + training) is not appropriate when pre-trained models already solve the problem.

### Alternatives Rejected

- **Character-level LSTM** — Requires learning everything from scratch; fails empirically on semantic similarity.
- **BoW** — Loses word order and compositional meaning.

### Confidence Level

High. Both theoretical (insufficient capacity) and empirical (observed similarity failures).

## Expected Outcomes

- Semantic similarity correctly captured by embedding model
- FLUME VAE receives meaningful input for structured compression

## Metrics & Impact

### Estimated

- Paraphrase similarity: <0.3 → >0.85

### Actual (Post-Implementation)

- Downstream trajectory analysis produces interpretable clusters

## Related Decisions & Lessons

- [[2026-02-23-character-level-tokenizers-are-inadequate-for-semantic-embeddings]]
- [[latent-coherence-stability-predictor-lcsp]] — measures the semantic coherence quality that character-level tokenizers fail to produce
- [[2026-02-24-anti-pattern-sha-256-as-semantic-embedding]] — related anti-pattern: hashes also lack semantic content
- [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning]] — hash-based approach fails for same fundamental reason: no semantic encoding
