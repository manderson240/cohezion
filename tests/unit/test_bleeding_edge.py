import pytest
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.tensor_calculus import VectorTensor
from cohezion.physics.geodesic_flow_ode import GeodesicState, GeodesicFlowODE
from cohezion.inference.speculative_engine import LocalSpeculativeEngine, SpeculativeBatch

def test_geodesic_flow_rk4_step():
    pt = PoincareManifoldND.project(tuple([0.05] * 12))
    vel = VectorTensor(tuple([0.1] + [0.0] * 11))
    state_0 = GeodesicState(position=pt, velocity=vel, time=0.0)

    state_1 = GeodesicFlowODE.step_rk4(state_0, dt=0.01)
    assert isinstance(state_1, GeodesicState)
    assert state_1.time == pytest.approx(0.01)
    assert state_1.position.dim == 12

def test_local_speculative_decoding():
    engine = LocalSpeculativeEngine(k_speculative=4)
    drafts = ["def", " calculate", "_trajectory", "("]

    batch = engine.verify_draft_batch(drafts)
    assert isinstance(batch, SpeculativeBatch)
    assert batch.acceptance_rate == 1.0
    assert batch.latency_saved_ms > 0.0
