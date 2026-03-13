# Phase 4: Bidirectional SurrealDB Sync — Design

**Date:** 2026-03-12
**Status:** APPROVED

## Problem

Phases 1-3 created a one-way pipeline: vault files sync to SurrealDB, and SurrealDB
pre-computes intelligence into vault markdown files. But SurrealDB-owned computed
state (activation after daily decay, stage transitions, inbound synapse counts) never
flows back to individual note frontmatter. The vault frontmatter `neural:` block is
stale the moment activation_decay.py runs.

## Domain Ownership Model

```
VAULT OWNS (content):          SURREALDB OWNS (graph state):
  title, date, tags, aspect      activation, stage
  status, body text              synapse_in, synapse_out
                                 cluster_id, last_fired
```

Content fields: vault is source of truth. Computed fields: SurrealDB is source of truth.

## Design: Approach 1 — Inline in vault_sync.py

### Part A: Forward Sync Fix (vault -> SurrealDB)

**Current bug:** sync_file() re-computes activation from file stats on every edit,
overwriting SurrealDB's decayed value.

**Fix:** On edit of an existing neuron, boost SurrealDB's current activation by +0.1
(capped at 1.0). Only compute from file stats for new neurons (first sync).

```python
if existing_nid:
    old = db.query_result(f"SELECT activation, stage FROM {nid} LIMIT 1;")
    if old:
        activation = min(1.0, old[0].get("activation", 0.5) + 0.1)
        stage = compute_stage(len(links), word_count, activation, days_since)
else:
    activation = compute_activation(word_count, len(links), days_since)
    stage = compute_stage(len(links), word_count, activation, days_since)
```

### Part B: Write-Back (SurrealDB -> vault frontmatter)

New `NeuralWriteBack` class, wired into the daemon alongside GraphReactor.

- **Throttle:** 300s (5 min)
- **Query:** All neurons in one SQL call
- **Diff:** Compare SurrealDB values against current frontmatter neural: block
- **Write:** Only files where values actually changed
- **Format:**
  ```yaml
  neural:
    activation: 0.61
    stage: growing
    synapse_in: 58
    synapse_out: 31
  ```

### Part C: Feedback Loop Prevention

Write-back modifies .md files -> inotify fires -> sync_file() runs.

1. **Content hash excludes neural: block:** New hash function strips the neural:
   YAML block before hashing. If only neural fields changed, hash matches -> skip.
2. **Write-back path set:** NeuralWriteBack sets a `_writeback_paths` set. sync_file()
   checks membership and skips re-sync. Cleared after each cycle.

### Part D: Checkpoint Upgrade

From `{path: timestamp}` to:
```json
{
  "path.md": {
    "hash": "content_hash_sans_neural",
    "neural_hash": "hash_of_neural_values",
    "synced_at": 1773198519.92
  }
}
```

Backward compatible: sync_file() already handles both float and dict entries.

### Part E: Wiring

```python
def watch_vault(db, quiet=False):
    reactor = GraphReactor(db)
    writeback = NeuralWriteBack(db)
    ...
    if events:
        if reactor.maybe_react(): ...
        if writeback.maybe_run(): ...
```

CLI: `python3 scripts/vault_sync.py --writeback` for manual one-shot.

## Performance

| Step | Cost |
|------|------|
| Query all neurons | 1 SQL, ~200ms |
| Read changed frontmatter | ~1ms/file, typically <50 files |
| Write updated files | ~1ms/file |
| Total | <500ms per cycle |

## Risks

- vault_sync.py is already 972 lines; this adds ~150 more. Module split is deferred.
- Frontmatter regex parsing could break on edge cases. Use the proven parse_frontmatter()
  already in vault_sync.py.
- 807 notes have neural: blocks; 227 don't. Write-back will add neural: to all content
  notes on first run.
