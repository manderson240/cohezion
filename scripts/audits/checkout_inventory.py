"""Deterministic inventory of a checkout's uncommitted state. No judgment here.

The deterministic half of the method behind docs/audits/MAIN_CHECKOUT_RECONCILE_2026-10-22.md:
for each modified tracked file, is the working-tree blob already in git history (which commit,
which branches)? Identical to HEAD (phantom)? Whitespace-only? Byte-equal to `ruff format` of
HEAD's version? For each untracked path: ignored by which rule, size, extension class. Only the
residue this script cannot classify goes to agents.

Usage:
    uv run python scripts/audits/checkout_inventory.py <output.json> [--repo <path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout.strip()


def _blob_in_history(repo: Path, blob: str) -> dict:
    commit = _git(
        repo, "log", "--all", "-1", "--format=%h %ad %s", "--date=short", f"--find-object={blob}"
    )
    if not commit:
        return {"found": False}
    short = commit.split()[0]
    branches = [
        b.strip().lstrip("* +")
        for b in _git(repo, "branch", "-a", "--contains", short).splitlines()
    ]
    return {
        "found": True,
        "commit": commit,
        "branches": branches[:6],
        "branch_count": len(branches),
    }


def _formatter_class(repo: Path, path: str) -> str | None:
    """WHITESPACE-ONLY, RUFF-FORMAT-OF-HEAD, RUFF-FIX+FORMAT-OF-HEAD, or None."""
    if (
        _git(
            repo,
            "diff",
            "--ignore-all-space",
            "--ignore-blank-lines",
            "--numstat",
            "HEAD",
            "--",
            path,
        )
        == ""
    ):
        return "WHITESPACE-ONLY"
    ruff = repo / ".venv" / "bin" / "ruff"
    if not path.endswith(".py") or not ruff.exists():
        return None
    head = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=repo, capture_output=True).stdout
    work = hashlib.sha1((repo / path).read_bytes()).digest()
    fmt = subprocess.run(
        [str(ruff), "format", "--stdin-filename", path, "-"], input=head, capture_output=True
    ).stdout
    if fmt and hashlib.sha1(fmt).digest() == work:
        return "RUFF-FORMAT-OF-HEAD"
    fix = subprocess.run(
        [str(ruff), "check", "--fix", "--quiet", "--stdin-filename", path, "-"],
        input=fmt or head,
        capture_output=True,
    ).stdout
    fix2 = subprocess.run(
        [str(ruff), "format", "--stdin-filename", path, "-"], input=fix, capture_output=True
    ).stdout
    if fix2 and hashlib.sha1(fix2).digest() == work:
        return "RUFF-FIX+FORMAT-OF-HEAD"
    return None


def inventory(repo: Path) -> dict:
    out: dict = {
        "head": _git(repo, "rev-parse", "--short", "HEAD"),
        "branch": _git(repo, "branch", "--show-current"),
        "modified": [],
        "untracked": [],
    }
    for entry in _git(repo, "status", "--porcelain", "-z").split("\0"):
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code == "??":
            p = repo / path
            row: dict = {"path": path}
            ignore = subprocess.run(
                ["git", "check-ignore", "-v", "--no-index", path],
                cwd=repo,
                capture_output=True,
                text=True,
            ).stdout.strip()
            row["ignored_by"] = ignore.split("\t")[0] if ignore else None
            if p.is_dir():
                files = [f for f in p.rglob("*") if f.is_file()]
                row.update(
                    kind="dir", file_count=len(files), bytes=sum(f.stat().st_size for f in files)
                )
                row["ext_mix"] = sorted({f.suffix for f in files})[:8]
            else:
                row.update(kind="file", bytes=p.stat().st_size if p.exists() else 0, ext=p.suffix)
            out["untracked"].append(row)
            continue
        p = repo / path
        row = {"path": path, "status": code}
        if not p.exists():
            row["class"] = "DELETED-IN-WORKTREE"
            out["modified"].append(row)
            continue
        blob = _git(repo, "hash-object", str(p))
        row["bytes"] = p.stat().st_size
        nums = _git(repo, "diff", "--numstat", "HEAD", "--", path).split("\t")
        row["added"], row["removed"] = int(nums[0] or 0), int(nums[1] or 0)
        if blob == _git(repo, "rev-parse", f"HEAD:{path}"):
            row["class"] = "PHANTOM-IDENTICAL-TO-HEAD"
        else:
            hist = _blob_in_history(repo, blob)
            if hist["found"]:
                row["class"] = "ALREADY-COMMITTED-ELSEWHERE"
                row.update(hist)
            else:
                row["class"] = _formatter_class(repo, path) or "UNIQUE-NEEDS-JUDGMENT"
                row["last_commit_touching"] = _git(
                    repo, "log", "-1", "--format=%h %ad %s", "--date=short", "--", path
                )
        out["modified"].append(row)
    summary: dict = {}
    for r in out["modified"]:
        summary[r["class"]] = summary.get(r["class"], 0) + 1
    summary["untracked"] = len(out["untracked"])
    summary["untracked_ignored"] = sum(1 for r in out["untracked"] if r["ignored_by"])
    out["summary"] = summary
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic inventory of a checkout's uncommitted state."
    )
    ap.add_argument("output", type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = ap.parse_args()
    data = inventory(args.repo)
    args.output.write_text(json.dumps(data, indent=1))
    print(json.dumps(data["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
