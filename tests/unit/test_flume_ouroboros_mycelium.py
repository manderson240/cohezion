from cohezion.agi.flume_vae import FLUMEVAE, FLUMEEncoding, FLUMEReconstruction
from cohezion.agi.mycelium_network import MyceliumNetwork, TransportResult
from cohezion.agi.ouroboros import OuroborosCycleResult, OuroborosEngine
from cohezion.physics.poincare_manifold import PoincareManifoldND


def test_flume_vae_encode_decode():
    vae = FLUMEVAE(state_dim=2048, latent_dim=256)
    p2048 = PoincareManifoldND.project([0.01] * 2048, target_dim=2048)

    enc = vae.encode(p2048)
    assert isinstance(enc, FLUMEEncoding)
    assert len(enc.mu) == 256
    assert len(enc.latent_z) == 256

    rec = vae.decode(enc, p2048)
    assert isinstance(rec, FLUMEReconstruction)
    assert rec.reconstructed_point.dim == 2048
    assert rec.reconstruction_loss >= 0.0


def test_ouroboros_self_improvement():
    ouroboros = OuroborosEngine()
    res = ouroboros.run_self_improvement_cycle("cohezion.agi.autoharness_policy")

    assert isinstance(res, OuroborosCycleResult)
    assert res.verified_by_autoharness is True
    assert res.zk_proof.is_valid is True
    assert res.applied is True


def test_mycelium_network_growth_and_transport():
    net = MyceliumNetwork()
    net.grow_hypha("npu_agent", "igpu_agent", strength=0.9, nutrient_type="learning_vector")
    net.grow_hypha("npu_agent", "vault_node", strength=0.95, nutrient_type="context_vector")

    res = net.transport_nutrients("npu_agent")
    assert isinstance(res, TransportResult)
    assert res.delivered_nutrients == 2
    assert res.active_hyphae_count == 2
    assert res.network_coherence > 0.8
