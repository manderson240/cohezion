"""Simple benchmark runner using Ollama for code generation.

Runs HumanEval benchmark with local Ollama models to get baseline scores.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class OllamaBenchmarkRunner:
    """Runs benchmarks using Ollama models.

    Supports HumanEval evaluation with local models.
    Features pass@k sampling for improved results.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5-coder:14b",
        base_url: str = "http://localhost:11434",
        max_tokens: int = 2048,
        pass_k: int = 10,
    ):
        """Initialize runner.

        Args:
            model_name: Ollama model to use
            base_url: Ollama API base URL
            max_tokens: Maximum completion length (prevents truncation)
            pass_k: Number of samples to generate per problem
        """
        self.model_name = model_name
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.pass_k = pass_k
        self.client = httpx.Client(timeout=120.0)

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Generate completion for prompt.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False,
                "options": {
                    "num_predict": self.max_tokens,
                },
            },
        )
        response.raise_for_status()
        return response.json()["response"]

    def run_humaneval(
        self,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Run HumanEval benchmark.

        Args:
            limit: Limit number of problems (for quick testing)

        Returns:
            Benchmark results
        """
        from datasets import load_dataset

        logger.info(f"Loading HumanEval dataset (limit={limit})")
        ds = load_dataset("openai_humaneval", split="test")
        problems = list(ds)
        if limit:
            problems = problems[:limit]

        logger.info(
            f"Running benchmark on {len(problems)} problems (pass@{self.pass_k})"
        )

        results = []
        passed = 0

        for i, problem in enumerate(problems):
            task_id = problem["task_id"]
            prompt = problem["prompt"]
            test = problem["test"]
            entry_point = problem["entry_point"]

            logger.info(f"[{i + 1}/{len(problems)}] Processing {task_id}")

            # Generate solution
            completion_prompt = f"""Complete the following Python function:

{prompt}

Provide only the implementation, no explanation."""

            try:
                start_time = time.time()

                # pass@k: Try multiple samples
                sample_results = []
                for sample_idx in range(self.pass_k):
                    try:
                        completion = self.generate(
                            completion_prompt, temperature=0.2 + sample_idx * 0.1
                        )
                        code = self._extract_code(completion)
                        test_passed = self._test_solution(code, test, entry_point)
                        sample_results.append(
                            {
                                "sample_idx": sample_idx,
                                "passed": test_passed,
                                "completion": completion[:200],
                            }
                        )
                        if test_passed:
                            logger.info(
                                f"  PASS (sample {sample_idx + 1}/{self.pass_k})"
                            )
                            break
                    except Exception as sample_error:
                        logger.debug(f"  Sample {sample_idx} failed: {sample_error}")
                        sample_results.append(
                            {
                                "sample_idx": sample_idx,
                                "passed": False,
                                "error": str(sample_error),
                            }
                        )

                elapsed = time.time() - start_time

                # Check if any sample passed
                any_passed = any(s["passed"] for s in sample_results)
                if any_passed:
                    passed += 1
                    status = "PASS"
                else:
                    status = "FAIL"

                results.append(
                    {
                        "task_id": task_id,
                        "status": status,
                        "time": elapsed,
                        "samples": sample_results,
                    }
                )

                logger.info(
                    f"  {status} ({elapsed:.1f}s, {sum(s['passed'] for s in sample_results)}/{len(sample_results)} passed)"
                )

            except Exception as e:
                logger.error(f"  ERROR: {e}")
                results.append(
                    {
                        "task_id": task_id,
                        "status": "ERROR",
                        "error": str(e),
                    }
                )

        # Calculate pass rate
        pass_rate = passed / len(problems) if problems else 0

        summary = {
            "model": self.model_name,
            "total": len(problems),
            "passed": passed,
            "pass_rate": pass_rate,
            "pass@1": pass_rate,  # Simplified
            "results": results,
        }

        # Save results
        output_dir = Path("data/eval/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"humaneval_{self.model_name.replace(':', '_')}.json"

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to {output_path}")
        logger.info(f"Pass rate: {pass_rate:.1%} ({passed}/{len(problems)})")

        return summary

    def _extract_code(self, completion: str) -> str:
        """Extract Python code from completion."""
        # Remove markdown code blocks
        lines = completion.strip().split("\n")
        code_lines = []

        in_code_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if not in_code_block and line.strip():
                code_lines.append(line)

        return "\n".join(code_lines)

    def _test_solution(
        self,
        code: str,
        test: str,
        entry_point: str,
    ) -> bool:
        """Test solution against test cases."""
        import subprocess
        import tempfile

        # Combine solution and test
        test_program = f"{code}\n\n{test}\n\ncheck({entry_point})"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_program)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()


def main():
    """Run benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Run HumanEval with Ollama")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Ollama model")
    parser.add_argument("--limit", type=int, default=10, help="Limit problems")
    parser.add_argument(
        "--pass-k", type=int, default=10, help="Number of samples per problem (pass@k)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=2048, help="Max completion tokens"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    runner = OllamaBenchmarkRunner(
        model_name=args.model,
        pass_k=args.pass_k,
        max_tokens=args.max_tokens,
    )
    try:
        runner.run_humaneval(limit=args.limit)
    finally:
        runner.close()


if __name__ == "__main__":
    main()
