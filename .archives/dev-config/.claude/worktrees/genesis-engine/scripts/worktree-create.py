#!/usr/bin/env python3
"""Create a new worktree with proper branch structure and manifest."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
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


def generate_worktree_hash(slug: str, base_branch: str) -> str:
    """Generate a short hash for the worktree name."""
    content = f"{slug}:{base_branch}:{datetime.now().isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def create_manifest(worktree_path: Path, slug: str, base_branch: str, branch_name: str) -> Path:
    """Create MANIFEST.md for the worktree."""
    manifest_path = worktree_path / "MANIFEST.md"

    manifest_content = f"""# Worktree Manifest: {slug}

## Metadata
- **Slug**: {slug}
- **Base Branch**: {base_branch}
- **Worktree Branch**: {branch_name}
- **Created**: {datetime.now().isoformat()}
- **Worktree Path**: {worktree_path}

## Status
- **Active**: true
- **Last Modified**: {datetime.now().isoformat()}

## Files
- `MANIFEST.md`: This file
- Source files in repository

## Notes
Worktree created for isolated development.
"""

    manifest_path.write_text(manifest_content)
    return manifest_path


def create_worktree(slug: str, base_branch: str) -> dict:
    """Create a new worktree with proper structure."""
    repo_root = get_repo_root()
    worktrees_dir = repo_root / ".worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    # Generate unique hash for this worktree
    wt_hash = generate_worktree_hash(slug, base_branch)
    worktree_name = f"spec-{slug}-{wt_hash}"
    worktree_path = worktrees_dir / worktree_name

    # Check if worktree already exists
    if worktree_path.exists():
        return {
            "success": False,
            "error": "exists",
            "detail": f"Worktree already exists at {worktree_path}",
        }

    # Create branch name
    branch_name = f"spec/{slug}"

    # Check if branch already exists
    try:
        run_git("rev-parse", "--verify", branch_name, check=False)
        branch_exists = True
    except subprocess.CalledProcessError:
        branch_exists = False

    if branch_exists:
        return {
            "success": False,
            "error": "branch_exists",
            "detail": f"Branch {branch_name} already exists",
        }

    # Create the branch from base
    run_git("checkout", "-b", branch_name, base_branch)

    # Create the worktree
    run_git("worktree", "add", str(worktree_path), branch_name)

    # Create manifest
    manifest = create_manifest(worktree_path, slug, base_branch, branch_name)

    return {
        "success": True,
        "path": str(worktree_path),
        "branch": branch_name,
        "base_branch": base_branch,
        "slug": slug,
        "hash": wt_hash,
        "manifest": str(manifest),
    }


def main():
    parser = argparse.ArgumentParser(description="Create a new worktree")
    parser.add_argument("slug", help="Worktree slug identifier")
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch to create from (default: main)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result = create_worktree(args.slug, args.base_branch)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Worktree created successfully:")
            print(f"  Path: {result['path']}")
            print(f"  Branch: {result['branch']}")
            print(f"  Base: {result['base_branch']}")
        else:
            print(f"Error: {result['error']}")
            print(f"  {result['detail']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
