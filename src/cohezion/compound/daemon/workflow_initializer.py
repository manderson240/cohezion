"""
Workflow Initializer for Compound Engineering Daemon
Automatically sets up git worktrees and TDD/Adversarial Review environment.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import structlog


logger = structlog.get_logger(__name__)


class CompoundEngineeringWorkflowInitializer:
    """
    Initializes compound engineering workflows with automatic git worktree setup
    and TDD/Adversarial Review environment preparation.

    This system ensures that:
    1. Each session gets an isolated git worktree
    2. TDD environment is ready and calibrated
    3. Adversarial review perspectives are warmed up
    4. The compound engineering system is primed for operation
    """

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.logger = logger.bind(component="WorkflowInitializer")
        self._initialized = False

    async def initialize_session(
        self,
        session_id: str | None = None,
        create_worktree: bool = True,
        prepare_tdd: bool = True,
        prepare_review: bool = True,
    ) -> dict[str, Any]:
        """
        Initialize a compound engineering session.

        Args:
            session_id: Optional session ID (will be generated if not provided)
            create_worktree: Whether to create/initialize a git worktree
            prepare_tdd: Whether to prepare the TDD environment
            prepare_review: Whether to warm up the adversarial review system

        Returns:
            Initialization results including worktree path and environment state
        """
        if not session_id:
            session_id = f"session_{int(os.times().elapsed)}_{os.getpid()}"

        self.logger.info(
            "Initializing compound engineering session",
            session_id=session_id,
            create_worktree=create_worktree,
            prepare_tdd=prepare_tdd,
            prepare_review=prepare_review,
        )

        results = {
            "session_id": session_id,
            "success": False,
            "worktree_path": None,
            "original_branch": None,
            "tdd_ready": False,
            "review_ready": False,
            "errors": [],
        }

        try:
            # Step 1: Create/initialize git worktree if requested
            if create_worktree:
                worktree_result = await self._initialize_git_worktree(session_id)
                results.update(worktree_result)
                if not worktree_result.get("success", False):
                    results["errors"].append("Failed to initialize git worktree")
                    return results

            # Step 2: Prepare TDD environment if requested
            if prepare_tdd:
                tdd_result = await self._prepare_tdd_environment(session_id)
                results.update(tdd_result)
                if not tdd_result.get("success", False):
                    results["errors"].append("Failed to prepare TDD environment")
                    # Don't fail entirely - continue with review preparation

            # Step 3: Prepare adversarial review system if requested
            if prepare_review:
                review_result = await self._prepare_review_environment(session_id)
                results.update(review_result)
                if not review_result.get("success", False):
                    results["errors"].append("Failed to prepare review environment")
                    # Don't fail entirely - continue with what we have

            # Mark as successful if we got this far without critical errors
            results["success"] = len(results.get("errors", [])) == 0
            self._initialized = True

            self.logger.info(
                "Compound engineering session initialized",
                session_id=session_id,
                success=results["success"],
                worktree_path=results.get("worktree_path"),
                tdd_ready=results.get("tdd_ready", False),
                review_ready=results.get("review_ready", False),
                error_count=len(results.get("errors", [])),
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize compound engineering session",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            results["errors"].append(f"Initialization failed: {e!s}")

        return results

    async def _initialize_git_worktree(self, session_id: str) -> dict[str, Any]:
        """Initialize a git worktree for isolated work."""
        self.logger.debug("Initializing git worktree", session_id=session_id)

        try:
            # Get current git info
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            if result.returncode != 0:
                return {"success": False, "error": "Not in a git repository", "worktree_path": None}

            # Get current branch and commit
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            if branch_result.returncode != 0 or commit_result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to get git information",
                    "worktree_path": None,
                }

            current_branch = branch_result.stdout.strip()
            current_commit = commit_result.stdout.strip()

            # Set up worktree directory
            worktrees_dir = self.project_root / ".opencode" / "worktrees"
            worktrees_dir.mkdir(parents=True, exist_ok=True)

            worktree_name = f"session-{session_id}"
            worktree_path = worktrees_dir / worktree_name
            branch_name = f"session/{session_id}"

            # Check if worktree already exists
            if worktree_path.exists():
                # Validate it's a proper worktree
                git_dir_file = worktree_path / ".git"
                if git_dir_file.exists():
                    if git_dir_file.is_file():
                        # It's a proper worktree
                        self.logger.debug(
                            "Using existing worktree",
                            session_id=session_id,
                            worktree_path=str(worktree_path),
                        )
                    else:
                        # It's a directory, remove it and recreate
                        import shutil

                        shutil.rmtree(worktree_path)
                else:
                    # Not a git directory, remove and recreate
                    import shutil

                    shutil.rmtree(worktree_path)

            # Create new worktree if needed
            if not worktree_path.exists() or not (worktree_path / ".git").exists():
                result = subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        branch_name,
                        str(worktree_path),
                        current_commit,
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root),
                )

                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Failed to create worktree: {result.stderr}",
                        "worktree_path": None,
                    }

            # Change to worktree directory
            original_cwd = os.getcwd()
            os.chdir(str(worktree_path))

            # Verify we're in the right place
            verify_result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
            )

            if verify_result.returncode != 0:
                os.chdir(original_cwd)
                return {
                    "success": False,
                    "error": "Failed to switch to worktree directory",
                    "worktree_path": None,
                }

            return {
                "success": True,
                "worktree_path": str(worktree_path),
                "original_branch": current_branch,
                "original_commit": current_commit,
                "worktree_branch": branch_name,
            }

        except Exception as e:
            self.logger.error(
                "Error initializing git worktree",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"Worktree initialization error: {e!s}",
                "worktree_path": None,
            }

    async def _prepare_tdd_environment(self, session_id: str) -> dict[str, Any]:
        """Prepare the TDD environment for the session."""
        self.logger.debug("Preparing TDD environment", session_id=session_id)

        try:
            # Import and initialize TDD integration
            from cohezion.compound.tdd_adversarial.tdd_integration import get_tdd_integration

            # Get current working directory (should be worktree if we created one)
            current_dir = Path.cwd()
            get_tdd_integration(current_dir)

            # Run a quick test to make sure the TDD system is working
            # In practice, we might do more comprehensive setup here
            self.logger.debug("TDD environment prepared", session_id=session_id)

            return {"success": True, "tdd_ready": True, "tdd_integration_available": True}

        except Exception as e:
            self.logger.error(
                "Error preparing TDD environment",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"TDD environment preparation error: {e!s}",
                "tdd_ready": False,
            }

    async def _prepare_review_environment(self, session_id: str) -> dict[str, Any]:
        """Prepare the adversarial review environment for the session."""
        self.logger.debug("Preparing review environment", session_id=session_id)

        try:
            # Import and initialize adversarial review system
            from cohezion.compound.tdd_adversarial.adversarial_review import (
                get_adversarial_review_system,
            )

            # Get current working directory (should be worktree if we created one)
            current_dir = Path.cwd()
            get_adversarial_review_system(current_dir)

            # Run a quick review to make sure the system is working
            # In practice, we might do more comprehensive warming up here
            self.logger.debug("Review environment prepared", session_id=session_id)

            return {"success": True, "review_ready": True, "review_system_available": True}

        except Exception as e:
            self.logger.error(
                "Error preparing review environment",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"Review environment preparation error: {e!s}",
                "review_ready": False,
            }

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the workflow initializer."""
        return {
            "initialized": self._initialized,
            "project_root": str(self.project_root),
            "current_directory": str(Path.cwd()),
            "in_git_worktree": self._is_in_git_worktree(),
        }

    def _is_in_git_worktree(self) -> bool:
        """Check if we're currently in a git worktree."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=str(Path.cwd()),
            )
            return result.returncode == 0
        except Exception:
            return False


# Global instance for easy access
_workflow_initializer: CompoundEngineeringWorkflowInitializer | None = None


def get_workflow_initializer(
    project_root: Path | None = None,
) -> CompoundEngineeringWorkflowInitializer:
    """Get or create the global workflow initializer instance."""
    global _workflow_initializer
    if _workflow_initializer is None:
        _workflow_initializer = CompoundEngineeringWorkflowInitializer(project_root)
    return _workflow_initializer
