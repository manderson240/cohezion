---
name: flume-vae-optimal-config
description: |
  Optimal FLUME VAE configuration for 768-dim skill/text embeddings, validated by
  autoresearch loop (195+ experiments, 2026-05-15). Use when: (1) training a VAE on
  768-dim PRIME skill embeddings, (2) rebuilding FlumeVAE from scratch, (3) selecting
  hidden_dim for VAE architecture. Key result: hd=4096, 2-layer decoder, cyclic β
  amp=0.005 → 5-seed mean 0.8816 ± 0.005 (+13.2% vs β=1.0 baseline).
author: Claude Code
version: 1.0.0
---

# FLUME VAE Optimal Config

## Problem

What is the optimal hyperparameter configuration for training a FLUME VAE on 768-dim PRIME skill text embeddings?

## Solution

```python
from cohezion.flume.vae import build_optimal_vae

# Quick start — pre-configured optimal model:
vae = build_optimal_vae(input_dim=768, latent_dim=768, hidden_dim=4096)

# Or manual config via FlumeVAETrainer:
from cohezion.flume.training import TrainConfig, FlumeVAETrainer
config = TrainConfig(
    z_dim=768,
    hidden_dim=4096,
    use_legacy_3layer_decoder=False,  # 2-layer decoder is CRITICAL
    batch_size=128,
    kl_weight=0.01,
)
trainer = FlumeVAETrainer(config)
```

## Architecture (critical details)

```python
# 2-layer encoder (correct):
vae._enc = nn.Sequential(nn.Linear(768, 4096), nn.ReLU(), nn.Linear(4096, 4096), nn.ReLU())

# 2-LAYER decoder (correct — NOT 3-layer!):
vae._dec = nn.Sequential(nn.Linear(768, 4096), nn.ReLU(), nn.Linear(4096, 768))
```

## Training Recipe

```python
import math
opt = optim.AdamW(vae.parameters(), lr=3e-4, weight_decay=1e-4)
sched = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=500)

for step in range(500):
    beta = 0.005 * (1 - math.cos(2 * math.pi * step / 100))  # amp=0.005! (NOT 0.01)
    x = train_data[torch.randint(0, len(train_data), (160,))]
    out = vae(x)
    loss = flume_vae_loss(x, recon=out[0], mu=out[1], logvar=out[2], beta=beta)['total_loss']
    opt.zero_grad(); loss.backward(); opt.step(); sched.step()

# Evaluation: always use beta=0.0 for inference
vae.eval()
with torch.no_grad():
    vl = flume_vae_loss(val_data, recon=..., mu=..., logvar=..., beta=0.0)
```

## Architecture Law (multi-seed means, 768-dim input)

| hidden_dim | params | 4-seed mean | Notes |
|------------|--------|------------|-------|
| 512 | 2.2M | 0.9309 | default (bad) |
| 1024 | 5.0M | 0.9146 | — |
| 2048 | 12.1M | 0.8864 | reasonable |
| **4096** | **32.5M** | **0.8815** | **OPTIMAL** |
| 6144 | 61.4M | 0.8881 | worse (over-capacity) |
| 8192 | 98.6M | 0.9016 | much worse |

## Common Mistakes

1. **Wrong β amplitude**: `0.01 * (1 - cos(...))` → max β=0.02 (2× over-regularization). Use `0.005`.
2. **3-layer decoder**: causes kl=0.30 vs healthy 0.79; reconstruction degrades to 0.91+
3. **Too many steps**: 1000 steps OVERFITS at N_train=160 (5% regression vs 500 steps)
4. **Linear LR scaling**: 4× LR at bs=128 → near-baseline (1.0099). Don't scale LR with bs.
5. **Period tuning**: period 100-300 all give identical multi-seed means (0.8815). Don't optimize period.

## Verification

After training, check:
- `kl_loss ≈ 0.7-0.8` (healthy latent space)
- `recon_loss < 0.89` (below baseline)
- If `kl_loss < 0.4`: posterior collapse — reduce β or check decoder depth

## References

- `src/cohezion/flume/vae.py:build_optimal_vae()` — pre-built factory
- `src/cohezion/flume/training.py:TrainConfig` — config dataclass
- `autoresearch.md` in the overnight-flume-optimizer worktree — full experiment log
