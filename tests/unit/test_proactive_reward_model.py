import pytest
from cohezion.proactive.proactive_reward_model import ProactiveRewardModel, RewardComponents
from cohezion.proactive.counterfactual_gym import CounterfactualProactiveGym, CounterfactualRollout
from cohezion.proactive.sensing import UserEvent

def test_reward_components_score():
    rc = RewardComponents(utility=0.90, intrusiveness_penalty=0.10, timing_precision=0.90)
    score = rc.total_score(gamma=0.5, tau=0.3)
    # 0.90 - (0.5 * 0.10) + (0.3 * 0.90) = 0.90 - 0.05 + 0.27 = 1.12
    assert pytest.approx(score) == 1.12

def test_proactive_reward_model_evi():
    rm = ProactiveRewardModel(evi_threshold=0.25)
    should_act, evi = rm.should_intervene("run_verification_tests", user_busy_state=False)

    assert should_act is True
    assert evi >= 0.25

def test_counterfactual_gym_rollout():
    gym = CounterfactualProactiveGym()
    events = [UserEvent("code_edit", {"file": "main.py"})]
    rollout = gym.simulate_rollout("memory_headroom_recovery", events, user_busy=False)

    assert isinstance(rollout, CounterfactualRollout)
    assert rollout.recommendation == "INTERVENE"
    assert rollout.evi > 0.0
