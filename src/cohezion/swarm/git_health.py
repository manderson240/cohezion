"""
Git Health Utilities.

Provides functions to collect git metadata and map codebase complexity 
(from DeepAuditor) to specific git commit history using git blame.
"""

import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from cohezion.healing.deep_audit import CodeIssue, FileStats

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

def collect_git_metadata() -> List[GitCommit]:
    """Collect recent git commits."""
    try:
        cmd = ["git", "log", "-n", "20", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(GitCommit(
                    hash=parts[0],
                    author=parts[1],
                    date=datetime.fromisoformat(parts[2]),
                    message="|".join(parts[3:])
                ))
        return commits
    except Exception as e:
        logger.error(f"Failed to collect git metadata: {e}")
        return []

def get_line_blame(file_path: str, line_number: int) -> Dict[str, Any]:
    """Get git blame info for a specific line."""
    try:
        cmd = ["git", "blame", "-L", f"{line_number},{line_number}", "--porcelain", file_path]
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

def attribute_complexity(issues: List[CodeIssue]) -> List[HealthTrace]:
    """Map CodeIssues to git history."""
    traces = []
    for issue in issues:
        blame = get_line_blame(issue.file_path, issue.line)
        if blame:
            traces.append(HealthTrace(
                file_path=issue.file_path,
                line=issue.line,
                commit_hash=blame["hash"],
                author=blame.get("author", "Unknown"),
                date=blame.get("date", datetime.now()),
                issue=issue
            ))
    return traces

def get_unpushed_commits() -> List[GitCommit]:
    """Returns commits that are local but not in remote."""
    try:
        # Check if there's an upstream
        subprocess.run(["git", "rev-parse", "--abbrev-ref", "@{u}"], capture_output=True, check=True)
        cmd = ["git", "log", "@{u}..HEAD", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Reuse logic from collect_git_metadata or refactor
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(GitCommit(parts[0], parts[1], datetime.fromisoformat(parts[2]), "|".join(parts[3:])))
        return commits
    except subprocess.CalledProcessError:
        # No upstream branch, take last 5 commits as "potential unpushed"
        return collect_git_metadata()[:5]

def get_repo_bloat() -> Dict[str, Any]:
    """Analyze untracked and modified files for repository bloat."""
    try:
        # Count total pending changes
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        total_pending = len(lines)
        
        # Categorize
        untracked = [l for l in lines if l.startswith("??")]
        modified = [l for l in lines if not l.startswith("??")]
        
        # Find top directories by file count (approximate)
        dirs = {}
        for line in lines[:2000]: # Limit for performance
            path = line[3:]
            parts = path.split("/")
            if len(parts) > 1:
                base_dir = parts[0]
                dirs[base_dir] = dirs.get(base_dir, 0) + 1
        
        return {
            "total_pending": total_pending,
            "untracked_count": len(untracked),
            "modified_count": len(modified),
            "hotspots": sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    except Exception as e:
        logger.error(f"Failed to analyze repo bloat: {e}")
        return {"total_pending": 0, "error": str(e)}

if __name__ == "__main__":
    import json
    commits = collect_git_metadata()
    print(f"Collected {len(commits)} commits.")
    if commits:
        print(f"Latest: {commits[0].hash} - {commits[0].message}")
