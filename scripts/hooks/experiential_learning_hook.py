#!/usr/bin/env python3
"""Git post-commit hook: narrative experiential learning via local fleet.

Companion to `vmodel_gate_post_commit.py`. Where that hook records the
STRUCTURAL V-model invariant (source-test pairing, hash chain), this hook
records the NARRATIVE invariant — a short prose summary of what the commit
taught, routed through the local fleet so it's cheap to produce.

Design rules:
  * stdlib-only for hook plumbing; narrative generation is subprocessed out to
    `scripts/delegate.py --local-only`, which is the CLI wrapper around
    `cohezion.inference.fleet`. Keeps this file independent of the project's
    Python deps — it works as a bare `git` hook even under a half-broken venv.
  * Hard 20s wall-clock ceiling for the whole hook (delegate subprocess +
    SurrealDB write combined). Commits MUST NOT block on learning.
  * Non-blocking: every failure path returns 0. The post-commit wrapper pipes
    stderr to /dev/null anyway, but we belt-and-suspenders.
  * Set EXPERIENTIAL_LEARNING_DISABLE=1 to skip entirely (rebases, squash
    merges, bulk commits where the narrative would be noise).

SurrealDB schema inserted (CREATE narrative_learning SET ...):
  learning_id     str   NARR-<short-sha>
  session_id      str   from $COHEZION_SESSION_ID or fallback
  commit_hash     str   full HEAD sha
  commit_subject  str   HEAD commit subject line
  files_changed   int   number of paths in the commit
  source          str   'experiential_learning_hook.py'
  model           str   which local model produced the narrative
  lane            str   fleet lane (e.g. igpu_rocwmma)
  latency_ms      float end-to-end narrative latency
  narrative       str   the prose summary itself
  ts              str   ISO timestamp

Not a replacement for `RetrospectionEngine` — that runs per compound cycle
with full session context. This runs per commit with only diff + subject.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")

DELEGATE_TIMEOUT_SEC = 15  # wall-clock cap for the narrative call
HOOK_TOTAL_BUDGET_SEC = 20  # hard overall hook budget

PROMPT_TEMPLATE = """\
You are the Cohezion Retrospection Engine. Read this commit and produce ONE
compact prose sentence (max 30 words) describing what was LEARNED or PROVEN —
not just what was DONE. Focus on the principle, invariant, or pattern this
commit embodies.

Commit: {subject}

Files changed:
{files}

Diff (first 1500 chars):
{diff}

Respond with ONLY the one-sentence narrative, no quotes, no preamble."""


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _head_sha() -> str:
    return _git(["rev-parse", "HEAD"])


def _head_subject() -> str:
    return _git(["log", "-1", "--format=%s"])


def _head_diff_and_files(char_budget: int = 1500) -> tuple[str, list[str]]:
    parent = _git(["rev-parse", "HEAD~1"])
    if parent:
        diff = _git(["diff", "HEAD~1", "HEAD"])
        files = _git(["diff", "--name-only", "HEAD~1", "HEAD"]).splitlines()
    else:
        diff = _git(["show", "HEAD"])
        files = _git(["show", "--name-only", "--format=", "HEAD"]).splitlines()
    return diff[:char_budget], [f for f in files if f.strip()]


def _session_id(head_sha: str) -> str:
    return os.environ.get("COHEZION_SESSION_ID") or f"auto-{head_sha[:12]}"


def _delegate_narrative(prompt: str, repo_root: Path) -> dict | None:
    """Call scripts/delegate.py --local-only --json. Returns the envelope dict
    or None if the call fails / times out / returns non-zero."""
    delegate = repo_root / "scripts" / "delegate.py"
    if not delegate.exists():
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(delegate),
                "--json",
                "--local-only",
                "--timeout",
                str(DELEGATE_TIMEOUT_SEC),
                "--max-tokens",
                "120",
                prompt,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=DELEGATE_TIMEOUT_SEC + 2,  # small cushion over delegate's own timeout
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _escape_sql_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _basic_auth(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


def _insert_narrative(record: dict) -> bool:
    fields = ", ".join(f"{k} = {_sql_value(v)}" for k, v in record.items())
    sql = f"CREATE narrative_learning SET {fields};"
    req = urllib.request.Request(  # noqa: S310
        SURREAL_URL,
        data=sql.encode("utf-8"),
        headers={
            "Accept": "application/json",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Authorization": _basic_auth(SURREAL_USER, SURREAL_PASS),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            payload = json.load(resp)
        return isinstance(payload, list) and bool(payload) and payload[0].get("status") == "OK"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def _sql_value(v: object) -> str:
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return "NONE"
    return f"'{_escape_sql_string(str(v))}'"


def main() -> int:
    if os.environ.get("EXPERIENTIAL_LEARNING_DISABLE") == "1":
        return 0
    start = time.perf_counter()
    sha = _head_sha()
    if not sha:
        return 0
    subject = _head_subject()
    diff, files = _head_diff_and_files()
    if not diff or not files:
        return 0

    repo_root = Path(_git(["rev-parse", "--show-toplevel"]))
    if not repo_root.exists():
        return 0

    prompt = PROMPT_TEMPLATE.format(
        subject=subject,
        files="\n".join(f"  - {f}" for f in files[:20]),
        diff=diff,
    )
    envelope = _delegate_narrative(prompt, repo_root)
    if envelope is None or not envelope.get("text"):
        return 0

    # Budget guard: if we've already spent most of the budget on inference,
    # skip the DB write rather than blocking the commit further.
    if (time.perf_counter() - start) > HOOK_TOTAL_BUDGET_SEC - 2:
        return 0

    narrative = envelope["text"].strip()
    # Model sometimes returns multiple sentences; keep it one line for storage.
    narrative = " ".join(narrative.split())[:500]

    record = {
        "learning_id": f"NARR-{sha[:12]}",
        "session_id": _session_id(sha),
        "commit_hash": sha,
        "commit_subject": subject[:160],
        "files_changed": len(files),
        "source": "experiential_learning_hook.py",
        "model": envelope.get("model", ""),
        "lane": envelope.get("lane", ""),
        "latency_ms": float(envelope.get("latency_ms") or 0.0),
        "narrative": narrative,
        "ts": datetime.now(UTC).isoformat(),
    }
    if _insert_narrative(record):
        model_tag = envelope.get("model", "?")
        lat = record["latency_ms"]
        lid = record["learning_id"]
        print(f"[experiential-learning] recorded {lid} ({model_tag}, {lat:.0f}ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
