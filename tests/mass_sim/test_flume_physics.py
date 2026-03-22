import numpy as np
import pytest

from cohezion.mass_sim.flume_physics_py import FlumePhysicsPy


@pytest.fixture
def sample_weights():
    z_dim = 16
    hidden_dim = 32
    w1 = np.random.randn(hidden_dim, z_dim).astype(np.float32)
    b1 = np.zeros(hidden_dim, dtype=np.float32)
    w2 = np.random.randn(z_dim, hidden_dim).astype(np.float32)
    b2 = np.zeros(z_dim, dtype=np.float32)
    gamma = np.ones(hidden_dim, dtype=np.float32)
    beta = np.full(hidden_dim, 0.5, dtype=np.float32)
    return {
        "w1": w1,
        "b1": b1,
        "w2": w2,
        "b2": b2,
        "gamma": gamma,
        "beta": beta,
        "delta_scale": 0.01,
        "hiho_damping": 0.05,
    }


@pytest.fixture
def physics(sample_weights):
    return FlumePhysicsPy(**sample_weights)


@pytest.mark.fast
def test_forward_pass_shape(physics):
    batch_size = 10
    z_dim = 16
    z = np.random.rand(batch_size, z_dim).astype(np.float32)
    delta = physics._forward(z)
    assert delta.shape == (batch_size, z_dim)


@pytest.mark.fast
def test_simulate_epochs_batch(physics):
    batch_size = 5
    z_dim = 16
    n_epochs = 3
    agents = np.random.rand(batch_size, z_dim).astype(np.float32)
    evolved = physics.simulate_epochs_batch(agents, n_epochs)
    assert evolved.shape == (batch_size, z_dim)
    assert not np.allclose(agents, evolved)


@pytest.mark.fast
def test_simulate_epochs_navigated(physics):
    batch_size = 5
    z_dim = 16
    n_epochs = 3
    agents = np.random.rand(batch_size, z_dim).astype(np.float32)
    evolved = physics.simulate_epochs_navigated(agents, n_epochs)
    assert evolved.shape == (batch_size, z_dim)
    assert not np.allclose(agents, evolved)


@pytest.mark.fast
def test_bounds_metrics():
    # Construct agents exactly so we know logic
    # Agent 0: all inside [0.3, 0.7] -> [0.5, 0.5]
    # Agent 1: 1 inside, 1 outside -> [0.5, 0.9]
    # Agent 2: all outside -> [0.1, 0.9]
    # Agent 3: 1 inside, 1 outside -> [0.2, 0.4]
    # Total elements = 8.
    # Inside elements: 0.5, 0.5, 0.5, 0.4 -> 4 elements out of 8 (0.5 pct)
    # Agents all inside: Agent 0 -> 1 out of 4 (0.25 pct)
    # Agents >80% inside: we need >80% to be true. Let's use 5 dims to test >80%.
    # 5 dims means 5*0.8 = 4.0, so needs 5 inside to be >80% (actually wait >0.8 means strictly greater, 4/5=0.8 so needs 5/5. Let's do 10 dims).

    # Let's test with 10 dims to get exact 80% fractions
    # Agent 0: 10/10 in bounds
    # Agent 1: 9/10 in bounds (90% -> majority)
    # Agent 2: 8/10 in bounds (80% -> NOT >80%)
    # Agent 3: 0/10 in bounds

    agents = np.zeros((4, 10), dtype=np.float32)
    agents[0, :] = 0.5
    agents[1, :9] = 0.5
    agents[1, 9] = 0.9
    agents[2, :8] = 0.5
    agents[2, 8:] = 0.1
    agents[3, :] = 0.1

    # Fake weights just to call compute_batch_stats
    dummy_w1 = np.zeros((1, 10))
    dummy_w2 = np.zeros((10, 1))
    dummy_b1 = np.zeros(1)
    dummy_b2 = np.zeros(10)
    gamma = np.zeros(1)
    beta = np.zeros(1)
    physics = FlumePhysicsPy(dummy_w1, dummy_b1, dummy_w2, dummy_b2, gamma, beta)

    stats = physics.compute_batch_stats(agents)

    # pct_within_bounds (all dims in bounds) -> Agent 0 only -> 1/4 = 0.25
    assert np.isclose(stats["pct_within_bounds"], 0.25)

    # pct_elements_within_bounds -> (10 + 9 + 8 + 0) = 27 / 40 = 0.675
    assert np.isclose(stats["pct_elements_within_bounds"], 0.675)

    # pct_agents_majority_in_bounds -> >80% -> 9/10 and 10/10 -> Agents 0 and 1 -> 2/4 = 0.5
    assert np.isclose(stats["pct_agents_majority_in_bounds"], 0.5)
