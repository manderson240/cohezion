---
name: surrealdb-debug
description: |
  Diagnose and fix common SurrealDB failures in the Cohezion vault.
  Use when: (1) HTTP 401 Unauthorized, (2) "Couldn't write to a read only transaction",
  (3) SurrealDB systemd service is failed, (4) schema errors on INFO FOR DB or DEFINE,
  (5) records are silently not persisting after CREATE/UPSERT (SCHEMAFULL silent rejection),
  (6) neuron paths are stale after vault directory renames.
  Key insight: credentials and port in docs are often stale — always inspect the
  live process, and always create namespace+database before applying schema.
author: Claude Code
version: 1.4.0
---

# SurrealDB Debugging

## Problem

SurrealDB connections fail with authentication errors, read-only transaction errors,
or schema application failures. Documented credentials are stale. The systemd service
may be failed while a manual process runs on a different port.

## Step 1: Find the Live Process

Never trust documented credentials. Always inspect what's actually running:

```bash
ps aux | grep surreal | grep -v grep
```

This reveals the actual `--user`, `--pass`, `--bind` port, and `--path` used.

Example output:
```
surreal start --auth --user root --pass root --bind 0.0.0.0:8001 rocksdb://path/to/db
```

## Step 2: Test Connectivity

```bash
curl -s -u root:root http://localhost:8001/health
# or
curl -s http://localhost:8001/health  # if no auth
```

If connection refused: the process died or is on a different port. Check the port
from `ps aux` output above.

## Step 3: Fix "read only transaction" Errors

This error occurs when you try to run statements (even INFO FOR DB) before the
namespace and database exist. Fix: create them explicitly first.

```bash
curl -s -X POST http://localhost:8001/sql \
  -H "Content-Type: application/json" \
  -H "NS: cohezion" -H "DB: vault" \
  -u root:root \
  --data-raw 'DEFINE NAMESPACE cohezion; USE NS cohezion; DEFINE DATABASE vault;'
```

Then verify the schema can be queried:
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "Content-Type: application/json" \
  -H "NS: cohezion" -H "DB: vault" \
  -u root:root \
  --data-raw 'INFO FOR DB;'
```

## Step 4: Apply Schema

After namespace+database exist:

```bash
surreal import --conn http://localhost:8001 --ns cohezion --db vault \
  -u root -p root scripts/triune-schema.surql
```

Or via HTTP:
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "NS: cohezion" -H "DB: vault" \
  -u root:root \
  --data-raw "$(cat scripts/triune-schema.surql)"
```

## Step 5: Start Fresh Instance (if systemd service is broken)

```bash
mkdir -p ~/dev/cohezion/data/surrealdb

surreal start \
  --auth --user root --pass root \
  --bind 0.0.0.0:8001 \
  rocksdb://~/dev/cohezion/data/surrealdb &

# Wait for it to be ready
sleep 2
curl -s -u root:root http://localhost:8001/health
```

## Batch Import Fallback Pattern

When importing large volumes via SQL, batch statements fail when any single one has
a parse error (bad characters in note titles, etc.). Fall back to one-at-a-time:

```python
def batch_query(self, statements: list[str], batch_size: int = 50) -> int:
    success = 0
    for i in range(0, len(statements), batch_size):
        batch = statements[i:i + batch_size]
        combined = "\n".join(batch)
        results = self.query(combined)
        # If batch returns single ERR, fall back to one-at-a-time
        if len(results) == 1 and results[0].get("status") == "ERR":
            for stmt in batch:
                r = self.query(stmt)
                if r and r[0].get("status") == "OK":
                    success += 1
        else:
            success += sum(1 for r in results if r.get("status") == "OK")
    return success
```

## Vault-Specific Configuration

| Setting | Value |
|---------|-------|
| Port | 8001 |
| Auth | root / root |
| Namespace | cohezion |
| Database | vault |
| Storage | rocksdb at `~/dev/cohezion/data/surrealdb` |
| Schema | `scripts/triune-schema.surql` |
| Import script | `scripts/triune-import.py` |

## RELATE vs CREATE for Relation Tables

Tables with `in TYPE record<X>` and `out TYPE record<Y>` are **RELATION tables**.
You MUST use `RELATE` syntax, not `CREATE`:

