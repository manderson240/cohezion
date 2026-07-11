"""Operator-cockpit state layer — pure, injectable readers + steer/advisor actions.

This module is the *testable logic* behind the marimo cockpit notebook
(``scripts/cockpit.py``). The V-model split is deliberate: everything that can
be wrong (SurrealDB counts, task-file mutation, subprocess parsing, the advisor
request body) lives here behind injectable seams, and the notebook is a thin
reactive shell over it. That makes the cockpit provable with ``pytest`` and zero
live services.

Design contract (all functions):
    * NO network / subprocess / file I/O at import time — stdio-safe for a
      marimo/Jupyter/MCP host. Heavy imports (``CapabilityMatrix``) are lazy.
    * Each reader/action takes an OPTIONAL seam (``sql_fn`` / ``fetch`` / ``run``
      / ``chat_fn`` / ``*_file`` path) defaulting to the real localhost source.
    * Every function returns a plain ``dict`` / ``str`` — JSON-friendly, type
      hinted, and fail-soft (a dead service yields empty/"down", never raises).

The write path (:func:`add_manual_task`) reuses the compound daemon's exact
on-disk schema and ``fcntl.flock`` lockfile (see ``compound_feeder.py``) so the
operator's "Add manual task" button is race-safe against the live daemon and
feeder — same lock, same atomic ``os.replace``.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# --- Paths (daemon's shared state) -----------------------------------------
STATE_DIR = Path.home() / ".cohezion"
TASKS_FILE = STATE_DIR / "compound_tasks.json"
LOCK_FILE = STATE_DIR / "compound_tasks.lock"
DAEMON_LOG = STATE_DIR / "compound_daemon.log"

# <repo>/src/cohezion/cockpit/daemon_state.py -> parents[3] == repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

# --- Endpoints (fleet defaults, all localhost) -----------------------------
SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_HEADERS = {"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain"}
_SURREAL_AUTH = "Basic cm9vdDpyb290"  # root:root — fleet default (matches compound_persist)
WORK_QUEUE_BASE = "http://localhost:8080"
LEMONADE_BASE = "http://localhost:13305"
ADVISOR_MODEL = "Gemma-4-E4B-it-GGUF"

# SurrealDB graph tables the compound loop writes (compound_persist.py).
_GRAPH_TABLES = ("compound_loop", "yielded", "spawned", "agent_journey")


# ===========================================================================
# Default seams (real localhost sources) — each isolated so tests inject fakes.
# ===========================================================================
def _default_sql(query: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """POST a SurrealQL query to the local SurrealDB HTTP endpoint.

    S310 is justified: ``SURREAL_URL`` is a fixed localhost literal, never
    user-controlled.
    """
    req = urllib.request.Request(  # noqa: S310 — fixed 127.0.0.1 literal
        SURREAL_URL,
        data=query.encode(),
        headers={**_SURREAL_HEADERS, "Authorization": _SURREAL_AUTH},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed literal
        return json.loads(resp.read())


def _default_work_queue_fetch(base: str, timeout: float = 10.0) -> dict[str, Any]:
    """GET the work-queue listing ``{"items": [...], "total": N}``.

    S310 is justified: ``base`` is the fixed local work-queue API base, scheme http.
    """
    url = f"{base.rstrip('/')}/api/work-queue"
    req = urllib.request.Request(url, method="GET")  # noqa: S310 — literal http API base
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — literal API base
        return json.loads(resp.read())


def _default_lemonade_fetch(base: str, timeout: float = 5.0) -> dict[str, Any]:
    """GET the OmniRouter health payload from :13305.

    S310 is justified: ``base`` is the fixed local Lemonade router, scheme http.
    """
    url = f"{base.rstrip('/')}/api/v1/health"
    req = urllib.request.Request(url, method="GET")  # noqa: S310 — literal localhost router
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — literal router
        return json.loads(resp.read())


def _default_run(cmd: list[str], timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    """Run a subprocess capturing text stdout/stderr (feeder invocation)."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _build_advisor_body(prompt: str) -> dict[str, Any]:
    """Build the Lemonade chat request body for the advisor.

    ``temperature`` is DELIBERATELY OMITTED so the loaded card's own sampling
    applies. Setting ``temperature=0.0`` on a Gemma-family card yields degenerate
    EMPTY output (finish_reason=length, content='') — the F0/F1 lesson learned
    the hard way. This function is extracted so a test can assert the omission
    on the actual built body.
    """
    return {
        "model": ADVISOR_MODEL,
        "max_tokens": 512,  # $0 local — generous budget avoids false-negative truncation
        "messages": [{"role": "user", "content": prompt}],
    }


