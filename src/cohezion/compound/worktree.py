"""Worktree Orchestrator for agentic session isolation."""

import logging
import os
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class WorktreeOrchestrator:
    """
    Manages Git worktrees for parallel agentic sessions.
    Ensures development occurs in isolated environments to prevent conflicts.
    """

    def __init__(self, base_path: str = "/tmp/cohezion_swarm"):
        self.base_path = Path(base_path)
        self.repo_root = self._find_repo_root()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _find_repo_root(self) -> Path:
        """Find the root of the current git repository."""
        try:
            root = (
                subprocess.check_output(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=os.getcwd(),
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
            return Path(root)
        except Exception:
            # Fallback to current directory if not in git
            return Path(os.getcwd())

    def create_session_worktree(self, session_id: str, branch: str = "main") -> str:
        """
        Create a new git worktree for a session.
        """
        worktree_path = self.base_path / session_id
        if worktree_path.exists():
            logger.warning(f"Worktree already exists for session {session_id}")
            return str(worktree_path)

        try:
            logger.info(f"Creating worktree for session {session_id} at {worktree_path}")
            # git worktree add [-f] [--checkout] [--lock] [-b <new-branch>] <path> [<commit-ish>]
            subprocess.run(
                ["git", "worktree", "add", "-b", f"swarm/{session_id}", str(worktree_path), branch],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
            )
            return str(worktree_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create worktree: {e.stderr.decode()}")
            # If it fails, we might just use the main repo (not ideal but fallback)
            return str(self.repo_root)

    def cleanup_session_worktree(self, session_id: str):
        """
        Remove a session's worktree.
        """
        worktree_path = self.base_path / session_id
        if not worktree_path.exists():
            return

        try:
            logger.info(f"Cleaning up worktree for session {session_id}")
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to cleanup worktree: {e.stderr.decode()}")


def get_orchestrator() -> WorktreeOrchestrator:
    return WorktreeOrchestrator()
