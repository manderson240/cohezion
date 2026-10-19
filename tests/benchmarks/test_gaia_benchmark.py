"""Comprehensive Test Suite for Cohezion GAIA Agentic Benchmark Runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cohezion.benchmarks.agentic_benchmark import (
    CANONICAL_GAIA_TASKS,
    GAIABenchmarkResult,
    GAIANormalizer,
    GAIARunner,
    GAIATask,
    GAIATaskResult,
)


class TestGAIANormalizer:
    """Exhaustive tests for deterministic GAIA answer normalization."""

    def test_numeric_integers(self) -> None:
        assert GAIANormalizer.exact_match("42", "42")
        assert GAIANormalizer.exact_match("42.0", "42")
        assert GAIANormalizer.exact_match("  42  ", "42")

    def test_numeric_floats(self) -> None:
        assert GAIANormalizer.exact_match("3.14159", "3.14159")
        assert GAIANormalizer.exact_match("3.14159265", "3.1416")  # within 1e-4 tolerance

    def test_numeric_scientific_notation(self) -> None:
        assert GAIANormalizer.exact_match("1.23e4", "12300")
        assert GAIANormalizer.exact_match("1.5e-3", "0.0015")

    def test_numeric_thousands_separators(self) -> None:
        assert GAIANormalizer.exact_match("1,234,567.89", "1234567.89")
        assert GAIANormalizer.exact_match("$10,000", "10000")
        assert GAIANormalizer.exact_match("€ 5,200.50", "5200.50")

    def test_numeric_percentages(self) -> None:
        assert GAIANormalizer.exact_match("85%", "0.85")
        assert GAIANormalizer.exact_match("85 percent", "85%")
        assert GAIANormalizer.exact_match("12.5%", "0.125")

    def test_dates(self) -> None:
        assert GAIANormalizer.exact_match("2023-11-15", "2023-11-15")
        assert GAIANormalizer.exact_match("11/15/2023", "2023-11-15")
        assert GAIANormalizer.exact_match("November 15, 2023", "2023-11-15")
        assert GAIANormalizer.exact_match("Nov 15, 2023", "2023-11-15")
        assert GAIANormalizer.exact_match("1783", "1783")

    def test_text_normalization(self) -> None:
        assert GAIANormalizer.exact_match("Hello, World!", "hello world")
        assert GAIANormalizer.exact_match("   Multiple    Spaces   ", "multiple spaces")
        assert GAIANormalizer.exact_match("Hyphenated-Word", "hyphenated word")

    def test_sets_and_lists(self) -> None:
        assert GAIANormalizer.exact_match("apple, banana, cherry", "cherry, apple, banana")
        assert GAIANormalizer.exact_match(
            "carbon, hydrogen, oxygen, phosphorus",
            "phosphorus, oxygen, hydrogen, carbon",
        )

    def test_exact_match_negative_cases(self) -> None:
        assert not GAIANormalizer.exact_match("42", "43")
        assert not GAIANormalizer.exact_match("2023-11-15", "2023-11-16")
        assert not GAIANormalizer.exact_match("apple, banana", "apple, orange")
        assert not GAIANormalizer.exact_match("correct", "incorrect")


class TestGAIARunner:
    """Test GAIARunner execution, AutoHarness gating, and metrics calculation."""

    @pytest.mark.asyncio
    async def test_canonical_suite_default_execution(self) -> None:
        runner = GAIARunner(tier="tier1_local")
        result = await runner.run_benchmark(CANONICAL_GAIA_TASKS)

        assert isinstance(result, GAIABenchmarkResult)
        assert result.tier == "tier1_local"
        assert len(result.task_results) == 6
        assert result.overall_accuracy == 1.0
        assert result.level1_resolved_rate == 1.0
        assert result.level2_resolved_rate == 1.0
        assert result.level3_resolved_rate == 1.0
        assert result.mean_latency > 0.0

    @pytest.mark.asyncio
    async def test_autoharness_policy_blocks_illegal_code(self) -> None:
        runner = GAIARunner()

        # Dangerous eval/exec in Python tool call must trigger AutoHarness violation
        v_res = runner.verify_tool_action("python", 'eval(\'__import__("os").system("ls")\')')
        assert not v_res.valid
        assert any("eval" in viol for viol in v_res.violations)

        # Safe python function definition
        v_res_safe = runner.verify_tool_action(
            "python", "def calc(x: int) -> int:\n    return x * 2\n"
        )
        assert v_res_safe.valid
        assert len(v_res_safe.violations) == 0

    @pytest.mark.asyncio
    async def test_mock_agent_selective_success(self) -> None:
        class MockAgent:
            async def run_task(self, task: GAIATask) -> dict:
                # Resolve Level 1 and 2, fail Level 3
                ans = task.ground_truth if task.level in (1, 2) else "wrong_answer"
                return {
                    "answer": ans,
                    "tool_calls": [],
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                }

        runner = GAIARunner(tier="tier2_cloud")
        res = await runner.run_benchmark(CANONICAL_GAIA_TASKS, agent=MockAgent())

        assert res.level1_resolved_rate == 1.0
        assert res.level2_resolved_rate == 1.0
        assert res.level3_resolved_rate == 0.0
        assert round(res.overall_accuracy, 2) == round(4 / 6, 2)
        assert res.token_efficiency > 0.0

    @pytest.mark.asyncio
    async def test_timeout_and_error_containment(self) -> None:
        class HangingAgent:
            async def run_task(self, task: GAIATask) -> dict:
                await asyncio.sleep(2.0)
                return {"answer": task.ground_truth}

        runner = GAIARunner(timeout_seconds=0.05)
        task = GAIATask(
            task_id="timeout_test",
            question="What is 1 + 1?",
            level=1,
            ground_truth="2",
        )
        result = await runner.evaluate_task(task, agent=HangingAgent())

        assert not result.resolved
        assert result.error is not None
        assert "timed out" in result.error.lower()

    def test_export_to_vault(self, tmp_path: Path) -> None:
        runner = GAIARunner(tier="tier3_thinking")
        mock_result = GAIABenchmarkResult(
            tier="tier3_thinking",
            timestamp="2026-10-18T12:00:00",
            task_results=[
                GAIATaskResult(
                    task_id="t1",
                    level=1,
                    question="Q1",
                    ground_truth="42",
                    candidate_answer="42",
                    resolved=True,
                    latency_s=0.123,
                    total_tokens=150,
                ),
                GAIATaskResult(
                    task_id="t2",
                    level=2,
                    question="Q2",
                    ground_truth="alpha",
                    candidate_answer="beta",
                    resolved=False,
                    latency_s=0.456,
                    total_tokens=250,
                ),
            ],
            level1_resolved_rate=1.0,
            level2_resolved_rate=0.0,
            level3_resolved_rate=0.0,
            overall_accuracy=0.5,
            mean_latency=0.2895,
            token_efficiency=25.0,
        )

        out_file = tmp_path / "vault" / "benchmarks" / "gaia_benchmark_test.md"
        saved_path = runner.export_to_vault(mock_result, vault_path=out_file)

        assert saved_path.exists()
        content = saved_path.read_text(encoding="utf-8")
        assert "# GAIA Agentic Benchmark Scorecard" in content
        assert "Overall Accuracy" in content
        assert "Level 1" in content
        assert "| `t1` | L1 | `42` | `42` | ✅ Pass |" in content
        assert "| `t2` | L2 | `alpha` | `beta` | ❌ Fail |" in content
