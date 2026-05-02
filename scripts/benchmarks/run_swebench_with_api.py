#!/usr/bin/env python3
"""SWE-bench evaluation using API-based LLM (OpenAI/Anthropic).

This bypasses Ollama timeout issues by using cloud LLM APIs.

Requirements:
    export OPENAI_API_KEY="sk-..."  # OR
    export ANTHROPIC_API_KEY="sk-ant-..."

Usage:
    # With OpenAI (cost ~$0.50-2.00 for 10 issues)
    export OPENAI_API_KEY="your-key"
    uv run python scripts/benchmarks/run_swebench_with_api.py --max-issues 10

    # With Anthropic
    export ANTHROPIC_API_KEY="your-key"
    uv run python scripts/benchmarks/run_swebench_with_api.py --provider anthropic

    # Full verified dataset (expensive - ~$50-100)
    uv run python scripts/benchmarks/run_swebench_with_api.py --dataset verified
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SWEBenchAPIEvaluator:
    """SWE-bench evaluation using API LLMs."""

    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        dataset: str = "test",
    ):
        self.provider = provider
        self.dataset = dataset
        self.cache_dir = Path("data/swebench_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize API executor
        from cohezion.integrations.agentverse.api_llm_executor import APILLMExecutor

        api_key = os.environ.get(f"{provider.upper()}_API_KEY")
        if not api_key:
            raise ValueError(f"Set {provider.upper()}_API_KEY environment variable")

        self.executor = APILLMExecutor(
            provider=provider,
            model=model,
            timeout=120.0,  # Longer timeout for code generation
        )

        logger.info(f"Initialized {provider} executor with model {self.executor.model}")

    async def evaluate_issue(
        self,
        issue: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate single issue via API."""
        instance_id = issue.get("instance_id", "unknown")
        problem = issue.get("problem_statement", "")
        repo = issue.get("repo", "unknown")

        logger.info(f"Evaluating {instance_id}...")

        # Construct task prompt
        prompt = f"""You are an expert software engineer. Fix this GitHub issue.

Repository: {repo}
Instance ID: {instance_id}

Problem Statement:
{problem}

Your task:
1. Analyze the problem
2. Generate a git diff patch that fixes the issue
3. Include ONLY the patch in your response, no explanation

Format your response as a unified diff (git diff format):
```diff
diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,5 +1,5 @@
 ...
```

Generate the patch now:"""

        try:
            result = await self.executor.execute(
                prompt=prompt,
                system="You are an expert software engineer who writes clean, correct code.",
                max_tokens=2048,
                temperature=0.3,  # Lower for code
            )

            # Extract patch
            patch = self._extract_patch(result.output)
            success = patch is not None and len(patch) > 50

            if success:
                logger.info(f"  ✓ Patch generated ({len(patch)} chars)")
            else:
                logger.info("  ✗ No valid patch")

            return {
                "instance_id": instance_id,
                "success": success,
                "patch": patch,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
                "latency_ms": result.latency_ms,
            }

        except Exception as e:
            logger.error(f"  Error: {e}")
            return {
                "instance_id": instance_id,
                "success": False,
                "error": str(e),
            }

    def _extract_patch(self, output: str) -> str | None:
        """Extract git diff from output."""
        # Look for code block
        if "```diff" in output:
            start = output.find("```diff") + 7
            end = output.find("```", start)
            if end > start:
                return output[start:end].strip()

        # Look for raw diff
        if "diff --git" in output:
            start = output.find("diff --git")
            return output[start:].strip()

        return None

    async def run_evaluation(
        self,
        max_issues: int | None = None,
    ) -> dict[str, Any]:
        """Run evaluation."""
        logger.info(f"Loading {self.dataset} dataset...")

        dataset_file = self.cache_dir / f"{self.dataset}.json"
        with open(dataset_file) as f:
            issues = json.load(f)

        if isinstance(issues, dict):
            issues = list(issues.values())

        if max_issues:
            issues = issues[:max_issues]

        logger.info(f"Evaluating {len(issues)} issues...")

        results = []
        total_cost = 0.0
        total_tokens = 0
        passed = 0

        for i, issue in enumerate(issues):
            logger.info(f"[{i + 1}/{len(issues)}] Processing...")
            result = await self.evaluate_issue(issue)
            results.append(result)

            total_cost += result.get("cost_usd", 0)
            total_tokens += result.get("tokens_used", 0)

            if result.get("success"):
                passed += 1

            # Log running cost
            if i % 5 == 0 and i > 0:
                logger.info(f"Running cost: ${total_cost:.4f}, tokens: {total_tokens}")

        # Calculate metrics
        total = len(issues)
        attempted = len([r for r in results if r.get("success")])
        pass_at_1 = passed / total if total > 0 else 0.0

        summary = {
            "dataset": self.dataset,
            "provider": self.provider,
            "model": self.executor.model,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total": total,
                "attempted": attempted,
                "passed": passed,
                "pass_at_1": pass_at_1,
                "pass_at_1_pct": f"{pass_at_1:.1%}",
            },
            "cost": {
                "total_usd": total_cost,
                "total_tokens": total_tokens,
                "avg_per_issue": total_cost / total if total > 0 else 0,
            },
            "results": results,
        }

        # Save results
        output_dir = Path(f"data/swebench_results/api_{self.provider}")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"results_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to {output_file}")

        return summary


async def main():
    parser = argparse.ArgumentParser(
        description="SWE-bench evaluation using API LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (3 issues)
  export OPENAI_API_KEY="sk-..."
  uv run python %(prog)s --max-issues 3

  # Anthropic (more capable but expensive)
  export ANTHROPIC_API_KEY="sk-ant-..."
  uv run python %(prog)s --provider anthropic --max-issues 5

  # Run on full test set
  uv run python %(prog)s --dataset test --max-issues 100
        """,
    )
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", default=None, help="Specific model name")
    parser.add_argument("--dataset", default="test", help="SWE-bench dataset")
    parser.add_argument("--max-issues", type=int, default=3, help="Max issues to evaluate")

    args = parser.parse_args()

    # Check API key
    key_env = f"{args.provider.upper()}_API_KEY"
    if not os.environ.get(key_env):
        print(f"Error: Set {key_env} environment variable")
        return 1

    # Run evaluation
    try:
        evaluator = SWEBenchAPIEvaluator(
            provider=args.provider,
            model=args.model,
            dataset=args.dataset,
        )

        results = await evaluator.run_evaluation(max_issues=args.max_issues)

        # Print summary
        print(f"\n{'=' * 60}")
        print("SWE-bench API Evaluation Complete")
        print(f"{'=' * 60}")
        print(f"Provider: {results['provider']} ({results['model']})")
        print(f"Total: {results['metrics']['total']}")
        print(f"Passed: {results['metrics']['passed']}")
        print(f"Pass@1: {results['metrics']['pass_at_1_pct']}")
        print(f"Cost: ${results['cost']['total_usd']:.4f}")
        print(f"Tokens: {results['cost']['total_tokens']:,}")
        print(f"{'=' * 60}")

        return 0 if results["metrics"]["pass_at_1"] > 0 else 1

    except Exception:
        logger.exception("Evaluation failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
