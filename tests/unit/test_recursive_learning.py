from unittest.mock import patch

import pytest

from cohezion.agi.recursive_learning import LearningCycleResult, RecursiveLearningEngine


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
