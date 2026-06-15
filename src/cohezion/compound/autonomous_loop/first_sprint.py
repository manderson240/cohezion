"""First sprint: Test Stabilization.

Fixes the 3 known test collection errors that block 9291 tests:
1. test_unified_harness.py name collision (tests/agent/ vs tests/agents/)
2. test_new_transforms.py missing import (arc.transforms.grid_symmetry_reflect)
3. test_frontier_oracle.py import error

Each fix is a self-contained task with verification.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class TestStabilizationSprint:
    """Sprint that fixes test collection errors to unblock the full test suite."""

    def __init__(self, repo_root: str = "/home/mike-anderson/dev/cohezion"):
        self.repo_root = Path(repo_root)

    def generate_tasks(self) -> list[dict]:
        """Generate test stabilization tasks."""
        tasks = [
            self._task_name_collision(),
            self._task_missing_arc_import(),
            self._task_frontier_oracle(),
        ]
        # Add follow-up tasks for any remaining issues
        tasks.extend(self._detect_additional_test_issues())
        return tasks

    def _task_name_collision(self) -> dict:
        """Fix test_unified_harness.py appearing in both tests/agent/ and tests/agents/."""
        agent_file = self.repo_root / "tests" / "agent" / "test_unified_harness.py"
        agents_file = self.repo_root / "tests" / "agents" / "test_unified_harness.py"

        if not agent_file.exists() and not agents_file.exists():
            return {
                "id": "test_fix_unified_harness_collision",
                "description": "test_unified_harness.py not found in expected locations",
                "priority": 0,
                "category": "test_fix",
                "verification": "uv run pytest tests/ --collect-only -q 2>&1 | grep unified_harness",
                "estimated_tokens": 1000,
                "skip": True,
                "skip_reason": "Files not found",
            }

        # Determine which file is the duplicate
        # The error says tests/agents/test_unified_harness.py conflicts with tests/agent/test_unified_harness.py
        # We need to rename one of them
        return {
            "id": "test_fix_unified_harness_collision",
            "description": (
                "Fix pytest name collision: test_unified_harness.py exists in both "
                "tests/agent/ and tests/agents/ — pytest collects both as the same module name. "
                "Rename one of the files (e.g., tests/agents/test_unified_harness.py → "
                "tests/agents/test_unified_harness_agents.py) so they have unique module names."
            ),
            "priority": 0,
            "category": "test_fix",
            "verification": "uv run pytest tests/ --collect-only -q 2>&1 | grep -i 'unified_harness' || echo 'no collision'",
            "estimated_tokens": 1500,
        }

    def _task_missing_arc_import(self) -> dict:
        """Fix missing grid_symmetry_reflect import in arc.transforms."""
        transforms_file = self.repo_root / "src" / "cohezion" / "arc" / "transforms.py"

        if not transforms_file.exists():
            return {
                "id": "test_fix_arc_transforms",
                "description": "src/cohezion/arc/transforms.py not found",
                "priority": 0,
                "category": "test_fix",
                "verification": "uv run pytest tests/arc/test_new_transforms.py -q --tb=short",
                "estimated_tokens": 1000,
                "skip": True,
                "skip_reason": "transforms.py not found",
            }

        # Check if the function exists
        try:
            content = transforms_file.read_text()
            has_function = "def grid_symmetry_reflect" in content
        except OSError:
            has_function = False

        if has_function:
            # The function exists but isn't exported — check __init__.py
            init_file = self.repo_root / "src" / "cohezion" / "arc" / "__init__.py"
            try:
                init_content = init_file.read_text() if init_file.exists() else ""
            except OSError:
                init_content = ""
            if "grid_symmetry_reflect" not in init_content:
                return {
                    "id": "test_fix_arc_transforms_export",
                    "description": (
                        "arc.transforms.grid_symmetry_reflect exists but is not exported from "
                        "src/cohezion/arc/__init__.py. The test imports it as "
                        "'from cohezion.arc.transforms import grid_symmetry_reflect' which should "
                        "work if the function exists in transforms.py. Verify the import path is correct."
                    ),
                    "priority": 0,
                    "category": "test_fix",
                    "verification": "uv run python -c 'from cohezion.arc.transforms import grid_symmetry_reflect; print(\"OK\")'",
                    "estimated_tokens": 1500,
                }

        return {
            "id": "test_fix_arc_transforms_missing",
            "description": (
                "arc.transforms.grid_symmetry_reflect is missing. Either: "
                "1) Add the function to src/cohezion/arc/transforms.py, or "
                "2) Fix the test import to use the correct function name. "
                "Check what functions actually exist in transforms.py."
            ),
            "priority": 0,
            "category": "test_fix",
            "verification": "uv run pytest tests/arc/test_new_transforms.py -q --tb=short",
            "estimated_tokens": 2000,
        }

    def _task_frontier_oracle(self) -> dict:
        """Fix test_frontier_oracle.py import error."""
        test_file = self.repo_root / "tests" / "inference" / "test_frontier_oracle.py"

        if not test_file.exists():
            return {
                "id": "test_fix_frontier_oracle",
                "description": "tests/inference/test_frontier_oracle.py not found",
                "priority": 0,
                "category": "test_fix",
                "verification": "uv run pytest tests/inference/test_frontier_oracle.py -q --tb=short",
                "estimated_tokens": 1000,
                "skip": True,
                "skip_reason": "Test file not found",
            }

        # Read the test file to find the import error
        try:
            content = test_file.read_text()
        except OSError:
            content = ""

        # Extract the import that's failing
        import_match = None
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("from ") or stripped.startswith("import "):
                import_match = stripped
                break

        if import_match:
            return {
                "id": "test_fix_frontier_oracle",
                "description": (
                    f"Fix import error in tests/inference/test_frontier_oracle.py. "
                    f"Failing import: {import_match}. "
                    f"Either fix the import path or add the missing module."
                ),
                "priority": 0,
                "category": "test_fix",
                "verification": "uv run pytest tests/inference/test_frontier_oracle.py -q --tb=short",
                "estimated_tokens": 2000,
            }

        return {
            "id": "test_fix_frontier_oracle",
            "description": (
                "Fix test collection error in tests/inference/test_frontier_oracle.py. "
                "Run the test with --tb=long to see the actual error."
            ),
            "priority": 0,
            "category": "test_fix",
            "verification": "uv run pytest tests/inference/test_frontier_oracle.py -q --tb=short",
            "estimated_tokens": 2000,
        }

    def _detect_additional_test_issues(self) -> list[dict]:
        """Run a quick collect-only to find any other test issues."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            timeout=60,
        )

        tasks = []
        # Look for skipped tests (potential issues)
        skip_match = result.stderr.split("skipped")
        if len(skip_match) > 1:
            count_str = skip_match[1].split()[0] if skip_match[1].split() else "0"
            if int(count_str) > 0:
                tasks.append(
                    {
                        "id": "test_review_skipped",
                        "description": f"Review {count_str} skipped tests — determine if they should be fixed or marked as xfail",
                        "priority": 5,
                        "category": "test_fix",
                        "verification": "uv run pytest tests/ --collect-only -q 2>&1 | grep skipped",
                        "estimated_tokens": 1500,
                    }
                )

        return tasks

    def save_tasks(self, path: str) -> None:
        """Save sprint tasks to JSON."""
        tasks = self.generate_tasks()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(tasks, indent=2))
        logger.info("Saved %d test stabilization tasks to %s", len(tasks), path)
