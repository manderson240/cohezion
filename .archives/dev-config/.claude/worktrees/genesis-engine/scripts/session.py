#!/usr/bin/env python3
"""
Session Manager for Cohezion - Automated Git Worktree Workflow.
Enforces the mandatory worktree pattern with safety gates.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


# Constants — use environment variables with sensible defaults
REPO_ROOT = Path(os.environ.get("COHEZION_ROOT", ".")).resolve()
DEV_ROOT = REPO_ROOT.parent


def run(cmd: list[str], check: bool = True, cwd: Path = REPO_ROOT) -> str | None:
    """Run a command (list form, no shell) and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        if check:
            sys.exit(1)
        return None


def get_next_session_id():
    """Find the next available session ID."""
    worktrees = run(["git", "worktree", "list"])
    ids = []
    for line in (worktrees or "").splitlines():
        if "cohezion-session-" in line:
            try:
                part = line.split("cohezion-session-")[1].split()[0]
                session_id = int(part.split("-")[0])
                ids.append(session_id)
            except (IndexError, ValueError):
                continue
    return max(ids, default=46) + 1


def start_session(phase):
    """Create a new worktree and branch for a session."""
    # Validate phase name to prevent injection
    if not re.match(r"^[a-zA-Z0-9_-]+$", phase):
        print(f"Invalid phase name: {phase!r}")
        sys.exit(1)

    session_id = get_next_session_id()
    branch = f"session-{session_id}-{phase}"
    worktree_dir = DEV_ROOT / f"cohezion-session-{session_id}"

    print(f"Starting Session {session_id}...")
    print(f"   Branch:   {branch}")
    print(f"   Worktree: {worktree_dir}")

    # 1. Create worktree
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch, "main"])

    # 2. Run validator in the new worktree
    print(f"Validating setup in {worktree_dir}...")
    run(["./scripts/validate-session-setup.sh"], cwd=worktree_dir)

    print(f"\nSession {session_id} ready!")
    print(f"   cd {worktree_dir}")
    print(f"   export SURREALDB_DB=session_{session_id}")


def list_sessions():
    """List active session worktrees."""
    print("Active Sessions:")
    worktrees = run(["git", "worktree", "list"])
    print(worktrees)


def clean_session(session_id, force=False):
    """Safely remove a session worktree."""
    worktree_dir = DEV_ROOT / f"cohezion-session-{session_id}"

    if not worktree_dir.exists():
        print(f"Worktree directory not found: {worktree_dir}")
        return

    print(f"Cleaning up Session {session_id}...")

    # Safety Check: Unpushed commits
    branch = run(["git", "-C", str(worktree_dir), "rev-parse", "--abbrev-ref", "HEAD"])
    unpushed = run(["git", "-C", str(worktree_dir), "cherry", "-v", "origin/main"], check=False)

    if unpushed and not force:
        print(f"WARNING: Unpushed commits found in {branch}:")
        print(unpushed)
        print("\nUse --force to delete anyway (DATA LOSS RISK).")
        return

    # Safety Check: Uncommitted changes
    status = run(["git", "-C", str(worktree_dir), "status", "--porcelain"])
    if status and not force:
        print(f"WARNING: Uncommitted changes found in {worktree_dir}:")
        print(status)
        print("\nUse --force to delete anyway (DATA LOSS RISK).")
        return

    # 1. Remove worktree
    remove_cmd = ["git", "worktree", "remove", str(worktree_dir)]
    if force:
        remove_cmd.append("--force")
    run(remove_cmd)

    # 2. Prune worktrees just in case
    run(["git", "worktree", "prune"])

    print(f"Session {session_id} cleaned up.")


def main():
    parser = argparse.ArgumentParser(description="Cohezion Session Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Start
    start_parser = subparsers.add_parser("start", help="Start a new session")
    start_parser.add_argument("--phase", required=True, help="Short name for the phase (e.g., bugfix)")

    # Status
    subparsers.add_parser("status", help="List active sessions")

    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean up a session")
    clean_parser.add_argument("--session", type=int, required=True, help="Session ID to clean")
    clean_parser.add_argument("--force", action="store_true", help="Force removal despite unpushed work")

    args = parser.parse_args()

    if args.command == "start":
        start_session(args.phase)
    elif args.command == "status":
        list_sessions()
    elif args.command == "clean":
        clean_session(args.session, args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
