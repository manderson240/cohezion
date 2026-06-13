---
name: vae-decoder-depth-pitfall
description: |
  Critical VAE debugging: 3-layer decoder causes posterior collapse (kl≈0.30 vs
  healthy 0.79) and reconstruction degrades from 0.89 to 0.91+. Use when: (1) VAE
  training gives kl_loss < 0.4 despite reasonable β, (2) reconstruction loss won't
  improve below 0.91, (3) experimenting with decoder depth. Symptom: kl_loss drops
  from healthy ~0.8 to ~0.3 after adding a hidden layer to decoder.
author: Claude Code
version: 1.0.0
---

# VAE Decoder Depth Pitfall

## Problem

Adding an extra hidden layer to a VAE decoder causes the encoder to converge to a degenerate solution where the latent code carries little information (partial posterior collapse). The reconstruction quality degrades significantly despite more decoder capacity.

## Symptom

```
# Healthy (2-layer decoder):
kl_loss ≈ 0.79   recon_loss ≈ 0.89

# Broken (3-layer decoder):
kl_loss ≈ 0.30   recon_loss ≈ 0.91+
```

kl_loss drops to 0.3 despite identical training config, β, learning rate, and data.

## Root Cause

The extra hidden layer `Linear(hidden, hidden)` in the decoder creates a more flexible reconstruction path. With this extra capacity:
1. The encoder can map all inputs to more diffuse latent distributions (lower variance)
2. The decoder can still reconstruct adequately from near-prior latents
3. The model settles in a "soft collapse" where KL is low but not zero

The 3-layer decoder provides enough capacity that the encoder doesn't need an expressive latent code — it can get by with noise-like latents, losing the learned structure.

## Fix

```python
# WRONG (3-layer — causes KL collapse):
vae._dec = nn.Sequential(
    nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
    nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),  # ← remove this
    nn.Linear(hidden_dim, input_dim),
)

# CORRECT (2-layer):
vae._dec = nn.Sequential(
    nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
    nn.Linear(hidden_dim, input_dim),
)
```

## Why 2-Layer Works Better

The 2-layer decoder creates a "bottleneck of capacity" between latent→hidden→output. The encoder must place structure in the latent code because the decoder can't compensate with extra layers. This is the opposite of intuition (more capacity = worse) but follows from VAE theory: the encoder and decoder compete, and a simpler decoder forces the encoder to work harder.

## Scope

Validated for:
- 768-dim text embedding inputs
- latent_dim=768 (no compression)
- hidden_dim=4096
- cyclic β with max β=0.01
- 500 training steps, N_train=160

## Verification

After fixing decoder depth, confirm:
- `kl_loss > 0.6` (healthy utilization of latent space)
- `recon_loss ≈ 0.89` (significantly better than 0.91+)

## Reference

Discovered during FLUME VAE autoresearch (2026-05-15, overnight-flume-optimizer worktree).
See `src/cohezion/flume/training.py:TrainConfig.use_legacy_3layer_decoder` for production guard.
