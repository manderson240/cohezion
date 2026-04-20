#!/usr/bin/env python3
"""Archive a worktree non-destructively with git bundle and manifest."""

import argparse
import json
import shutil
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


def get_worktree_info(worktree_path: Path) -> dict:
    """Get information about a worktree."""
    # Get worktree list
    output = run_git("worktree", "list", "--porcelain")

    for block in output.split("\n\n"):
        lines = block.strip().split("\n")
        if not lines:
            continue

        path_line = lines[0]
        if path_line.startswith("worktree "):
            wt_path = path_line[9:]
            if Path(wt_path) == worktree_path:
                info = {"path": wt_path}
                for line in lines[1:]:
                    if line.startswith("branch "):
                        info["branch"] = line[7:]
                    elif line.startswith("HEAD "):
                        info["head"] = line[5:]
                    elif line == "bare":
                        info["bare"] = True
                    elif line == "detached":
                        info["detached"] = True
                return info

    return {}


def create_bundle(worktree_path: Path, archive_dir: Path, slug: str) -> Path | None:
    """Create a git bundle from the worktree."""
    bundle_name = f"{slug}-{datetime.now().strftime('%Y%m%d')}.bundle"
    bundle_path = archive_dir / bundle_name

    try:
        # Get the current HEAD
        head = run_git("rev-parse", "HEAD", cwd=worktree_path)

        # Create bundle with all refs
        run_git(
            "bundle", "create",
            str(bundle_path),
            "HEAD",
            cwd=worktree_path,
        )

        return bundle_path
    except subprocess.CalledProcessError:
        return None


def archive_manifest(original_manifest: Path, archive_dir: Path, slug: str) -> Path:
    """Archive the manifest with updated status."""
    archive_manifest_path = archive_dir / "MANIFEST.md"

    if original_manifest.exists():
        content = original_manifest.read_text()
        # Update status lines
        content = content.replace(
            "**Active**: true",
            "**Active**: false (archived)"
        )
        content = content.replace(
            "## Status",
            f"## Status\n- **Archived**: {datetime.now().isoformat()}"
        )
        content += f"\n\n## Archive Info\n- **Archived At**: {datetime.now().isoformat()}\n"
    else:
        content = f"""# Archived Worktree: {slug}

## Archive Info
- **Slug**: {slug}
- **Archived At**: {datetime.now().isoformat()}
- **Status**: Archived
"""

    archive_manifest_path.write_text(content)
    return archive_manifest_path


def archive_worktree(worktree_path: str | Path) -> dict:
    """Archive a worktree non-destructively."""
    worktree_path = Path(worktree_path).resolve()
    repo_root = get_repo_root()

    if not worktree_path.exists():
        return {
            "success": False,
            "error": "not_found",
            "detail": f"Worktree not found at {worktree_path}",
        }

    # Extract slug from path
    slug = worktree_path.name.replace("spec-", "").rsplit("-", 1)[0]

    # Get worktree info
    wt_info = get_worktree_info(worktree_path)
    if not wt_info:
        return {
            "success": False,
            "error": "not_worktree",
            "detail": f"Path {worktree_path} is not a git worktree",
        }

    # Create archive directory
    archive_dir = repo_root / "archive" / "worktrees" / worktree_path.name
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Create git bundle
    bundle_path = create_bundle(worktree_path, archive_dir, slug)

    # Archive manifest
    original_manifest = worktree_path / "MANIFEST.md"
    manifest_path = archive_manifest(original_manifest, archive_dir, slug)

    # Copy any other important files (logs, configs, etc.)
    copied_files = []
    for pattern in ["*.log", "*.json", ".env*"]:
        for file in worktree_path.glob(pattern):
            if file.is_file():
                dest = archive_dir / file.name
                shutil.copy2(file, dest)
                copied_files.append(str(dest))

    return {
        "success": True,
        "slug": slug,
        "archive_dir": str(archive_dir),
        "bundle": str(bundle_path) if bundle_path else None,
        "manifest": str(manifest_path),
        "copied_files": copied_files,
        "original_path": str(worktree_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Archive a worktree")
    parser.add_argument("worktree_path", help="Path to the worktree to archive")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result = archive_worktree(args.worktree_path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Worktree archived successfully:")
            print(f"  Slug: {result['slug']}")
            print(f"  Archive Dir: {result['archive_dir']}")
            print(f"  Bundle: {result['bundle']}")
            print(f"  Manifest: {result['manifest']}")
        else:
            print(f"Error: {result['error']}")
            print(f"  {result['detail']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