```sql
-- WRONG (returns "expected a RELATION IN neuron OUT neuron" error)
CREATE kinship CONTENT { in: neuron:foo, out: neuron:bar, relation: "moiety" };

-- CORRECT
RELATE neuron:foo->kinship->neuron:bar CONTENT { relation: "moiety", obligation: "cite together" };
```

**How to detect:** If a CREATE on a table with `in`/`out` record fields fails with
"which is not a relation, but expected a RELATION IN X OUT Y", switch to RELATE.

## SCHEMAFULL Silent Record Rejection

**SCHEMAFULL tables silently discard records with unknown fields — no error is returned.**

This is the hardest SurrealDB bug to diagnose: `SELECT count()` returns 0 after what
appeared to be a successful INSERT/UPSERT, but there's no error message.

**Diagnosis:** Add an unknown field to a CREATE statement and check if it persists:
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -u root:root \
  --data-raw 'CREATE country:test CONTENT { name: "test", mystery_field: "x" };
              SELECT * FROM country:test;'
# If mystery_field is absent from the result → table is SCHEMAFULL
```

**Fix:** Add the missing field to the schema:
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -u root:root \
  --data-raw 'DEFINE FIELD avg_activation ON country TYPE float DEFAULT 0.5;
              DEFINE FIELD updated ON country TYPE string DEFAULT "";'
```

**Common culprits in Triune Vault:**
- `country` table: `avg_activation`, `updated` fields were added later
- `hiho_event` table: `country` field type changed from `record<country>` to `string`
- After any schema change, re-run the import script

## Stale Neuron Paths After Directory Renames

When the vault directories were renamed (e.g., `concepts/` → `cortex/`) AFTER the
SurrealDB import ran, all neuron paths become stale. Queries by path return nothing.

**Diagnose:**
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -u root:root \
  --data-raw "SELECT count() FROM neuron WHERE string::starts_with(path, 'concepts/') GROUP ALL;"
# If > 0, paths are stale
```

**Fix — batch rename (SurrealDB 3.0 uses `string::starts_with`, NOT `STARTS WITH`):**
```bash
RENAMES=(
  "concepts cortex"
  "papers sensory"
  "lessons memory"
  "specs genome"
  "decisions prefrontal"
  "experiments laboratory"
  "patterns cerebellum"
  "projects motor"
  "inbox thalamus"
  "canvas visual-cortex"
)

for pair in "${RENAMES[@]}"; do
  old=$(echo $pair | cut -d' ' -f1)
  new=$(echo $pair | cut -d' ' -f2)
  curl -s -X POST http://localhost:8001/sql \
    -H "surreal-ns: cohezion" -H "surreal-db: vault" \
    -u root:root \
    --data-raw "UPDATE neuron SET path = string::replace(path, '${old}/', '${new}/') WHERE string::starts_with(path, '${old}/');"
done
```

Apply same pattern to `cluster_id` field if it also stores directory names.

## json.dumps ensure_ascii=False for SurrealQL

**Python's `json.dumps()` defaults to `ensure_ascii=True`, encoding emoji/Unicode as `\uXXXX` escape sequences. SurrealDB rejects these with HTTP 400.**

```python
# WRONG — SurrealDB returns 400 Bad Request
title = "🏆 PROJECT COMPLETE"
sql = f'UPDATE neuron SET title = {json.dumps(title)};'
# Produces: title = "\ud83c\udfc6 PROJECT COMPLETE"  ← surrogate pair, SurrealDB can't parse

# CORRECT
sql = f'UPDATE neuron SET title = {json.dumps(title, ensure_ascii=False)};'
# Produces: title = "🏆 PROJECT COMPLETE"  ← raw UTF-8, SurrealDB accepts
```

**Rule:** Always use `json.dumps(value, ensure_ascii=False)` when building SurrealQL strings.

## Field Projection HTTP 400

**SurrealDB 3.0 returns HTTP 400 for field-projected queries on some tables.** This is silent and confusing — the same query with `SELECT *` works fine.

**Symptom:** `SELECT country, coherence_score FROM hiho_event ORDER BY date DESC` returns HTTP 400, but `SELECT * FROM hiho_event` works.

**Affected patterns:**
- Projected fields on tables with computed/derived columns
- `GROUP BY` on RELATION tables (kinship, synapse): `SELECT out, count() FROM kinship GROUP BY out` → HTTP 400
- Any field-projected query that SurrealDB's query planner can't resolve

**Fix: Use `SELECT *` and filter client-side:**
```python
# WRONG — HTTP 400
results = query("SELECT country, coherence_score FROM hiho_event ORDER BY date DESC;")

