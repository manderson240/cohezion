---
title: "Checkpoint Format with Full Reproducibility State"
date: "2026-02-24"
tags: [pattern]
---

## Problem

Model checkpoints often save only weights (`state_dict`), making it impossible to reproduce training or understand provenance. When a checkpoint produces unexpected behavior, you can't diagnose whether the issue is the architecture, the data, the hyperparameters, or the random seed used during training.

This is a more comprehensive version of the VAE checkpoint pattern, emphasizing complete reproducibility — not just the ability to load the model, but to re-run the training and get the same result.

## Solution

Save a checkpoint that contains everything needed to reproduce the training run from scratch:
- Complete model architecture config
- All training hyperparameters
- Random seeds (Python, NumPy, PyTorch)
- Data source reference (path, hash, or version identifier)
- Environment state (library versions, git commit)
- Training history (loss curves, metrics at each epoch)

## Code Example

```python
import hashlib
import json
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

def capture_reproducibility_state() -> dict:
    """Capture all state needed to reproduce the current run."""
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        git_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"]).strip())
    except Exception:
        git_commit = "unknown"
        git_dirty = None

    return {
        "seeds": {
            "python": random.getstate()[1][0],
            "numpy": int(np.random.get_state()[1][0]),
            "torch": torch.initial_seed(),
        },
        "env": {
            "git_commit": git_commit,
            "git_dirty": git_dirty,
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "python_version": os.sys.version,
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def restore_reproducibility_state(state: dict) -> None:
    """Restore random seeds from saved state."""
    seeds = state["seeds"]
    random.seed(seeds["python"])
    np.random.seed(seeds["numpy"])
    torch.manual_seed(seeds["torch"])

def save_checkpoint(
    path: Path,
    model,
    optimizer,
    config: dict,
    hparams: dict,
    epoch: int,
    history: list[dict],
    dataset_info: dict,
) -> None:
    reproducibility = capture_reproducibility_state()

    checkpoint = {
        "format_version": 2,
        "config": config,
        "hparams": hparams,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "history": history,  # list of {epoch, train_loss, val_loss, ...}
        "dataset": dataset_info,  # {path, sha256, n_samples, split}
        "reproducibility": reproducibility,
    }
    torch.save(checkpoint, path)
```

## When to Use

- Any training run where you want to be able to reproduce results exactly
- Before sharing a checkpoint with collaborators
- When training is expensive and you need confidence you can recover from a bug
- Research workflows where exact reproducibility is required for publication

**Data hashing**: Include `sha256` of the dataset file or a dataset version identifier. Without this, "same checkpoint" + "different data" produces mystery results.

**Dirty git**: Log a warning when `git_dirty=True`. A checkpoint from a dirty tree cannot be exactly reproduced from the git commit alone.

## Related

- [[patterns/vae-checkpoint-format-with-config]]
- [[experiments/2026-02-24-flume-vae-v2-training-results]]
