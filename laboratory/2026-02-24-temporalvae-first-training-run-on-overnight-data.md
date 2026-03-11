---
title: "TemporalVAE First Training Run on Overnight Data"
date: "2026-02-24"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.585
  stage: mature
  cluster: experiments
---

## Hypothesis

A TemporalVAE (Variational Autoencoder with temporal attention layers) trained on the real 5.5M trajectory dataset from the [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories|overnight simulation]] would learn a meaningful latent space that captures trajectory dynamics -- unlike previous training runs on synthetic Gaussian noise, which learned to reconstruct randomness rather than structure. The hypothesis predicted that the VAE's reconstruction loss would converge to a lower value on real data (because real data has learnable structure) and that the latent space would show clustering corresponding to the trajectory families identified during characterization.

## Method

1. **Data preparation**: Loaded the post-transient-exclusion dataset (~4.95M trajectories) from the overnight simulation. Applied the [[structured-experience-vector-layout]] format and split into training (80%), validation (10%), and test (10%) sets.
2. **Architecture**: TemporalVAE with 12D input (matching the [[2026-02-24-overnight-simulation-55m-12d-trajectories|12D trajectory embedding]]), temporal attention layers for sequence modeling, and a latent space dimensionality to be determined by the training run (starting at 32D latent).
3. **Training configuration**: Used the [[vae-checkpoint-format-with-config]] pattern for checkpointing, saving full reproducibility state (model weights, optimizer state, data loader position, random seeds) at regular intervals.
4. **Baseline comparison**: Compared training curves against the previous synthetic-data run to quantify the difference between real and synthetic training dynamics.
5. **Latent space analysis**: After training, projected the test set into latent space and applied clustering to check whether the learned representation preserves the trajectory family structure identified during characterization.
6. **Stability monitoring**: Applied the [[latent-coherence-stability-predictor-lcsp|LCSP]] pattern to track latent space stability throughout training, detecting any signs of mode collapse or posterior collapse.

## Results

- **Training convergence**: Reconstruction loss converged to a significantly lower value on real data compared to synthetic Gaussian data, confirming that the model learned genuine trajectory structure rather than noise patterns.
- **Latent space structure**: Clustering analysis of the latent space showed separation corresponding to the 4 main trajectory families (bound, scatter, capture, eject) identified during characterization. The latent space was not a featureless blob.
- **LCSP stability**: Latent coherence remained stable throughout training without signs of posterior collapse. The temporal attention layers maintained consistent activation patterns across training epochs.
- **Checkpoint integrity**: All checkpoints saved in [[vae-checkpoint-format-with-config|full reproducibility format]], enabling exact training resumption from any checkpoint.
- **Training time**: Full training on ~4M trajectories completed within the expected time budget using available compute resources.

## Analysis

This first real-data training run validated the entire pipeline from simulation through characterization through embedding through training. The meaningful latent space structure proves that the [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]] decision was correct: synthetic data training produced a VAE that could reconstruct noise (high loss, no structure), while real data training produced a VAE that captures actual trajectory dynamics (lower loss, clustered latent space).

The temporal attention layers proved their value by capturing sequence-level patterns (acceleration, deceleration, orbital period) that a standard VAE without temporal awareness would miss. This validates the TemporalVAE architecture choice over simpler alternatives.

## Learnings

1. **Real data produces qualitatively different training dynamics**: Loss curves on real data show characteristic "elbow" patterns as the model learns successive trajectory features, unlike the smooth monotonic decrease on synthetic data.
2. **Latent space clustering validates data characterization**: The trajectory families visible in the raw data survive encoding into the latent space, confirming the VAE preserves meaningful structure.
3. **LCSP monitoring catches training instabilities early**: The [[latent-coherence-stability-predictor-lcsp|LCSP]] pattern provided early warning for one near-collapse episode that was resolved by reducing the learning rate. Without monitoring, this would have gone undetected until evaluation.
4. **[[checkpoint-format-with-full-reproducibility-state|Full reproducibility checkpoints]] are non-negotiable**: The ability to resume from any checkpoint with bit-exact reproducibility saves hours of wasted compute when training is interrupted or hyperparameters need adjustment.
5. **The simulation-to-training pipeline works end-to-end**: From overnight N-body simulation through characterization, embedding, and now training, the complete data pipeline produces useful learned representations.

## Relevance to Cohezion

This experiment produces the first trained trajectory model for the Cohezion framework. The TemporalVAE's latent space becomes the representation layer for [[agent-journey-tracking]]: agent trajectories can be projected into this latent space for comparison, clustering, and prediction. The [[predictive-throttling-via-12d-trajectory-velocity|predictive throttling]] system uses the latent representation to detect trajectory velocity changes that predict resource exhaustion. By training on real simulation data instead of synthetic noise, the model captures the actual dynamics of trajectories through the [[12D-Manifold]], making its predictions operationally meaningful.

## Related

- [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories]] — the overnight simulation data used as training input for this run
- [[latent-coherence-stability-predictor-lcsp]] — the LCSP pattern should be applied during this run to track latent space stability convergence
- [[checkpoint-format-with-full-reproducibility-state]] — checkpoint format to use for all saves in this run to ensure full reproducibility from overnight data
- [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]] — the decision requiring real simulation data (which this run satisfies via the overnight dataset)
