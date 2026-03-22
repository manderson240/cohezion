"""Git utilities for configuration orchestration.

Handles commit history analysis, auto-commit operations,
and conflict detection via git state.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class GitUtils:
    """Git operations for config file tracking and auto-commit."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize GitUtils with repository root."""
        if repo_root is None:
            repo_root = Path.cwd()
        self.repo_root = repo_root
        if not (repo_root / ".git").exists():
            logger.warning(f"Not a git repository: {repo_root}")

    def get_last_commit_author(self, file_path: Path) -> str | None:
        """Get the author of the last commit for a file."""
        try:
            result = subprocess.run(
                ["git", "log", "--format=%an", "-1", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get commit author for {file_path}: {e}")
        return None

    def get_last_commit_time(self, file_path: Path) -> datetime | None:
        """Get the timestamp of the last commit for a file."""
        try:
            result = subprocess.run(
                ["git", "log", "--format=%ai", "-1", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return datetime.fromisoformat(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get commit time for {file_path}: {e}")
        return None

    def is_manual_edit(
        self, file_path: Path, orchestrator_name: str = "config"
    ) -> bool:
        """Check if file was manually edited vs auto-generated.

        Args:
            file_path: Path to config file
            orchestrator_name: Git author name used by orchestrator (e.g., "config")

        Returns:
            True if manually edited, False if auto-generated
        """
        author = self.get_last_commit_author(file_path)
        if author is None:
            return False  # File may not be in git yet
        return author != orchestrator_name

    def get_uncommitted_changes(self, file_path: Path) -> bool:
        """Check if file has uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--quiet", str(file_path)],
                cwd=self.repo_root,
                timeout=5,
            )
            # git diff --quiet returns 1 if there are changes, 0 if no changes
            return result.returncode == 1
        except Exception as e:
            logger.warning(f"Failed to check git changes for {file_path}: {e}")
            return False

    def get_file_diff(self, file_path: Path) -> str | None:
        """Get diff of uncommitted changes for a file."""
        try:
            result = subprocess.run(
                ["git", "diff", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.warning(f"Failed to get git diff for {file_path}: {e}")
        return None

    async def auto_commit(
        self,
        file_path: Path,
        message: str,
        author_name: str = "Cohezion ConfigOrchestrator",
        author_email: str = "config@cohezion.local",
    ) -> bool:
        """Create an atomic git commit with AI-generated message.

        Args:
            file_path: Path to file to commit
            message: Commit message (descriptive, auto-generated)
            author_name: Git author name
            author_email: Git author email

        Returns:
            True if commit successful, False otherwise
        """
        try:
            # Stage file
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                timeout=5,
                check=True,
            )

            # Commit with author info
            env = {
                "GIT_AUTHOR_NAME": author_name,
                "GIT_AUTHOR_EMAIL": author_email,
                "GIT_COMMITTER_NAME": author_name,
                "GIT_COMMITTER_EMAIL": author_email,
            }
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                env={**subprocess.os.environ, **env},
            )

            if result.returncode == 0:
                logger.info(f"Auto-committed {file_path}: {message}")
                return True
            elif "nothing to commit" in result.stdout:
                logger.debug(f"No changes to commit for {file_path}")
                return True
            else:
                logger.error(f"Commit failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to auto-commit {file_path}: {e}")
            return False

    async def create_backup_commit(self, file_path: Path) -> bool:
        """Create a backup commit before making significant changes."""
        message = f"config: backup {file_path.name} before orchestration changes"
        return await self.auto_commit(file_path, message)

    def get_commit_history(self, file_path: Path, max_count: int = 10) -> list[dict]:
        """Get recent commit history for a file."""
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--max-count={max_count}",
                    "--format=%H|%an|%ai|%s",
                    str(file_path),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    commit_hash, author, timestamp, subject = line.split("|", 3)
                    commits.append(
                        {
                            "hash": commit_hash,
                            "author": author,
                            "timestamp": timestamp,
                            "subject": subject,
                        }
                    )
            return commits

        except Exception as e:
            logger.warning(f"Failed to get commit history for {file_path}: {e}")
            return []

    def get_repo_status(self) -> dict:
        """Get overall git repository status."""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            current_branch = (
                branch_result.stdout.strip()
                if branch_result.returncode == 0
                else "unknown"
            )

            # Get dirty status
            dirty_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_dirty = bool(dirty_result.stdout.strip())

            return {
                "branch": current_branch,
                "dirty": is_dirty,
                "changed_files": len(dirty_result.stdout.strip().split("\n"))
                if is_dirty
                else 0,
            }

        except Exception as e:
            logger.warning(f"Failed to get git status: {e}")
            return {"branch": "unknown", "dirty": False, "changed_files": 0}
