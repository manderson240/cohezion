---
title: "FLUME Architecture"
date: 2026-03-05
tags: [concept, cohezion, flume, vae, latent-space, agent-trajectory]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 40
  synapse_out: 21
---

# FLUME Architecture

## What It Is

FLUME (Fast Latent Universal Manifold Encoder) is a variational autoencoder that compresses agent session trajectories into a 256-dimensional continuous latent space. The latent space enables three things that aren't possible with discrete representations: semantic similarity retrieval between sessions, anomaly detection via reconstruction error, and interpolation between behavioral states.

The key design decision: agent state is encoded as a sequence of 12-dimensional vectors capturing coherence, token efficiency, task complexity, skill coverage, and related axes. Each step in a session produces one 12D vector. A session becomes a trajectory through this space. FLUME compresses that trajectory into a single latent vector that can be retrieved, compared, and decoded.

## Architecture

**Encoder:** Maps 12D trajectory snapshots → probabilistic distribution (mean μ, log-variance σ²) in 256D latent space. Temporal self-attention layers capture sequential dependencies — tool-call ordering matters; the value of a debugging step depends on what preceded it.

**Reparameterization:** z = μ + ε·σ, where ε ~ N(0,1). Enables gradient-based training through stochastic sampling.

**Decoder:** Reconstructs 12D trajectories from latent samples for ELBO loss computation.

**Training objective:** ELBO = reconstruction loss − β·KL(q(z|x) || p(z)). Cyclical β annealing prevents posterior collapse in early training.

**Projection:** 256D latent space → 12D visualization coordinates via learned projection for Observatory rendering.

## Empirical Results (VAE v2, trained on 5.5M trajectories)

| Metric | v1 | v2 | Notes |
|---|---|---|---|
| Reconstruction MSE | 0.032 | 0.015 | 53% improvement |
| KL divergence | ~0 (collapsed) | 4.2 nats | Healthy — 2-8 nat target range |
| Training throughput | — | 3,200 traj/sec | Single GPU |
| Latent space structure | Random | Clustered | t-SNE shows success/fail separation |

**What the numbers mean:** KL divergence of 4.2 nats confirms the encoder is learning a meaningful posterior distinct from the prior — the latent space is being used, not bypassed. The t-SNE visualization shows distinct clusters for successful vs failed sessions with a gradient region for partial completions, indicating the latent space has captured a semantically meaningful behavioral axis.

**Status:** Results are from epochs 1-30 of a 100-epoch run. Full validation including semantic reconstruction fidelity (target: >70% semantic preservation) is pending. See [[2026-03-05-flume-kl-collapse-diagnostic]] for the planned full diagnostic.

## Key Empirical Finding: Hash-Based Encoding Fails

The prior approach encoded agent state by taking the first 12 bytes of SHA-256(state_string) normalized to floats. This produced positions that were internally consistent but semantically random — the avalanche property of SHA-256 means adjacent states map to distant positions.

**Observed failure:** Average step distance in 12D space ~1.4 (matches random walk expectation). Drift detection produced false positives on every step. Cluster analysis found no meaningful structure.

**After switching to FLUME embeddings:** Average step distance <0.3 for coherent trajectories. Interpretable geometric structure visible in visualization. Drift detection identifies genuine reasoning drift.

This was discovered empirically, documented as ADR [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories]], and validated through the trajectory visualization change.

## What Was Trained On

5.5M agent trajectories from an overnight N-body simulation, each trajectory representing an agent path through the 12D compound learning space. The simulation generates trajectories at scale; real Cohezion session trajectories supplement with authentic agent behavior.

Data characterization was a prerequisite — the [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories]] run identified outliers and quality issues that would have corrupted training on raw data.

## Anti-Patterns Documented

- [[2026-02-24-anti-pattern-training-vae-on-random-noise-syntheticflumedataset]] — SyntheticFLUMEDataset generated random noise; model learned to reconstruct noise perfectly (MSE → 0) with collapsed latent space
- [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning]] — SHA-256 position encoding produces semantically meaningless trajectories
- [[2026-02-24-anti-pattern-dual-vae-architecture-creates-integration-debt]] — two parallel VAE implementations created divergence; one coherent model beats two partial implementations
- [[2026-02-23-never-use-sha-256-hashes-as-semantic-embeddings]] — general principle derived from FLUME failure

## Open Questions (Validation Pending)

1. Does the 100-epoch model improve on the 30-epoch preliminary results?
2. What is the semantic reconstruction fidelity? (Target: >70% semantic preservation measured by entailment)
3. Do synthetic trajectories sampled from the prior decode to coherent agent behavior?
4. Does FLUME guidance help downstream agent task performance vs baseline without FLUME?

## Related Concepts

- [[agent-journey-tracking]] — the data collection system that produces trajectory inputs for FLUME training
- [[compound-engineering]] — FLUME embeddings make prior session knowledge retrievable, enabling compound engineering
- [[experience-feedback-loop]] — FLUME closes the loop from execution → training → better execution
- [[anomaly-detection]] — high reconstruction error flags anomalous sessions
- [[semantic-search]] — latent space enables semantic similarity search over sessions
- [[reinforcement-learning]] — EcoAgent environment uses FLUME embeddings for state representation
- [[neural-network-architecture]] — encoder-decoder VAE with temporal attention
- [[VAE-Encoder]] — the encoder component
- [[12D-Projection]] — visualization projection from 256D latent space
- [[Ouroboros-Loop]] — real-time stability monitoring using FLUME embeddings
- [[agents-as-exotic-vacuum-objects]] — FLUME provides the computational infrastructure for agent EVO precipitation
- [[12D-Manifold]] — the 12D Manifold is FLUME's input space; agent sessions are encoded as trajectories through the manifold before compression to 256D latent vectors

## Related Experiments and Decisions

- [[2026-02-13-first-real-data-vae-training-run]] — first training run on real (not synthetic) agent trajectory data
- [[2026-02-24-flume-vae-v2-training-results]] — v2 training results with temporal attention and cyclical annealing
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories]] — the critical empirical finding that FLUME embeddings are necessary
- [[2026-02-24-sprint-4-end-to-end-integration-compound-execution-flume-cache-pipeline]] — end-to-end integration with compound execution pipeline
- [[2026-03-05-flume-kl-collapse-diagnostic]] — planned full validation diagnostic

## Primary Sources

- Kingma & Welling (2013). *Auto-Encoding Variational Bayes*. arXiv:1312.6114 — foundational VAE architecture
- Fu et al. (2019). *Cyclical Annealing Schedule*. arXiv:1903.10145 — the annealing schedule that prevented KL collapse in v2
- Ha & Schmidhuber (2018). *World Models* — VAE + recurrent model for learning world representations; informs the temporal attention design
