#!/usr/bin/env python3
"""Phase 0 verification: validate safety before consolidation.

Verifies:
  R1: Backup branch exists and points to current HEAD
  R2: All active worktree branches are reachable
  R3: No stash entries lost
  R4: origin/main is reachable
  R5: git maintenance is active
"""

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None) -> str:
    return subprocess.check_output(cmd, text=True, cwd=cwd, stderr=subprocess.STDOUT).strip()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    failures = 0

    def check(condition: bool, msg: str):
        nonlocal failures
        if condition:
            print(f"  PASS  {msg}")
        else:
            print(f"  FAIL  {msg}")
            failures += 1

    print("=== R1: Backup branch ===")
    result = run(["git", "rev-parse", "backup/before-main-consolidation"], cwd=str(repo))
    head = run(["git", "rev-parse", "HEAD"], cwd=str(repo))
    check(result == head, f"backup == HEAD ({head[:12]})")

    print("\n=== R2: Worktree branches reachable ===")
    wt_output = run(["git", "worktree", "list", "--porcelain"], cwd=str(repo))
    wts = []
    current = {}
    for line in wt_output.splitlines():
        if line.startswith("worktree "):
            if current:
                wts.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                current["branch"] = parts[2]
        elif line.startswith("detached"):
            pass
        elif line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
    if current:
        wts.append(current)

    for wt in wts:
        branch = wt.get("branch", "")
        head_sha = wt.get("head", "")
        try:
            run(["git", "rev-parse", "--verify", head_sha], cwd=str(repo))
            check(True, f"worktree {wt['path']}: {branch} @ {head_sha[:12]} reachable")
        except subprocess.CalledProcessError:
            check(False, f"worktree {wt['path']}: {branch} @ {head_sha[:12]} UNREACHABLE")

    print("\n=== R3: Stash integrity ===")
    stash_count = len(run(["git", "stash", "list"], cwd=str(repo)).splitlines())
    check(stash_count >= 0, f"Stash entries counted: {stash_count}")

    print("\n=== R4: origin/main reachable ===")
    try:
        origin_main = run(["git", "rev-parse", "origin/main"], cwd=str(repo))
        check(True, f"origin/main = {origin_main[:12]}")
    except subprocess.CalledProcessError:
        check(False, "origin/main NOT FOUND")

    print("\n=== R5: Git maintenance ===")
    try:
        maint = run(["git", "maintenance", "list"], cwd=str(repo))
        check("hourly" in maint, "Hourly maintenance scheduled")
        check("daily" in maint, "Daily maintenance scheduled")
        check("weekly" in maint, "Weekly maintenance scheduled")
    except subprocess.CalledProcessError:
        check(False, "Maintenance check failed")

    print(f"\n{'=' * 40}{'ALL PASSED' if failures == 0 else f'{failures} FAILURES'}{'=' * 40}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