def _default_advisor_chat(prompt: str, timeout: float = 60.0, base: str = LEMONADE_BASE) -> str:
    """One bounded local-inference call to :13305; returns raw content string.

    S310 is justified: ``base`` is the fixed local Lemonade router.
    """
    body = _build_advisor_body(prompt)
    req = urllib.request.Request(  # noqa: S310 — fixed localhost router
        f"{base.rstrip('/')}/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — literal router
        out = json.loads(resp.read())
    return str(out["choices"][0]["message"]["content"])


# ===========================================================================
# MONITOR readers
# ===========================================================================
def read_task_queue(path: Path | None = None) -> dict[str, Any]:
    """Read the compound daemon's task file.

    The daemon treats ``[t for t in tasks if not t.get("done")]`` as pending.
    Returns ``{"total": int, "done": int, "pending": [{id, source_item_id,
    prompt}]}`` — ``pending`` is the detail LIST (the notebook shows ``len``);
    manually-added tasks carry no ``source_item_id`` so it is read with ``.get``.
    """
    tasks_path = path or TASKS_FILE
    tasks: list[dict[str, Any]] = []
    if tasks_path.exists():
        try:
            loaded = json.loads(tasks_path.read_text())
            tasks = loaded if isinstance(loaded, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("read_task_queue failed to parse %s: %s", tasks_path, exc)
    pending = [
        {"id": t.get("id"), "source_item_id": t.get("source_item_id"), "prompt": t.get("prompt")}
        for t in tasks
        if not t.get("done")
    ]
    return {"total": len(tasks), "done": len(tasks) - len(pending), "pending": pending}


def read_graph_counts(
    sql_fn: Callable[[str], list[dict[str, Any]]] | None = None,
) -> dict[str, int]:
    """Count rows in the compound-loop SurrealDB graph tables.

    Returns ``{"compound_loop", "yielded", "spawned", "agent_journey"}`` → int,
    each 0 on any per-table failure (SurrealDB down, table absent).
    """
    sql = sql_fn or _default_sql
    counts: dict[str, int] = {}
    for table in _GRAPH_TABLES:
        try:
            res = sql(f"SELECT count() FROM {table} GROUP ALL;")
            rows = res[-1].get("result") or []
            counts[table] = int(rows[0]["count"]) if rows else 0
        except (KeyError, IndexError, ValueError, TypeError, OSError) as exc:
            logger.debug("graph count for %s failed: %s", table, exc)
            counts[table] = 0
    return counts


def read_work_queue(
    base: str = WORK_QUEUE_BASE,
    fetch: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read the work-queue and break it down by status and relevance.

    Returns ``{"total": int, "by_status": {...}, "by_relevance": {...}}`` —
    empty breakdowns when the API (:8080) is unreachable.
    """
    fetcher = fetch or _default_work_queue_fetch
    try:
        data = fetcher(base)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.debug("read_work_queue failed: %s", exc)
        return {"total": 0, "by_status": {}, "by_relevance": {}}
    items = data.get("items", []) if isinstance(data, dict) else []
    by_status: dict[str, int] = {}
    by_relevance: dict[str, int] = {}
    for it in items:
        s = str(it.get("status", "unknown"))
        r = str(it.get("relevance", "unknown"))
        by_status[s] = by_status.get(s, 0) + 1
        by_relevance[r] = by_relevance.get(r, 0) + 1
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    return {"total": int(total), "by_status": by_status, "by_relevance": by_relevance}


def read_gap_analysis(matrix_factory: Callable[[], Any] | None = None) -> list[dict[str, Any]]:
    """Run the CapabilityMatrix gap analysis, mapped to plain dicts.

    Returns ``[{"task_type", "score", "action"}, ...]`` — ``[]`` on any failure
    (import error, matrix construction). The heavy import is lazy so this module
    stays import-cheap and stdio-safe.
    """
    try:
        if matrix_factory is None:
            from cohezion.compound.capability_matrix import CapabilityMatrix

            matrix = CapabilityMatrix()
        else:
            matrix = matrix_factory()
        return [
            {
                "task_type": g.task_type,
                "score": g.best_available_score,
                "action": g.suggested_action,
            }
            for g in matrix.run_gap_analysis()
        ]
    except Exception as exc:
        logger.debug("read_gap_analysis failed: %s", exc)
        return []


def read_lemonade_health(
    base: str = LEMONADE_BASE,
    fetch: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read OmniRouter (:13305) health.

    Returns ``{"status": str, "loaded": [...]}`` — ``{"status": "down",
    "loaded": []}`` when the router is unreachable.
    """
    fetcher = fetch or _default_lemonade_fetch
    try:
        payload = fetcher(base)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.debug("read_lemonade_health failed: %s", exc)
        return {"status": "down", "loaded": []}
    return {
        "status": str(payload.get("status", "ok")),
        "loaded": list(payload.get("all_models_loaded", [])),
    }


def tail_daemon_log(path: Path | None = None, n: int = 20) -> str:
    """Return the last ``n`` lines of the compound daemon log (``""`` if absent)."""
    log_path = path or DAEMON_LOG
    if not log_path.exists():
        return ""
    try:
        lines = log_path.read_text(errors="replace").splitlines()
    except OSError as exc:
        logger.debug("tail_daemon_log failed: %s", exc)
        return ""
    return "\n".join(lines[-n:])


# ===========================================================================
# STEER actions
# ===========================================================================
def run_feeder(
    limit: int = 5,
    *,
    run: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Run the repo's ``scripts/compound_feeder.py`` once and parse its JSON.

    Subprocesses the clone's feeder wrapper via ``<repo>/.venv/bin/python`` (the
    same interpreter the systemd daemon uses, writing the shared task file).
    Returns ``{"ok": bool, "returncode": int, "summary": {...}}`` — or
    ``{"ok": False, ...}`` with ``error``/``raw`` on failure or unparseable output.
    """
    runner = run or _default_run
    py = REPO_ROOT / ".venv" / "bin" / "python"
    script = REPO_ROOT / "scripts" / "compound_feeder.py"
    try:
        proc = runner([str(py), str(script), "--limit", str(limit)])
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("run_feeder subprocess failed: %s", exc)
        return {"ok": False, "error": str(exc)}
    stdout = getattr(proc, "stdout", "") or ""
    returncode = int(getattr(proc, "returncode", 1))
    try:
        summary = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return {"ok": False, "returncode": returncode, "raw": stdout[-500:]}
    return {"ok": returncode == 0, "returncode": returncode, "summary": summary}


def add_manual_task(
    prompt: str,
    priority: int = 2,
    *,
    tasks_file: Path | None = None,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    """Append one pending task to the daemon's task file, race-safely.

    Uses ``fcntl.flock`` on the daemon's lockfile + atomic ``os.replace`` and the
    daemon's exact schema ``{id: max+1, prompt, priority, done: False}`` — the
    same lock the feeder takes, so this is safe against overlapping feeder runs.
    Returns ``{"added": <task>, "total": int}``.
    """
    tasks_path = tasks_file or TASKS_FILE
    lock_path = lock_file or LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_fp:
        fcntl.flock(lock_fp, fcntl.LOCK_EX)
        try:
            raw = json.loads(tasks_path.read_text()) if tasks_path.exists() else []
            tasks: list[dict[str, Any]] = raw if isinstance(raw, list) else []
            next_id = max((t["id"] for t in tasks if isinstance(t.get("id"), int)), default=0) + 1
            task = {"id": next_id, "prompt": prompt, "priority": priority, "done": False}
            tasks.append(task)
            tmp = tasks_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(tasks, indent=2))
            os.replace(tmp, tasks_path)
        finally:
            fcntl.flock(lock_fp, fcntl.LOCK_UN)
    return {"added": task, "total": len(tasks)}


# ===========================================================================
# ADVISOR
# ===========================================================================
def ask_local_advisor(state_summary: str, chat_fn: Callable[[str], str] | None = None) -> str:
    """Ask the local Gemma advisor to interpret + steer the compound-loop state.

    One bounded :13305 call (``temperature`` omitted — card-inherit). ``chat_fn``
    is injectable for tests. Fails soft: any exception or empty content returns a
    human-readable fallback string, never raises.
    """
    caller = chat_fn or _default_advisor_chat
    prompt = (
        "Given this compound-loop state, what is it doing, any concerns, "
        f"what would you steer? 3 sentences.\n\n{state_summary}"
    )
    try:
        text = caller(prompt)
    except Exception as exc:
        logger.debug("ask_local_advisor failed: %s", exc)
        return f"(advisor unavailable: {exc})"
    text = (text or "").strip()
    return text or "(advisor returned no content)"
