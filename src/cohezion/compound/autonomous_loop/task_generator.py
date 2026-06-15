"""TaskGenerator — creates autonomous improvement tasks from real issues.

Scans the codebase for:
- Test collection errors (import errors, name collisions)
- Lint failures (ruff)
- Type errors (mypy)
- Long functions that exceed LOC limits
- Missing __init__.py files
- Dead imports

Tasks are prioritized by impact: test fixes > lint > types > refactoring.

Priority is adjusted based on historical loop learnings (loop_learnings.jsonl):
categories that consistently fail in recent runs are deprioritized (+penalty),
so the loop naturally focuses on tasks where local inference succeeds.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path


logger = logging.getLogger(__name__)

# Default location mirrors LoopConfig.results_path parent directory
_DEFAULT_LEARNINGS_PATH = "/tmp/cohezion-autonomous-loop/loop_learnings.jsonl"

# How many recent JSONL entries (loop runs) to consider
_LEARNING_WINDOW = 5

# Priority penalty applied per 10% above the failure threshold
# e.g. 80% failure rate → 3 penalty levels → priority += 3
_FAILURE_THRESHOLD = 0.4  # below this = healthy, no penalty
_MAX_PENALTY = 5


class TaskGenerator:
    """Generate prioritized improvement tasks from real codebase issues.

    Args:
        repo_root: Path to the repository root.
        learnings_path: Path to loop_learnings.jsonl. If None, uses the
            default location under /tmp/cohezion-autonomous-loop/. Pass an
            empty string "" to disable learning-based priority adjustment.
    """

    def __init__(
        self,
        repo_root: str = "/home/mike-anderson/dev/cohezion",
        learnings_path: str | None = None,
    ):
        self.repo_root = Path(repo_root)
        if learnings_path is None:
            self._learnings_path: Path | None = Path(_DEFAULT_LEARNINGS_PATH)
        elif learnings_path == "":
            self._learnings_path = None
        else:
            self._learnings_path = Path(learnings_path)

        self._category_stats: dict[str, dict[str, int]] = {}
        self._load_category_stats()

    def _load_category_stats(self) -> None:
        """Read loop_learnings.jsonl and compute per-category success/failure counts.

        Only considers the last _LEARNING_WINDOW runs so stale history doesn't
        permanently penalize a category that has since been fixed.
        """
        if self._learnings_path is None or not self._learnings_path.exists():
            return

        entries: list[dict] = []
        try:
            for line in self._learnings_path.read_text().splitlines():
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except Exception as exc:
            logger.debug("Could not load loop learnings: %s", exc)
            return

        # Most recent window only
        recent = entries[-_LEARNING_WINDOW:]

        stats: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "successes": 0})
        for entry in recent:
            for task_result in entry.get("results", []):
                cat = task_result.get("category", "")
                if not cat:
                    continue
                stats[cat]["attempts"] += 1
                if task_result.get("success", False):
                    stats[cat]["successes"] += 1

        self._category_stats = dict(stats)
        if self._category_stats:
            summary = {
                cat: f"{d['successes']}/{d['attempts']}" for cat, d in self._category_stats.items()
            }
            logger.info("Loop learnings loaded (last %d runs): %s", len(recent), summary)

    def _priority_penalty(self, category: str) -> int:
        """Return the priority penalty for a category based on its historical failure rate.

        Returns 0 when the category has no history or failure rate is below threshold.
        Returns up to _MAX_PENALTY for consistently failing categories.
        """
        stats = self._category_stats.get(category)
        if not stats or stats["attempts"] == 0:
            return 0

        failure_rate = 1.0 - (stats["successes"] / stats["attempts"])
        if failure_rate <= _FAILURE_THRESHOLD:
            return 0

        # Scale penalty linearly from threshold to 1.0
        # e.g. 0.4 threshold: 0.8 failure rate = (0.8-0.4)/(1.0-0.4) = 0.67 → 3 penalty
        normalized = (failure_rate - _FAILURE_THRESHOLD) / (1.0 - _FAILURE_THRESHOLD)
        return min(_MAX_PENALTY, int(normalized * (_MAX_PENALTY + 1)))

    def generate_all(self) -> list[dict]:
        """Generate all task categories, sorted by priority.

        Priority is adjusted based on recent loop learnings: categories with
        high failure rates are deprioritized so the loop focuses on tasks where
        local inference has demonstrated success.
        """
        tasks = []
        tasks.extend(self._detect_test_collection_errors())
        tasks.extend(self._detect_ruff_issues())
        tasks.extend(self._detect_long_functions())
        tasks.extend(self._detect_missing_init_files())
        tasks.extend(self._detect_dead_imports())

        # Apply learning-based priority adjustment
        for task in tasks:
            penalty = self._priority_penalty(task.get("category", ""))
            if penalty > 0:
                task["priority"] += penalty
                task["_learning_penalty"] = penalty  # visible in backlog for inspection

        # Sort by adjusted priority (0 = highest)
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
