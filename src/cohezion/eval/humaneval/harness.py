"""HumanEval evaluation harness for code generation.

Evaluates functional correctness on 164 Python programming problems.
Uses pass@k metric for rigorous evaluation.
"""

import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class HumanEvalHarness:
    """Harness for HumanEval code generation benchmark.

    Evaluates functional correctness on 164 Python problems.
    Key metric: pass@k (functional test pass rate at k samples)
    """

    def __init__(
        self,
        dataset_name: str = "openai_humaneval",
        results_dir: str = "data/eval/humaneval",
    ):
        """Initialize HumanEval harness.

        Args:
            dataset_name: Dataset name (usually openai_humaneval)
            results_dir: Directory for results
        """
        self.dataset_name = dataset_name
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._dataset: list[dict[str, Any]] | None = None

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load HumanEval dataset.

        Returns:
            List of 164 programming problems
        """
        if self._dataset is not None:
            return self._dataset

        try:
            from datasets import load_dataset

            logger.info("Loading HumanEval dataset")
            ds = load_dataset(self.dataset_name, split="test")
            self._dataset = list(ds)
            logger.info(f"Loaded {len(self._dataset)} problems")
            return self._dataset
        except ImportError:
            logger.error("datasets library not installed")
            raise

    def generate_solutions(
        self,
        model_name: str,
        agent_factory: Any,
        num_samples: int = 1,
        temperature: float = 0.2,
    ) -> str:
        """Generate solutions for all problems.

        Args:
            model_name: Model identifier
            agent_factory: Factory to create code generation agent
            num_samples: Number of samples per problem (for pass@k)
            temperature: Sampling temperature

        Returns:
            Path to generated solutions file
        """
        dataset = self.load_dataset()

        all_solutions = []

        for problem in dataset:
            task_id = problem["task_id"]
            prompt = problem["prompt"]

            logger.info(f"Generating solutions for {task_id}")

            # Generate multiple samples for pass@k
            samples = []
            for i in range(num_samples):
                try:
                    agent = agent_factory()
                    solution = self._generate_single(agent, prompt, temperature)
                    samples.append(
                        {
                            "task_id": task_id,
                            "completion": solution,
                            "sample_index": i,
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to generate sample {i} for {task_id}: {e}")
                    samples.append(
                        {
                            "task_id": task_id,
                            "completion": "",
                            "sample_index": i,
                        }
                    )

            all_solutions.extend(samples)

        # Save solutions
        solutions_path = self.results_dir / f"{model_name}_solutions.jsonl"
        with open(solutions_path, "w") as f:
            for sol in all_solutions:
                f.write(json.dumps(sol) + "\n")

        return str(solutions_path)

    def _generate_single(
        self,
        agent: Any,
        prompt: str,
        temperature: float,
    ) -> str:
        """Generate single solution."""
        task = f"""Complete the following Python function:

{prompt}

Provide only the implementation, no explanation."""

        result = agent.execute(task)

        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            return result.get("completion", result.get("code", ""))

        return ""

    def evaluate(
        self,
        solutions_path: str,
        k_values: list[int] | None = None,
    ) -> dict[str, Any]:
        """Evaluate solutions using pass@k metric.

        Args:
            solutions_path: Path to solutions JSONL
            k_values: List of k values for pass@k

        Returns:
            Evaluation results with pass@k scores
        """
        k_values = k_values or [1, 10, 100]
        logger.info(f"Evaluating {solutions_path}")

        # Load solutions
        with open(solutions_path) as f:
            solutions = [json.loads(line) for line in f]

        # Group by task
        by_task: dict[str, list[str]] = {}
        for sol in solutions:
            task_id = sol["task_id"]
            if task_id not in by_task:
                by_task[task_id] = []
            by_task[task_id].append(sol.get("completion", ""))

        # Evaluate each task
        results = {}
        for task_id, completions in by_task.items():
            task_results = self._evaluate_task(task_id, completions)
            results[task_id] = task_results

        # Calculate pass@k
        pass_at_k = {}
        for k in k_values:
            pass_at_k[f"pass@{k}"] = self._calculate_pass_at_k(results, k)

        summary = {
            "total_problems": len(by_task),
            "pass_at_k": pass_at_k,
            "per_task_results": results,
        }

        # Save results
        results_path = self.results_dir / "evaluation_results.json"
        with open(results_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results: {pass_at_k}")
        return summary

    def _evaluate_task(
        self,
        task_id: str,
        completions: list[str],
    ) -> dict[str, Any]:
        """Evaluate all completions for a task."""
        # Get test cases
        dataset = self.load_dataset()
        problem = next(p for p in dataset if p["task_id"] == task_id)
        test = problem["test"]
        entry_point = problem["entry_point"]

        # Test each completion
        passed = []
        for completion in completions:
            try:
                # Create test program
                test_program = completion + "\n" + test + "\n" + f"check({entry_point})"

                # Execute safely
                result = self._execute_test(test_program)
                passed.append(result)
            except Exception as e:
                logger.debug(f"Test failed for {task_id}: {e}")
                passed.append(False)

        return {
            "task_id": task_id,
            "total": len(completions),
            "passed": sum(passed),
            "pass_rate": sum(passed) / len(completions) if completions else 0,
            "individual_results": passed,
        }

    def _execute_test(self, test_program: str) -> bool:
        """Execute test program safely."""
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_program)
            temp_path = f.name

        try:
            result = subprocess.run(  # noqa: S603
                ["python", temp_path],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _calculate_pass_at_k(
        self,
        results: dict[str, Any],
        k: int,
    ) -> float:
        """Calculate pass@k across all tasks."""
        import math

        total_pass = 0
        for task_results in results.values():
            n = task_results["total"]
            c = task_results["passed"]

            if n < k:
                continue

            # pass@k = 1 - C(n-c, k) / C(n, k)
            if c == 0:
                pass_rate = 0.0
            elif c == n:
                pass_rate = 1.0
            else:
                # Approximate using log factorial
                log_c_nk = math.log(math.comb(n - c, k)) - math.log(math.comb(n, k))
                pass_rate = 1.0 - math.exp(log_c_nk)

            total_pass += pass_rate

        return total_pass / len(results) if results else 0.0

    def get_baseline(self) -> dict[str, float]:
        """Get HumanEval baseline scores from literature."""
        return {
            "codex_12b_pass@1": 0.288,
            "codex_12b_pass@10": 0.462,
            "codex_12b_pass@100": 0.728,
            "claude_3_5_sonnet_pass@1": 0.92,  # Estimated
            "gpt_4_pass@1": 0.88,  # Estimated
        }
