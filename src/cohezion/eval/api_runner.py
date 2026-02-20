"""API-based benchmark runner for Anthropic/GPT models.

Enables benchmark evaluation using API models for accurate capability assessment.
Includes token limit handling and auto-retry for robustness.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

# Default token limits for different providers
DEFAULT_MAX_TOKENS = 512  # Reduced from 2048 to prevent limit errors
DEFAULT_TOKEN_BUDGET = 4096  # Total budget (prompt + completion)


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
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ):
        """Initialize runner."""
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        self.token_budget = token_budget
        self._token_reduction_factor = 2  # How much to reduce on token errors

    def _get_client(self):
        """Get or create Anthropic client."""
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        return self.client

    def calculate_max_tokens(self, prompt: str) -> int:
        """Calculate safe max completion tokens based on prompt.

        Args:
            prompt: Input prompt

        Returns:
            Safe max_tokens for completion
        """
        # Rough estimate: 1 token ≈ 4 characters
        prompt_tokens = len(prompt) // 4

        # Reserve buffer for response overhead
        buffer = 100

        max_completion = self.token_budget - prompt_tokens - buffer

        return max(256, min(max_completion, 4096))  # Min 256, max 4096

    def generate(
        self,
        prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """Generate completion with error handling and auto-retry.

        Args:
            prompt: Input prompt
            max_tokens: Max tokens (auto-calculated if None)

        Returns:
            Generated text

        Raises:
            Exception: If all retries fail
        """
        # Auto-calculate safe max_tokens if not provided
        if max_tokens is None:
            max_tokens = self.calculate_max_tokens(prompt)
            logger.debug(f"Auto-calculated max_tokens: {max_tokens}")

        last_error = None
        current_max_tokens = max_tokens

        for attempt in range(3):  # Max 3 attempts
            try:
                return self._do_generate(prompt, current_max_tokens)
            except Exception as e:
                error_msg = str(e).lower()
                last_error = e

                if "too many tokens" in error_msg or "max_tokens" in error_msg:
                    # Reduce tokens and retry
                    current_max_tokens = max(256, current_max_tokens // 2)
                    logger.warning(
                        f"Token limit hit (attempt {attempt + 1}), "
                        f"reducing to {current_max_tokens} tokens"
                    )
                    continue
                elif "rate_limit" in error_msg or "rate limit" in error_msg:
                    # Wait and retry with backoff
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limit hit, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error
                    raise

        # All retries failed
        raise last_error

    def _do_generate(self, prompt: str, max_tokens: int) -> str:
        """Actual generation call."""
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
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ):
        """Initialize runner."""
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.token_budget = token_budget
        self.client = None

    def calculate_max_tokens(self, prompt: str) -> int:
        """Calculate safe max completion tokens based on prompt."""
        prompt_tokens = len(prompt) // 4
        buffer = 100
        max_completion = self.token_budget - prompt_tokens - buffer
        return max(256, min(max_completion, 4096))

    def generate(
        self,
        prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """Generate with error handling."""
        if max_tokens is None:
            max_tokens = self.calculate_max_tokens(prompt)

        last_error = None
        current_max_tokens = max_tokens

        for attempt in range(3):
            try:
                return self._do_generate(prompt, current_max_tokens)
            except Exception as e:
                error_msg = str(e).lower()
                last_error = e

                if "too many tokens" in error_msg or "max_tokens" in error_msg:
                    current_max_tokens = max(256, current_max_tokens // 2)
                    logger.warning(f"Token limit hit, reducing to {current_max_tokens}")
                    continue
                elif "rate_limit" in error_msg:
                    time.sleep((attempt + 1) * 10)
                    continue
                else:
                    raise

        raise last_error

    def _do_generate(self, prompt: str, max_tokens: int) -> str:
        """Actual generation call."""
        from openai import OpenAI

        if self.client is None:
            self.client = OpenAI(api_key=self.api_key)

        response = self.client.chat.completions.create(
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
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        max_tokens: int | None = None,
        **kwargs,
    ):
        """Initialize runner.

        Args:
            provider: "anthropic" or "openai"
            model: Model name
            token_budget: Total token budget (prompt + completion)
            max_tokens: Override max completion tokens (None = auto-calculate)
            **kwargs: Additional provider-specific args
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        runner_class = self.PROVIDERS[provider]
        self.runner = runner_class(
            model=model,
            token_budget=token_budget,
            **kwargs,
        )
        self.model = model
        self.provider = provider
        self._max_tokens_override = max_tokens

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Generate completion."""
        # Use override or provided value
        tokens = max_tokens or self._max_tokens_override
        return self.runner.generate(prompt, tokens)

    def run_humaneval(
        self,
        limit: int | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Run HumanEval benchmark.

        Args:
            limit: Number of problems to run
            max_tokens: Max completion tokens (None = auto-calculate)

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
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max completion tokens (default: auto-calculate)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=DEFAULT_TOKEN_BUDGET,
        help=f"Total token budget (default: {DEFAULT_TOKEN_BUDGET})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    runner = APIBenchmarkRunner(
        provider=args.provider,
        model=args.model,
        token_budget=args.token_budget,
        max_tokens=args.max_tokens,
    )
    runner.run_humaneval(limit=args.limit, max_tokens=args.max_tokens)


if __name__ == "__main__":
    main()
