"""TaskGenerator — creates autonomous improvement tasks from real issues.

Scans the codebase for:
- Test collection errors (import errors, name collisions)
- Lint failures (ruff)
- Type errors (mypy)
- Long functions that exceed LOC limits
- Missing __init__.py files
- Dead imports

Tasks are prioritized by impact: test fixes > lint > types > refactoring.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class TaskGenerator:
    """Generate prioritized improvement tasks from real codebase issues."""

    def __init__(self, repo_root: str = "/home/mike-anderson/dev/cohezion"):
        self.repo_root = Path(repo_root)

    def generate_all(self) -> list[dict]:
        """Generate all task categories, sorted by priority."""
        tasks = []
        tasks.extend(self._detect_test_collection_errors())
        tasks.extend(self._detect_ruff_issues())
        tasks.extend(self._detect_long_functions())
        tasks.extend(self._detect_missing_init_files())
        tasks.extend(self._detect_dead_imports())
        # Sort by priority (0 = highest)
        tasks.sort(key=lambda t: t["priority"])
        return tasks

    def save_backlog(self, tasks: list[dict], path: str) -> None:
        """Save task backlog to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(tasks, indent=2))
        logger.info("Saved %d tasks to %s", len(tasks), path)

    def load_backlog(self, path: str) -> list[dict]:
        """Load task backlog from JSON file."""
        return json.loads(Path(path).read_text())

    # ── Test collection errors ───────────────────────────────────────────────

    def _detect_test_collection_errors(self) -> list[dict]:
        """Find test files that fail to collect (import errors, name collisions)."""
        tasks = []
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            timeout=60,
        )
        # Parse ERROR lines (pytest outputs to stdout in -q mode)
        error_pattern = re.compile(r"^ERROR\s+(tests/.+\.py)$", re.MULTILINE)
        errors = error_pattern.findall(result.stdout)
        if not errors:
            errors = error_pattern.findall(result.stderr)

        if not errors:
            logger.info("No test collection errors found")
            return tasks

        for error_file in errors:
            full_path = self.repo_root / error_file
            if not full_path.exists():
                continue

            # Extract the actual error from stderr
            error_text = self._extract_error_from_stderr(result.stderr, error_file)

            # Generate task
            task_id = f"test_fix_{Path(error_file).stem}"
            tasks.append(
                {
                    "id": task_id,
                    "description": self._describe_test_error(error_file, error_text),
                    "priority": 0,  # Highest priority — unblocks many tests
                    "category": "test_fix",
                    "verification": f"uv run pytest {error_file} -q --tb=short",
                    "estimated_tokens": 2000,
                    "error_details": error_text[:500],
                }
            )

        logger.info("Found %d test collection errors", len(errors))
        return tasks

    def _extract_error_from_stderr(self, stderr: str, test_file: str) -> str:
        """Extract the actual error message for a specific test file."""
        lines = stderr.split("\n")
        # Find the block for this file
        for i, line in enumerate(lines):
            if test_file in line and "ERROR" in line:
                # Grab the next 20 lines for context
                return "\n".join(lines[i : i + 20])
        return "Unknown collection error"

    def _describe_test_error(self, test_file: str, error_text: str) -> str:
        """Generate a human-readable task description from raw error."""
        # Try to identify the specific error type
        if "ImportError" in error_text or "cannot import" in error_text:
            match = re.search(r"cannot import name '(\w+)' from '(\w+\.?[\w]*)'", error_text)
            if match:
                name, module = match.groups()
                return (
                    f"Fix import error in {test_file}: cannot import '{name}' from '{module}'. "
                    f"The symbol either doesn't exist or needs to be exported. "
                    f"Check if the source module exports it or if the test import is stale."
                )
        if "module" in error_text.lower() and "same" in error_text.lower():
            return (
                f"Fix test name collision in {test_file}: "
                f"pytest is collecting two test files with the same module name. "
                f"Rename one of the test files or use unique module basenames."
            )
        if "SyntaxError" in error_text:
            match = re.search(r"SyntaxError.*?line (\d+)", error_text)
            line = match.group(1) if match else "unknown"
            return f"Fix syntax error in {test_file} at line {line}."
        return f"Fix test collection error in {test_file}. Error: {error_text[:200]}"

    # ── Lint issues ──────────────────────────────────────────────────────────

    def _detect_ruff_issues(self) -> list[dict]:
        """Find ruff lint failures."""
        tasks = []
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "tests/", "--output-format", "json"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            timeout=60,
        )
        if result.returncode != 0:
            try:
                issues = json.loads(result.stdout)
            except json.JSONDecodeError:
                return tasks

            # Group by file
            by_file: dict[str, list[dict]] = {}
            for issue in issues:
                f = issue.get("filename", "")
                by_file.setdefault(f, []).append(issue)

            for filepath, file_issues in list(by_file.items())[:10]:  # top 10 files
                codes = [i.get("code", "?") for i in file_issues]
                task_id = f"lint_{Path(filepath).stem}"
                tasks.append(
                    {
                        "id": task_id,
                        "description": (
                            f"Fix {len(file_issues)} ruff lint issues in {filepath}: "
                            f"{', '.join(codes[:5])}"
                        ),
                        "priority": 2,
                        "category": "lint_fix",
                        "verification": f"uv run ruff check {filepath}",
                        "estimated_tokens": 1500,
                    }
                )

        return tasks

    # ── Long functions ───────────────────────────────────────────────────────

    def _detect_long_functions(self) -> list[dict]:
        """Find functions exceeding LOC limits."""
        tasks = []
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "--select", "C901", "--output-format", "text"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            timeout=60,
        )
        if result.returncode != 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                match = re.search(r"(\S+):\d+:\d+.*function.*is too complex", line)
                if match:
                    filepath = match.group(1)
                    tasks.append(
                        {
                            "id": f"refactor_{Path(filepath).stem}",
                            "description": f"Reduce cyclomatic complexity in {filepath} (C901)",
                            "priority": 4,
                            "category": "refactor",
                            "verification": f"uv run ruff check {filepath} --select C901",
                            "estimated_tokens": 3000,
                        }
                    )

        return tasks

    # ── Missing __init__.py ──────────────────────────────────────────────────

    def _detect_missing_init_files(self) -> list[dict]:
        """Find src/ directories missing __init__.py."""
        tasks = []
        src_dir = self.repo_root / "src" / "cohezion"
        if not src_dir.is_dir():
            return tasks

        for root, _dirs, files in list(os.walk(str(src_dir)))[:50]:
            rel = Path(root).relative_to(self.repo_root)
            if "__pycache__" in str(rel) or ".git" in str(rel):
                continue
            if "__init__.py" not in files:
                # Check if there are Python files that need importing
                py_files = [f for f in files if f.endswith(".py")]
                if py_files:
                    tasks.append(
                        {
                            "id": f"init_{str(rel).replace('/', '_')}",
                            "description": f"Add __init__.py to {rel}/ (contains {len(py_files)} Python modules)",
                            "priority": 5,
                            "category": "refactor",
                            "verification": f'python -c \'import importlib.util; print(importlib.util.spec_from_file_location("mod", "{rel}/__init__.py"))\'',
                            "estimated_tokens": 500,
                        }
                    )

        return tasks

    # ── Dead imports ─────────────────────────────────────────────────────────

    def _detect_dead_imports(self) -> list[dict]:
        """Find F401 (imported but unused) issues via ruff."""
        tasks = []
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "--select", "F401", "--output-format", "json"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            timeout=60,
        )
        if result.returncode != 0:
            try:
                issues = json.loads(result.stdout)
            except json.JSONDecodeError:
                return tasks

            by_file: dict[str, list[dict]] = {}
            for issue in issues:
                f = issue.get("filename", "")
                by_file.setdefault(f, []).append(issue)

            for filepath, file_issues in list(by_file.items())[:5]:
                task_id = f"dead_import_{Path(filepath).stem}"
                tasks.append(
                    {
                        "id": task_id,
                        "description": (f"Remove {len(file_issues)} unused imports in {filepath}"),
                        "priority": 3,
                        "category": "lint_fix",
                        "verification": f"uv run ruff check {filepath} --select F401",
                        "estimated_tokens": 1000,
                    }
                )

        return tasks
