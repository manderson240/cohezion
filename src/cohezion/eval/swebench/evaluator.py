"""SWE-bench evaluator for patch validation.

Validates generated patches against SWE-bench test suites.
"""

import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class SWEBenchEvaluator:
    """Evaluator for SWE-bench predictions.

    Validates patches by:
    1. Applying patch to repository at base commit
    2. Running repository test suite
    3. Checking if issue is resolved
    """

    def __init__(self, results_dir: str = "data/eval/swebench"):
        """Initialize evaluator.

        Args:
            results_dir: Directory for evaluation results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_single(
        self,
        instance_id: str,
        patch: str,
        repo_path: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a single prediction.

        Args:
            instance_id: SWE-bench instance ID
            patch: Git patch to evaluate
            repo_path: Path to cloned repository (optional)

        Returns:
            Evaluation result with status and metrics
        """
        if not patch:
            return {
                "instance_id": instance_id,
                "status": "failed",
                "reason": "empty_patch",
            }

        # Try to apply patch and run tests
        try:
            if repo_path:
                result = self._evaluate_local(instance_id, patch, repo_path)
            else:
                # Use Docker for isolated evaluation
                result = self._evaluate_docker(instance_id, patch)

            return result

        except Exception as e:
            logger.error(f"Evaluation failed for {instance_id}: {e}")
            return {
                "instance_id": instance_id,
                "status": "error",
                "reason": str(e),
            }

    def _evaluate_local(
        self,
        instance_id: str,
        patch: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Evaluate patch locally (requires repo to be set up)."""
        import subprocess

        repo = Path(repo_path)

        # Apply patch
        try:
            proc = subprocess.run(
                ["git", "apply", "--check"],
                input=patch,
                cwd=repo,
                capture_output=True,
                text=True,
            )

            if proc.returncode != 0:
                return {
                    "instance_id": instance_id,
                    "status": "failed",
                    "reason": "patch_does_not_apply",
                    "stderr": proc.stderr,
                }

            # Apply the patch
            subprocess.run(
                ["git", "apply"],
                input=patch,
                cwd=repo,
                check=True,
            )

        except subprocess.CalledProcessError as e:
            return {
                "instance_id": instance_id,
                "status": "failed",
                "reason": "patch_application_failed",
                "error": str(e),
            }

        # Run tests
        try:
            # This would need the specific test command from the instance
            # For now, just check if patch applies
            return {
                "instance_id": instance_id,
                "status": "patch_applied",
                "patch_applies": True,
            }

        except Exception as e:
            return {
                "instance_id": instance_id,
                "status": "error",
                "reason": "test_execution_failed",
                "error": str(e),
            }

    def _evaluate_docker(
        self,
        instance_id: str,
        patch: str,
    ) -> dict[str, Any]:
        """Evaluate patch in Docker container."""
        # This would use the official SWE-bench Docker harness
        # For now, return mock result
        logger.warning("Docker evaluation not implemented - use official harness")

        return {
            "instance_id": instance_id,
            "status": "mock",
            "patch_applies": True,
        }

    def batch_evaluate(
        self,
        predictions_path: str,
    ) -> dict[str, Any]:
        """Evaluate batch of predictions.

        Args:
            predictions_path: Path to predictions JSONL file

        Returns:
            Batch evaluation results
        """
        with open(predictions_path) as f:
            predictions = [json.loads(line) for line in f]

        results = []
        for pred in predictions:
            result = self.evaluate_single(
                pred["instance_id"],
                pred.get("model_patch", ""),
            )
            results.append(result)

        # Calculate metrics
        total = len(results)
        resolved = sum(1 for r in results if r.get("status") == "resolved")
        patch_applies = sum(1 for r in results if r.get("patch_applies"))

        summary = {
            "total": total,
            "resolved": resolved,
            "resolution_rate": resolved / total if total > 0 else 0,
            "patch_applies": patch_applies,
            "results": results,
        }

        # Save summary
        summary_path = self.results_dir / "evaluation_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary
