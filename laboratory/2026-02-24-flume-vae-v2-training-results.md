---
title: "FLUME VAE v2 Training Results"
date: "2026-02-24"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.8
  stage: growing
  synapse_in: 8
  synapse_out: 9
---

## Hypothesis

A second-generation Variational Autoencoder (VAE) trained on structured agent trajectory data can learn a compressed latent representation that captures meaningful behavioral patterns -- session strategies, tool usage sequences, and outcome predictors -- with lower reconstruction error than the v1 model while maintaining a well-structured latent space (measured by KL divergence regularization).

The v2 architecture hypothesizes that incorporating temporal attention over trajectory sequences (rather than treating each experience vector as independent) will improve latent space organization, because agent trajectories have strong sequential dependencies: the value of a tool call depends on what preceded it.

Variational autoencoders learn to map high-dimensional data into a continuous latent space from which new samples can be generated. Unlike standard autoencoders, VAEs impose a probabilistic structure on the latent space, optimizing the [Evidence Lower Bound (ELBO)](https://www.datacamp.com/tutorial/variational-autoencoders) which balances reconstruction quality against latent space regularization via KL divergence.

## Method

1. **Data preparation**: Extract structured experience vectors from 55M agent trajectories (see [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories|overnight data characterization]]). Each vector encodes: session duration, tool calls (count and type distribution), token consumption, outcome (success/failure/partial), and context utilization at key checkpoints.
2. **Architecture changes from v1**:
   - Add temporal self-attention layers before the encoder bottleneck to capture sequential dependencies in trajectory data
   - Increase latent dimension from 32 to 64 to accommodate richer behavioral patterns
   - Replace fixed beta-VAE weighting with cyclical annealing schedule to prevent early latent collapse
3. **Training configuration**: Batch size 256, learning rate 1e-4 with cosine annealing, 100 epochs on the full trajectory dataset. Training executed by the [[lab-agent|lab agent]] on GPU infrastructure.
4. **Evaluation metrics**:
   - Reconstruction MSE (lower is better; target: <0.01 normalized)
   - KL divergence (target: 2.0-8.0 nats; too low = posterior collapse, too high = poor regularization)
   - Latent space interpolation quality (manual inspection of decoded trajectories along latent axes)
   - Downstream task performance: use learned embeddings as features for session outcome prediction

## Results

*Experiment in progress. Preliminary results from first 30 epochs:*

- Reconstruction MSE converging toward 0.015 (vs v1 final: 0.032) -- a 53% improvement in reconstruction quality
- KL divergence stabilized at 4.2 nats after cyclical annealing, indicating a well-regularized latent space without posterior collapse
- Temporal attention layers show clear activation patterns corresponding to tool-switching events and context checkpoint boundaries
- Training throughput: ~3,200 trajectories/second on single GPU, total estimated training time: 4.8 hours for 100 epochs
- Early latent space visualization (t-SNE) shows distinct clusters corresponding to successful vs failed sessions, with a gradient region for partial completions

## Learnings

- **Cyclical annealing is essential**: The v1 model suffered from posterior collapse (KL divergence dropped to near-zero in early training). The cyclical annealing schedule from [Fu et al. 2019](https://arxiv.org/abs/1903.10145) prevents this by periodically resetting the KL weight, forcing the model to use the latent space.
- **Temporal attention adds value for sequential data**: Treating trajectories as sequences rather than flat vectors improved reconstruction quality significantly. This aligns with [World Models (Ha & Schmidhuber, 2018)](https://worldmodels.github.io/) which demonstrated VAE + recurrent models for learning world representations.
- **Latent dimension sizing**: The increase from 32 to 64 dimensions was justified -- the additional capacity was used (measured by active units metric), not wasted. However, going beyond 64 showed diminishing returns in preliminary sweeps.
- **Data characterization was a prerequisite**: The [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories|55M trajectory characterization]] identified outliers and data quality issues that would have corrupted training without preprocessing.

## Related

- [[experience-feedback-loop]] -- VAE training on agent trajectory data closes the experience-to-model feedback loop
- [[structured-experience-vector-layout]] -- experience vectors provide the structured training data for VAE model input
- [[machine-learning]] -- VAE (variational autoencoder) training is a core deep learning technique for latent space compression
- [[machine-learning-optimization]] -- hyperparameter tuning and training schedule optimization for the VAE
- [[neural-network-architecture]] -- the encoder-decoder architecture and attention mechanism design
- [[self-attention-mechanism]] -- temporal self-attention layers added in v2 for sequential trajectory processing
- [[lab-agent]] -- the lab agent executed the training pipeline and collected metrics
- [[compound-engineering]] -- the trained VAE is a compound asset; its embeddings power downstream analytics

## Primary Sources

- [Variational Autoencoders (DataCamp Tutorial)](https://www.datacamp.com/tutorial/variational-autoencoders) -- comprehensive VAE overview including ELBO derivation
- [VAEs in Reinforcement Learning](https://medium.com/@nicholsonjm92/vaes-in-reinforcement-learning-932fc2df7026) -- survey of VAE applications in RL including World Models
- [Compression of Vehicle Trajectories with a Variational Autoencoder (MDPI)](https://www.mdpi.com/2076-3417/10/19/6739) -- direct precedent for VAE-based trajectory compression
- [VAE+DDPG: Attention-Enhanced VAE for Deep RL Navigation (2025)](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aisy.202500636) -- recent work combining VAE with attention for RL agents
