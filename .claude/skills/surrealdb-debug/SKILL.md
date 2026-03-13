---
name: surrealdb-debug
description: |
  Diagnose and fix common SurrealDB failures in the Cohezion vault.
  Use when: (1) HTTP 401 Unauthorized, (2) "Couldn't write to a read only transaction",
  (3) SurrealDB systemd service is failed, (4) schema errors on INFO FOR DB or DEFINE,
  (5) records are silently not persisting after CREATE/UPSERT (SCHEMAFULL silent rejection),
  (6) neuron paths are stale after vault directory renames,
  (7) synapse count doubles on re-import, (8) ID collisions after re-import with different derivation,
  (9) wrong aspect field (all neurons getting 'connective' default due to stale DIR_TO_ASPECT mapping),
  (10) ORDER BY inside DEFINE FUNCTION doesn't sort — results come back in arbitrary order,
  (11) "in" reserved keyword conflict — SELECT in FROM synapse fails with parse error,
  (12) count() GROUP result is wrapped — returns [{count: N}] not N,
  (13) N+1 query: searching N candidates with N sequential HTTP calls — batch into
  one OR query for 3-10x speedup,
  (14) _esc() for SurrealQL string literals must escape backslashes BEFORE single
  quotes, or a trailing backslash breaks the string boundary.
  Key insight: credentials and port in docs are often stale — always inspect the
  live process, and always create namespace+database before applying schema.
author: Claude Code
version: 1.7.0
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

## Import Idempotency: Synapses Double on Re-Import

**Symptom:** Synapse count doubles each time `triune-import.py` runs (e.g., 8,658 → 19,578 → 39,156).

**Cause:** `RELATE` for synapse/kinship tables creates new records even if the same relationship already exists. There is no upsert for relation tables.

**Fix:** DELETE all synapses before re-creating them in the import script:

```python
# Phase 2 — synapse import (idempotent)
print("Deleting existing synapses before re-import...")
db.query("DELETE synapse;")  # Must come BEFORE re-creating synapses

# Then create synapses as usual
for source_path, targets in links.items():
    ...
    db.query(f"RELATE {src_id}->synapse->{tgt_id} CONTENT {{...}};")
```

Same pattern applies to `kinship` and any other relation table.

## Import Idempotency: ID Collisions After Re-Import

**Symptom:** Import logs show errors like `neuron:cortex_moc_triune_self_md already exists with different ID`. Neurons accumulate stale duplicates.

**Cause:** The ID derivation algorithm may differ between import runs (e.g., if the path-to-ID function was changed). SurrealDB IDs are immutable — the old record can't be updated with a new ID.

**Fix: Phase 0 — resolve ID collisions before import:**

```python
# Phase 0: Build map of existing path → ID from the live database
existing = db.query("SELECT id, path FROM neuron")
path_to_existing_id: dict[str, str] = {}
if existing and existing[0].get("result"):
    for row in existing[0]["result"]:
        raw_id = str(row["id"]).removeprefix("neuron:")
        path_to_existing_id[row["path"]] = raw_id

# Override record_id for any note that already exists under a different ID
for note in notes:
    if note["path"] in path_to_existing_id:
        existing_id = path_to_existing_id[note["path"]]
        if existing_id != note["record_id"]:
            note["record_id"] = existing_id  # Reuse the old ID for UPSERT
```

This ensures UPSERT uses the existing record's ID rather than generating a new one.

## Import Idempotency: Orphan Cleanup

After directory renames or file deletions, old neuron records accumulate for files that no longer exist.

**Fix: Phase 5 — delete neurons whose vault files are gone:**

```python
# Phase 5: Orphan neuron cleanup
all_neurons = db.query("SELECT id, path FROM neuron")
if all_neurons and all_neurons[0].get("result"):
    vault_paths = {n["path"] for n in notes}  # paths computed during import
    for row in all_neurons[0]["result"]:
        if row["path"] not in vault_paths:
            nid = str(row["id"])
            db.query(f"DELETE {nid};")
            print(f"  Deleted orphan neuron: {nid}")
```

## Wrong Aspect Mapping (All Neurons Get 'connective')

**Symptom:** After import, aspect distribution shows ~70% `connective` (the default fallback). Expected: knower~30%, thinker~22%, doer~44%, connective~4%.

**Cause:** `DIR_TO_ASPECT` in `triune-import.py` uses old/pre-rename directory names that no longer match the vault's current structure.

**Fix:** Update `DIR_TO_ASPECT` to include ALL current directory names:

```python
DIR_TO_ASPECT = {
    # Knower (ground truth)
    "cortex": "knower",       # was: concepts
    "sensory": "knower",      # was: papers
    "memory": "knower",       # was: lessons
    "genome": "knower",       # was: specs
    # Thinker (reasoning)
    "prefrontal": "thinker",  # was: decisions
    "laboratory": "thinker",  # was: experiments
    "cerebellum": "thinker",  # was: patterns
    # Doer (action)
    "motor": "doer",          # was: projects
    "hippocampus": "doer",    # was: daily/sessions
    "thalamus": "doer",       # was: inbox
    "missions": "doer",
    "retrospectives": "doer",
    "Agents": "doer",
    # Connective
    "dreaming": "connective",
    "songlines": "connective",
    "subconscious": "connective",
    "metabolism": "connective",
    "visual-cortex": "connective",
}
```

