import pytest
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.agi.observational_monad import Observed, RecursiveTraceLogicEngine
from cohezion.agi.markov_chain import PoincareMarkovChain
from cohezion.agi.regenerative_software import RegenerativeSoftwareEngine
from cohezion.proactive.ambient_agent import AmbientAgent
from cohezion.proactive.sensing import UserEvent

def test_observational_monad_and_recursive_trace_logic():
    m1 = Observed.unit(10, initial_action="init")
    m2 = m1.bind(lambda x: Observed.unit(x * 2, initial_action="double"), action_name="step1")
    
    assert m2.value == 20
    assert len(m2.trace) >= 3
    
    predicate_valid = RecursiveTraceLogicEngine.evaluate_trace_predicate(m2, lambda obs: len(obs.action) > 0)
    assert predicate_valid is True

def test_poincare_markov_chain():
    p1 = PoincareManifoldND.project((0.1, 0.1), target_dim=2)
    p2 = PoincareManifoldND.project((0.2, 0.2), target_dim=2)
    
    mc = PoincareMarkovChain([p1, p2], temperature=1.0)
    res = mc.predict_next_state(0)
    
    assert res.current_state_idx == 0
    assert 0 <= res.next_state_idx <= 1
    assert 0.0 <= res.probability <= 1.0

def test_regenerative_software_engine():
    engine = RegenerativeSoftwareEngine()
    res = engine.heal_code_snippet("def add(a, b): return a + b")
    
    assert res.healed is True
    assert res.proof.is_valid is True
    assert len(res.proof.proof_bytes) == 32

def test_ambient_agent():
    agent = AmbientAgent("ambient_test")
    events = [UserEvent("code_edit", {"file": "a.py"}), UserEvent("code_edit", {"file": "b.py"})]
    
    res = agent.perceive_and_act(events)
    assert res.agent_id == "ambient_test"
    assert res.sensed_events_count == 2
    assert res.bypassed_llm is True
