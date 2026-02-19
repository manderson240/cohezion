"""SWE-bench evaluation harness for Cohezion agentic systems.

Wraps the official SWE-bench harness to evaluate code fixing capabilities.
Supports SWE-bench Lite (recommended for testing) and full SWE-bench.
"""

import json
import logging
from pathlib import Path
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class SWEBenchHarness:
    """Harness for running SWE-bench evaluations.

    Evaluates agentic capabilities on real-world GitHub issues.
    Each instance is a bug report with test suite verification.

    Attributes:
        dataset_name: SWE-bench dataset (Lite, Verified, or full)
        predictions_path: Path to generated predictions
        max_workers: Parallel evaluation workers
        results_dir: Directory for evaluation results
    """

    DATASETS: ClassVar[dict[str, str]] = {
        "lite": "princeton-nlp/SWE-bench_Lite",
        "verified": "princeton-nlp/SWE-bench_Verified",
        "full": "princeton-nlp/SWE-bench",
        "multimodal": "princeton-nlp/SWE-bench_Multimodal",
    }

    def __init__(
        self,
        dataset_name: str = "lite",
        predictions_path: str | None = None,
        max_workers: int = 8,
        results_dir: str = "data/eval/swebench",
    ):
        """Initialize SWE-bench harness.

        Args:
            dataset_name: One of 'lite', 'verified', 'full', 'multimodal'
            predictions_path: Path to predictions JSONL file
            max_workers: Number of parallel evaluation workers
            results_dir: Directory for results
        """
        if dataset_name not in self.DATASETS:
            raise ValueError(
                f"Unknown dataset: {dataset_name}. "
                f"Use one of: {list(self.DATASETS.keys())}"
            )

        self.dataset_name = dataset_name
        self.dataset_path = self.DATASETS[dataset_name]
        self.predictions_path = (
            predictions_path or f"data/eval/swebench/predictions_{dataset_name}.jsonl"
        )
        self.max_workers = max_workers
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._dataset: list[dict[str, Any]] | None = None

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load SWE-bench dataset.

        Returns:
            List of instances with bug reports and test specs
        """
        if self._dataset is not None:
            return self._dataset

        try:
            from datasets import load_dataset

            logger.info(f"Loading SWE-bench dataset: {self.dataset_path}")
            ds = load_dataset(self.dataset_path, split="test")
            self._dataset = list(ds)
            logger.info(f"Loaded {len(self._dataset)} instances")
            return self._dataset
        except ImportError:
            logger.error("datasets library not installed. Run: pip install datasets")
            raise
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise

    def generate_predictions(
        self,
        model_name: str,
        agent_factory: Any,
        limit: int | None = None,
    ) -> str:
        """Generate predictions using Cohezion agent.

        Args:
            model_name: Name of the model/agent
            agent_factory: Factory function to create agent
            limit: Limit number of instances (for testing)

        Returns:
            Path to generated predictions file
        """
        dataset = self.load_dataset()
        if limit:
            dataset = dataset[:limit]

        predictions = []

        for instance in dataset:
            instance_id = instance["instance_id"]

            logger.info(f"Processing instance: {instance_id}")

            try:
                # Create agent for this instance
                agent = agent_factory()

                # Generate patch
                patch = self._generate_patch(agent, instance)

                prediction = {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "model_patch": patch,
                }
                predictions.append(prediction)

            except Exception as e:
                logger.error(f"Failed to process {instance_id}: {e}")
                # Add empty prediction for failed instances
                predictions.append(
                    {
                        "instance_id": instance_id,
                        "model_name_or_path": model_name,
                        "model_patch": "",
                    }
                )

        # Save predictions
        pred_path = Path(self.predictions_path)
        pred_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pred_path, "w") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")

        logger.info(f"Saved {len(predictions)} predictions to {pred_path}")
        return str(pred_path)

    def _generate_patch(
        self,
        agent: Any,
        instance: dict[str, Any],
    ) -> str:
        """Generate patch for a single instance.

        Args:
            agent: Cohezion agent instance
            instance: SWE-bench instance with problem statement

        Returns:
            Generated git patch
        """
        problem = instance["problem_statement"]
        repo = instance["repo"]
        base_commit = instance["base_commit"]

        # Create task for agent
        task = f"""Fix the bug described below in the {repo} repository.

