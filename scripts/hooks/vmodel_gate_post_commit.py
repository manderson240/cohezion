#!/usr/bin/env python3
"""Git post-commit hook: record V-model gates for each source file in HEAD.

Fast, deterministic, stdlib-only sibling to experiential_learning_hook.py. Where
the experiential hook does LLM-driven narrative analysis (slow, graceful
failure), this hook records the STRUCTURAL V-model invariant: for each source
file in the commit, does a paired test file exist, and were both changed
together? That heuristic maps to the `vmodel_gate` table's `passed` field.

Target runtime: <300ms typical. Non-blocking: all failures exit 0 so the
commit is never refused. Install once via `bash scripts/hooks/install.sh` (or
manually symlink from .git/hooks/post-commit).

Schema inserted (CREATE vmodel_gate SET ...):
  gate_id         str   DRR-<short-sha>-<nn>
  gate_name       str   commit subject (first 80 chars)
  level           str   'implementation' for src/*.py, 'architecture' for *.md
  session_id      str   from $COHEZION_SESSION_ID or fallback "auto-<sha>"
  left_artifact   str   the source file path
  right_artifact  str   paired test file path (or '' if none)
  artifact_hash   str   `git hash-object <left>`
  test_hash       str   `git hash-object <right>` (or '')
  passed          bool  True iff test file exists AND was modified this commit
  drr_summary     str   commit subject + short sha

Non-goals:
  * Running pytest in the hook (too slow; trust CI).
  * Blocking commits. Even a failing pairing heuristic just records passed=False.
  * Handling rebase/cherry-pick/squash specially — set VMODEL_GATE_DISABLE=1 to skip.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")


def _git(args: list[str]) -> str:
    # `git` via PATH is the idiom for git hooks; full path varies per install.
    # Args are controlled by this module, not user input.
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _head_sha() -> str:
    return _git(["rev-parse", "HEAD"])


def _head_subject() -> str:
    return _git(["log", "-1", "--format=%s"])


def _head_changed_files() -> list[str]:
    # --name-only on the HEAD commit; first commit case → diff against empty tree.
    parent = _git(["rev-parse", "HEAD~1"])
    if parent:
        raw = _git(["diff", "--name-only", "HEAD~1", "HEAD"])
    else:
        raw = _git(["show", "--name-only", "--format=", "HEAD"])
    return [line for line in raw.splitlines() if line.strip()]


def _paired_test_for(source: str) -> str | None:
    """Mirror src/cohezion/<mod>/<name>.py → tests/<mod>/test_<name>.py.
    scripts/<name>.py → search tests/**/test_<name>.py (first match).
    Returns the path if the file exists in the working tree; else None.
    """
    repo = Path(__file__).resolve().parents[2]
    src = Path(source)
    if src.suffix != ".py":
        return None
    if source.startswith("src/cohezion/"):
        rel = src.relative_to("src/cohezion")
        candidate = Path("tests") / rel.parent / f"test_{rel.name}"
        if (repo / candidate).exists():
            return str(candidate)
    # Fallback: any tests/**/test_<basename> match
    basename = f"test_{src.name}"
    for match in (repo / "tests").rglob(basename):
        return str(match.relative_to(repo))
    return None


def _hash_object(path: str) -> str:
    return _git(["hash-object", path])


def _session_id(head_sha: str) -> str:
    sid = os.environ.get("COHEZION_SESSION_ID")
    if sid:
        return sid
    return f"auto-{head_sha[:12]}"


def _escape_sql_string(s: str) -> str:
    """Single-quote-safe SurrealQL string escape. Keep it simple."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _insert_gate(
    gate_id: str,
    gate_name: str,
    level: str,
    session_id: str,
    left: str,
    right: str,
    left_hash: str,
    right_hash: str,
    passed: bool,
    summary: str,
) -> bool:
    sql = (
        f"CREATE vmodel_gate SET "
        f"gate_id = '{_escape_sql_string(gate_id)}', "
        f"gate_name = '{_escape_sql_string(gate_name[:80])}', "
        f"level = '{_escape_sql_string(level)}', "
        f"session_id = '{_escape_sql_string(session_id)}', "
        f"left_artifact = '{_escape_sql_string(left)}', "
        f"right_artifact = '{_escape_sql_string(right)}', "
        f"artifact_hash = '{_escape_sql_string(left_hash)}', "
        f"test_hash = '{_escape_sql_string(right_hash)}', "
        f"passed = {str(passed).lower()}, "
        f"drr_summary = '{_escape_sql_string(summary)}';"
    )
    req = urllib.request.Request(  # noqa: S310 — localhost operator tool
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
        return isinstance(payload, list) and payload and payload[0].get("status") == "OK"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def _basic_auth(user: str, pw: str) -> str:
    import base64

    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


def main() -> int:
    if os.environ.get("VMODEL_GATE_DISABLE") == "1":
        return 0
    sha = _head_sha()
    if not sha:
        return 0  # not in a git repo or git broken; quietly skip
    short_sha = sha[:12]
    subject = _head_subject()
    session_id = _session_id(sha)
    files = _head_changed_files()

    source_py = [f for f in files if f.endswith(".py") and not f.startswith("tests/")]
    doc_md = [f for f in files if f.startswith("src/cohezion/skills/") and f.endswith(".md")]

    recorded = 0
    for idx, source in enumerate(source_py + doc_md):
        is_doc = source.endswith(".md")
        level = "architecture" if is_doc else "implementation"
        right = _paired_test_for(source) or ""
        right_changed = right in files
        left_hash = _hash_object(source)
        right_hash = _hash_object(right) if right else ""
        passed = bool(right) and right_changed
        gate_id = f"DRR-{short_sha}-{idx:02d}"
        summary = f"{subject}  [{short_sha}]"
        ok = _insert_gate(
            gate_id=gate_id,
            gate_name=subject,
            level=level,
            session_id=session_id,
            left=source,
            right=right,
            left_hash=left_hash,
            right_hash=right_hash,
            passed=passed,
            summary=summary,
        )
        if ok:
            recorded += 1
    if recorded:
        print(f"[vmodel-gate] recorded {recorded} gate(s) for {short_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
