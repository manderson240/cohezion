---
title: "VAE Checkpoint Format with Config"
date: "2026-02-23"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 3
  synapse_out: 4
---

## Problem

Neural network checkpoints saved with only model weights (`state_dict`) are fragile: they can only be loaded if you have the exact same model class with the exact same architecture. When you iterate on model architecture (different hidden dims, different depth), old checkpoints become unloadable. Additionally, checkpoints without training metadata make it impossible to diagnose why a model behaves a certain way.

## Solution

Save checkpoints as structured dicts containing both the model weights and the complete configuration needed to reconstruct the model from scratch. Include training provenance metadata.

Checkpoint structure:
```
{
  "config": { full model architecture config },
  "model_state_dict": { weights },
  "optimizer_state_dict": { optimizer state, for resuming },
  "training": {
    "epoch": N,
    "step": N,
    "train_loss": ...,
    "val_loss": ...,
    "best_val_loss": ...,
  },
  "metadata": {
    "created_at": ISO timestamp,
    "dataset": path or hash,
    "git_commit": hash,
    "python_version": ...,
    "torch_version": ...,
  }
}
```

## Code Example

```python
import torch
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class TemporalVAEConfig:
    input_dim: int = 768
    latent_dim: int = 256
    hidden_dims: list = None
    beta: float = 1.0

    def __post_init__(self):
        if self.hidden_dims is None:
            self.hidden_dims = [512, 256]

class CheckpointManager:
    def save(
        self,
        model,
        optimizer,
        config: TemporalVAEConfig,
        epoch: int,
        step: int,
        train_loss: float,
        val_loss: float,
        path: Path,
        dataset_path: str | None = None,
    ) -> None:
        import subprocess
        try:
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip()
        except Exception:
            git_commit = "unknown"

        checkpoint = {
            "config": asdict(config),
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "training": {
                "epoch": epoch,
                "step": step,
                "train_loss": train_loss,
                "val_loss": val_loss,
            },
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "dataset": dataset_path,
                "git_commit": git_commit,
                "torch_version": torch.__version__,
            },
        }
        torch.save(checkpoint, path)

    @staticmethod
    def load(path: Path, device: str = "cpu"):
        """Load checkpoint and reconstruct model from saved config."""
        checkpoint = torch.load(path, map_location=device)
        config = TemporalVAEConfig(**checkpoint["config"])
        # Reconstruct model from config — no need to know architecture upfront
        from cohezion_engine.flume import TemporalVAE
        model = TemporalVAE(config)
        model.load_state_dict(checkpoint["model_state_dict"])
        return model, config, checkpoint["training"]
```

## When to Use

- Any model that will be iterated on (architecture will change)
- Checkpoints that need to be shared or used outside the training codebase
- When debugging requires understanding training provenance ("why does this checkpoint behave this way?")
- Production models where audit trail is required

**Never** use `torch.save(model)` (saves the entire class reference; breaks when class moves). Always use `torch.save(state_dict)` in combination with saved config.

## Related

- [[structured-feature-vector-layout-for-agent-state]]
- [[2026-02-24-flume-vae-v2-training-results]]
- [[checkpoint-format-with-full-reproducibility-state]] — extends this pattern with complete reproducibility state (random seeds, environment, data hashes)
- [[latent-coherence-stability-predictor-lcsp]] — LCSP metrics should be stored alongside checkpoint training metadata to track latent space convergence
