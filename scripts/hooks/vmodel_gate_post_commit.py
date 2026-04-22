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

import ast
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


# ---------------------------------------------------------------------------
# Structural import-drift gate (L367 / ARC Lesson 2)
# ---------------------------------------------------------------------------
# For each `from cohezion.X import Y` in a modified Python file, verify that
# Y actually exists as a top-level name in src/cohezion/X.py (or its package
# __init__.py). Catches the `KaggleAPI.submit_adapter`-style drift where a
# symbol is imported/referenced but doesn't exist — the class of bug that
# would silently pass linting + CI and only blow up at call-site.
#
# AST-only (no runtime imports) so the hook works in bare-python environments
# without the cohezion package installed. Trade-off: misses symbols added via
# `__all__` extensions or re-exports; we accept those false negatives since
# the goal is catching obvious typos / deleted symbols, not full static check.


def _resolve_cohezion_module(module: str, repo_root: Path) -> Path | None:
    """Map 'cohezion.X.Y' → src/cohezion/X/Y.py or src/cohezion/X/Y/__init__.py."""
    if not module.startswith("cohezion"):
        return None
    # Strip leading 'cohezion.' and split
    parts = module.split(".")
    base = repo_root / "src" / parts[0]
    if not base.exists():
        return None
    candidate = base
    for part in parts[1:]:
        candidate = candidate / part
    as_file = candidate.with_suffix(".py")
    as_pkg = candidate / "__init__.py"
    if as_file.exists():
        return as_file
    if as_pkg.exists():
        return as_pkg
    return None


def _top_level_names(source_path: Path) -> set[str]:
    """Extract top-level defs, classes, assignments, and __all__ entries via AST.
    Returns empty set if the file can't be parsed (syntax error → likely caught
    elsewhere; don't double-report)."""
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            # Re-exports count as top-level names
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def _check_import_drift(py_file: Path, repo_root: Path) -> list[str]:
    """Return a list of drift messages for `from cohezion.X import Y` statements
    where Y is not a top-level name in cohezion.X. Empty list = clean."""
    drifts: list[str] = []
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return drifts
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is None or not node.module.startswith("cohezion"):
            continue
        target = _resolve_cohezion_module(node.module, repo_root)
        if target is None:
            drifts.append(f"from {node.module} import ... — module not found under src/")
            continue
        available = _top_level_names(target)
        # Skip the check if the target's AST yielded nothing (parse failure
        # means we can't reliably verify; avoid noise).
        if not available:
            continue
        for alias in node.names:
            name = alias.name
            if name == "*":
                continue  # wildcard imports bypass the check
            if name not in available:
                drifts.append(
                    f"from {node.module} import {name} — '{name}' not defined "
                    f"in {target.relative_to(repo_root)}"
                )
    return drifts


def _insert_import_drift(
    gate_id: str,
    session_id: str,
    source_file: str,
    drifts: list[str],
    summary: str,
) -> bool:
    """Record an import_drift row to SurrealDB. Non-blocking; returns False on
    any failure. One row per source file, drifts collapsed into a string array."""
    drift_array = "[" + ", ".join(f"'{_escape_sql_string(d)}'" for d in drifts) + "]"
    sql = (
        f"CREATE import_drift SET "
        f"drift_id = '{_escape_sql_string(gate_id)}', "
        f"session_id = '{_escape_sql_string(session_id)}', "
        f"source_file = '{_escape_sql_string(source_file)}', "
        f"drift_count = {len(drifts)}, "
        f"drifts = {drift_array}, "
        f"summary = '{_escape_sql_string(summary)}';"
    )
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

    # Structural import-drift check — one row per .py file with drift.
    repo_root = Path(__file__).resolve().parents[2]
    drift_recorded = 0
    drift_total = 0
    for idx, source in enumerate(source_py):
        src_path = repo_root / source
        if not src_path.exists():
            continue
        drifts = _check_import_drift(src_path, repo_root)
        if not drifts:
            continue
        drift_total += len(drifts)
        drift_id = f"IMP-{short_sha}-{idx:02d}"
        ok = _insert_import_drift(
            gate_id=drift_id,
            session_id=session_id,
            source_file=source,
            drifts=drifts,
            summary=f"{subject}  [{short_sha}]",
        )
        if ok:
            drift_recorded += 1
        # Also print to stderr so the drift is visible in the commit output.
        # This is non-blocking — the commit already landed. Operator sees it
        # and can remediate; git can't "un-commit" at this point.
        for d in drifts:
            print(f"[vmodel-gate] import_drift in {source}: {d}", file=sys.stderr)

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
    if drift_recorded:
        print(
            f"[vmodel-gate] recorded {drift_recorded} import_drift row(s) "
            f"({drift_total} total drifts) for {short_sha}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
