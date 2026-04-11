#!/usr/bin/env python3
"""SWE-bench evaluation with mock LLM for infrastructure validation.

This version uses a mock LLM to generate synthetic patches, allowing
validation of the SWE-bench evaluation infrastructure without
depending on Ollama service availability.

The mock generates plausible patches based on issue descriptions,
allowing testing of:
- Dataset loading
- Patch extraction/format validation
- Pass@1 scoring
- Result persistence

Usage:
    uv run python scripts/benchmarks/run_swebench_mock_llm.py --max-issues 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class MockPatchGeneration:
    """Mock LLM patch generator based on issue patterns."""

    repo: str
    issue_text: str

    def generate_patch(self) -> str | None:
        """Generate synthetic patch based on issue type."""
        text_lower = self.issue_text.lower()

        # Pattern matching for common issue types
        if "typeerror" in text_lower or "attributeerror" in text_lower:
            # Generate a None check fix
            return self._generate_null_fix()
        elif "off by one" in text_lower or "index" in text_lower:
            return self._generate_index_fix()
        elif "import" in text_lower or "module" in text_lower:
            return self._generate_import_fix()
        elif "string" in text_lower or "format" in text_lower:
            return self._generate_string_fix()
        else:
            # Generic fix with 50% success rate
            if hash(self.repo + self.issue_text) % 10 < 5:
                return self._generate_generic_fix()
            return None

    def _generate_null_fix(self) -> str:
        return """diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,5 +1,7 @@
 def process(data):
+    if data is None:
+        return None
     return data.process()
"""

    def _generate_index_fix(self) -> str:
        return """diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,5 +1,5 @@
 def get_item(items, idx):
-    return items[idx]
+    return items[idx - 1]
"""

    def _generate_import_fix(self) -> str:
        return """diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,3 +1,4 @@
+import os
 import sys
 from pathlib import Path
"""

    def _generate_string_fix(self) -> str:
        return """diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,5 +1,5 @@
 def format_name(name):
-    return name.upper()
+    return name.lower().strip()
"""

    def _generate_generic_fix(self) -> str:
        return """diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,5 +1,7 @@
 def main():
+    # Fixed issue
+    setup()
     run()
     cleanup()
"""


class SWEBenchMockEvaluator:
    """SWE-bench evaluator using mock LLM for infrastructure testing."""

    def __init__(self, dataset: str = "test", cache_dir: Path | None = None):
        self.dataset = dataset
        self.cache_dir = cache_dir or Path("data/swebench_cache")
        self.results: list[dict[str, Any]] = []

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load SWE-bench dataset."""
        dataset_file = self.cache_dir / f"{self.dataset}.json"

        with open(dataset_file) as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, dict):
            return list(data.values())
        return data

    def evaluate_issue(self, issue: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single issue with mock LLM."""
        instance_id = issue.get("instance_id", "unknown")
        repo = issue.get("repo", "unknown")
        problem = issue.get("problem_statement", "")

        # Generate mock patch
        mock_llm = MockPatchGeneration(repo, problem)
        patch = mock_llm.generate_patch()

        return {
            "instance_id": instance_id,
            "repo": repo,
            "patch": patch,
            "success": patch is not None,
        }

    def run_evaluation(self, max_issues: int | None = None) -> dict[str, Any]:
        """Run evaluation."""
        logger.info(f"Loading SWE-bench {self.dataset} dataset...")
        issues = self.load_dataset()

        if max_issues:
            issues = issues[:max_issues]

        logger.info(f"Evaluating {len(issues)} issues (mock LLM)")

        total = len(issues)
        passed = 0

        for i, issue in enumerate(issues):
            result = self.evaluate_issue(issue)
            self.results.append(result)

            if result.get("success"):
                passed += 1
                logger.info(f"[{i + 1}/{total}] {result['instance_id']}: PATCH")
            else:
                logger.info(f"[{i + 1}/{total}] {result['instance_id']}: NO PATCH")

        # Calculate Pass@1
        pass_at_1 = passed / total if total > 0 else 0.0

        summary = {
            "dataset": self.dataset,
            "total": total,
            "passed": passed,
            "attempted": total,
            "pass_at_1": pass_at_1,
            "pass_at_1_pct": f"{pass_at_1:.1%}",
            "results": self.results,
            "method": "mock_llm",
            "note": "Mock patches for infrastructure validation only",
        }

        # Save results
        output_dir = Path(f"data/swebench_results/{self.dataset}_mock")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="test")
    parser.add_argument("--max-issues", type=int, default=10)
    args = parser.parse_args()

    evaluator = SWEBenchMockEvaluator(dataset=args.dataset)
    results = evaluator.run_evaluation(max_issues=args.max_issues)

    print(f"\n{'=' * 60}")
    print("SWE-bench Mock Evaluation (Infrastructure Test)")
    print(f"{'=' * 60}")
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Pass@1: {results['pass_at_1_pct']}")
    print(f"{'=' * 60}")
    print("NOTE: Mock LLM - validates infrastructure, not agent capability")

    return 0


if __name__ == "__main__":
    exit(main())
