"""
Quality enforcement hooks.

Attribution: Quality enforcement pattern inspired by Pilot
Implementation: Original COHEZION hooks using ruff, basedpyright, pytest
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def post_tool_use_quality_hook(context: Dict[str, Any]) -> None:
    """Run quality checks after tool usage.

    Attribution: Inspired by Pilot's PostToolUse quality enforcement
    Implementation: COHEZION-native using ruff + basedpyright

    Args:
        context: Tool execution context (may include modified_files)
    """
    modified_files = context.get("modified_files", [])
    if not modified_files:
        logger.debug("No modified files, skipping quality checks")
        return

    # Filter for Python files
    py_files = [f for f in modified_files if f.endswith(".py")]
    if not py_files:
        return

    logger.info(f"Running quality checks on {len(py_files)} Python files")

    # Run ruff format
    try:
        subprocess.run(
            ["ruff", "format", *py_files],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug("ruff format completed")
    except subprocess.CalledProcessError as e:
        logger.warning(f"ruff format failed: {e.stderr}")

    # Run ruff linting
    try:
        subprocess.run(
            ["ruff", "check", "--fix", *py_files],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug("ruff check completed")
    except subprocess.CalledProcessError as e:
        logger.warning(f"ruff check failed: {e.stderr}")

    # Run basedpyright (non-blocking)
    try:
        result = subprocess.run(
            ["basedpyright", *py_files],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"basedpyright found issues:\n{result.stdout}")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.warning(f"basedpyright check failed: {e}")


def session_end_test_hook(context: Dict[str, Any]) -> None:
    """Run tests at session end.

    Attribution: Inspired by Pilot's session lifecycle hooks
    Implementation: COHEZION pytest integration
    """
    logger.info("Running test suite at session end")

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            logger.info("All tests passed at session end")
        else:
            logger.warning(
                f"Tests failed at session end:\n{result.stdout}\n{result.stderr}"
            )

    except subprocess.TimeoutExpired:
        logger.error("Test suite timed out (>120s)")
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")


def coherence_drop_hook(context: Dict[str, Any]) -> None:
    """Handle HIHO coherence violations.

    COHEZION-specific hook for maintaining 0.5 coherence stability.
    """
    coherence = context.get("coherence", 1.0)
    threshold = context.get("threshold", 0.5)

    if coherence < threshold:
        logger.warning(
            f"HIHO coherence violation: {coherence:.2f} < {threshold:.2f}"
        )

        # Trigger recovery actions
        # TODO: Integrate with DegradationDetector
        # TODO: Record in JourneyTracker
        # TODO: Escalate to SkillRefiner if persistent


def vault_sync_hook(context: Dict[str, Any]) -> None:
    """Sync session state to vault.

    COHEZION-specific hook for persistent knowledge management.
    """
    session_id = context.get("session_id", "unknown")
    state = context.get("state", {})

    logger.info(f"Syncing session {session_id} to vault")

    # TODO: Integrate with vault MCP server
    # TODO: Store journey checkpoints
    # TODO: Persist skill refinements
