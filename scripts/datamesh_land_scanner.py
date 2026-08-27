#!/usr/bin/env python3
"""Datamesh land scanner — the DISCOVERY producer for the ambient landing loop.

Deterministic, $0, stdlib-only, and deliberately free of ``cohezion`` imports so it
runs identically from any branch the primary checkout happens to be on (the live
daemons import the CHECKOUT's code, which can lag main — a zero-import script has
no surface to go stale).

One pass:
  1. Census every local branch against ``main`` with ``git merge-tree --write-tree``
     (pure object-db math; works while ``.git/worktrees`` is read-only):
       INTEGRATED  merge result tree == main's tree  -> nothing to land (the ONLY
                   honest integration test — ancestry and ``git cherry`` both lie
                   after squash merges)
       CLEAN       merges without conflict           -> landing candidate
       CONFLICTS   needs human/merge-train work      -> reported, not published
  2. Dedup against the ``land_scan_seen`` SurrealDB table (branch@head), so each
     branch head is published at most once.
  3. Publish up to ``--max-events`` ``land_ready`` data_product_events. The live
     ``cohezion-event-consumer`` timer routes these to ``land_runner`` (gates +
     light local review + semver) and files a kanban work-item. The PUSH stays
     human-gated — this loop surfaces reviewed candidates, it never lands them.

SurrealDB traps encoded (both cost real debugging time):
  - ``data_product_event.timestamp`` is TYPE float (epoch) — ``time::now()``
    fails schema coercion.
  - SurrealDB answers HTTP 200 for statement errors; success is
    ``status == "OK" AND result``, never the status code.

Usage:
  uv run --no-sync python scripts/datamesh_land_scanner.py            # dry-run report
  uv run --no-sync python scripts/datamesh_land_scanner.py --publish  # publish events
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Authorization": "Basic cm9vdDpyb290",  # root:root, local-only instance
}

# Branch families that are session/agent scaffolding, never landing candidates.
SKIP_BRANCH_RE = re.compile(
    r"^(archive/|agent-\d|worktree-agent-|backup/|prelanding/|autoresearch/)"
)


@dataclass
class BranchVerdict:
    branch: str
    head: str
    classification: str  # INTEGRATED | CLEAN | CONFLICTS
    ahead: int = 0
    files_changed: int = 0
    conflict_files: list[str] = field(default_factory=list)


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, timeout=120
    )


def census(repo: str, base: str = "main") -> list[BranchVerdict]:
    """Classify every candidate branch against *base* via in-memory merges."""
    base_tree = _git(repo, "rev-parse", f"{base}^{{tree}}").stdout.strip()
    out: list[BranchVerdict] = []
    branches = _git(
        repo, "for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads/"
    ).stdout.splitlines()
    for line in branches:
        head, _, branch = line.strip().partition(" ")
        if not branch or branch == base or SKIP_BRANCH_RE.match(branch):
            continue
        mt = _git(repo, "merge-tree", "--write-tree", base, branch)
        if mt.returncode == 0:
            tree = mt.stdout.splitlines()[0].strip() if mt.stdout else ""
            if tree == base_tree:
                out.append(BranchVerdict(branch, head, "INTEGRATED"))
                continue
            ahead = _git(repo, "rev-list", "--count", f"{base}..{branch}").stdout.strip()
            nfiles = _git(
                repo, "diff-tree", "-r", "--name-only", base_tree, tree
            ).stdout.strip()
            out.append(
                BranchVerdict(
                    branch,
                    head,
                    "CLEAN",
                    ahead=int(ahead or 0),
                    files_changed=len(nfiles.splitlines()) if nfiles else 0,
                )
            )
        else:
            conflicts = [
                ln.rsplit(" in ", 1)[-1]
                for ln in mt.stdout.splitlines()
                if ln.startswith("CONFLICT")
            ]
            out.append(
                BranchVerdict(branch, head, "CONFLICTS", conflict_files=conflicts[:10])
            )
    return out


def _sql(query: str, timeout: float = 10.0) -> list[dict]:
    req = urllib.request.Request(  # noqa: S310 — fixed localhost literal
        SURREAL_URL, data=query.encode(), headers=SURREAL_HEADERS, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        body = json.loads(resp.read().decode())
    if not (isinstance(body, list) and body and body[0].get("status") == "OK"):
        raise RuntimeError(f"SurrealDB statement error: {str(body)[:200]}")
    return body


def _seen_key(branch: str, head: str) -> str:
    # Record ids must be SurrealQL-safe; the raw pair lives in fields.
    return re.sub(r"[^a-zA-Z0-9_]", "_", f"{branch}@{head[:12]}")


# A published head is suppressed for this long, then re-offered. Publish-time
# marking means a TRANSIENT consumer/review failure would otherwise suppress the
# branch forever (until a new commit changes the head) — the cloud-oracle review
# (qwen3.5:397b, 2026-08-14) flagged this as the dead-letter failure mode.
SEEN_TTL_SECONDS = 7 * 24 * 3600


def already_seen(branch: str, head: str) -> bool:
    try:
        body = _sql(f"SELECT * FROM land_scan_seen:{_seen_key(branch, head)};")
        rows = body[0].get("result") or []
        if not rows:
            return False
        age = time.time() - float(rows[0].get("timestamp") or 0)
        return age < SEEN_TTL_SECONDS  # expired entries re-offer the branch
    except Exception:
        return False  # fail-open: a broken seen-set must not silence discovery


def mark_seen(branch: str, head: str) -> None:
    # UPSERT: a TTL-expired re-publish must refresh the clock, not error on the
    # existing record id.
    _sql(
        f"UPSERT land_scan_seen:{_seen_key(branch, head)} SET "
        f'branch = "{branch}", head = "{head}", timestamp = {time.time()};'
    )


def publish_land_ready(repo: str, v: BranchVerdict) -> bool:
    payload = json.dumps(
        {
            "repo": repo,
            "branch": v.branch,
            "head": v.head,
            "classification": v.classification,
            "ahead": v.ahead,
            "files_changed": v.files_changed,
        }
    ).replace('"', '\\"')
    _sql(
        "CREATE data_product_event SET "
        'event_type = "land_ready", '
        'source = "land_scanner", '
        f"timestamp = {time.time()}, "
        f'payload = "{payload}", '
        "priority = 0;"
    )
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="/home/mike-anderson/dev/cohezion")
    ap.add_argument("--base", default="main")
    ap.add_argument("--max-events", type=int, default=3)
    ap.add_argument(
        "--publish", action="store_true", help="publish land_ready events (default: dry-run)"
    )
    args = ap.parse_args()

    verdicts = census(args.repo, args.base)
    clean = [v for v in verdicts if v.classification == "CLEAN"]
    conflicted = [v for v in verdicts if v.classification == "CONFLICTS"]
    integrated = [v for v in verdicts if v.classification == "INTEGRATED"]

    print(
        f"land_scanner: {len(verdicts)} branches — "
        f"{len(clean)} CLEAN, {len(conflicted)} CONFLICTS, {len(integrated)} INTEGRATED"
    )
    for v in sorted(clean, key=lambda v: -v.ahead):
        print(f"  CLEAN {v.branch} (+{v.ahead} commits, {v.files_changed} files)")
    for v in conflicted:
        print(f"  CONFLICTS {v.branch}: {', '.join(v.conflict_files[:4])}")

    published = 0
    if args.publish:
        for v in sorted(clean, key=lambda v: -v.ahead):
            if published >= args.max_events:
                break
            if already_seen(v.branch, v.head):
                continue
            try:
                publish_land_ready(args.repo, v)
                mark_seen(v.branch, v.head)
                published += 1
                print(f"  PUBLISHED land_ready for {v.branch}@{v.head[:9]}")
            except Exception as exc:
                print(f"  publish failed for {v.branch}: {exc}")
    print(f"land_scanner: published {published} event(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
