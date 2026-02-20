"""HumanEval evaluation harness for code generation.

Evaluates functional correctness on 164 Python programming problems.
Uses pass@k metric for rigorous evaluation.
"""

import json
import logging
import time
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
        self._dataset: Any = None
        self._journey_tracker = None

    def _get_journey_tracker(self):
        """Get or create journey tracker."""
        if self._journey_tracker is None:
            try:
                from cohezion.eval.journey_integration import BenchmarkJourneyTracker

                self._journey_tracker = BenchmarkJourneyTracker()
            except ImportError:
                logger.warning("Journey tracking not available")
                self._journey_tracker = None
        return self._journey_tracker

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
            self._dataset = [dict(d) for d in ds]  # type: ignore[assignment]
            logger.info(f"Loaded {len(self._dataset)} problems")
            return self._dataset  # type: ignore[return-value]
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

        with open(solutions_path) as f:
            solutions = [json.loads(line) for line in f]

        by_task: dict[str, list[str]] = {}
        for sol in solutions:
            task_id = sol["task_id"]
            if task_id not in by_task:
                by_task[task_id] = []
            by_task[task_id].append(sol.get("completion", ""))

        results = {}
        for task_id, completions in by_task.items():
            task_results = self._evaluate_task(task_id, completions)
            results[task_id] = task_results

        pass_at_k = {}
        for k in k_values:
            pass_at_k[f"pass@{k}"] = self._calculate_pass_at_k(results, k)

        summary = {
            "total_problems": len(by_task),
            "pass_at_k": pass_at_k,
            "per_task_results": results,
        }

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
        dataset = self.load_dataset()
        problem = next(p for p in dataset if p["task_id"] == task_id)
        test = problem["test"]
        entry_point = problem["entry_point"]

        passed = []
        for completion in completions:
            try:
                test_program = completion + "\n" + test + "\n" + f"check({entry_point})"
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
            result = subprocess.run(
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

            if c == 0:
                pass_rate = 0.0
            elif c == n:
                pass_rate = 1.0
            else:
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
            "claude_3_5_sonnet_pass@1": 0.92,
            "gpt_4_pass@1": 0.88,
        }


class OllamaAgent:
    """Simple agent that uses Ollama for code generation."""

    def __init__(
        self,
        model_name: str = "qwen3-coder:30b",
        base_url: str = "http://localhost:11434",
        max_tokens: int = 2048,
    ):
        """Initialize agent.

        Args:
            model_name: Ollama model to use
            base_url: Ollama API base URL
            max_tokens: Maximum completion length
        """
        self.model_name = model_name
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.client = None

    def _get_client(self):
        """Get or create HTTP client."""
        if self.client is None:
            import httpx

            self.client = httpx.Client(timeout=120.0)
        return self.client

    def execute(self, task: str) -> str:
        """Execute code generation task.

        Args:
            task: Task prompt

        Returns:
            Generated code
        """
        client = self._get_client()

        try:
            response = client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": task,
                    "temperature": 0.2,
                    "stream": False,
                    "options": {
                        "num_predict": self.max_tokens,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()["response"]
            return self._extract_code(result)
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return ""

    def _extract_code(self, completion: str) -> str:
        """Extract Python code from completion."""
        import re

        code_block_match = re.search(
            r"```(?:python)?\s*\n(.*?)```", completion, re.DOTALL
        )
        if code_block_match:
            return code_block_match.group(1).strip()

        lines = completion.strip().split("\n")
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                continue
            if stripped and not stripped.startswith("#"):
                code_lines.append(line)

        return "\n".join(code_lines)

    def close(self):
        """Close HTTP client."""
        if self.client:
            self.client.close()


def create_agent_factory(model_name: str):
    """Create agent factory for harness.

    Args:
        model_name: Ollama model to use

    Returns:
        Factory function that creates OllamaAgent instances
    """

    def factory():
        return OllamaAgent(model_name=model_name)

    return factory


def run_benchmark(
    model_name: str | None = None,
    limit: int | None = None,
    num_samples: int = 1,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Run HumanEval benchmark with local Ollama model.

    Args:
        model_name: Ollama model name (auto-detected from guardrails if None)
        limit: Limit number of problems (None = all 164)
        num_samples: Number of samples per problem for pass@k
        temperature: Sampling temperature

    Returns:
        Benchmark results
    """
    if model_name is None:
        from cohezion.simulation.guardrails import get_guardrails

        guardrails = get_guardrails()
        model_name = guardrails.get_local_model(guardrails.default_local_model)

    logger.info(f"Using model: {model_name}")

    harness = HumanEvalHarness()
    dataset = harness.load_dataset()

    if limit:
        dataset = dataset[:limit]

    logger.info(
        f"Running benchmark on {len(dataset)} problems with {num_samples} samples"
    )

    all_solutions = []
    tracker = None

    try:
        from cohezion.eval.journey_integration import BenchmarkJourneyTracker

        tracker = BenchmarkJourneyTracker()
    except ImportError:
        logger.warning("Journey tracking not available")

    for problem in dataset:
        task_id = problem["task_id"]
        prompt = problem["prompt"]
        test = problem["test"]
        entry_point = problem["entry_point"]

        logger.info(f"Processing {task_id}")

        task = f"""Complete the following Python function:

{prompt}

Provide only the implementation, no explanation."""

        passed = False
        best_completion = ""

        for sample_idx in range(num_samples):
            agent = OllamaAgent(model_name=model_name)
            try:
                start_time = time.time()
                completion = agent.execute(task)
                duration = time.time() - start_time

                if completion:
                    test_program = (
                        completion + "\n" + test + "\n" + f"check({entry_point})"
                    )
                    test_passed = harness._execute_test(test_program)

                    if test_passed:
                        passed = True
                        best_completion = completion
                        logger.info(f"  PASS (sample {sample_idx + 1}/{num_samples})")
                        break
                    else:
                        best_completion = completion
            except Exception as e:
                logger.debug(f"Sample {sample_idx} failed: {e}")
            finally:
                agent.close()

        all_solutions.append(
            {
                "task_id": task_id,
                "completion": best_completion,
                "passed": passed,
            }
        )

        if tracker and best_completion:
            try:
                from cohezion.eval.journey_integration import (
                    compute_journey_from_completion,
                )

                journey_metrics = compute_journey_from_completion(best_completion)
                tracker.record_attempt(
                    benchmark="humaneval",
                    task_id=task_id,
                    model=model_name,
                    success=passed,
                    completion=best_completion,
                    **journey_metrics,
                )
            except Exception as e:
                logger.debug(f"Journey recording failed: {e}")

    passed_count = sum(1 for s in all_solutions if s["passed"])
    pass_rate = passed_count / len(all_solutions) if all_solutions else 0

    results = {
        "model": model_name,
        "total": len(all_solutions),
        "passed": passed_count,
        "pass_rate": pass_rate,
        "pass@1": pass_rate,
        "solutions": all_solutions,
    }

    output_dir = Path("data/eval/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"humaneval_{model_name.replace(':', '_')}.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {output_path}")
    logger.info(f"Pass rate: {pass_rate:.1%} ({passed_count}/{len(all_solutions)})")

    return results


def main():
    """CLI for running HumanEval benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Run HumanEval benchmark")
    parser.add_argument("--model", help="Ollama model name")
    parser.add_argument("--limit", type=int, help="Limit problems")
    parser.add_argument("--samples", type=int, default=1, help="Samples per problem")
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    run_benchmark(
        model_name=args.model,
        limit=args.limit,
        num_samples=args.samples,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
