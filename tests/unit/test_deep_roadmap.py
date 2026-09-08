from cohezion.agi.zkfv_compiler import ZKFVCompiler, ZKProof
from cohezion.physics.ctac_engine import CTACEngine, TopologicalState
from cohezion.physics.poincare_manifold import PoincareManifoldND


def test_ctac_engine_calibration():
    engine = CTACEngine(target_coherence=0.50)
    pts = [
        PoincareManifoldND.project(tuple([0.05] * 12)),
        PoincareManifoldND.project(tuple([0.10] * 12)),
    ]

    state = engine.evaluate_topology(pts, current_kappa=1.0)
    assert isinstance(state, TopologicalState)
    assert state.betti_0 >= 1.0
    assert 0.0 <= state.coherence <= 1.0


def test_zkfv_compiler_proof():
    gates = ZKFVCompiler.compile_ast_to_gates("autonomy_rule")
    assert len(gates) == 2

    # Valid inputs: a=2, b=3, c=5 (satisfies a + b - c = 0 and a - a = 0)
    proof_valid = ZKFVCompiler.generate_proof(gates, (5.0, 0.0, 5.0))
    assert isinstance(proof_valid, ZKProof)
    assert proof_valid.is_valid is True
    assert proof_valid.verification_time_ms < 5.0
