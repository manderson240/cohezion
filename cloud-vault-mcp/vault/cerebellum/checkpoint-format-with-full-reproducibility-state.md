---
title: "Checkpoint Format with Full Reproducibility State"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.76
  stage: mature
  synapse_in: 10
  synapse_out: 11
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

- [[vae-checkpoint-format-with-config]]
- [[2026-02-24-flume-vae-v2-training-results]]
- [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data|Decision: Never Train VAE on Random Noise as Synthetic Data]] - Reproducibility requires meaningful training data
- [[2026-02-24-anti-pattern-training-vae-on-random-noise-syntheticflumedataset]] — the anti-pattern: checkpoint records must include dataset source to prevent silent reuse of synthetic data
- [[2026-02-23-never-use-sha-256-hashes-as-semantic-embeddings|Decision: Never Use SHA-256 Hashes as Semantic Embeddings]]
- [[2026-02-13-experience-vae-training-pipeline-session-58|Decision: Experience VAE Training Pipeline Session 58]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review|Experiment: Session 58 — 7-Phase Journey Enrichment]] — Phase 5 of this experiment implemented the VAE training pipeline where this checkpoint format applies
- [[2026-02-24-temporalvae-first-training-run-on-overnight-data]] — the TemporalVAE training run that requires full reproducibility state to enable re-run from overnight simulation data
- [[latent-coherence-stability-predictor-lcsp]] — LCSP temporal coherence metrics should be included in checkpoint history alongside train/val loss for complete training state

## Scientific Foundation

- [[protein-tape-recorder-cytotape]] — CytoTape is nature's implementation of this exact pattern: a protein fiber that records temporal signals in chronological order for post-mortem readout, analogous to the training history + random seeds + git commit this format preserves. Both answer the same question: "given this artifact, can you reconstruct exactly what happened and replay it?" CytoTape does it for cell biology; this checkpoint format does it for ML training. The biological insight — record the *sequence* not just the *endpoint* — is the key design principle.
- [[lesson-measurement-integrity-honest-reporting]] — the `git_dirty=True` warning in this pattern is a direct implementation of measurement integrity: a dirty-tree checkpoint cannot be honestly claimed as reproducible. Honest provenance tracking is the reproducibility equivalent of honest test reporting.
