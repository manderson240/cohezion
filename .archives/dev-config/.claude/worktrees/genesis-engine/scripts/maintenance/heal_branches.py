#!/usr/bin/env python3
"""
Automated Git Branch Healer.
Categorizes and renames historical branches to adhere to the new SemVer style,
archiving old or non-compliant branches.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from dataclasses import dataclass


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Valid conventional commit prefixes used for branches
VALID_PREFIXES = ("feat/", "fix/", "chore/", "docs/", "refactor/", "perf/", "test/", "security/")

# Branches to explicitly leave alone
PROTECTED_BRANCHES = {"main", "master", "develop", "dev"}


@dataclass
class BranchAction:
    old_name: str
    new_name: str
    reason: str


def get_all_local_branches() -> list[str]:
    """Get a list of all local git branches."""
    try:
        result = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [b.strip() for b in result.stdout.split() if b.strip()]
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get branches: {e}")
        sys.exit(1)


def determine_action(branch: str) -> BranchAction | None:
    """Determine what to do with a branch based on its name."""
    if branch in PROTECTED_BRANCHES:
        return None

    if branch.startswith("archive/"):
        return None  # Already archived

    # Check if it already has a valid prefix
    if any(branch.startswith(prefix) for prefix in VALID_PREFIXES):
        return None

    # Common non-compliant patterns
    if branch.startswith("feature/"):
        return BranchAction(branch, branch.replace("feature/", "feat/", 1), "Standardize 'feature/' to 'feat/'")
    if branch.startswith(("bugfix/", "bug/")):
        new_name = re.sub(r"^bug(fix)?/", "fix/", branch)
        return BranchAction(branch, new_name, "Standardize bugfix prefix to 'fix/'")
    if branch.startswith(("session-", "epic-", "story-")):
        # These are usually features
        return BranchAction(branch, f"feat/{branch}", "Wrap session/epic branch as a feature")
    if branch.startswith("entire/"):
        # Snapshots
        return BranchAction(branch, branch.replace("entire/", "archive/entire/"), "Archive 'entire' snapshot branch")
    if branch.startswith("worktree-"):
        return BranchAction(branch, f"archive/{branch}", "Archive abandoned worktree branch")
    if branch.startswith("spec/"):
        return BranchAction(branch, branch.replace("spec/", "docs/spec/"), "Standardize 'spec/' to 'docs/spec/'")

    # If it doesn't match any known pattern, archive it as legacy
    return BranchAction(branch, f"archive/legacy/{branch}", "Archive non-compliant legacy branch")


def execute_action(action: BranchAction, dry_run: bool = True) -> bool:
    """Execute the git branch rename command."""
    logger.info(f"[{action.reason}] {action.old_name} -> {action.new_name}")
    if dry_run:
        return True

    try:
        subprocess.run(
            ["git", "branch", "-m", action.old_name, action.new_name],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to rename {action.old_name}: {e.stderr.decode().strip()}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Heal non-compliant git branches.")
    parser.add_argument("--execute", action="store_true", help="Actually rename the branches (default is dry-run)")
    args = parser.parse_args()

    branches = get_all_local_branches()
    actions: list[BranchAction] = []

    for branch in branches:
        # Don't try to rename the currently checked out branch if we are on it
        # (Git allows renaming current branch, but it's cleaner to handle current branch separately if needed)
        action = determine_action(branch)
        if action:
            actions.append(action)

    if not actions:
        logger.info("All local branches are clean and compliant! 🌟")
        return

    logger.info(f"Found {len(actions)} branches needing healing.")
    if not args.execute:
        logger.info("DRY RUN MODE. Pass --execute to apply these changes.")

    success_count = 0
    for action in actions:
        if execute_action(action, dry_run=not args.execute):
            success_count += 1

    if args.execute:
        logger.info(f"Successfully healed {success_count}/{len(actions)} branches.")
    else:
        logger.info("Dry run complete. Use 'uv run python scripts/maintenance/heal_branches.py --execute' to apply.")


if __name__ == "__main__":
    main()
