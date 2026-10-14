"""Tests for StatelessKaggleOptimizer (arXiv:2610.07625)."""

import asyncio
from pathlib import Path
import pytest

from cohezion.competitions.stateless_kaggle_optimizer import (
    KaggleOptimizationConfig,
    StatelessKaggleOptimizer,
    get_default_rsna_knee_sla_config,
)
from cohezion.compound.stateless_language_agent import CandidateOutcome


@pytest.mark.asyncio
async def test_stateless_kaggle_optimizer_initialization(tmp_path: Path):
    initial_code = tmp_path / "baseline_script.py"
    initial_code.write_text("def solve(): return 0.943", encoding="utf-8")

    config = KaggleOptimizationConfig(
        competition_slug="rsna-knee-abnormality-detection",
        metric_name="Macro ROC-AUC",
        baseline_score=0.943,
        initial_code_path=initial_code,
        initial_directions=[
            {"direction_id": "dir_temp", "hypothesis": "Temperature scaling"},
            {"direction_id": "dir_weights", "hypothesis": "Pathology weights"},
        ],
        worker_models={"w_0": "mock_model"},
        advisor_model="mock_advisor",
    )

    optimizer = StatelessKaggleOptimizer(config)

    async def mock_evaluator(code: str):
        return 0.945, "Executed cleanly", False

    harness = optimizer.build_harness(evaluator_fn=mock_evaluator)
    seed = await harness.initialize()

    assert seed.score == 0.945
    assert seed.outcome == CandidateOutcome.MEASURED_NON_IMPROVEMENT
    assert harness.global_best_candidate is not None


@pytest.mark.asyncio
async def test_stateless_kaggle_optimizer_multi_epoch_disambiguation(tmp_path: Path):
    initial_code = tmp_path / "baseline.py"
    initial_code.write_text("baseline = 0.943", encoding="utf-8")

    config = KaggleOptimizationConfig(
        competition_slug="arc-prize-2026-arc-agi-2",
        metric_name="Solve Rate",
        baseline_score=31.81,
        initial_code_path=initial_code,
        initial_directions=[
            {"direction_id": "dir_affordance", "hypothesis": "Affordance search"},
            {"direction_id": "dir_zobrist", "hypothesis": "Zobrist cycle hashing"},
        ],
        worker_models={"w_0": "mock_0", "w_1": "mock_1"},
        advisor_model="mock_adv",
        local_retention_k=2,
    )

    optimizer = StatelessKaggleOptimizer(config)

    eval_calls = 0

    async def mock_evaluator(code: str):
        nonlocal eval_calls
        eval_calls += 1
        if eval_calls == 1:
            return 31.81, "Baseline clean", False
        if "w_0" in code:
            return 0.0, "SyntaxError: unexpected indent", True
        if "w_1" in code:
            return 33.50, "Topological invariant verified", False
        return 31.81, "No change", False

    async def mock_adv_fn(prompt: str) -> str:
        return ""  # Trigger heuristic fallback assignment

    async def mock_w0_fn(prompt: str) -> str:
        return "```python\n# code by w_0 trial 0\nsolve = True\n```"

    async def mock_w1_fn(prompt: str) -> str:
        return "```python\n# code by w_1 trial 0\nsolve = 33.5\n```"

    optimizer.build_harness(
        evaluator_fn=mock_evaluator,
        mock_advisor=mock_adv_fn,
        mock_workers={"w_0": mock_w0_fn, "w_1": mock_w1_fn},
    )
    history = await optimizer.run_iterations(epochs=1)

    assert len(history) == 1
    ep1 = history[0]
    assert ep1["epoch"] == 1
    assert ep1["global_best_score"] == 33.50

    # Verify that w_0's failure was categorized as INCONCLUSIVE_FAILURE
    candidates = list(optimizer.harness.candidates.values())
    inconclusive = [c for c in candidates if c.outcome == CandidateOutcome.INCONCLUSIVE_FAILURE]
    improved = [c for c in candidates if c.outcome == CandidateOutcome.MEASURED_IMPROVEMENT]

    assert len(inconclusive) >= 1
    assert len(improved) >= 1


def test_default_rsna_knee_sla_config():
    cfg = get_default_rsna_knee_sla_config()
    assert cfg.competition_slug == "rsna-knee-abnormality-detection"
    assert len(cfg.initial_directions) == 4
    assert "dir_pref_temperature" in [d["direction_id"] for d in cfg.initial_directions]
    assert "dir_r7_tri_arm_blend" in [d["direction_id"] for d in cfg.initial_directions]
    assert cfg.advisor_model == "deepseek-v4-pro:cloud"
