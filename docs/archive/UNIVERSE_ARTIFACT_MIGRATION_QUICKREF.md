# Universe Artifact Migration - Quick Reference

**Phase 2 & 3 Implementation (Session 55)**

---

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/cohezion/knowledge_graph/universe_artifact_surrealdb_schema.sql` | 323 | SurrealDB schema: 6 tables, 15 indexes, 3 views, 2 functions |
| `src/cohezion/knowledge_graph/universe_artifact_migration.py` | 420 | Migration service: Phases 0-3 orchestration |

---

## Database Schema Overview

### Core Tables

1. **universe_training_runs** (training run metadata)
   - Fields: run_id, timestamp, model_id, universe_epoch, coherence_score
   - Indexes: timestamp, model_id, epoch, status
   - Size: ~500 rows (1 per training run)

2. **universe_artifacts** (artifact files)
   - Fields: artifact_id, run_id, file_path, file_size_bytes, content_hash
   - Supports: compression (file_compressed), language model tracking
   - Indexes: run_id, artifact_type, training_phase, verified
   - Size: ~200K rows (max 100GB storage)

3. **artifact_journey_links** (JourneyTracker integration)
   - Links artifacts to 12D journey states
   - Fields: artifact_id, journey_id, universe_coordinates, flume_embedding
   - Semantic alignment scoring (0.0-1.0)
   - Enables: "Which journey steps generated these artifacts?"

4. **artifact_collections** (grouped queries)
   - Organizes artifacts by semantic/temporal/experimental criteria
   - Fields: collection_id, artifact_ids (array), collection_type
   - Example: "All semantic drift artifacts from epoch 5"

5. **universe_patterns** (extracted learnings)
   - Captures patterns discovered during analysis
   - Fields: pattern_name, pattern_type, confidence_score, affected_artifacts
   - Stores Phase 1 extraction results

6. **migration_snapshots** (audit trail)
   - Tracks migration progress per phase
   - Fields: phase, timestamp, artifacts_processed, status
   - Enables: safe rollback/recovery

---

## Migration Service API

### Basic Usage

```python
from cohezion.knowledge_graph.universe_artifact_migration import UniverseArtifactMigration

# Initialize
migration = UniverseArtifactMigration()

# Execute full pipeline
results = migration.execute_full_migration()

# Check results
print(results["status"])  # "completed" or "failed"
print(results["phase_0_measure"])
print(results["phase_1_extract"])
print(results["phase_2_migrate"])
print(results["phase_3_verify"])
print(results["total_duration_seconds"])
print(results["total_errors"])
```

### Individual Phases

```python
migration = UniverseArtifactMigration()

# Phase 0: Measure artifacts in git
measure_results = migration.phase_0_measure()
# Returns: {file_count, total_size_mb, commit_count, duration_seconds}

# Phase 1: Extract to tar.gz
extract_results = migration.phase_1_extract()
# Returns: {tar_path, tar_size_mb, checksum, member_count, duration_seconds}

# Phase 2: Prepare migration
migrate_results = migration.phase_2_migrate()
# Returns: {schema_prepared, expected_inserts, migration_status, duration_seconds}

# Phase 3: Verify integrity
verify_results = migration.phase_3_verify()
# Returns: {verified_samples, verification_status, duration_seconds}
```

---

## Command Line Usage

```bash
# Execute full migration
uv run python src/cohezion/knowledge_graph/universe_artifact_migration.py

# Monitor progress
tail -f /tmp/cohezion_universe_artifacts_export/migration_report.json

# Check results
cat /tmp/cohezion_universe_artifacts_export/migration_report.json
```

---

## SurrealDB Queries

### Apply Schema

```bash
# Apply schema to running SurrealDB
surreal sql --conn ws://localhost:8000 \
  --namespace cohezion --database core \
  --file src/cohezion/knowledge_graph/universe_artifact_surrealdb_schema.sql
```

### Common Queries

```sql
-- View recent universe evolution
SELECT * FROM recent_universe_evolution LIMIT 10;

-- Track language drift
SELECT * FROM language_drift_timeline ORDER BY universe_epoch;

-- Artifact coverage by type
SELECT * FROM artifact_coverage_summary;

-- Find artifacts linked to specific journey
SELECT * FROM artifact_journey_links
WHERE journey_id = 'journey_123';

-- List all collections
SELECT * FROM artifact_collections;

-- Find patterns from specific epoch
SELECT * FROM universe_patterns
WHERE universe_epoch = 5
ORDER BY confidence_score DESC;

-- Migration progress
SELECT * FROM migration_snapshots
ORDER BY timestamp DESC LIMIT 5;
```

---

## Configuration

### Custom Paths

```python
from pathlib import Path
from cohezion.knowledge_graph.universe_artifact_migration import UniverseArtifactMigration

