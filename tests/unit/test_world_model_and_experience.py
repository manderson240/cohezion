import pytest

from cohezion.agi.experiential_learning import ExperienceRecord, ExperientialLearningEngine
from cohezion.agi.hyperbolic_world_model import HyperbolicWorldModel, WorldModelPrediction
from cohezion.agi.recursive_learning import LearningCycleResult, RecursiveLearningEngine
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.tensor_calculus import VectorTensor


def test_hyperbolic_world_model_predict_and_imagine():
    wm = HyperbolicWorldModel(state_dim=2048)
    p0 = PoincareManifoldND.project([0.01] * 2048, target_dim=2048)
    act = VectorTensor(tuple([0.05] + [0.0] * 2047), is_covariant=False)

    pred = wm.predict_next_state(p0, act)
    assert isinstance(pred, WorldModelPrediction)
    assert pred.predicted_state.dim == 2048
    assert pred.predicted_reward > 0.0
    assert pred.confidence > 0.0

    rollout = wm.imagine_rollout(p0, [act, act])
    assert len(rollout) == 2
    assert rollout[1].horizon_step == 2


@pytest.mark.asyncio
async def test_experiential_learning_engine():
    engine = ExperientialLearningEngine()
    p0 = PoincareManifoldND.project([0.01] * 2048, target_dim=2048)
    p1 = PoincareManifoldND.project([0.02] * 2048, target_dim=2048)

    record = await engine.process_experience("grid_bounds", p0, p1, reward=0.95)
    assert isinstance(record, ExperienceRecord)
    assert record.action_type == "grid_bounds"
    assert record.reward == 0.95
    assert record.verified is True
    assert record.proof_valid is True


@pytest.mark.asyncio
async def test_recursive_learning_engine():
    engine = RecursiveLearningEngine()
    res = await engine.execute_recursive_learning_cycle("Test trajectory summary")
    assert isinstance(res, LearningCycleResult)
    assert res.autoharness_score == 1.0
    assert res.autocontext_dim == 2048
    assert res.ctac_coherence >= 0.0
