---
name: context-light-agentic-loop
description: |
  Pattern for building context-light agentic loops that use SurrealDB vault_neuron
  as the authoritative state store — not in-memory state or JSONL files. Use when:
  (1) an agentic loop needs to calibrate batch sizes or task priority from live
  execution history, (2) a cron-driven script must skip already-solved issues
  across sessions without loading the entire prior log, (3) a loop's _build_backlog()
  should reflect current win rate / health rather than static task definitions.
  Key pattern: query DB at startup → calibrate parameters → run batch → push summary
  back to DB. Never hold loop state in context; pull on demand.
author: Claude Code
version: 1.0.0
---

# Context-Light Agentic Loop Pattern

## Problem

Agentic loops that store state in-memory or in flat JSONL files lose context across
sessions (cron runs, restarts, context compaction). They also can't self-calibrate —
a loop with a 20% win rate should use a smaller batch than one with 80%.

## Core Pattern

```
startup:
  prior_keys = query_db("SELECT task_id FROM vault_neuron WHERE success = true")
  stats = query_db("SELECT count(), avg(quality_score) FROM vault_neuron GROUP BY category")
  calibrate batch_size = 5 if win_rate >= 0.5 else 3

per-item:
  if issue_key in prior_keys: skip
  fix → verify → record WIN/LOSS to vault_neuron

shutdown:
  push batch summary (total, wins, rules_fixed) to vault_neuron as bughunt_summary row
```

## SurrealDB WIN Cache Query

```python
def _query_surrealdb_wins() -> set[str]:
    sql = "SELECT task_id FROM vault_neuron WHERE category = 'code_quality' AND success = true;"
    resp = http_post("http://localhost:8001/sql", sql, headers=SURREAL_HEADERS)
    return {
        r["task_id"].removeprefix("pyright:")
        for r in resp[0].get("result", [])
        if r.get("task_id", "").startswith("pyright:")
    }
```

## Live State Query for Backlog Calibration

```python
def _query_bughunt_state() -> dict:
    sql = ("SELECT count() AS total, count(success = true) AS wins "
           "FROM vault_neuron WHERE category = 'code_quality' GROUP ALL;")
    row = http_post("http://localhost:8001/sql", sql)[0].get("result", [{}])[0]
    return {"total": row.get("total", 0), "wins": row.get("wins", 0)}

# In _build_backlog():
state = _query_bughunt_state()
win_rate = state["wins"] / state["total"] if state["total"] > 0 else 0.0
batch_size = 5 if win_rate >= 0.5 else 3  # scale conservatively when struggling
```

## Vault Context Header (Loop Startup)

```python
def _query_vault_context() -> str:
    sql = ("SELECT category, count() AS n, math::mean(quality_score) AS avg_quality "
           "FROM vault_neuron GROUP BY category ORDER BY n DESC LIMIT 5;")
    rows = http_post("http://localhost:8001/sql", sql)[0].get("result", [])
    return "\n".join(f"  {r['category']}: {r['n']} records, q={r.get('avg_quality',0):.2f}"
                     for r in rows)

# At loop start — gives state awareness without holding it in context:
logger.info("Vault summary:\n%s", _query_vault_context())
```

## Batch Summary Push

```python
def _push_batch_summary(results: list[dict], elapsed_s: float) -> None:
    wins = sum(1 for r in results if r.get("outcome") == "WIN")
    total = len(results)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    sql = (
        f"INSERT INTO vault_neuron {{"
        f" task_id: 'pyright:batch:{ts}', category: 'bughunt_summary', "
        f" success: {str(wins > 0).lower()}, quality_score: {round(wins/total,2)}, "
        f" elapsed_ms: {int(elapsed_s*1000)}, recorded_at: time::now()"
        f"}};"
    )
    http_post("http://localhost:8001/sql", sql)
```

## F-String Gotcha

Python 3.11 doesn't allow method calls with escaped quotes inside f-strings.
Extract the value BEFORE the f-string:

```python
# WRONG — SyntaxError
sql = f"... '{datetime.now().strftime(\"%Y%m%d\")}'..."

# RIGHT — extract first
ts = datetime.now().strftime("%Y%m%d")
sql = f"... '{ts}'..."
```

## Reference Implementation

- `scripts/drivers/routine_pyright_bughunt.py` — batch bughunt with SurrealDB WIN cache
- `scripts/run_agentic_loop.py` — `_build_backlog()` with live state calibration

## Cron Integration

```python
# Schedule batch with explicit --batch flag so it's visible in the cron log:
CronCreate(
    cron="17 */2 * * *",
    prompt="uv run python scripts/drivers/routine_pyright_bughunt.py --batch 5",
    durable=True,
)
```
