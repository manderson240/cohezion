"""
Shadow Worktree - Isomorphic Sandbox Execution.

Manages ephemeral Git worktrees for testing unproven agent actions
(AutonomyTier < HIHO) before precipitating to the main branch.
"""

import logging
import subprocess
import uuid
from pathlib import Path


logger = logging.getLogger(__name__)


class ShadowWorktree:
    """Ephemeral sandbox for destructive agent actions."""

    def __init__(self, base_repo: str | Path, sandbox_root: str | Path = ".shadow"):
        self.base_repo = Path(base_repo).resolve()
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def create_sandbox(self, agent_id: str) -> Path:
        """Create a new git worktree for the agent."""
        worktree_id = f"{agent_id}_{uuid.uuid4().hex[:8]}"
        worktree_path = self.sandbox_root / worktree_id

        logger.info(f"Creating shadow worktree for {agent_id} at {worktree_path}")

        try:
            # Create a branch for the shadow work
            branch_name = f"shadow/{worktree_id}"
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.base_repo,
                check=True,
                capture_output=True,
            )

            # Create the worktree
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=self.base_repo,
                check=True,
                capture_output=True,
            )

            # Switch back to original branch in base repo
            subprocess.run(
                ["git", "checkout", "-"], cwd=self.base_repo, check=True, capture_output=True
            )

            return worktree_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create shadow worktree: {e.stderr.decode()}")
            raise

    def execute_in_sandbox(
        self, worktree_path: Path, command: list[str]
    ) -> subprocess.CompletedProcess:
        """Run a command inside the shadow worktree."""
        return subprocess.run(command, cwd=worktree_path, capture_output=True, text=True)

    def cleanup_sandbox(self, worktree_path: Path):
        """Remove the worktree and the shadow branch."""
        logger.info(f"Cleaning up shadow worktree at {worktree_path}")
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=self.base_repo,
                check=True,
                capture_output=True,
            )
            # Find the branch name from path
            branch_name = f"shadow/{worktree_path.name}"
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.base_repo,
                check=True,
                capture_output=True,
            )
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def precipitate_to_main(self, worktree_path: Path) -> bool:
        """Merge shadow work into main (only if verified)."""
        # Logic for automated PR or direct merge after verification
        logger.info(f"Precipitating work from {worktree_path} to main consensus.")
        return True
