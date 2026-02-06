"""
Git Health Utilities.

Provides functions to collect git metadata and map codebase complexity
(from DeepAuditor) to specific git commit history using git blame.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.healing.deep_audit import CodeIssue

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    hash: str
    author: str
    date: datetime
    message: str


@dataclass
class HealthTrace:
    file_path: str
    line: int
    commit_hash: str
    author: str
    date: datetime
    issue: CodeIssue | None = None


def collect_git_metadata() -> list[GitCommit]:
    """Collect recent git commits."""
    try:
        cmd = ["git", "log", "-n", "20", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(
                    GitCommit(
                        hash=parts[0],
                        author=parts[1],
                        date=datetime.fromisoformat(parts[2]),
                        message="|".join(parts[3:]),
                    )
                )
        return commits
    except Exception as e:
        logger.error(f"Failed to collect git metadata: {e}")
        return []


def get_line_blame(file_path: str, line_number: int) -> dict[str, Any]:
    """Get git blame info for a specific line."""
    try:
        cmd = [
            "git",
            "blame",
            "-L",
            f"{line_number},{line_number}",
            "--porcelain",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        if not lines:
            return {}

        commit_info = lines[0].split()
        commit_hash = commit_info[0]

        blame_data = {"hash": commit_hash}
        for line in lines[1:]:
            if line.startswith("author "):
                blame_data["author"] = line[7:]
            elif line.startswith("author-time "):
                blame_data["date"] = datetime.fromtimestamp(int(line[12:]))

        return blame_data
    except Exception as e:
        logger.error(f"Failed to get blame for {file_path}:{line_number}: {e}")
        return {}


def attribute_complexity(issues: list[CodeIssue]) -> list[HealthTrace]:
    """Map CodeIssues to git history."""
    traces = []
    for issue in issues:
        blame = get_line_blame(issue.file_path, issue.line)
        if blame:
            traces.append(
                HealthTrace(
                    file_path=issue.file_path,
                    line=issue.line,
                    commit_hash=blame["hash"],
                    author=blame.get("author", "Unknown"),
                    date=blame.get("date", datetime.now()),
                    issue=issue,
                )
            )
    return traces


def get_unpushed_commits() -> list[GitCommit]:
    """Returns commits that are local but not in remote."""
    try:
        # Check if there's an upstream
        subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            capture_output=True,
            check=True,
        )
        cmd = [
            "git",
            "log",
            "@{u}..HEAD",
            "--pretty=format:%H|%an|%ad|%s",
            "--date=iso",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Reuse logic from collect_git_metadata or refactor
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(
                    GitCommit(
                        parts[0],
                        parts[1],
                        datetime.fromisoformat(parts[2]),
                        "|".join(parts[3:]),
                    )
                )
        return commits
    except subprocess.CalledProcessError:
        # No upstream branch, take last 5 commits as "potential unpushed"
        return collect_git_metadata()[:5]


def get_repo_bloat() -> dict[str, Any]:
    """Analyze untracked, staged files and index size for repository bloat."""
    try:
        # 1. Count total pending changes (porcelain)
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        total_pending = len(lines)

        # 2. Categorize
        untracked = [line for line in lines if line.startswith("??")]
        modified = [line for line in lines if not line.startswith("??")]

        # 3. Count staged files
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        staged_count = len(staged_result.stdout.splitlines())

        # 4. Check index size
        index_path = Path(".git/index")
        index_size_mb = 0
        if index_path.exists():
            index_size_mb = index_path.stat().st_size / (1024 * 1024)

        # 5. Find top directories by file count (approximate)
        dirs: dict[str, int] = {}
        for line in lines[:2000]:  # Limit for performance
            path = line[3:]
            parts = path.split("/")
            if len(parts) > 1:
                base_dir = parts[0]
                dirs[base_dir] = dirs.get(base_dir, 0) + 1

        return {
            "total_pending": total_pending,
            "untracked_count": len(untracked),
            "modified_count": len(modified),
            "staged_count": staged_count,
            "index_size_mb": round(index_size_mb, 2),
            "hotspots": sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:5],
        }
    except Exception as e:
        logger.error(f"Failed to analyze repo bloat: {e}")
        return {"total_pending": 0, "error": str(e)}


if __name__ == "__main__":
    commits = collect_git_metadata()
    print(f"Collected {len(commits)} commits.")
    if commits:
        print(f"Latest: {commits[0].hash} - {commits[0].message}")
