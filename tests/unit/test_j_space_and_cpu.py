from cohezion.inference.cpu_inference_engine import CPUInferenceEngine, CPUInferenceResult
from cohezion.physics.j_space_manifold import JSpaceManifold, JSpaceProjection
from cohezion.physics.poincare_manifold import PoincareManifoldND


def test_j_space_manifold_projection_and_reconstruction():
    j_engine = JSpaceManifold(soul_dim=2048, j_dim=256)
    p2048 = PoincareManifoldND.project([0.01] * 2048, target_dim=2048)

    proj = j_engine.project_to_j_space(p2048)
    assert isinstance(proj, JSpaceProjection)
    assert len(proj.j_vector) == 256
    assert proj.reconstructed_soul.dim == 2048
    assert proj.holographic_loss >= 0.0
    assert 0.0 <= proj.workspace_coherence <= 1.0


def test_cpu_inference_engine():
    cpu = CPUInferenceEngine(threads=32)
    res = cpu.execute_cpu_inference("Analyze CPU parallel performance.")

    assert isinstance(res, CPUInferenceResult)
    assert res.threads_used == 32
    assert res.available_ram_gb > 0.0
    assert res.latency_ms >= 0.0
