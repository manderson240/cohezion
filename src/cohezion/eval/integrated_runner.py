"""Complete integrated benchmark runner.

Combines all components: orchestrator, self-correction, FLUME guidance, pattern analysis.
"""

import json
import logging
from pathlib import Path

from cohezion.eval.flume_guided import FLUMEGuidedGenerator, create_flume_guided_runner
from cohezion.eval.journey_integration import BenchmarkFeedbackLoop
from cohezion.eval.pattern_analyzer import PatternAnalyzer, JourneyAttempt

logger = logging.getLogger(__name__)


class IntegratedBenchmarkRunner:
    """Complete benchmark pipeline with FLUME integration.

    Runs benchmarks with:
    1. Self-correction loop
    2. Journey tracking
    3. FLUME-guided generation
    4. Pattern analysis
    5. Continuous improvement
    """

    def __init__(
        self,
        generator,
        provider: str = "api",
        model: str = "claude-sonnet-4-20250514",
    ):
        """Initialize integrated runner."""
        self.generator = generator
        self.provider = provider
        self.model = model

        # Components
        self.feedback = BenchmarkFeedbackLoop()
        self.analyzer = PatternAnalyzer()

        # FLUME-guided generation
        self.flume_generator: FLUMEGuidedGenerator | None = None
        self.phi_coherence_data: list[dict] = []

    def enable_flume_guidance(self, historical_data: list[dict]) -> None:
        """Enable FLUME-guided generation based on historical data."""
        self.phi_coherence_data = historical_data
        self.flume_generator = create_flume_guided_runner(
            self.generator, historical_data
        )
        logger.info("FLUME-guided generation enabled")

    def run_benchmark(
        self,
        benchmark: str = "humaneval",
        limit: int = 10,
        max_attempts: int = 3,
        use_flume: bool = True,
    ) -> dict:
        """Run complete benchmark with all integrations.

        Args:
            benchmark: Benchmark name
            limit: Number of problems
            max_attempts: Max self-correction attempts
            use_flume: Use FLUME guidance

        Returns:
            Complete benchmark results with analysis
        """
        from datasets import load_dataset

        logger.info(f"Running {benchmark} with limit={limit}, attempts={max_attempts}")

        # Load dataset
        if benchmark == "humaneval":
            ds = load_dataset("openai_humaneval", split="test")
            problems = list(ds)[:limit]
        else:
            raise ValueError(f"Unknown benchmark: {benchmark}")

        results = []
        total_passed = 0

        for i, problem in enumerate(problems):
            task_id = problem["task_id"]
            prompt = problem["prompt"]
            test = problem["test"]
            entry_point = problem["entry_point"]

            logger.info(f"[{i + 1}/{len(problems)}] {task_id}")

            # Generate with FLUME guidance if enabled
            for attempt in range(max_attempts):
                try:
                    # Choose generator
                    if use_flume and self.flume_generator:
                        completion = self.flume_generator.generate(
                            f"Complete this function:\n{prompt}\n\nReturn ONLY code."
                        )
                    else:
                        completion = self.generator.generate(
                            f"Complete this function:\n{prompt}\n\nReturn ONLY code."
                        )

                    code = self._extract_code(completion)

                    # Test
                    passed = self._test_solution(code, test, entry_point)

                    # Record journey
                    phi_score = self._estimate_phi(code)
                    coherence = self._estimate_coherence(code)

                    self.feedback.record_result(
                        benchmark=benchmark,
                        task_id=task_id,
                        model=self.model,
                        success=passed,
                        completion=code,
                    )

                    self.analyzer.add_attempt(
                        JourneyAttempt(
                            task_id=task_id,
                            benchmark=benchmark,
                            model=self.model,
                            success=passed,
                            phi_score=phi_score,
                            coherence=coherence,
                            completion=code,
                            num_tokens=len(code.split()),
                        )
                    )

                    results.append(
                        {
                            "task_id": task_id,
                            "attempt": attempt + 1,
                            "success": passed,
                            "phi_score": phi_score,
                            "coherence": coherence,
                        }
                    )

                    if passed:
                        total_passed += 1
                        logger.info(f"  PASS (attempt {attempt + 1})")
                        break
                    else:
                        logger.info(f"  FAIL (attempt {attempt + 1})")

                except Exception as e:
                    logger.error(f"  ERROR: {e}")

        # Analyze patterns
        analysis = self.analyzer.analyze()
        recommendations = self.analyzer.generate_recommendations()

        # Learn from results for future runs
        if self.flume_generator:
            self.flume_generator.learn_from_results(results)

        summary = {
            "benchmark": benchmark,
            "provider": self.provider,
            "model": self.model,
            "total": len(problems),
            "passed": total_passed,
            "pass_rate": total_passed / len(problems) if problems else 0,
            "flume_enabled": use_flume,
            "analysis": analysis,
            "recommendations": recommendations[:5],
            "results": results,
        }

        # Save
        output = f"data/eval/results/integrated_{benchmark}_{self.provider}_{self.model.replace('-', '_')}.json"
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(
            f"Complete: {summary['pass_rate']:.1%} ({total_passed}/{len(problems)})"
        )

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

    def _test_solution(self, code: str, test: str, entry_point: str) -> bool:
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
            Path(path).unlink(missing_ok=True)

    def _estimate_phi(self, code: str) -> float:
        """Estimate phi_score from code characteristics."""
        lines = [l for l in code.split("\n") if l.strip()]
        has_loops = any("for " in l or "while " in l for l in lines)
        has_conditionals = any("if " in l for l in lines)
        has_returns = any("return" in l for l in lines)

        return min(
            (has_loops * 0.3 + has_conditionals * 0.3 + has_returns * 0.4) * 1.5,
            1.0,
        )

    def _estimate_coherence(self, code: str) -> float:
        """Estimate coherence from code."""
        lines = [l for l in code.split("\n") if l.strip()]
        if not lines:
            return 0.0
        return min(len(lines) / 20.0, 1.0)
