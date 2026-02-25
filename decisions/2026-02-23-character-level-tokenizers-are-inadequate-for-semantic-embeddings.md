---
title: 'Character-level tokenizers are inadequate for semantic embeddings'
date: '2026-02-23'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Pre-trained models encode vast linguistic knowledge. A 74-char vocab trained on small domain data cannot compete. Use pre-trained embeddings as input to a VAE that learns structured compression, not raw text understanding.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Character-level tokenizers are inadequate for semantic embeddings'
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

An early FLUME implementation built semantic embeddings from scratch using a 74-character vocabulary (lowercase letters, digits, punctuation). A small LSTM was trained on domain-specific agent state descriptions to produce dense vectors. Despite reasonable perplexity on the training set, the embeddings showed poor semantic similarity — "search for food" and "find food source" mapped to distant points in embedding space.

The 74-char vocabulary meant the model had to learn word boundaries, morphology, and semantics simultaneously from a limited domain corpus. It couldn't compete with models trained on billions of tokens.

## Decision

Use pre-trained embedding models (nomic-embed-text) as input to the FLUME VAE. The pre-trained model provides rich semantic representation; the VAE learns structured compression of that representation, not language understanding from scratch.

## Chosen Option

Pipeline: `agent_state_text → nomic-embed-text (768D) → FLUME VAE → latent (256D)`

The VAE's job is structured compression and trajectory modeling. Language understanding is delegated to the pre-trained model.

## Alternatives Considered

1. Character-level LSTM trained on domain data (74-char vocab)
2. Word-level bag-of-words
3. Fine-tuned small language model (GPT-2 scale)
4. Pre-trained embedding model (nomic-embed-text)

## Decision Reasoning

### Why This Option?

Pre-trained models have already learned semantic structure from orders of magnitude more data than any domain corpus we can collect. The capability gap is fundamental, not a training-time issue. The FLUME VAE should focus on what it can uniquely contribute: learning the geometric structure of agent trajectory space.

### Alternatives Rejected

- **Character-level LSTM** — Must learn morphology + semantics simultaneously from a tiny corpus. Empirically demonstrated to fail.
- **Bag-of-words** — Loses word order and context, breaks on paraphrase ("find food" ≠ "food find" in agent reasoning terms but equals in BoW).
- **Fine-tuned LLM** — Expensive, outside project scope, and likely overkill for state representation in a controlled environment.

### Confidence Level

High. The semantic similarity failure was observed empirically; the reason is theoretically well-understood.

## Expected Outcomes

- Semantically similar state descriptions cluster together in embedding space
- VAE receives meaningful input signal
- FLUME trajectory analysis produces interpretable geometric structure

## Metrics & Impact

### Estimated

- Semantic similarity for paraphrase pairs: from <0.3 (char-level) to >0.85 (pre-trained)

### Actual (Post-Implementation)

- Cosine similarity for near-identical states consistently >0.9 with nomic-embed-text input

## Related Decisions & Lessons

- [[2026-02-23-never-use-sha-256-hashes-as-semantic-embeddings]]
- [[2026-02-24-anti-pattern-character-level-tokenizer-for-semantic-embeddings]]
