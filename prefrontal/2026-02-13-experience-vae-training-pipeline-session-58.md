---
title: "Experience to VAE Training Pipeline (Session 58)"
date: '2026-02-13'
status: accepted
tags: [decision, vae, training, experience-feedback, pipeline]
aspect: thinker
neural:
  activation: 0.533
  stage: growing
  cluster: decisions
---

# Experience to VAE Training Pipeline (Session 58)

## Context

The Cohezion platform's Variational Autoencoder (VAE) was being trained on synthetic data (random noise distributions) because no mechanism existed to feed real agent experience data into the training pipeline. The VAE's purpose is to learn a compressed latent representation of agent state — encoding 256-dimensional experience vectors into a lower-dimensional latent space for efficient similarity search and trajectory prediction.

Training on synthetic data meant the VAE learned to reconstruct random distributions, not the actual distributions of real agent behavior. This produced a latent space that was geometrically correct (encoder/decoder worked) but semantically empty (the latent dimensions didn't correspond to meaningful agent state variations).

The [[experience-feedback-loop]] required closing this gap: real experience data from SurrealDB (agent session observations, journey trajectories, decision embeddings) needed to flow into the VAE training pipeline so the latent space would reflect actual agentic behavior patterns.

## Decision

Build an **Experience-to-VAE training pipeline** that:

1. **Extracts real experience data from SurrealDB** — queries the `agent_journey` and `observation` tables for 256D feature vectors recorded during actual agent sessions
2. **Normalizes to 256D compatibility** — pads or truncates incoming vectors to match the existing VAE architecture's expected input dimension
3. **Implements graceful degradation** — when insufficient real data exists (cold start), falls back to synthetic data generated from a distribution that approximates the real data statistics (mean, variance of available real samples). As real data accumulates, the synthetic proportion decreases automatically
4. **Non-blocking SurrealDB access** — uses async queries with timeouts so the training pipeline does not depend on database availability. If SurrealDB is down, the pipeline proceeds with cached data or synthetic fallback
5. **Checkpoint compatibility** — training checkpoints include both model weights and the data source metadata (real/synthetic ratio, data timestamp range) for reproducibility per [[checkpoint-format-with-full-reproducibility-state]]

## Consequences

**Positive:**
- Closes the feedback loop — VAE latent space now reflects real agentic behavior distributions
- Graceful degradation ensures the pipeline works from day 1 (zero real data) through maturity (thousands of real observations)
- Non-blocking SurrealDB access prevents infrastructure coupling — training proceeds even when the database is unavailable
- Checkpoint metadata enables reproducing any training run with identical data composition

**Negative:**
- Real data is initially sparse — the VAE may not meaningfully improve until 100+ real observations are recorded
- 256D compatibility constraint limits flexibility — if the feature vector format changes, both the pipeline and the VAE architecture need updating
- Data extraction adds load to SurrealDB during training runs (mitigated by batching and caching)

## Alternatives Considered

**Continue training on synthetic data only:** Keep using random noise until the VAE architecture is finalized, then switch to real data. Rejected because the VAE architecture decisions depend on the data distribution — training on synthetic data produces a latent space that may need restructuring when real data is introduced.

**Real data only (no synthetic fallback):** Wait until sufficient real data exists before any training. Rejected because it blocks all VAE development until enough sessions have been recorded — a chicken-and-egg problem where the system cannot improve until it is already working.

**Direct embedding storage (no VAE):** Store raw 256D vectors and use cosine similarity for retrieval, skipping the VAE entirely. Rejected because the VAE provides dimensionality reduction (256D to 32D latent space) and interpolation capabilities that raw vectors do not — trajectory prediction requires smooth latent space traversal.

## Related

- [[surrealdb-agent-context-schema]] — the schema that stores the experience data this pipeline extracts
- [[experience-feedback-loop]] — the conceptual framework this pipeline implements
- [[meta-learning]] — the VAE performs meta-learning by extracting patterns across agent sessions
- [[checkpoint-format-with-full-reproducibility-state]] — the checkpoint pattern for reproducible VAE training runs
- [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]] — the anti-pattern this pipeline was designed to avoid
- [[2026-02-24-anti-pattern-training-vae-on-random-noise-syntheticflumedataset]] — detailed analysis of why synthetic random noise produces semantically empty latent spaces
- [[agentic-ai]] — the agentic AI framework whose experience data drives the training pipeline
- [[neural-network-architecture]] — the VAE is a neural network architecture with encoder-decoder structure