migration = UniverseArtifactMigration(
    cohezion_root=Path("/custom/path/to/cohezion"),
    output_dir=Path("/custom/export/dir"),
    surreal_ns="custom_ns",
    surreal_db="custom_db",
    surreal_url="ws://surreal.example.com:8000/rpc",
)

results = migration.execute_full_migration()
```

### Default Values

```python
cohezion_root = Path.home() / "dev" / "cohezion"
output_dir = Path("/tmp/cohezion_universe_artifacts_export")
surreal_ns = "cohezion"
surreal_db = "core"
surreal_url = "ws://localhost:8000/rpc"
```

---

## Monitoring & Troubleshooting

### Check Migration Status

```bash
# Read full report
python -c "import json; print(json.dumps(json.load(open('/tmp/cohezion_universe_artifacts_export/migration_report.json')), indent=2))"

# Count artifacts exported
tar -tzf /tmp/cohezion_universe_artifacts_export/artifacts/universe_artifacts.tar.gz | wc -l

# Verify tar integrity
tar -tzf /tmp/cohezion_universe_artifacts_export/artifacts/universe_artifacts.tar.gz > /dev/null && echo "✅ OK" || echo "❌ CORRUPT"
```

### Common Issues

**Issue**: `fatal: Not a valid object name HEAD:...`
- Cause: Artifact path doesn't exist in current branch
- Solution: Check if artifacts were purged; see backup branch

**Issue**: SurrealDB connection failed
- Cause: SurrealDB not running or URL incorrect
- Solution: Start SurrealDB or adjust `surreal_url` parameter

**Issue**: Permission denied on /tmp
- Cause: Output directory not writable
- Solution: Change `output_dir` or fix permissions: `chmod 777 /tmp`

---

## Integration Points

### With Cohezion Framework

```python
# In cohezion.compound.executor or other services:
from cohezion.knowledge_graph.universe_artifact_migration import UniverseArtifactMigration


async def execute():
    migration = UniverseArtifactMigration()
    # All I/O is prepared for async patterns
    results = migration.execute_full_migration()
    # Non-blocking even if errors occur
    return results
```

### With SurrealDB Client

```python
from cohezion.core.persistence.surreal_client import get_surreal_client


async def insert_artifacts():
    client = await get_surreal_client()

    # Create training run
    await client.query(
        """
        CREATE universe_training_runs SET
            run_id = $run_id,
            timestamp = now(),
            model_id = $model_id,
            universe_epoch = $epoch,
            coherence_score = $coherence
    """,
        {"run_id": "run_001", "model_id": "gpt-4", "epoch": 5, "coherence": 0.87},
    )
```

---

## Performance Expectations

| Phase | Operation | Duration | Notes |
|-------|-----------|----------|-------|
| 0 | Measure | <30s | Git operations, file counting |
| 1 | Extract | 10-60s | Creates tar.gz, calculates SHA256 |
| 2 | Migrate | <5s | Prepares SurrealDB insertion |
| 3 | Verify | 5-10s | Samples tar file integrity |
| Total | Full pipeline | <2 min | Depends on git history size |

### Query Performance (With Indexes)

| Query | Latency | Notes |
|-------|---------|-------|
| recent_universe_evolution | <50ms | Materialized view, cached |
| artifact_journey_links lookup | <100ms | Single index query |
| artifact_coverage_summary | <200ms | Aggregation with grouping |
| language_drift_timeline | <150ms | Time-series ordering |

---

## Testing

### Unit Tests

```bash
# Run migration service tests
uv run pytest tests/knowledge_graph/test_universe_artifact_migration.py -v

# Test specific phase
uv run pytest tests/knowledge_graph/test_universe_artifact_migration.py::test_phase_0_measure -v
```

### Integration Tests

```bash
# Test with real SurrealDB
uv run pytest tests/knowledge_graph/test_universe_artifact_migration_integration.py -v
```

---

## Next Steps

1. **Phase 4: Verification**
   - Apply schema to SurrealDB
   - Test basic queries
   - Verify indexes work

2. **Phase 5: Cleanup Planning**
   - Document migration results
   - Plan removal from git (if needed)
   - Update .gitignore

3. **Phase 6: Learning Extraction**
   - Document patterns discovered
   - Create PRIME skill definitions
   - Add to compound engineering library

---

## References

- Schema file: `src/cohezion/knowledge_graph/universe_artifact_surrealdb_schema.sql`
- Service file: `src/cohezion/knowledge_graph/universe_artifact_migration.py`
- Full documentation: `SESSION_55_SCHEMA_ENGINEER_PHASE_2_3_DELIVERABLES.md`
- SurrealDB docs: https://surrealdb.com/docs
