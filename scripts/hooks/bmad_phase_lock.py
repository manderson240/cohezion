#!/usr/bin/env python3
"""BMAD Phase Lock — claim, release, and inspect phase ownership.

Usage:
  bmad_phase_lock.py claim <phase> [--owner <name>] [--branch <name>]
  bmad_phase_lock.py release <phase>
  bmad_phase_lock.py status
  bmad_phase_lock.py enforce

Phases: 1-analysis, 2-planning, 3-solutioning, 4-implementation

Lock files live in _bmad-output/{planning,implementation}-artifacts/.phase-lock-N

Lock file format (2 lines):
  line 1: owner (session ID, agent name, or human name)
  line 2: branch name
  line 3: ISO timestamp of claim

The `enforce` subcommand is designed for pre-commit hooks:
  exits 1 if current branch doesn't own the phase for modified artifacts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))
BMAD_OUTPUT = PROJECT_ROOT / "_bmad-output"
PLANNING_DIR = BMAD_OUTPUT / "planning-artifacts"
IMPLEMENTATION_DIR = BMAD_OUTPUT / "implementation-artifacts"

PHASE_LOCKS = {
    "1-analysis": PLANNING_DIR / ".phase-lock-1",
    "2-planning": PLANNING_DIR / ".phase-lock-2",
    "3-solutioning": PLANNING_DIR / ".phase-lock-3",
    "4-implementation": IMPLEMENTATION_DIR / ".phase-lock-4",
}

# Which artifacts belong to which phase
PHASE_ARTIFACTS = {
    "1-analysis": ["*brief*", "*research*", "*brainstorm*"],
    "2-planning": ["*prd*", "*ux-design*"],
    "3-solutioning": ["*architecture*", "*epic*", "*stories*"],
    "4-implementation": ["*sprint*", "*story*", "*retrospective*"],
}


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return result.stdout.strip() or "detached"


def claim(phase: str, owner: str, branch: str) -> int:
    lock_file = PHASE_LOCKS.get(phase)
    if not lock_file:
        print(f"Unknown phase: {phase}. Valid: {', '.join(PHASE_LOCKS)}")
        return 1

    lock_file.parent.mkdir(parents=True, exist_ok=True)

    if lock_file.exists():
        content = lock_file.read_text().strip().splitlines()
        existing_owner = content[0] if content else "?"
        existing_branch = content[1] if len(content) > 1 else "?"
        existing_time = content[2] if len(content) > 2 else "?"
        print(
            f"Phase {phase} already locked by {existing_owner} on {existing_branch} at {existing_time}"
        )
        print("Use 'release' first if the previous session is done.")
        return 1

    lock_file.write_text(f"{owner}\n{branch}\n{datetime.now().isoformat()}\n")
    print(f"✓ Phase {phase} claimed by {owner} on {branch}")
    return 0


def release(phase: str) -> int:
    lock_file = PHASE_LOCKS.get(phase)
    if not lock_file:
        print(f"Unknown phase: {phase}")
        return 1

    if not lock_file.exists():
        print(f"Phase {phase} is not locked")
        return 0

    content = lock_file.read_text().strip().splitlines()
    owner = content[0] if content else "?"
    lock_file.unlink()
    print(f"✓ Phase {phase} released (was owned by {owner})")
    return 0


def status() -> int:
    any_locked = False
    for phase, lock_file in sorted(PHASE_LOCKS.items()):
        if lock_file.exists():
            content = lock_file.read_text().strip().splitlines()
            owner = content[0] if content else "?"
            branch = content[1] if len(content) > 1 else "?"
            ts = content[2] if len(content) > 2 else "?"
            print(f"🔒 Phase {phase}: {owner} on {branch} (since {ts})")
            any_locked = True
        else:
            print(f"   Phase {phase}: available")

    if not any_locked:
        print("\nNo phases locked — sessions can coordinate via 'claim'")

    # Show current branch for context
    branch = current_branch()
    print(f"\nCurrent branch: {branch}")
    return 0


def enforce() -> int:
    """Pre-commit enforcement: check current branch owns phases for modified artifacts."""
    branch = current_branch()

    # Get staged files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    staged = [f for f in result.stdout.splitlines() if "_bmad-output" in f]

    if not staged:
        return 0  # No BMAD artifacts in this commit

    # Check each staged file against phase ownership
    violations = []
    for staged_file in staged:
        fname = Path(staged_file).name
        for phase, patterns in PHASE_ARTIFACTS.items():
            lock_file = PHASE_LOCKS[phase]
            # Check if file matches this phase's artifact patterns
            import fnmatch

            matched = any(fnmatch.fnmatch(fname, p) for p in patterns)
            if matched and lock_file.exists():
                content = lock_file.read_text().strip().splitlines()
                owner_branch = content[1] if len(content) > 1 else "?"
                if owner_branch != branch:
                    violations.append((staged_file, phase, owner_branch))

    if violations:
        print("BMAD phase lock violations:")
        for fpath, phase, owner_branch in violations:
            print(
                f"  ✗ {fpath} belongs to Phase {phase} (owned by {owner_branch}, you're on {branch})"
            )
        print("\nClaim the phase first: python scripts/hooks/bmad_phase_lock.py claim {phase}")
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BMAD Phase Lock Manager")
    sub = parser.add_subparsers(dest="command")

    claim_p = sub.add_parser("claim", help="Claim a BMAD phase")
    claim_p.add_argument("phase", help="Phase to claim (1-analysis, 2-planning, etc.)")
    claim_p.add_argument("--owner", default=None, help="Owner name (default: current git user)")
    claim_p.add_argument("--branch", default=None, help="Branch (default: current branch)")

    release_p = sub.add_parser("release", help="Release a BMAD phase")
    release_p.add_argument("phase", help="Phase to release")

    sub.add_parser("status", help="Show phase lock status")
    sub.add_parser("enforce", help="Enforce phase ownership (for pre-commit)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "claim":
        owner = args.owner or os.environ.get("USER", "unknown")
        branch = args.branch or current_branch()
        return claim(args.phase, owner, branch)
    elif args.command == "release":
        return release(args.phase)
    elif args.command == "status":
        return status()
    elif args.command == "enforce":
        return enforce()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
