# FLUME: 256D Latent Space Encoding

## Overview
FLUME (Flow-based Latent Universe Modeling Engine) is a Variational Autoencoder that compresses high-dimensional simulation data (2048D) into a manageable 256-dimensional latent space, then projects to 12D for agentic journey tracking.

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Parameters | 0 |
| Compression Ratio | 8.0:1 |
| Input Dimensions | 2048 |
| Latent Dimensions | 256 |
| Compression Efficiency | 87.5% |

## Architecture

Variational Autoencoder (VAE)

**Encoder:** 2048 → 1024 → 512 → 256
**Decoder:** 256 → 512 → 1024 → 2048

## Anthropic Alignment

### Long-Horizon Agentic Tasks
Captures temporal patterns across simulation epochs

### Navigate Ambiguity
Probabilistic latent representations

### Robust Infrastructure
Checkpoint trained to epoch 50 with stability metrics

## Checkpoints Available
- `flume_vae_ep2.pt` - Early training snapshot
- `flume_vae_ep50.pt` - **Primary checkpoint** (used for portfolio)

## Visualization
See `flume_latent_space.html` for interactive t-SNE projection of the 256D latent space.
