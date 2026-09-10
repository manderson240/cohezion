from unittest.mock import patch

import pytest

from cohezion.agi.recursive_learning import (
    LearningCycleResult,
    MarkovStateMonad,
    RecursiveLearningEngine,
)
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.physics.poincare_manifold import PoincareManifoldND


@pytest.mark.asyncio
async def test_recursive_learning_engine():
    engine = RecursiveLearningEngine()

    with patch.object(engine, "surreal_upsert", return_value=True):
        res = await engine.execute_recursive_learning_cycle(
            "Successfully completed 2048D Poincaré trajectory."
        )
        assert isinstance(res, LearningCycleResult)
        assert res.autoharness_score == 1.0
        assert res.autocontext_dim == 2048
        assert res.ctac_coherence == 0.50
        assert res.surreal_persisted is True
        assert res.vault_persisted is True
        assert res.delta_entropy <= 0.0
        assert res.zkfv_verified is True


def test_markov_state_monad_success():
    compiler = ZKFVCompiler(salt="test_salt")
    p0 = PoincareManifoldND.project([0.1] * 12, target_dim=12)
    p1 = PoincareManifoldND.project([0.05] * 12, target_dim=12)

    def valid_action(state: int):
        return state + 1, "action_step", "def valid_func() -> int:\n    return 42\n", [p0, p1]

    def negentropic_evaluator(pre, post):
        return -0.05

    res = MarkovStateMonad.bind(
        current_state=10,
        action_fn=valid_action,
        entropy_evaluator=negentropic_evaluator,
        zkfv_compiler=compiler,
    )

    assert res.is_valid is True
    assert res.new_state == 11
    assert res.zkfv_verified is True
    assert res.delta_entropy == -0.05


def test_markov_state_monad_rollback_on_entropy_increase():
    compiler = ZKFVCompiler(salt="test_salt")
    p0 = PoincareManifoldND.project([0.05] * 12, target_dim=12)
    p1 = PoincareManifoldND.project([0.5] * 12, target_dim=12)

    def entropic_action(state: int):
        return state + 10, "bad_step", "def valid_code() -> None:\n    pass\n", [p0, p1]

    def entropic_evaluator(pre, post):
        return 0.45  # Entropy increased!

    res = MarkovStateMonad.bind(
        current_state=10,
        action_fn=entropic_action,
        entropy_evaluator=entropic_evaluator,
        zkfv_compiler=compiler,
    )

    # Must rollback state!
    assert res.is_valid is False
    assert res.new_state == 10  # Rolled back
    assert "Negentropy violation" in res.diagnostic


def test_markov_state_monad_rollback_on_invalid_code():
    compiler = ZKFVCompiler(salt="test_salt")
    p0 = PoincareManifoldND.project([0.1] * 12, target_dim=12)
    p1 = PoincareManifoldND.project([0.05] * 12, target_dim=12)

    def invalid_code_action(state: int):
        return state + 1, "corrupt_step", "def broken_code( -> invalid python", [p0, p1]

    def negentropic_evaluator(pre, post):
        return -0.05

    res = MarkovStateMonad.bind(
        current_state=10,
        action_fn=invalid_code_action,
        entropy_evaluator=negentropic_evaluator,
        zkfv_compiler=compiler,
    )

    # Must rollback state!
    assert res.is_valid is False
    assert res.new_state == 10  # Rolled back
    assert res.zkfv_verified is False
