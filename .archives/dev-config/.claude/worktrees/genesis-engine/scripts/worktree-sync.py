#!/usr/bin/env python3
"""Squash merge a worktree branch back to its base branch."""

import argparse
import json
import subprocess
from pathlib import Path


def run_git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    """Run a git command and return output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=check,
    )
    return result.stdout.strip()


def get_repo_root() -> Path:
    """Get the repository root directory."""
    output = run_git("rev-parse", "--show-toplevel")
    return Path(output)


def get_branch_from_slug(slug: str) -> str | None:
    """Get branch name from slug."""
    branch_name = f"spec/{slug}"

    # Check if branch exists
    try:
        run_git("rev-parse", "--verify", branch_name)
        return branch_name
    except subprocess.CalledProcessError:
        return None


def get_worktree_for_branch(branch: str) -> Path | None:
    """Get worktree path for a branch."""
    output = run_git("worktree", "list", "--porcelain")

    for block in output.split("\n\n"):
        lines = block.strip().split("\n")
        if not lines:
            continue

        path_line = lines[0]
        if path_line.startswith("worktree "):
            wt_path = path_line[9:]
            for line in lines[1:]:
                if line.startswith("branch "):
                    branch_ref = line[7:]
                    if branch_ref.endswith(branch):
                        return Path(wt_path)

    return None


def sync_worktree(slug: str, squash_message: str | None = None) -> dict:
    """Squash merge worktree to base branch."""
    repo_root = get_repo_root()

    # Get branch name
    branch = get_branch_from_slug(slug)
    if not branch:
        return {
            "success": False,
            "error": "branch_not_found",
            "detail": f"No branch found for slug '{slug}' (expected spec/{slug})",
        }

    # Get worktree path
    worktree_path = get_worktree_for_branch(branch)
    if not worktree_path:
        return {
            "success": False,
            "error": "worktree_not_found",
            "detail": f"No worktree found for branch {branch}",
        }

    # Get current branch (to return to)
    original_branch = run_git("branch", "--show-current")

    # Get base branch from manifest if available
    base_branch = "main"
    manifest_path = worktree_path / "MANIFEST.md"
    if manifest_path.exists():
        content = manifest_path.read_text()
        for line in content.split("\n"):
            if "**Base Branch**:" in line:
                base_branch = line.split(":", 1)[1].strip()
                break

    try:
        # Checkout base branch
        run_git("checkout", base_branch)

        # Squash merge
        message = squash_message or f"feat: squash merge {slug}"
        run_git("merge", "--squash", branch)

        # Commit the squash
        run_git("commit", "-m", message)

        # Get commit hash
        commit_hash = run_git("rev-parse", "HEAD")

        # Get files changed
        diff_output = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash)
        files_changed = diff_output.split("\n") if diff_output else []

        return {
            "success": True,
            "slug": slug,
            "branch": branch,
            "base_branch": base_branch,
            "commit_hash": commit_hash,
            "files_changed": files_changed,
            "count": len(files_changed),
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": "merge_failed",
            "detail": str(e),
        }
    finally:
        # Return to original branch
        if run_git("branch", "--show-current") != original_branch:
            run_git("checkout", original_branch, check=False)


def main():
    parser = argparse.ArgumentParser(description="Sync worktree to base branch")
    parser.add_argument("slug", help="Worktree slug")
    parser.add_argument(
        "--message",
        help="Squash commit message",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result = sync_worktree(args.slug, args.message)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Worktree synced successfully:")
            print(f"  Slug: {result['slug']}")
            print(f"  Branch: {result['branch']}")
            print(f"  Base: {result['base_branch']}")
            print(f"  Commit: {result['commit_hash'][:8]}")
            print(f"  Files Changed: {result['count']}")
            for f in result["files_changed"]:
                print(f"    - {f}")
        else:
            print(f"Error: {result['error']}")
            print(f"  {result['detail']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