Repository: {repo}
Base Commit: {base_commit}

Problem:
{problem}

Generate a git patch that resolves this issue. The patch should:
1. Fix the described bug
2. Pass the repository's test suite
3. Follow the repository's coding style

Return only the git patch (diff), no explanation."""

        # Execute agent
        result = agent.execute(task)

        # Extract patch from result
        patch = self._extract_patch(result)

        return patch

    def _extract_patch(self, result: dict[str, Any]) -> str:
        """Extract git patch from agent result."""
        # Try different result formats
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # Try common keys
            for key in ["patch", "diff", "code", "output", "result"]:
                if key in result:
                    return str(result[key])

            # Try to find diff markers in output
            output = result.get("output", "")
            if "diff --git" in output:
                # Extract diff section
                start = output.find("diff --git")
                return output[start:]

        return ""

    def evaluate(
        self,
        predictions_path: str | None = None,
        timeout: int = 1800,
    ) -> dict[str, Any]:
        """Run SWE-bench evaluation.

        Args:
            predictions_path: Path to predictions (defaults to self.predictions_path)
            timeout: Timeout per instance in seconds

        Returns:
            Evaluation results with resolution rate
        """
        pred_path = predictions_path or self.predictions_path

        logger.info(f"Running SWE-bench evaluation on {pred_path}")

        try:
            # Try to use official SWE-bench harness
            import subprocess

            cmd = [
                "python",
                "-m",
                "swebench.harness.run_evaluation",
                "--dataset_name",
                self.dataset_path,
                "--predictions_path",
                pred_path,
                "--max_workers",
                str(self.max_workers),
                "--timeout",
                str(timeout),
            ]

            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.results_dir),
            )

            logger.info(f"Evaluation completed with return code: {result.returncode}")

            # Parse results
            results = self._parse_results(result.stdout)

            # Save results
            results_path = self.results_dir / f"results_{self.dataset_name}.json"
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(f"Results saved to {results_path}")
            return results

        except FileNotFoundError:
            logger.warning("SWE-bench not installed. Using mock evaluation.")
            return self._mock_evaluate(pred_path)
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

    def _parse_results(self, stdout: str) -> dict[str, Any]:
        """Parse SWE-bench evaluation output."""
        # SWE-bench outputs results in a specific format
        # This is a simplified parser
        lines = stdout.split("\n")

        results = {
            "resolution_rate": 0.0,
            "resolved": [],
            "failed": [],
            "total": 0,
        }

        for line in lines:
            if "Resolution rate:" in line:
                try:
                    rate = float(line.split(":")[1].strip().replace("%", ""))
                    results["resolution_rate"] = rate / 100
                except (ValueError, IndexError):
                    pass

        return results

    def _mock_evaluate(self, predictions_path: str) -> dict[str, Any]:
        """Mock evaluation when SWE-bench not installed."""
        logger.warning("Running mock evaluation - install swebench for real results")

        # Count predictions
        with open(predictions_path) as f:
            predictions = [json.loads(line) for line in f]

        # Mock results (assume 10% resolution for testing)
        resolved = [p["instance_id"] for p in predictions[: len(predictions) // 10]]

        results = {
            "resolution_rate": len(resolved) / len(predictions),
            "resolved": resolved,
            "failed": [
                p["instance_id"]
                for p in predictions
                if p["instance_id"] not in resolved
            ],
            "total": len(predictions),
            "mock": True,
        }

        return results

    def get_summary(self) -> dict[str, Any]:
        """Get summary of benchmark capabilities."""
        dataset = self.load_dataset()

        repos = {instance["repo"] for instance in dataset}

        return {
            "dataset": self.dataset_name,
            "instances": len(dataset),
            "repositories": len(repos),
            "repo_list": sorted(repos),
        }
