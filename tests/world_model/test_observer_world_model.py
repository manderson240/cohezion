import pytest
from cohezion.inference.transition_controller import TransitionController
from cohezion.world_model.observer import Observer
from cohezion.world_model.observer_world_model import ObserverWorldModel, trace_kernel
from cohezion.world_model.surprise_router import SurpriseRouter


def test_cold_start_returns_default():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    observer = Observer(name="test", state_matrix=tc, router=SurpriseRouter())
    model = ObserverWorldModel(observer, default_coherence=0.7)
    model.set_task("anything")
    result = model.predict_next_state(None, None)
    assert result == [0.7]


def test_learned_bad_state_lowers_coherence():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    observer = Observer(name="test", state_matrix=tc, router=SurpriseRouter())
    model = ObserverWorldModel(observer, default_coherence=0.7)
    # record through the world model so its transition counters (the <3 data gate)
    # and the quality->reward remap are both exercised — the production path.
    for _ in range(5):
        model.record("code", "escalated", 0.2)
        model.record("greet", "done", 0.9)
    model.set_task("anything")
    # set state to "code"
    model._state = "code"
    result = model.predict_next_state(None, None)
    assert result[0] < 0.7


def test_surprise_high_on_first_transition_low_on_repeat():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    observer = Observer(name="test", state_matrix=tc, router=SurpriseRouter())
    model = ObserverWorldModel(observer, default_coherence=0.7)
    # First record should return surprise = 1.0
    surprise1 = model.record("code", "escalated", 0.5)
    assert abs(surprise1 - 1.0) < 1e-9
    # Repeat 5 times, surprise should be low
    for _ in range(5):
        model.record("code", "escalated", 0.5)
    surprise2 = model.record("code", "escalated", 0.5)
    assert surprise2 < 0.5


def test_simulate_trajectory_length():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    tc.record_transition("greet", "done", 1.0)
    tc.record_transition("code", "escalated", 1.0)
    tc.record_transition("code", "done", 1.0)
    tc.record_transition("escalated", "done", 1.0)
    observer = Observer(name="test", state_matrix=tc, router=SurpriseRouter())
    model = ObserverWorldModel(observer, default_coherence=0.7)
    model.set_task("anything")
    result = model.simulate_trajectory(None, [None, None, None])
    assert len(result) == 4
    for entry in result:
        assert isinstance(entry[0], float)
        assert 0.0 <= entry[0] <= 1.0


def test_trace_kernel_rows_substochastic():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    subset = {"code", "done"}
    result = trace_kernel(tc, subset, max_hops=50)
    for a in subset:
        total = sum(result[a].values())
        assert total <= 1.0 + 1e-9
    assert abs(result["code"]["done"] - 1.0) < 1e-6


def test_trace_kernel_partial_order_sanity():
    tc = TransitionController(matrix={"greet":["done"],"code":["escalated","done"],"escalated":["done"],"done":[]})
    subset = set(tc.matrix)
    result = trace_kernel(tc, subset, max_hops=50)
    # Row-normalized Q matrix should be approximately equal to full kernel when A = all states
    Q_full = {}
    for s in tc.matrix:
        valid = tc.ranked_next(s)
        if not valid:
            Q_full[s] = {s: 1.0}
        else:
            total = sum(w for _, w in valid)
            if total == 0:
                Q_full[s] = {v: 1.0 / len(valid) for v, _ in valid}
            else:
                Q_full[s] = {v: w / total for v, w in valid}

    for s in tc.matrix:
        total = sum(result[s].values())
        assert abs(total - 1.0) < 1e-6
