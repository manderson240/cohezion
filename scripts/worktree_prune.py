#!/usr/bin/env python3
"""Nightly worktree & orphan-branch prune — report, optionally remove.

Safe-to-remove criteria (ALL must hold):
  1. Branch is fully merged into main (git branch --merged main)
  2. Working tree is clean (git status --porcelain empty)
  3. Branch NOT in the protect list (kaggle/*, nemotron, agi-golf, arc-*)
  4. Last commit is older than STALE_DAYS

Modes:
  (default / --dry-run):   report candidates, print removal commands
  --auto:                  dry-run report + run `entire clean --all --force`
                           for shadow branches (reconstructable); never removes
                           worktrees automatically — review first
  --execute:               dry-run, then remove after per-item confirmation

Usage (from repo root):
  uv run python scripts/worktree_prune.py
  uv run python scripts/worktree_prune.py --auto     # cron: report + shadow clean
  uv run python scripts/worktree_prune.py --execute  # interactive removal

Cron (add via `crontab -e`):
  0 3 * * * cd /home/mike-anderson/dev/cohezion && \
    uv run python scripts/worktree_prune.py --auto >> ~/.local/share/cohezion/prune.log 2>&1
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 7

# Patterns in branch names that are NEVER auto-removed.
# Add to this list before activating --auto on new competition tracks.
PROTECT_PATTERNS = [
    "kaggle/",
    "nemotron",
    "agi-golf",
    "neurogolf",
    "arc-prize",
    "arc-code",
    "arc-paper",
    "loop-backlog",
    "main",
    "master",
    "develop",
    "isolated/",
    "spec/",
    "feat/adaptive",  # current uncommitted fleet.py work
]


@dataclass
class WorktreeEntry:
    path: str
    head: str
    branch: str | None  # None = detached HEAD
    is_main_checkout: bool = False
    # populated by analyse()
    is_merged: bool = False
    is_clean: bool = False
    age_days: float = 0.0
    is_protected: bool = False
    safe_to_remove: bool = False
    block_reason: str = ""


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def parse_worktrees() -> list[WorktreeEntry]:
    _, out, _ = _run(["git", "worktree", "list", "--porcelain"])
    entries: list[WorktreeEntry] = []
    current: dict[str, str] = {}
    for raw_line in out.splitlines():
        line = raw_line.strip()
        if line.startswith("worktree "):
            if current:
                entries.append(_make_entry(current, is_first=len(entries) == 0))
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            ref = line.split(" ", 1)[1]  # refs/heads/foo
            if ref.startswith("refs/heads/"):
                current["branch"] = ref[len("refs/heads/"):]
            else:
                current["branch"] = ref
        elif line == "detached":
            current["branch"] = ""  # empty = detached
    if current:
        entries.append(_make_entry(current, is_first=len(entries) == 0))
    return entries


def _make_entry(d: dict, *, is_first: bool) -> WorktreeEntry:
    return WorktreeEntry(
        path=d.get("path", ""),
        head=d.get("head", ""),
        branch=d.get("branch") or None,
        is_main_checkout=is_first,
    )


def get_merged_branches() -> set[str]:
    _, out, _ = _run(["git", "branch", "--merged", "main"])
    return {b.strip().lstrip("* ") for b in out.splitlines() if b.strip()}


def analyse(entries: list[WorktreeEntry]) -> list[WorktreeEntry]:
    now_ts = datetime.now(timezone.utc).timestamp()
    merged = get_merged_branches()

    for e in entries:
        if e.is_main_checkout:
            e.block_reason = "main checkout"
            continue

        branch = e.branch

        # Protected branch?
        if branch:
            for pat in PROTECT_PATTERNS:
                if pat in branch:
                    e.is_protected = True
                    e.block_reason = f"protected pattern '{pat}'"
                    break

        # Merged into main?
        if branch and branch in merged:
            e.is_merged = True
        elif not branch:
            # Detached HEAD — treat as unmerged to be conservative
            e.block_reason = "detached HEAD"

        # Skip entirely if the worktree path no longer exists on disk
        if not Path(e.path).exists():
            e.is_merged = True  # treat as safe to prune (path is gone)
            e.is_clean = True
            e.age_days = float("inf")
            e.block_reason = ""  # will pass safety gate below
            # Override: mark directly safe if path is missing
            if not e.is_protected:
                e.safe_to_remove = True
                e.block_reason = "path missing on disk"
            continue

        # Clean working tree?
        rc, status, _ = _run(["git", "status", "--porcelain"], cwd=Path(e.path))
        e.is_clean = rc == 0 and status == ""

        # Age of last commit
        rc2, ts_str, _ = _run(
            ["git", "log", "-1", "--format=%ct", "HEAD"],
            cwd=Path(e.path),
        )
        if rc2 == 0 and ts_str.isdigit():
            e.age_days = (now_ts - int(ts_str)) / 86400.0

        # Final verdict
        if e.is_protected:
            e.safe_to_remove = False
        elif not e.is_merged:
            if not e.block_reason:
                e.block_reason = "has unmerged commits"
            e.safe_to_remove = False
        elif not e.is_clean:
            e.block_reason = "dirty working tree"
            e.safe_to_remove = False
        elif e.age_days < STALE_DAYS:
            e.block_reason = f"recent ({e.age_days:.0f}d < {STALE_DAYS}d threshold)"
            e.safe_to_remove = False
        else:
            e.safe_to_remove = True

    return entries


def print_report(entries: list[WorktreeEntry]) -> None:
    safe = [e for e in entries if e.safe_to_remove]
    blocked = [e for e in entries if not e.safe_to_remove and not e.is_main_checkout]

    print(f"\n{'='*70}")
    print(f"Worktree Prune Report  ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"{'='*70}")
    print(f"Total worktrees : {len(entries)}")
    print(f"Safe to remove  : {len(safe)}")
    print(f"Blocked (kept)  : {len(blocked)}")

    if safe:
        print(f"\n{'─'*70}")
        print("SAFE TO REMOVE (merged + clean + stale):")
        for e in safe:
            branch_str = e.branch or "(detached)"
            print(f"  [{e.age_days:.0f}d]  {branch_str}")
            print(f"         {e.path}")
            print(f"         # remove:  git worktree remove --force \"{e.path}\"")
            if e.branch:
                print(f"         # cleanup: git branch -D \"{e.branch}\"")

    if blocked:
        print(f"\n{'─'*70}")
        print("BLOCKED (kept, reason shown):")
        for e in blocked:
            branch_str = e.branch or "(detached)"
            print(f"  {branch_str}  →  {e.block_reason or 'kept'}")

    print(f"{'='*70}\n")


def remove_worktree(e: WorktreeEntry, *, confirm: bool = True) -> bool:
    branch_str = e.branch or "(detached)"
    if confirm:
        ans = input(f"Remove worktree '{branch_str}'? [y/N] ").strip().lower()
        if ans != "y":
            print(f"  Skipped {branch_str}")
            return False

    rc1, _, err1 = _run(["git", "worktree", "remove", "--force", e.path])
    if rc1 != 0:
        print(f"  ERROR removing worktree: {err1}")
        return False
    print(f"  Removed worktree: {e.path}")

    if e.branch:
        rc2, _, err2 = _run(["git", "branch", "-D", e.branch])
        if rc2 != 0:
            print(f"  WARNING: worktree removed but branch deletion failed: {err2}")
        else:
            print(f"  Deleted branch: {e.branch}")

    return True


def run_entire_shadow_clean() -> None:
    """Remove entire.io shadow branches (pre-prompt-*.json files + shadow entries).
    These are fully reconstructable from journal entries."""
    rc, out, err = _run(["entire", "clean", "--all", "--force"])
    if rc == 0:
        print(f"[entire clean] Done. {out[:200] if out else '(no output)'}")
    else:
        print(f"[entire clean] WARNING: rc={rc} stderr={err[:200]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report only (default behaviour — no deletions)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Dry-run report + run entire clean for shadow branches (cron mode)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Interactive removal of safe-to-remove worktrees",
    )
    args = parser.parse_args()

    entries = parse_worktrees()
    entries = analyse(entries)
    print_report(entries)

    safe = [e for e in entries if e.safe_to_remove]

    if args.execute:
        if not safe:
            print("Nothing safe to remove.")
            return 0
        print(f"Interactive removal of {len(safe)} worktree(s):")
        removed = sum(remove_worktree(e, confirm=True) for e in safe)
        print(f"\nRemoved {removed}/{len(safe)} worktrees.")

    if args.auto:
        print("\n[auto mode] Running entire clean for shadow branches...")
        run_entire_shadow_clean()
        if safe:
            print(
                f"\n[auto mode] {len(safe)} worktree(s) ready to remove."
                " Review the report above, then run:\n"
                "  uv run python scripts/worktree_prune.py --execute"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
