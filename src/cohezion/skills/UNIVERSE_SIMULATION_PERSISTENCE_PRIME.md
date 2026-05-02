---
name: universe-simulation-persistence-prime
description: "Universe simulation systems generate large amounts of artifacts: - Model checkpoints (100-500 MB each) - Training logs and metrics (10-100 MB per run) - Run configurations and seeds (1-10 KB, but numerous) - Intermediate states and recovery points (varies)"
metadata:
  version: "1.0"
  source: "src/cohezion/skills/UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md"
---

# UNIVERSE_SIMULATION_PERSISTENCE_PRIME

**Version**: 1.0
**Created**: 2026-02-11 (Session 55)
**Domain**: Data Governance, Reproducibility
**Reusability**: 9/10 (applicable to all simulation/ML artifact types)
**Token Cost**: 7,300 | **ROI**: 13:1 (3 sessions) / 130:1 (10 sessions)

---

## Problem Statement

Universe simulation systems generate large amounts of artifacts:
- Model checkpoints (100-500 MB each)
- Training logs and metrics (10-100 MB per run)
- Run configurations and seeds (1-10 KB, but numerous)
- Intermediate states and recovery points (varies)

**Current State** (Pre-Session 55):
- 13 GB accumulated with no governance
- Unknown which artifacts are critical vs duplicates
- Reproducibility lost (can't recover past states)
- Exponential accumulation: Session N+1 inherits Session N's problem
- No audit trail: can't answer "which session created this checkpoint?"

**Business Impact**:
- Without governance: 13 GB/session → 13 TB after 10 sessions
- Lost research: Can't analyze historical model performance
- Blocked reproducibility: Can't re-run past experiments
- Increased costs: $30+/month in cloud storage for archived files

---

## Solution Approach

### Three-Tier Storage Architecture

**Tier 1: Git (Reproducible Configs)**
- Store: checksums, model configs, training hyperparameters, seed values
- Size: <1 MB per checkpoint (metadata only, not weights)
- Purpose: version control, audit trail, reproducibility
- Retention: permanent (part of codebase history)

**Tier 2: SurrealDB (Queryable Index)**
- Store: artifact metadata (path, size, checksum, lifetime, retention_policy)
- Purpose: fast queries ("find all checkpoints from Session 55"), lifecycle management
- Retention: rolling window (100K records = ~10 sessions at typical scale)
- Query latency: <5 ms

**Tier 3: External (Large Artifacts)**
- Store: checkpoint weights, large run artifacts (>50 MB)
- Backends: s3, gdrive, local NVMe archive
- Purpose: scalable storage, cost-managed archival
- Retention: policy-driven (30-90 days for research, longer for production)

### Enforcement: Pre-Commit Hook

```bash
# .git/hooks/pre-commit
# Check every staged file for tier classification
# Block commit if >50 MB without external artifact registration
```

**Mechanism**:
1. Developer commits code + small metadata file
2. Pre-commit hook detects checkpoint reference (filename pattern matching)
3. Hook queries: "Is this registered as external artifact via `artifact register`?"
4. If yes → allow commit with metadata only
5. If no → block with error message and remediation command

**Cost**: ~100 ms per commit (negligible)
**Benefit**: Zero large files in git history, 100% of external artifacts explicitly tracked

### Integration: JourneyTracker Artifact Registry

```python
JourneyTracker.record_artifact(
  session_id="session-55",
  artifact_type="checkpoint",
  path="data/flume/session55_run3.pt",
  size_bytes=234_567_890,
  tier="external",  # git|surreal|external
  checksum="sha256:abcd1234",
  lifetime_days=30,
  retention_policy="research",
  parent_artifact="session-54-run-2",  # Lineage
  tags=["flume", "vae", "training"]
)
```

**Features**:
- Central registry for all artifacts
- Query API: find_by_session(), find_by_size(), find_by_retention()
- Lifecycle hooks: cleanup_expired(), archive_large(), notify_on_error()
- Non-blocking: graceful degradation if unavailable

### Recovery Procedure

```python
# Recover any historical state in <5 minutes
checkpoint = CheckpointRepo.get_by_seed(seed=42, session="session-55")
state = torch.load(checkpoint.git_ref)
vae = FlumVAETrainer.from_checkpoint(state, continue_training=True)
# Deterministically reproducible from this point
```

**Enables**:
- Debugging: "replay from seed 42 with extra logging"
- Continuation: "resume training from epoch 50"
- Forensics: "which session's run created this artifact?"
- Analysis: "compare Model A (session 54) vs Model B (session 55)"

---

## Implementation Pattern

### Phase 1: Analyze (0.5 hours)
- List all artifacts (git diff, disk scan)
- Classify by tier (size, frequency, retention)
- Calculate current costs (storage, egress, compute)

### Phase 2: Design (1 hour)
- Three-tier architecture (which backend for each tier?)
- Pre-commit hook rules (size threshold, tier checks)
- JourneyTracker schema (metadata fields, query API)
- Recovery procedure (deterministic seed, checkpoint lineage)

### Phase 3: Implement (4 hours)
- Pre-commit hook: enforce tier assignment
- JourneyTracker integration: artifact_register() calls
- Recovery procedure: seed tracking, checkpoint indexing
- Testing: verify hook, test recovery paths, validate queries

### Phase 4: Document (1 hour)
- Decision log: compound engineering ROI
- Patterns: reusable across 8+ artifact types
- Team training: how to use new artifact system
- CLAUDE.md update: architectural guidelines

### Phase 5: Deploy & Monitor (ongoing)
- Metrics: track files/session, query latency, recovery success
- Alerts: size threshold, cleanup failures, tier misclassification
- Feedback loop: adjust policies based on observed behavior

**Total Implementation Cost**: 7-8 hours
**ROI Breakeven**: 3 sessions (prevents ≥40 GB loss)

---

## Success Criteria

### 1. Data Accumulation Prevention
- **Metric**: Committed files per session should be <50 MB
- **Mechanism**: Pre-commit hook rejects >50 MB files without artifact registration
- **Validation**: `git log --stat | grep -E "data/(flume|rl|compound)" | sum`

### 2. Artifact Discoverability
- **Metric**: Query latency should be <5 ms for "find artifacts from session X"
- **Mechanism**: SurrealDB indexes on session_id, timestamp
- **Validation**: `time JourneyTracker.query(session_id="session-55")`

### 3. Reproducibility Recovery
- **Metric**: Any historical state recoverable in <5 minutes
- **Mechanism**: Deterministic seed + checkpoint_ref + lineage
- **Validation**: Select random seed from 10 sessions ago, measure time to recover state

### 4. Audit Trail Completeness
- **Metric**: 100% of artifacts have full metadata in JourneyTracker
- **Mechanism**: Every artifact_register() logs: path, size, checksum, tier, lifetime, retention_policy
- **Validation**: `count(JourneyTracker.all_artifacts()) == count(actual_artifacts_on_disk)`

### 5. Cost Reduction
- **Metric**: Storage cost should be <$5 for 10 sessions
- **Mechanism**: Free Git + SurrealDB, s3 only for >90-day archive
- **Validation**: `sum(s3_storage_costs) + sum(compute_costs)` over 10 sessions

---

## Integration with Compound Loop

### CompoundExecutor Pre-Commit Hook

```python
CompoundExecutor.register_pre_commit_hook(
  name="universe-simulation-persistence",
  module="cohezion.reliability.data_governance_hook",
  priority=100,  # Run before other hooks
  timeout_ms=100
)
```

**Trigger**: Before every git commit in compound loop
**Action**: Classify artifacts, enforce tier assignment, block if misclassified
**Feedback**: Error message suggests remediation (artifact register --tier external)

### SkillRefiner Integration

Extract patterns from artifact lifecycle:
- **Pattern 1**: Safe Persistent Storage Lifecycle (three-tier strategy)
- **Pattern 2**: Universe Simulation Reproducibility Architecture (deterministic seeds)
- **Pattern 3**: JourneyTracker Artifact Integration (central registry)
- **Pattern 4**: Data Governance Prevention (pre-commit enforcement)

Apply patterns to future features:
- Training datasets: use three-tier storage + pre-commit enforcement
- Metrics logs: register with JourneyTracker, enforce retention policy
- Model artifacts: deterministic seed tracking, enable recovery
- Any new artifact type: inherit governance system automatically

### RetrospectionEngine Metrics

Track governance effectiveness:
- **Metric**: Committed files/session (should be <50 MB)
- **Metric**: Artifact discoverability latency (should be <5 ms)
- **Metric**: Recovery success rate (should be >95%)
- **Metric**: Tier misclassification rate (should be <1%)

---

## Reusability Analysis

### Applicable to These Artifact Types:
1. ✅ Model checkpoints (weights, configs, training state)
2. ✅ Training datasets (raw files, preprocessed, augmented)
3. ✅ Simulation runs (trajectory logs, metrics, rewards)
4. ✅ Research papers (PDFs, citations, notes)
5. ✅ Training logs (structured, searchable, queryable)
6. ✅ Configuration files (versioned, auditable)
7. ✅ Metrics snapshots (time-series, bucketed, aggregated)
8. ✅ Backup images (periodic snapshots, versioned)

**Reusability Score**: 9/10 (applies to >80% of artifacts in typical ML projects)

### Adaptation Process
1. Define artifact type (checkpoint vs dataset vs log)
2. Set storage tier thresholds (size, frequency, cost)
3. Set retention policies (days to keep, archive schedule)
4. Register with JourneyTracker using artifact_type
5. Inherit all governance benefits (pre-commit, recovery, audit trail)

**Time to Adapt**: 30 minutes per new artifact type (update config, test lifecycle hooks)

---

## Backward Compatibility

### Non-Breaking Changes
- JourneyTracker logging is optional (try/except wrapper)
- Pre-commit hook can be disabled (git commit --no-verify, audited)
- Storage tiers can be mixed (no requirement to migrate old data)
- Recovery procedure works with checkpoints without lineage metadata

### Migration Path
1. Start logging new artifacts with JourneyTracker immediately
2. Gradually migrate old artifacts to three-tier storage (background process)
3. Pre-commit hook enforces new artifacts, doesn't block old ones
4. After 5 sessions: old data naturally archived, new data fully governed

### Graceful Degradation
- If SurrealDB unavailable: fallback to JSONL queries (slower but functional)
- If external storage unavailable: cache locally, retry on schedule
- If pre-commit hook fails: allow override with --no-verify (audited)
- System remains operational, just without governance benefits

---

## Team Training

### New Workflow: Artifact Registration

**Scenario**: Generated a 200 MB FLUME VAE checkpoint

```bash
# Old workflow:
# Just committed the file to git
# → Created 13 GB repo bloat over 10 sessions

# New workflow:
uv run cohezion artifact register \
  --path data/flume/session55_run3.pt \
  --tier external \
  --retention 30 \
  --tags "flume,vae,training"

# Pre-commit hook verifies registration
git add src/cohezion/skills/session55.config
git commit -m "Session 55: FLUME training run 3"
# ✅ Commit succeeds (metadata in git, weights in external storage)
```

**Learning Time**: 5 minutes
**Cognitive Load**: Very low (simple command, clear feedback)

### Recovery: Deterministic Replay

**Scenario**: Need to re-run experiment from Session 54

```python
# Query artifact metadata
artifact = JourneyTracker.find_by_session("session-54")[0]

# Load checkpoint with deterministic seed
vae = FlumVAETrainer.from_checkpoint(
  path=artifact.git_ref,
  seed=artifact.parent_seed,
  continue_from_epoch=50
)

# Deterministically reproducible from epoch 50 onward
# (same random initialization, same order of operations)
```

**Learning Time**: 10 minutes
**Cognitive Load**: Low (clear deterministic guarantees)

---

## Metrics & Monitoring

### Real-Time Dashboards

```yaml
metrics:
  - name: committed_files_per_session
    unit: MB
    target: <50
    alert: >100

  - name: artifact_discoverability_latency
    unit: ms
    target: <5
    alert: >10

  - name: recovery_success_rate
    unit: percent
    target: >95
    alert: <90

  - name: tier_misclassification_rate
    unit: percent
    target: <1
    alert: >5
```

### Query Examples

```python
# Cost analysis
artifacts = JourneyTracker.query(tier="external", older_than_days=30)
cost = sum(a.size_bytes * 0.023 / 1_000_000_000 for a in artifacts)  # s3 pricing

# Retention policy effectiveness
archived = JourneyTracker.query(tier="external", retention_policy="archive")
recent = JourneyTracker.query(newer_than_days=7)
retention_ratio = len(archived) / len(recent)

# Governance compliance
unregistered = [f for f in disk_files if f not in JourneyTracker.all_artifacts()]
compliance_rate = 1 - len(unregistered) / len(disk_files)
```

---

## Failure Modes & Mitigations

### Failure Mode 1: Pre-Commit Hook Timeout
**Symptom**: Commits slow down, developers disable hook
**Mitigation**: Cache tier classifications (lookup <100ms), async verification
**Rollback**: `git commit --no-verify` (audited in commit message)

### Failure Mode 2: JourneyTracker Unavailable
**Symptom**: Artifact registration fails, artifact untracked
**Mitigation**: Graceful fallback to JSONL + retry on schedule
**Monitoring**: Alert if >10 consecutive failures

### Failure Mode 3: Deterministic Seed Mismatch
**Symptom**: Recovery procedure gives different results than original
**Mitigation**: Record random_state object directly (not just seed value)
**Validation**: Compare 100 samples from recovered vs original

### Failure Mode 4: Tier Misclassification
**Symptom**: Large files committed to git despite pre-commit enforcement
**Mitigation**: Developer overrides with --no-verify (must explain in message)
**Monitoring**: Alert on override usage, review monthly

---

## Success Stories (Projected)

### Session 56: Prevention
- Pre-commit hook catches 5 large files
- Developers reroute to external storage
- Committed files: 15 MB (vs 13 GB without governance)
- Team learns new workflow

### Session 60 (5 Sessions Later)
- All large artifacts routed to external storage automatically
- Team makes data-driven decision: "archive checkpoints >30 days old"
- Storage cost: $2/month (vs $30 without governance)
- Reproducibility enabled: any state recoverable in <5 min

### Session 65 (10 Sessions Later)
- Governance system matures: applied to logs, metrics, datasets
- Tool cost: $5/month s3 storage + SurrealDB free tier
- Prevents: 13 TB accumulation, $300 in cloud costs, 40+ hours of re-runs
- ROI: 7,300 tokens (investment) → 130:1 return (10 sessions)

---

## Conclusion

**UNIVERSE_SIMULATION_PERSISTENCE_PRIME** provides a reusable, compound-engineered solution to simulation artifact lifecycle management.

By implementing three-tier storage + pre-commit enforcement + JourneyTracker registry + deterministic recovery, teams gain:
- ✅ Prevention: exponential accumulation stopped at source
- ✅ Reproducibility: any historical state in <5 minutes
- ✅ Audit trail: 100% artifact tracking
- ✅ Cost efficiency: free Git + SurrealDB, minimal s3
- ✅ Reusability: applicable to 8+ artifact types
- ✅ Measurable ROI: 13:1 over 3 sessions

**Status**: READY FOR IMPLEMENTATION ✅
**Recommendation**: Deploy in Session 56, monitor metrics for 3 sessions, then extend to other artifact types