**Sanity check after import:**
```bash
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -u root:root \
  --data-raw 'SELECT aspect, count() FROM neuron GROUP BY aspect;'
# Expected: connective < 10% of total
```

## ORDER BY Inside DEFINE FUNCTION Doesn't Sort (SurrealDB 3.0)

**Symptom:** `LET $top = (SELECT ... ORDER BY activation DESC LIMIT 5)` inside a function returns arbitrary records, not the top-N by activation. The exact same query works correctly as an ad-hoc SQL call.

**Cause:** SurrealDB 3.0 does not preserve `ORDER BY` on `LET` variable assignments inside `DEFINE FUNCTION` bodies. This is a known limitation — the query planner does not push ordering through the function's variable scope.

**Fix:** Issue a direct query from the client for any results that need correct ordering. Don't rely on ordering inside function bodies.

```python
# In graph_context.py — neighborhood command
sql = f"SELECT * FROM fn::context_neighborhood({nid});"
data = query(sql)[0]["result"][0]

# Workaround: fetch cluster_top via direct query (function ordering is broken)
cluster_sql = (
    f"SELECT id, title, activation, stage FROM neuron "
    f"WHERE cluster_id = '{cluster_id}' AND id != {nid} "
    f"ORDER BY activation DESC LIMIT 5;"
)
data["cluster_top"] = query(cluster_sql)[0]["result"]
```

**Rule of thumb:** Use SurrealDB functions for data *retrieval* and *aggregation*. Use direct queries for anything that needs reliable *ordering*.

## `in` Is a Reserved Keyword in SurrealQL

**Symptom:** Queries on RELATION tables (synapse, kinship) fail with a parse error when selecting the `in` field directly.

```sql
-- FAILS — parse error
SELECT DISTINCT in AS id FROM synapse WHERE in.cluster_id = "cortex";

-- WORKS — use VALUE to extract the field
SELECT VALUE in FROM synapse WHERE in = neuron:foo;

-- WORKS — use field access via traversal
SELECT in.id, in.title FROM synapse WHERE out = neuron:bar;
```

**Context:** `in` and `out` are SurrealDB reserved keywords for RELATION table edge fields. They cannot be aliased or selected with bare `SELECT in` syntax. Use `SELECT VALUE in` (returns an array of raw values) or `SELECT in.field` (dot-access for nested fields).

## count() GROUP Result Is Wrapped

**Symptom:** `SELECT count() FROM neuron GROUP ALL` returns `[{'count': 1602}]` instead of `1602`. Code that expects a plain integer breaks.

**Pattern:**

```python
def _unwrap_count(v):
    """Unwrap count() GROUP result: [{count: N}] → N."""
    if isinstance(v, list) and v and isinstance(v[0], dict):
        return v[0].get("count", v)
    return v

# Usage
result = query("SELECT count() FROM neuron GROUP ALL;")
total = _unwrap_count(result[0]["result"])  # → 1602 (int)
```

**Why this happens:** `GROUP ALL` always returns a list with one aggregated row. The `count()` value lives at `result[0]["result"][0]["count"]`. Using `SELECT VALUE count() FROM neuron GROUP ALL` returns the same wrapped format.

## N+1 Query: Batch Multiple Title Searches into One OR Query

**Symptom:** A hook or search function issues N sequential HTTP requests to SurrealDB
to find the first matching record across N candidate strings. At 12 candidates with
a 3s timeout each, worst-case latency is 36 seconds. Even at normal speed (15ms/query),
12 queries = 180ms vs 1 batch = 25ms.

**Anti-pattern (sequential):**
```python
for candidate in candidates:
    sql = f"SELECT ... FROM neuron WHERE string::contains(title, '{candidate}') LIMIT 1;"
    result = query(sql)
    if result: return result[0]
```

**Fix — batch with OR conditions, filter client-side:**
```python
conditions = " OR ".join(
    f"string::contains(string::lowercase(title), '{_esc(c)}')"
    for c in candidates
)
sql = f"SELECT id, title, activation, path FROM neuron WHERE {conditions} ORDER BY activation DESC LIMIT 20;"
hits = query(sql)[0]["result"]

# Preserve candidate priority order client-side
for candidate in candidates:       # earlier candidates = higher priority
    for hit in hits:
        if candidate in hit.get("title", "").lower():
            return hit
return hits[0] if hits else None   # fallback: highest activation
```

**Key insight:** One round-trip with client-side filtering beats N round-trips by
3-10x in practice. The ORDER BY activation gives a quality fallback when priority
ordering doesn't find a distinct winner.

## SurrealQL String Escaping: Backslash Before Single Quote

**Symptom:** Notes with backslash in the title (e.g., `C:\path` or `a\b`) produce
malformed SurrealQL. If input contains `\`, the naive `_esc` transforms `foo\'` into
`'foo\''` — the backslash escapes the closing quote, breaking the query.

**Broken pattern:**
```python
def _esc(s):
    return s.replace("'", "\\'")   # WRONG — backslash not escaped first
```

**Example failure:**
```
Input:  "foo\"
After _esc: "foo\"
SQL:    WHERE title = 'foo\'   ← backslash eats the closing quote → broken
```

**Fix — always escape backslash BEFORE single quote:**
```python
def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")
```

**Rule:** In SurrealQL string literals, backslash is the escape character. You must
double it (`\\`) before handling any other escaped characters. This is the same rule
as MySQL, SQLite, and most SQL dialects. Apply to ALL user-controlled string
interpolation into SurrealQL queries.

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
