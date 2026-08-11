import pytest
from cohezion.proactive.sensing import ActivitySensingGym, UserEvent
from cohezion.proactive.predictor import ProactiveGoalPredictor, GoalPrediction
from cohezion.proactive.trigger_gate import ProactiveTriggerGate
from cohezion.proactive.agent import ProactiveAgent, ProactiveResult

def test_activity_sensing_gym():
    gym = ActivitySensingGym(max_history=5)
    for i in range(10):
        gym.log_event("code_edit", {"file": f"test_{i}.py"})

    recent = gym.get_recent_events(count=10)
    assert len(recent) == 5  # Max history cap enforced
    assert recent[-1].payload["file"] == "test_9.py"

def test_proactive_goal_predictor_rule():
    events = [
        UserEvent("code_edit", {"file": "a.py"}),
        UserEvent("code_edit", {"file": "b.py"}),
    ]
    pred = ProactiveGoalPredictor.predict_goal(events)
    assert pred.predicted_goal == "run_verification_tests"
    assert pred.confidence >= 0.75

def test_proactive_trigger_gate():
    pred_high = GoalPrediction("test", confidence=0.85, suggested_action="act", rationale="r")
    pred_low = GoalPrediction("test", confidence=0.50, suggested_action="act", rationale="r")

    assert ProactiveTriggerGate.should_trigger(pred_high, min_threshold=0.75) is True
    assert ProactiveTriggerGate.should_trigger(pred_low, min_threshold=0.75) is False

from unittest.mock import patch
from cohezion.reliability.oom_guard import MemoryState

def test_proactive_agent_orchestration():
    agent = ProactiveAgent(confidence_threshold=0.75)
    agent.record_activity("code_edit", {"file": "contracts.py"})
    agent.record_activity("code_edit", {"file": "agent.py"})

    with patch("cohezion.proactive.agent.OOMGuard.get_memory_state", return_value=MemoryState(available_gb=50.0, total_gb=128.0, swap_used_gb=0.0, is_safe=True)):
        res = agent.evaluate_and_act()
        assert isinstance(res, ProactiveResult)
        assert res.triggered is True
        assert res.verified is True
        assert res.bypassed_llm is True
        assert res.execution_time_ms < 50.0  # Zero-cost execution latency
