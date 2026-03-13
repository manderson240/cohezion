---
title: "Latent Coherence Stability Predictor (LCSP)"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.73
  stage: growing
  synapse_in: 15
  synapse_out: 7
---

## Problem

A VAE produces latent representations, but latent representations can be unstable: the same semantic input might produce very different latent vectors across training epochs, or the latent space geometry may shift. This makes it hard to:
- Detect when the model has changed meaningfully between checkpoints
- Predict whether the current latent representation will remain stable as training continues
- Set early stopping criteria based on representation stability rather than just reconstruction loss

## Solution

A **Latent Coherence Stability Predictor (LCSP)** maintains a set of anchor inputs — semantically meaningful states sampled from the training distribution — and tracks their latent representations over time. Coherence is measured as the consistency of latent representations for the same inputs across training steps.

Two types of coherence:
1. **Temporal coherence**: Does the same input map to similar latent vectors over consecutive training steps? (low = model is changing rapidly)
2. **Semantic coherence**: Do semantically similar inputs cluster in latent space? (low = model hasn't learned semantic structure)

## Code Example

```python
import torch
import numpy as np
from torch import Tensor

class LatentCoherenceStabilityPredictor:
    """Tracks latent space stability over training."""

    def __init__(self, model, anchor_inputs: Tensor, n_history: int = 10):
        self.model = model
        self.anchor_inputs = anchor_inputs  # (N_anchors, input_dim)
        self.n_history = n_history
        self._latent_history: list[Tensor] = []

    @torch.no_grad()
    def record(self) -> dict:
        """Record current latent representations for all anchors."""
        mu, _ = self.model.encode(self.anchor_inputs)
        self._latent_history.append(mu.cpu())
        if len(self._latent_history) > self.n_history:
            self._latent_history.pop(0)
        return self.compute_metrics()

    def compute_metrics(self) -> dict:
        if len(self._latent_history) < 2:
            return {"temporal_coherence": 1.0, "semantic_coherence": None}

        # Temporal coherence: cosine similarity between consecutive latent snapshots
        prev = self._latent_history[-2]
        curr = self._latent_history[-1]
        cos_sim = torch.nn.functional.cosine_similarity(prev, curr, dim=-1)
        temporal_coherence = float(cos_sim.mean())

        # Semantic coherence: intra-cluster similarity vs inter-cluster similarity
        # Requires anchor labels; compute if available
        semantic_coherence = self._compute_semantic_coherence(curr)

        return {
            "temporal_coherence": temporal_coherence,
            "semantic_coherence": semantic_coherence,
            "latent_variance": float(curr.var(dim=0).mean()),
        }

    def _compute_semantic_coherence(self, latents: Tensor) -> float | None:
        """If anchors have semantic groupings, measure intra/inter-group similarity."""
        # Implement based on available anchor metadata
        return None

    def is_stable(self, min_temporal_coherence: float = 0.95) -> bool:
        """True if latent space has stabilized."""
        metrics = self.compute_metrics()
        return metrics["temporal_coherence"] >= min_temporal_coherence
```

## When to Use

- Long training runs where you want to know when the model has "converged" in representation space, not just in loss
- Detecting training instability (sudden drops in temporal coherence = training divergence)
- Comparing checkpoints: "has the model meaningfully changed since the last checkpoint?"
- Setting data-driven early stopping criteria

**Anchor selection**: Choose anchors that represent diverse, semantically distinct states. Include edge cases and common cases. 50-200 anchors is typically sufficient.

**Integration with training loop**: Record metrics every N steps. Log to your training tracker alongside train/val loss.

## Related

- [[2026-02-23-hiho-coherence-loss-must-target-per-sample-not-batch-mean]]
- [[2026-02-24-anti-pattern-hiho-coherence-loss-on-batch-mean]] — batch-mean anti-pattern that LCSP metrics expose
- [[2026-02-24-anti-pattern-character-level-tokenizer-for-semantic-embeddings]] — poor embeddings produce low LCSP semantic coherence scores
- [[vae-checkpoint-format-with-config]]
- [[2026-02-24-temporalvae-first-training-run-on-overnight-data]] — the first TemporalVAE training run where LCSP should be applied to detect whether the latent space stabilizes
- [[checkpoint-format-with-full-reproducibility-state]] — LCSP temporal coherence metrics belong in the full reproducibility checkpoint so convergence evidence is preserved alongside weights
- [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories]] — the 55M trajectory dataset whose diversity determines representative anchor input selection for semantic coherence measurement
