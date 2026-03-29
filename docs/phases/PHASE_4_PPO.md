# Phase 4: TRIUNE PPO Trainer

## Overview

Implements a PyTorch PPO (Proximal Policy Optimization) trainer with a 3-tier TRIUNE policy head for the FlumeNav environment.

## Architecture

### TRIUNE Policy Network

The TRIUNE (Knower→Thinker→Doer) policy implements a three-tier hierarchy:

```
256D VAE Latent (z)
    │
    ▼
┌─────────────────────────┐
│  KNOWER (256 → 2048)   │ Abstract feature extraction
│  nn.Linear + ReLU       │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  THINKER (2048 → 512)   │ Structured reasoning
│  nn.Linear + ReLU +     │
│  nn.Linear + ReLU       │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  DOER (512 → 12)        │ Action emission
│  nn.Linear + ReLU +     │
│  nn.Linear + Tanh       │ → bounded [-1, 1]
└─────────────────────────┘
    │
    ▼
12D Action
```

### Value Network

Separate value head for state value estimation (used in GAE advantage computation):

```
256D VAE Latent (z)
    │
    ▼
┌─────────────────────────┐
│  nn.Linear(256, 512)    │
│  nn.ReLU()             │
│  nn.Linear(512, 256)    │
│  nn.ReLU()             │
│  nn.Linear(256, 1)     │
└─────────────────────────┘
    │
    ▼
1D State Value
```

## PPO Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `clip_epsilon` | 0.2 | PPO clip ratio |
| `n_epochs` | 4 | Epochs per update |
| `lr` | 3e-4 | Adam learning rate |
| `eps` | 1e-5 | Adam epsilon |
| `gamma` | 0.99 | Discount factor |
| `gae_lambda` | 0.95 | GAE lambda |
| `entropy_coef` | 0.01 | Entropy bonus coefficient |
| `value_coef` | 0.5 | Value loss coefficient |
| `max_grad_norm` | 0.5 | Gradient clipping norm |
| `min_samples` | 64 | Min samples for update |

## Key Algorithms

### GAE (Generalized Advantage Estimation)

```python
advantages, returns = compute_gae(rewards, values, dones, gamma, gae_lambda)
```

Computes advantages using the GAE formula:
- δ_t = r_t + γ * V(s_{t+1}) * (1 - done_t) - V(s_t)
- A_t = δ_t + γ * λ * (1 - done_t) * A_{t+1}

### PPO Update

Performs `n_epochs` iterations of:
1. Compute ratio = exp(new_log_prob - old_log_prob)
2. Clipped surrogate: min(ratio * A, clamp(ratio, 1-ε, 1+ε) * A)
3. Policy loss = -mean(min(surr1, surr2))
4. Entropy bonus = -entropy_coef * entropy(action_dist)
5. Value loss = value_coef * MSE(values, returns)
6. Update policy and value networks

## Memory Management

- Buffer stores transitions as 32-bit floats (np.float32)
- Minimum 64 samples required before update
- Buffer cleared after each update

## Checkpointing

Save/load includes:
- Policy state dict
- Value network state dict
- Optimizer state dict
- Scheduler state dict
- Log std parameter
- Config (PPOConfig)

## Files

| File | Purpose |
|------|---------|
| `src/cohezion/rl/ppo_trainer.py` | Implementation |
| `tests/rl/test_ppo_trainer.py` | Test suite |

## Integration

The PPO trainer works with:
- `FlumeNav-v0` environment (256D state, 12D action output)
- TRIUNE-weighted coherence computation
- EVO emission tracking

## References

- Schulman et al., "Proximal Policy Optimization Algorithms" (2017)
- FlumeNav environment (Phase 3)
