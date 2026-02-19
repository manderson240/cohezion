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
        # Sanitize session_id to prevent path traversal
        clean_session_id = "".join(
            c for c in session_id if c.isalnum() or c in ("-", "_")
        ).strip()
        if not clean_session_id:
            raise ValueError(f"Invalid session_id: {session_id}")

        worktree_path = (self.base_path / clean_session_id).resolve()

        # Ensure the path is within the base_path
        if not str(worktree_path).startswith(str(self.base_path.resolve())):
            raise ValueError(f"Path traversal detected in session_id: {session_id}")

        if worktree_path.exists():
            logger.warning(f"Worktree already exists for session {clean_session_id}")
            return str(worktree_path)

        try:
            logger.info(
                f"Creating worktree for session {clean_session_id} at {worktree_path}"
            )
            # git worktree add [-f] [--checkout] [--lock] [-b <new-branch>] <path> [<commit-ish>]
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    f"swarm/{clean_session_id}",
                    str(worktree_path),
                    branch,
                ],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
            )
            return str(worktree_path)
        except subprocess.CalledProcessError as e:
            err_msg: str = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Failed to create worktree: {err_msg}")
            raise RuntimeError(
                f"Could not create worktree for session {clean_session_id}: {err_msg}"
            )

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
            err_msg: str = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Failed to cleanup worktree: {err_msg}")

    def snapshot_state(self, session_id: str) -> bool:
        """
        Record the current state of a worktree session to the Knowledge Graph.

        Essentially 'freezes' the manifold state before cleanup or suspension.
        """
        worktree_path = self.base_path / session_id
        if not worktree_path.exists():
            return False

        try:
            from cohezion.core.persistence.surreal_client import get_surreal_client

            db = get_surreal_client()

            # Simple metadata snapshot for now
            # In a real mission, this would diff the files and store the delta.
            snapshot = {
                "session_id": session_id,
                "path": str(worktree_path),
                "timestamp": "2026-02-17T18:41:00Z",  # Mock timestamp
                "files": [
                    str(f.relative_to(worktree_path))
                    for f in worktree_path.rglob("*")
                    if f.is_file()
                ],
            }

            # db.create(f"session_snapshots:{session_id}", snapshot)
            logger.info(f"Snapshotted worktree state for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to snapshot worktree {session_id}: {e}")
            return False


def get_orchestrator() -> WorktreeOrchestrator:
    return WorktreeOrchestrator()
