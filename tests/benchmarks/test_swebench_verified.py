"""Tests for SWE-bench Verified benchmark runner, AutoHarness, and Equilibrium Governor."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.benchmarks.coding_benchmark import (
    CodeResult,
    CodeTask,
    CohezionCodeBenchmark,
    SWEBenchRunner,
)


@pytest.fixture
def sample_task() -> CodeTask:
    return CodeTask(
        repo="astropy/astropy",
        issue_number=14523,
        problem_statement="Fix coordinate transformation singular matrix error in galactic frame.",
        base_commit="e4b8a1c9",
        test_patch="diff --git a/test_coord.py b/test_coord.py\n+def test_singular(): pass\n",
        golden_patch="diff --git a/coord.py b/coord.py\n+def solve(): return 1\n",
        difficulty="hard",
        language="python",
        time_estimate_minutes=25,
    )


def test_code_task_and_result_dataclasses(sample_task: CodeTask):
    """Test CodeTask and CodeResult fields and serialization."""
    res = CodeResult(
        task_id=f"{sample_task.repo}#{sample_task.issue_number}",
        success=True,
        patch_generated="diff --git a/coord.py b/coord.py\n+def solve(): return 1\n",
        tests_passed=True,
        compilation_success=True,
        lint_score=1.0,
        time_taken_seconds=12.4,
        token_usage=450,
        attempts=1,
        error_message=None,
        difficulty=sample_task.difficulty,
        autoharness_verified=True,
        autoharness_latency_ms=0.15,
        tier_dispatched="tier_1_npu",
    )
    d = asdict(res)
    assert d["difficulty"] == "hard"
    assert d["autoharness_verified"] is True
    assert d["tier_dispatched"] == "tier_1_npu"
    assert d["success"] is True


@pytest.mark.asyncio
async def test_swebench_runner_evaluation_flow(sample_task: CodeTask, tmp_path: Path):
    """Test end-to-end evaluation flow with AutoHarness and Governor."""
    runner = SWEBenchRunner(
        cache_dir=tmp_path / "cache",
        enable_autoharness=True,
        enable_governor=True,
    )

    mock_executor = MagicMock()
    mock_executor.execute_task = AsyncMock(
        return_value=MagicMock(
            success=True,
            output="```diff\ndiff --git a/src/math_util.py b/src/math_util.py\n+def add(a: int, b: int) -> int:\n+    return a + b\n```",
        )
    )

    with (
        patch.object(runner, "_setup_repo", return_value=tmp_path / "repo"),
        patch.object(
            runner,
            "_run_tests",
            return_value={
                "tests_pass": True,
                "compiles": True,
                "lint_score": 0.95,
                "tokens": 300,
                "attempts": 1,
            },
        ),
    ):
        result = await runner.evaluate_task(sample_task, mock_executor, timeout_minutes=5)
        assert result.success is True
        assert result.tests_passed is True
        assert result.autoharness_verified is True
        assert result.difficulty == "hard"
        assert result.tier_dispatched in {"tier_1_npu", "tier_1_cpu", "tier_2_ollama_cloud"}


@pytest.mark.asyncio
async def test_cohezion_code_benchmark_summary_and_export(tmp_path: Path):
    """Test multi-task benchmark aggregation and Obsidian vault export."""
    benchmark = CohezionCodeBenchmark()

    # Populate synthetic results
    benchmark.results = [
        CodeResult(
            task_id="repo1#1",
            success=True,
            patch_generated="diff ...",
            tests_passed=True,
            compilation_success=True,
            lint_score=1.0,
            time_taken_seconds=10.0,
            token_usage=200,
            attempts=1,
            error_message=None,
            difficulty="easy",
            autoharness_verified=True,
            autoharness_latency_ms=0.12,
            tier_dispatched="tier_1_npu",
        ),
        CodeResult(
            task_id="repo2#2",
            success=True,
            patch_generated="diff ...",
            tests_passed=True,
            compilation_success=True,
            lint_score=0.9,
            time_taken_seconds=20.0,
            token_usage=400,
            attempts=1,
            error_message=None,
            difficulty="medium",
            autoharness_verified=True,
            autoharness_latency_ms=0.20,
            tier_dispatched="tier_1_npu",
        ),
        CodeResult(
            task_id="repo3#3",
            success=False,
            patch_generated=None,
            tests_passed=False,
            compilation_success=False,
            lint_score=0.0,
            time_taken_seconds=30.0,
            token_usage=600,
            attempts=2,
            error_message="Test failure",
            difficulty="hard",
            autoharness_verified=False,
            autoharness_latency_ms=0.0,
            tier_dispatched="tier_2_ollama_cloud",
        ),
    ]

    summary = benchmark._compute_summary()
    assert summary["overall"]["total_tasks"] == 3
    assert abs(summary["overall"]["pass_at_1"] - 2 / 3) < 1e-4
    assert abs(summary["overall"]["autoharness_pass_rate"] - 2 / 3) < 1e-4

    # Check difficulty breakdown is strictly preserved
    diffs = summary["by_difficulty"]
    assert "easy" in diffs
    assert "medium" in diffs
    assert "hard" in diffs
    assert diffs["easy"]["pass_rate"] == 1.0
    assert diffs["medium"]["pass_rate"] == 1.0
    assert diffs["hard"]["pass_rate"] == 0.0

    # Test report generation and vault export
    vault_dir = tmp_path / "vault_benchmarks"
    report_file = benchmark.export_to_vault(vault_dir=vault_dir)
    assert report_file.exists()
    content = report_file.read_text()
    assert "SWE-bench" in content or "Code Benchmark Report" in content
    assert "AutoHarness" in content
