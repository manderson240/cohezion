"""Git worktree isolation management for cohezion-engine."""
import hashlib
import re
import subprocess
from pathlib import Path


def derive_slug(plan_path: str) -> str:
    """Derive a worktree slug from a plan filename.

    Examples:
        '2026-02-21-add-auth.md' -> 'add-auth'
        'docs/plans/2026-02-21-my-feature.md' -> 'my-feature'
        'simple-slug' -> 'simple-slug'
    """
    name = Path(plan_path).stem  # strip directory and .md
    # Remove date prefix: YYYY-MM-DD-
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return name or plan_path


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _repo_root(cwd: Path) -> Path:
    """Find the git repository root."""
    result = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if result.returncode != 0:
        return cwd
    return Path(result.stdout.strip())


def _worktree_path(slug: str, repo_root: Path) -> Path:
    """Compute the worktree directory path for a given slug."""
    # Use short hash of HEAD for uniqueness
    head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
    commit_hash = head_result.stdout.strip() if head_result.returncode == 0 else "unknown"
    return repo_root / ".worktrees" / f"spec-{slug}-{commit_hash}"


def detect_worktree(slug: str, repo_root: Path | None = None) -> dict:
    """Check if a worktree for the given slug exists.

    Returns: {"found": bool, "path": str|None, "branch": str|None, "base_branch": str|None}
    """
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    result = _run_git(["worktree", "list", "--porcelain"], repo_root)
    if result.returncode != 0:
        return {"found": False}

    branch_pattern = f"spec/{slug}"
    current_path = None
    current_branch = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current_branch = line.split(" ", 1)[1].replace("refs/heads/", "")
            if current_branch == branch_pattern and current_path:
                base_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
                base_branch = base_result.stdout.strip() if base_result.returncode == 0 else "main"
                return {
                    "found": True,
                    "path": current_path,
                    "branch": current_branch,
                    "base_branch": base_branch,
                }

    return {"found": False}


def create_worktree(slug: str, repo_root: Path | None = None) -> dict:
    """Create a new git worktree for the given slug.

    Returns success dict or error dict with "error" key.
    """
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    # Check for dirty working tree
    status_result = _run_git(["status", "--porcelain"], repo_root)
    if status_result.returncode != 0:
        return {"success": False, "error": "git_error", "detail": status_result.stderr}

    if status_result.stdout.strip():
        return {
            "success": False,
            "error": "dirty",
            "detail": f"Uncommitted changes detected:\n{status_result.stdout.strip()}",
        }

    # Determine base branch
    base_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    base_branch = base_result.stdout.strip() if base_result.returncode == 0 else "main"

    # Compute worktree path
    wt_path = _worktree_path(slug, repo_root)
    branch_name = f"spec/{slug}"

    # Create worktree with new branch
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    result = _run_git(
        ["worktree", "add", "-b", branch_name, str(wt_path), base_branch],
        repo_root,
    )

    if result.returncode != 0:
        return {"success": False, "error": "worktree_create_failed", "detail": result.stderr}

    # Add .worktrees to .gitignore if not already there (only on success)
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".worktrees/" not in content:
            gitignore.write_text(content.rstrip() + "\n.worktrees/\n")
    else:
        gitignore.write_text(".worktrees/\n")

    return {
        "success": True,
        "path": str(wt_path),
        "branch": branch_name,
        "base_branch": base_branch,
    }


def get_worktree_status(repo_root: Path | None = None) -> dict:
    """Return info about the currently active worktree (if any)."""
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""

    if current_branch.startswith("spec/"):
        slug = current_branch.removeprefix("spec/")
        return {
            "active": True,
            "branch": current_branch,
            "slug": slug,
            "path": str(repo_root),
        }
    return {"active": False}


def diff_worktree(slug: str, repo_root: Path | None = None) -> dict:
    """List files changed in the worktree vs. base branch."""
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    wt_info = detect_worktree(slug, repo_root)
    if not wt_info["found"]:
        return {"success": False, "error": "worktree_not_found"}

    wt_path = Path(wt_info["path"])
    base = wt_info["base_branch"]
    result = _run_git(["diff", "--name-only", base], wt_path)
    if result.returncode != 0:
        return {"success": False, "error": result.stderr}

    files = [f for f in result.stdout.splitlines() if f]
    return {"success": True, "files_changed": files, "count": len(files)}


def sync_worktree(slug: str, repo_root: Path | None = None) -> dict:
    """Squash merge worktree branch back to base branch."""
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    wt_info = detect_worktree(slug, repo_root)
    if not wt_info["found"]:
        return {"success": False, "error": "worktree_not_found"}

    base_branch = wt_info["base_branch"]
    wt_branch = wt_info["branch"]

    # Switch to base branch and squash merge
    checkout = _run_git(["checkout", base_branch], repo_root)
    if checkout.returncode != 0:
        return {"success": False, "error": checkout.stderr}

    merge = _run_git(["merge", "--squash", wt_branch], repo_root)
    if merge.returncode != 0:
        return {"success": False, "error": merge.stderr}

    commit = _run_git(
        ["commit", "-m", f"feat: sync worktree {slug} to {base_branch}"],
        repo_root,
    )
    if commit.returncode != 0:
        return {"success": False, "error": commit.stderr}

    hash_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"

    diff = diff_worktree(slug, repo_root)
    return {
        "success": True,
        "commit_hash": commit_hash,
        "files_changed": diff.get("count", 0),
    }


def cleanup_worktree(slug: str, repo_root: Path | None = None) -> dict:
    """Remove worktree directory and delete its branch."""
    if repo_root is None:
        repo_root = _repo_root(Path.cwd())

    wt_info = detect_worktree(slug, repo_root)
    if not wt_info["found"]:
        return {"success": False, "error": "worktree_not_found"}

    wt_path = wt_info["path"]
    wt_branch = wt_info["branch"]

    # Remove worktree
    remove = _run_git(["worktree", "remove", "--force", wt_path], repo_root)
    # Delete branch
    branch_del = _run_git(["branch", "-D", wt_branch], repo_root)

    if remove.returncode != 0 and branch_del.returncode != 0:
        return {"success": False, "error": f"{remove.stderr} | {branch_del.stderr}"}

    return {"success": True, "removed_path": wt_path, "deleted_branch": wt_branch}
