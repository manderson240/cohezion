"""API-based benchmark runner for Anthropic/GPT models.

Enables benchmark evaluation using API models for accurate capability assessment.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class APIBenchmarkResult:
    """Result from API benchmark."""

    task_id: str
    model: str
    success: bool
    completion: str
    duration: float
    tokens: int
    error: str | None = None


class AnthropicBenchmarkRunner:
    """Run benchmarks using Anthropic Claude API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
    ):
        """Initialize runner."""
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None

    def _get_client(self):
        """Get or create Anthropic client."""
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        return self.client

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate completion."""
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class OpenAIBenchmarkRunner:
    """Run benchmarks using OpenAI API."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
    ):
        """Initialize runner."""
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate completion."""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


class APIBenchmarkRunner:
    """Unified API benchmark runner supporting multiple providers."""

    PROVIDERS = {
        "anthropic": AnthropicBenchmarkRunner,
        "openai": OpenAIBenchmarkRunner,
    }

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-20250514",
        **kwargs,
    ):
        """Initialize runner.

        Args:
            provider: "anthropic" or "openai"
            model: Model name
            **kwargs: Additional provider-specific args
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        self.runner = self.PROVIDERS[provider](model=model, **kwargs)
        self.model = model
        self.provider = provider

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate completion."""
        return self.runner.generate(prompt, max_tokens)

    def run_humaneval(
        self,
        limit: int | None = None,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Run HumanEval benchmark.

        Args:
            limit: Number of problems to run
            max_tokens: Max completion tokens

        Returns:
            Benchmark results
        """
        from datasets import load_dataset

        logger.info(f"Loading HumanEval dataset (limit={limit})")
        ds = load_dataset("openai_humaneval", split="test")
        problems = list(ds)
        if limit:
            problems = problems[:limit]

        logger.info(f"Running {self.provider}/{self.model} on {len(problems)} problems")

        results = []
        passed = 0

        for i, problem in enumerate(problems):
            task_id = problem["task_id"]
            prompt = problem["prompt"]
            test = problem["test"]
            entry_point = problem["entry_point"]

            logger.info(f"[{i + 1}/{len(problems)}] {task_id}")

            try:
                start = time.time()

                # Generate solution
                completion_prompt = f"""Complete this Python function. Return ONLY the code, no explanation:

{prompt}
"""
                completion = self.generate(completion_prompt, max_tokens)
                code = self._extract_code(completion)

                # Test
                test_passed = self._test_solution(code, test, entry_point)

                duration = time.time() - start
                if test_passed:
                    passed += 1

                results.append(
                    {
                        "task_id": task_id,
                        "success": test_passed,
                        "completion": code[:200],
                        "duration": duration,
                    }
                )
                logger.info(f"  {'PASS' if test_passed else 'FAIL'} ({duration:.1f}s)")

            except Exception as e:
                logger.error(f"  ERROR: {e}")
                results.append(
                    {
                        "task_id": task_id,
                        "success": False,
                        "error": str(e),
                    }
                )

        pass_rate = passed / len(problems) if problems else 0
        summary = {
            "provider": self.provider,
            "model": self.model,
            "total": len(problems),
            "passed": passed,
            "pass_rate": pass_rate,
            "results": results,
        }

        # Save
        output = f"data/eval/results/humaneval_{self.provider}_{self.model.replace('-', '_')}.json"
        os.makedirs("data/eval/results", exist_ok=True)
        with open(output, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results: {pass_rate:.1%} ({passed}/{len(problems)})")
        return summary

    def _extract_code(self, completion: str) -> str:
        """Extract code from completion."""
        lines = completion.strip().split("\n")
        code_lines = []
        in_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if not in_block and line.strip() and not line.strip().startswith("#"):
                code_lines.append(line)

        return "\n".join(code_lines)

    def _test_solution(
        self,
        code: str,
        test: str,
        entry_point: str,
    ) -> bool:
        """Test solution."""
        import subprocess
        import tempfile

        test_program = f"{code}\n\n{test}\n\ncheck({entry_point})"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_program)
            path = f.name

        try:
            result = subprocess.run(
                ["python", path],
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False
        finally:
            import pathlib

            pathlib.Path(path).unlink(missing_ok=True)


def main():
    """CLI for API benchmarks."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", choices=["anthropic", "openai"], default="anthropic"
    )
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=2048)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    runner = APIBenchmarkRunner(provider=args.provider, model=args.model)
    runner.run_humaneval(limit=args.limit, max_tokens=args.max_tokens)


if __name__ == "__main__":
    main()
