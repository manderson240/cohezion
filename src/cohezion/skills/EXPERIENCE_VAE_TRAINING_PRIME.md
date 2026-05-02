---
name: experience-vae-training-prime
description: "Train the FLUME VAE on real agentic execution experiences instead of synthetic gaussian noise, closing the feedback loop between compound execution and universe simulation."
metadata:
  version: "1.0"
  source: "src/cohezion/skills/EXPERIENCE_VAE_TRAINING_PRIME.md"
---

# EXPERIENCE_VAE_TRAINING_PRIME

## Intent
Train the FLUME VAE on real agentic execution experiences instead of synthetic gaussian noise, closing the feedback loop between compound execution and universe simulation.

## Trigger
- After accumulating >=10 real execution records in Parquet/SurrealDB/vault
- After a session with significant compound execution activity
- Periodically (weekly) to update the VAE on latest behavior distributions

## Procedure

### 1. Collect Experiences
Gather execution records from three tiers:
- **Tier 1**: `data/journeys/shard_*.parquet` -- 12D trajectories + metadata
- **Tier 2**: SurrealDB `mission_journey` table (non-blocking, skip if unavailable)
- **Tier 3**: `~/vaults/cohezion-vault/experiments/**/*.json` vault files

### 2. Encode as 256D Vectors
Each experience is encoded via `ExperienceEncoder`:
```
Dims [0:12]   -- 12D axiomatic trajectory
Dims [12:24]  -- 12 scalar execution metrics (phi, anomaly, tokens, cost...)
Dims [24:29]  -- 5 operation type one-hot (generate/analyze/search/transform/persist)
Dims [29:256] -- 227 semantic fingerprint (SHA-256 hash expansion)
```

### 3. Build Dataset
- Pre-encode all experiences at init (fast `__getitem__`)
- Optional gaussian noise augmentation for regularization
- Compatible with existing `FlumeVAETrainer.train(dataset=...)`

### 4. Train VAE
- Uses `TrainConfig(z_dim=256)` and `FlumeVAETrainer`
- Graceful fallback: if real data < threshold, pad with `SyntheticFlumeDataset`
- Checkpoints saved to `data/flume/checkpoints/`

### 5. Verify
```bash
uv run pytest tests/flume/test_experience_pipeline.py -v
uv run python scripts/drivers/train_experience_vae.py --epochs 5 --min-real 1
```

## Key Files
| File | Purpose |
|------|---------|
| `src/cohezion/flume/experience_encoder.py` | 256D encoding (trajectory + metrics + one-hot + fingerprint) |
| `src/cohezion/flume/experience_collector.py` | Multi-tier data collection (Parquet, SurrealDB, vault) |
| `src/cohezion/flume/experience_dataset.py` | Torch Dataset returning 256D tensors |
| `src/cohezion/flume/experience_pipeline.py` | End-to-end orchestration with synthetic fallback |
| `scripts/drivers/train_experience_vae.py` | CLI entry point |

## Success Criteria
- Encoder output is deterministic (same input → same 256D vector)
- Pipeline completes with synthetic fallback when no real data exists
- Checkpoint is valid and loadable
- 5 tests pass in `tests/flume/test_experience_pipeline.py`

## Anti-Patterns
- Training on only synthetic data without logging a warning
- Blocking on SurrealDB when it's unavailable
- Using Python `hash()` instead of SHA-256 (non-deterministic across sessions)
- Hardcoding operation types instead of matching JourneyTracker.OperationType

## Tags
`flume`, `vae`, `training`, `experience`, `compound-engineering`
