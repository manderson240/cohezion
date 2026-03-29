---
name: cohezion-data-governance
description: Three-tier data storage governance for Cohezion universe simulations. Covers Git (Tier 1: configs), SurrealDB (Tier 2: queryable index), External/S3 (Tier 3: large artifacts). Includes pre-commit hook for >50MB files, JourneyTracker artifact registration, recovery procedures, and success metrics. Use when managing simulation artifacts, checkpoint storage, or implementing data governance.
---

# Data Storage Architecture for Simulations (Session 55 Patterns)

**Problem**: Universe simulation systems generate large artifacts (model checkpoints, training logs, metrics). Without governance, data accumulates exponentially: 13 GB/session → 13 TB after 10 sessions without controls.

**Solution**: Three-tier storage strategy with pre-commit enforcement and JourneyTracker registry.

### Three-Tier Storage Tiers

**Tier 1: Git (Reproducible Configs)**
- Store: checksums, model configs, training hyperparameters, seed values
- Size: <1 MB per checkpoint (metadata only, not weights)
- Purpose: version control, audit trail, reproducibility
- Retention: permanent (part of codebase history)
- Example: `data/flume/session55_config.json` (metadata, no weights)

**Tier 2: SurrealDB (Queryable Index)**
- Store: artifact metadata (path, size, checksum, lifetime, retention_policy)
- Purpose: fast queries ("find all checkpoints from Session 55"), lifecycle management
- Retention: rolling window (100K records = ~10 sessions at typical scale)
- Query latency: <5 ms
- Example: `JourneyTracker.query(session_id="session-55", tier="external")`

**Tier 3: External (Large Artifacts)**
- Store: checkpoint weights, large run artifacts (>50 MB)
- Backends: s3, gdrive, local NVMe archive
- Purpose: scalable storage, cost-managed archival
- Retention: policy-driven (30-90 days for research, longer for production)
- Example: `s3://cohezion-data/session-55/checkpoint-ep50.pt`

### Enforcement: Pre-Commit Hook

```bash
# .git/hooks/pre-commit
# Block commits if >50 MB files detected without external artifact registration

git diff --cached --name-only | while read file; do
  size=$(git cat-file -s ":0:$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
  if [ "$size" -gt 52428800 ]; then  # 50 MB
    echo "ERROR: Large artifact requires external storage registration"
    echo "Fix: uv run cohezion artifact register --path '$file' --tier external"
    exit 1
  fi
done
```

Cost: ~100 ms per commit | Benefit: prevents exponential accumulation

### JourneyTracker Artifact Registration

```python
from cohezion.compound.journey_tracker import JourneyTracker

JourneyTracker.record_artifact(
  session_id="session-55",
  artifact_type="checkpoint",
  path="data/flume/session55_run3.pt",
  size_bytes=234_567_890,
  tier="external",  # git|surreal|external
  checksum="sha256:abcd1234",
  lifetime_days=30,
  retention_policy="research",
  tags=["flume", "vae", "training"]
)

# Query for lifecycle management
artifacts = JourneyTracker.query(tier="external", older_than_days=7)
for artifact in artifacts:
  if artifact.is_expired():
    notify_ops(f"Archive cleanup due: {artifact.path}")
```

### Recovery Procedure (Deterministic Replay)

```python
# Recover any historical state in <5 minutes
checkpoint = CheckpointRepo.get_by_seed(seed=42, session="session-55")
state = torch.load(checkpoint.git_ref)
vae = FlumVAETrainer.from_checkpoint(state, continue_training=True)
# Deterministically reproducible from this point
```

### Success Metrics

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Committed files/session | <50 MB | Pre-commit hook enforces tier assignment |
| Artifact discoverability | <5 ms | SurrealDB queries on session_id, timestamp |
| Recovery time | <5 min | Deterministic seed + checkpoint lineage |
| Audit trail completeness | 100% | JourneyTracker registers every artifact |
| Storage cost | <$5/10 sessions | Free Git + SurrealDB, s3 for >90-day archive |

### Implementation Notes

- **Backward compatible**: JourneyTracker logging is optional (try/except wrapper)
- **Graceful degradation**: If SurrealDB unavailable, falls back to JSONL queries
- **Non-blocking**: All tracking operations non-blocking (won't crash system if unavailable)
- **Reusable patterns**: See `/vaults/cohezion-vault/patterns/` for extracted patterns

### Related PRIME Skills

- `UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md`: Complete specification with ROI analysis
- See: `src/cohezion/skills/UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md`
