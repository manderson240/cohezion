---
name: bidirectional-sync-pattern
description: |
  Design and implement bidirectional sync between a file store and a database
  without feedback loops or conflicts. Use when: (1) a daemon watches files
  and syncs to a DB, AND the DB also writes back to those files; (2) you need
  to prevent inotify → sync → write-back → inotify oscillation; (3) designing
  a system with two sources of truth that must stay in sync.
  Key insight: "conflict resolution" is eliminated by domain ownership — assign
  each field to exactly one owner, never write the other's fields.
author: Claude Code
version: 1.0.0
---

# Bidirectional Sync Pattern

## Problem

A daemon watches files, syncs content to a database, and the database also
computes values that must be written back to those files. Naive implementation
causes oscillation: write-back modifies file → inotify fires → sync runs →
re-syncs the file → triggers write-back → loop.

## Core Insight: Domain Ownership Eliminates Conflicts

"Conflict resolution" is a false problem when domains are cleanly separated.
Assign every field to exactly one owner:

```
FILE STORE OWNS (content):     DATABASE OWNS (computed state):
  title, date, tags, body        activation, stage
  status, wiki-links             synapse_in, synapse_out
                                 cluster_id, last_fired
```

- File store is source of truth for its fields — DB never overwrites them
- DB is source of truth for computed fields — sync never re-computes them on edit
- No merge logic needed. No conflict detection needed.

## Feedback Loop Prevention (Two Layers)

### Layer 1: Hash Excluding Written-Back Fields (Primary Guard)

Strip the written-back block from content before hashing. If only those fields
changed, the hash matches → skip re-sync.

```python
import hashlib, re

_NEURAL_BLOCK_RE = re.compile(
    r"^neural:\s*\n(?:[ \t]+\S.*\n)*",
    re.MULTILINE,
)

def content_hash_sans_neural(text: str) -> str:
    """Hash file content excluding the DB-written neural: block."""
    stripped = _NEURAL_BLOCK_RE.sub("", text)
    return hashlib.sha256(stripped.encode()).hexdigest()[:16]
```

Use this hash in the checkpoint, not the full-content hash.

### Layer 2: In-Process Path Exclusion Set (Fast-Path)

When the write-back class and the sync handler are in the same process, maintain
a shared set of paths just written. The sync handler checks and clears it.

```python
_writeback_paths: set[str] = set()   # module-level, shared in-process

# In sync_file():
if rel_path in _writeback_paths:
    _writeback_paths.discard(rel_path)
    return True  # skip — we wrote this

# In NeuralWriteBack._run():
_writeback_paths.add(rel_path)
file_path.write_text(updated_text)
```

**Limitation:** Layer 2 only works within the same process. A standalone
`--writeback` CLI run while a daemon is running will cause one oscillation
cycle before Layer 1 catches it. This is acceptable for manual/diagnostic use.

## Forward Sync: Respect DB-Owned Fields on Edit

When syncing an edited file, don't re-compute DB-owned fields from scratch.
Instead, boost the DB's current value:

```python
# WRONG — overwrites DB's decayed/computed activation
activation = compute_activation(word_count, len(links), days_since)

# CORRECT — respect DB ownership, just signal "this note was touched"
if existing_record:
    old = db.query(f"SELECT activation FROM {nid} LIMIT 1;")
    old_act = old[0].get("activation", 0.5) if old else 0.5
    activation = min(1.0, old_act + 0.1)   # boost, capped at 1.0
else:
    activation = compute_activation(...)    # first sync: compute from scratch
```

## Write-Back Class Pattern

```python
WRITEBACK_THROTTLE_SECS = 300  # 5 minutes

class NeuralWriteBack:
    def __init__(self, db):
        self.db = db
        self._last_run = 0.0

    def maybe_run(self, force: bool = False) -> bool:
        now = time.time()
        if not force and now - self._last_run < WRITEBACK_THROTTLE_SECS:
            return False
        self._last_run = now
        return self._run()

    def _run(self) -> bool:
        # 1. Query all DB-owned fields in one SQL call
        rows = self.db.query("SELECT path, activation, stage, synapse_in, synapse_out FROM neuron;")
        changed = 0
        for row in rows:
            path = row["path"]
            file = VAULT_DIR / path
            if not file.exists():
                continue
            text = file.read_text()
            current = self._parse_neural_block(text)
            desired = {
                "activation": round(row.get("activation", 0.5), 3),
                "stage": row.get("stage", "dormant"),
                "synapse_in": row.get("synapse_in", 0),
                "synapse_out": row.get("synapse_out", 0),
            }
            if current == desired:
                continue  # diff — only write changed files
            _writeback_paths.add(path)   # Layer 2 guard
            updated = self._update_neural_block(text, desired)
            file.write_text(updated)
            changed += 1
        return changed > 0
```

## Wiring Into the Watch Loop

```python
def watch_vault(db):
    reactor = GraphReactor(db)
    writeback = NeuralWriteBack(db)

    for events in inotify_loop():
        for path in events:
            sync_file(path, db)          # file → DB (with feedback guard)
        reactor.maybe_react()            # DB intelligence → vault markdown
        writeback.maybe_run()            # DB computed fields → frontmatter
```

## CLI One-Shot Mode

```python
if "--writeback" in sys.argv:
    wb = NeuralWriteBack(db)
    wb.maybe_run(force=True)
```

Run manually when the daemon isn't running (e.g., after a bulk DB update).
Don't run concurrently with the daemon — Layer 2 won't cross process boundaries.

## Checkpoint Format

Store sans-neural hashes for change detection:

```json
{
  "cortex/compound-engineering.md": {
    "hash": "a3f9c21d",
    "neural_hash": "b7e12a4f",
    "synced_at": 1773198519.92
  }
}
```

On checkpoint migration from full-hash to sans-neural-hash: all hashes will
mismatch on first run → full re-sync. This is a one-time, expected cost.

## Verification

```bash
# Confirm no oscillation: write-back runs once, sync doesn't re-trigger
python3 scripts/vault_sync.py --writeback   # standalone run
grep "write-back" logs/vault-sync.log | tail -5
# Should show one run, not a loop

# Daemon write-back (in-process): check logs for single cycle
tail -f logs/vault-sync.log | grep -E "(write-back|Neural)"
```