# CORRECT — fetch all, filter in Python
all_events = query("SELECT * FROM hiho_event;")
results = sorted(all_events, key=lambda e: e.get("date",""), reverse=True)
hiho_scores = {e["country"]: e["coherence_score"] for e in all_events if "country" in e}
```

**GROUP BY alternative (for relation tables like kinship, synapse):**
```python
# WRONG — HTTP 400
counts = query("SELECT out AS nid, count() FROM kinship GROUP BY out;")

# CORRECT — fetch all, aggregate in Python
all_kin = query("SELECT in, out FROM kinship;")
kinship_counts = {}
for r in all_kin:
    for field in ["in", "out"]:
        nid = str(r.get(field, ""))
        kinship_counts[nid] = kinship_counts.get(nid, 0) + 1
```

## Neuron IDs Are Immutable (Use Path Field for Lookups)

**SurrealDB record IDs are immutable after creation.** After vault directory renames (e.g., `concepts/` → `cortex/`), neuron IDs still contain the OLD directory name even after path fields are updated.

**Example:**
```
# ID (immutable, reflects import-time path):
neuron:concepts_compound_engineering_md

# path field (updated by UPDATE SET path = ...):
cortex/compound-engineering.md
```

**Consequence:** If you derive an ID from a current vault path, it won't match the stored ID.

**Always query by path, never by derived ID:**
```python
# WRONG — ID derived from current path won't match
nid = "neuron:" + path.replace("/", "_").replace("-", "_").replace(".md", "_md")
result = query(f"SELECT * FROM ONLY {nid};")  # → NONE

# CORRECT — query by path field
result = query(f'SELECT * FROM neuron WHERE path = "{path}" LIMIT 1;')
```

**Verification:**
```bash
# Find neurons where ID and path disagree
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -u root:root \
  --data-raw 'SELECT id, path FROM neuron WHERE NOT string::contains(string::lowercase(string::slice(string::from(id), 7)), string::replace(string::split(path, "/")[1], "-", "_")) LIMIT 5;'
```

## Graph-Walk Trajectory Generation (Synthetic Training Data)

When temporal history is unavailable (all records have same timestamp from bulk import), use SurrealDB's graph traversal to generate synthetic trajectories for ML training:

```python
def extract_graph_walk_trajectories(neuron_vectors, n_walks=200, walk_length=8):
    """Generate random walks using SurrealDB ->synapse->neuron traversal."""
    seeds = query(
        "SELECT id, cluster_id FROM neuron WHERE activation > 0.4 "
        "AND synapse_out > 2 ORDER BY RAND() LIMIT 200;"
    )
    trajectories = []
    for seed in seeds[:n_walks]:
        walk = [seed["id"]]
        current = seed["id"]
        for _ in range(walk_length - 1):
            nbrs_result = query(f"SELECT ->synapse->neuron AS n FROM {current};")
            if not nbrs_result:
                break
            nbrs = nbrs_result[0].get("n", [])
            if not nbrs:
                break
            current = random.choice(nbrs)
            if str(current) in [str(w) for w in walk]:
                break  # avoid cycles
            walk.append(current)
        if len(walk) >= 3:
            # Convert to 12D vector sequence
            vecs = [neuron_vectors[str(nid)] for nid in walk if str(nid) in neuron_vectors]
            if len(vecs) >= 3:
                trajectories.append({"waypoints": [str(n) for n in walk], "vectors": vecs})
    return trajectories
```

Key: `SELECT ->synapse->neuron AS n FROM {node_id}` returns all outbound neighbors in one hop. This is SurrealDB's graph traversal syntax — no JOIN needed.

## Verification

```bash
# Check tables exist
curl -s -X POST http://localhost:8001/sql \
  -H "NS: cohezion" -H "DB: vault" \
  -u root:root \
  --data-raw 'INFO FOR DB;' | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d[0]['result']['tables'].keys()))"

# Check record counts
curl -s -X POST http://localhost:8001/sql \
  -H "NS: cohezion" -H "DB: vault" \
  -u root:root \
  --data-raw 'SELECT count() FROM neuron GROUP ALL; SELECT count() FROM synapse GROUP ALL;'
```
