import numpy as np
import pytest

from cohezion.universe.hiho_unified_engine import (
    BioelectricsEngine,
    CellularAutomataEngine,
    CellularAutomataState,
    ChaosTheoryEngine,
    ChaosTheoryParameters,
    EsotericPhysicsEngine,
    EVOInitializationFactory,
    EvoState,
    HIHOStabilizationEngine,
    HIHOUnifiedEngine,
    MagnetohydrodynamicsEngine,
    PenroseTwistorEngine,
    QuantumEmergenceEngine,
    SacredGeometryEngine,
)


@pytest.mark.fast
def test_cellular_automata_rule_30():
    """Test standard Rule 30 Cellular Automata evolution."""
    config = CellularAutomataState(grid_size=5, rule=30, state=[0, 0, 1, 0, 0])
    ca = CellularAutomataEngine(config)

    # Rule 30 binary is 00011110 -> [0, 0, 0, 1, 1, 1, 1, 0] reversed
    # For (0, 1, 0) -> pattern is 2 -> binary index 2 -> 1
    # Check manual step
    state_1 = ca.evolve()
    assert state_1 == [0, 1, 1, 1, 0]

    state_2 = ca.evolve()
    assert state_2 == [1, 1, 0, 0, 1]


@pytest.mark.fast
def test_chaos_theory_divergence():
    """Test chaos theory exponential divergence over time."""
    params = ChaosTheoryParameters(lyapunov_exponent=1.0, sensitivity=1e-5)
    chaos = ChaosTheoryEngine(params)

    d1 = chaos.compute_divergence(0.0)
    assert d1 == pytest.approx(1e-5)

    d2 = chaos.compute_divergence(1.0)
    assert d2 == pytest.approx(1e-5 * np.exp(1.0))


@pytest.mark.fast
def test_chaos_theory_butterfly_effect():
    """Test butterfly effect perturbation scaling on latent vectors."""
    params = ChaosTheoryParameters(lyapunov_exponent=2.0, sensitivity=0.001)
    chaos = ChaosTheoryEngine(params)

    np.random.seed(42)
    vec = np.zeros(256)

    perturbed_vec = chaos.apply_butterfly_effect(vec, 0.0)
    # The magnitude of perturbation should be exactly sensitivity
    expected_std = 0.001
    assert np.std(perturbed_vec) == pytest.approx(expected_std, rel=0.1)

    perturbed_vec_later = chaos.apply_butterfly_effect(vec, 1.0)
    expected_std_later = 0.001 * np.exp(2.0)
    assert np.std(perturbed_vec_later) == pytest.approx(expected_std_later, rel=0.1)


@pytest.mark.asyncio
@pytest.mark.fast
async def test_hiho_unified_engine_step():
    """Test HIHOUnifiedEngine orchestrates CA and Chaos correctly."""
    engine = HIHOUnifiedEngine(ca_rule=110, chaos_lyapunov=0.5)

    vectors = [np.ones(12) for _ in range(3)]
    np.random.seed(42)

    evolved = await engine.step_simulation(vectors)

    assert len(evolved) == 3
    assert engine.current_time == 0.01

    # Check that CA evolved
    assert engine.ca_engine.config.state.count(1) > 1

    # Vectors should be perturbed
    for vec in evolved:
        assert vec.shape == (12,)
        # Should no longer be exactly 1.0 due to chaos and fabric coupling
        assert not np.allclose(vec, np.ones(12))


@pytest.mark.fast
def test_mhd_engine():
    """Test MHD forces on an EVO latent vector."""
    mhd = MagnetohydrodynamicsEngine()
    evo = EvoState(magnetic_helicity=1.0, toroidal_moment=2.0, coherence=0.5)
    vec = np.array([1.0, 0.0, 1.0])

    # Twist angle should be dt * helicity = 0.1 * 1.0 = 0.1 rad
    dt = 0.1
    evolved = mhd.apply_mhd_forces(evo, vec, dt)

    # Helicity twist rotation
    # Initial was (1, 0), rotation makes it (cos, sin)
    # Then toroidal scaling: norm was sqrt(2) ~ 1.414.
    # Attractor is 2.0, so it scales up by 1 + (2.0 - 1.414)*0.1*0.1 ≈ 1.0058
    assert evolved[0] > 0.9  # Roughly cos(0.1) * scale
    assert evolved[1] > 0.0  # Roughly sin(0.1) * scale
    assert evolved[2] > 1.0  # Just scaled up

    # Coherence dissipates charge: density * exp(-dt * 0.5)
    assert evo.charge_density == pytest.approx(1.0 * np.exp(-0.05))


@pytest.mark.fast
def test_sacred_geometry_torus():
    """Test Sacred Geometry Torus mapping."""
    geo = SacredGeometryEngine()

    # Test a point exactly on the torus surface:
    # R=2.0, r=0.5
    # If point is at x=2.5, y=0, z=0
    # dist = (sqrt(2.5^2) - 2.0)^2 + 0 - 0.5^2 = 0.5^2 - 0.25 = 0
    vec = np.array([2.5, 0.0, 0.0])
    align = geo.compute_torus_alignment(vec, major_r=2.0, minor_r=0.5)
    assert align == pytest.approx(1.0)

    # Point off surface
    vec2 = np.array([0.0, 0.0, 0.0])
    # dist = (0 - 2)^2 - 0.25 = 3.75
    align2 = geo.compute_torus_alignment(vec2, major_r=2.0, minor_r=0.5)
    assert align2 == pytest.approx(np.exp(-3.75))


@pytest.mark.fast
def test_penrose_twistor_engine():
    """Test Penrose Twistor mapping phase shift."""
    twistor = PenroseTwistorEngine()

    vec = np.array([1.0, 0.0, 0.0, 1.0])
    mapped = twistor.apply_twistor_mapping(vec)

    expected_0 = 1.0 * np.cos(0.5) - 0.0 * np.sin(0.5)
    expected_2 = 1.0 * np.sin(0.5) + 0.0 * np.cos(0.5)

    expected_1 = 0.0 * np.cos(0.5) + 1.0 * np.sin(0.5)
    expected_3 = -0.0 * np.sin(0.5) + 1.0 * np.cos(0.5)

    assert mapped[0] == pytest.approx(expected_0)
    assert mapped[1] == pytest.approx(expected_1)
    assert mapped[2] == pytest.approx(expected_2)
    assert mapped[3] == pytest.approx(expected_3)


@pytest.mark.fast
def test_evo_initialization():
    """Test EVO initialization generates correctly bounded states."""
    evo = EVOInitializationFactory.create_evo(seed=42)
    assert 0.8 <= evo.charge_density <= 1.2
    assert -0.5 <= evo.magnetic_helicity <= 0.5
    assert 0.5 <= evo.toroidal_moment <= 2.0
    assert evo.coherence == 0.5


@pytest.mark.fast
def test_hiho_stabilization_engine():
    """Test HIHO Stabilization drives coherence toward 0.5."""
    engine = HIHOStabilizationEngine()

    evo = EvoState(
        charge_density=1.0,
        magnetic_helicity=0.0,
        toroidal_moment=1.0,
        coherence=0.4,  # Below 0.5
    )
    vec = np.array([1.0, 2.0, 3.0])

    # Run loop
    new_evo, new_vec = engine.apply_hiho_loop(evo, vec, dt=0.1)

    # 0.5 - 0.4 = 0.1 delta
    # restoring_force = 2.0 * 0.1 * 0.1 = 0.02
    assert new_evo.coherence == pytest.approx(0.42)
    # Vec shouldn't decay yet (delta is 0.1 <= 0.4)
    np.testing.assert_array_equal(vec, new_vec)

    # Extreme case
    evo.coherence = 1.0
    new_evo, new_vec = engine.apply_hiho_loop(evo, vec, dt=0.01)
    # delta = -0.5, restoring_force = 2.0 * -0.5 * 0.01 = -0.01
    # new coherence = 0.99
    # abs(0.99 - 0.5) > 0.4 => decay applied
    assert np.all(new_vec < vec)  # Array decayed


@pytest.mark.fast
def test_quantum_emergence_engine():
    """Test ER=EPR and quantization."""
    engine = QuantumEmergenceEngine()
    vec = np.array([0.15, 0.25])

    mapped = engine.apply_quantum_effects(vec, chirality=0.0)

    # First quantized: 0.15 -> 0.2, 0.25 -> 0.2
    # Chirality 0 means no rotation
    assert mapped[0] == pytest.approx(0.2)
    assert mapped[1] == pytest.approx(0.2)  # 0.25 rounds to 0.2


@pytest.mark.fast
def test_bioelectrics_engine():
    """Test biologically-attracted states."""
    engine = BioelectricsEngine()
    vec = np.array([0.0, 0.0, 0.0])

    # Coherence = 1.0 -> strength = tanh(1.0) ~ 0.76
    mapped = engine.apply_morphogenetic_field(vec, coherence=1.0)

    # Shifted towards attractor [1,1,1]
    assert np.all(mapped > 0.0)
    assert np.all(mapped < 0.1)


@pytest.mark.fast
def test_esoteric_physics_engine():
    """Test scaling of Triune Self dimensions."""
    engine = EsotericPhysicsEngine()
    vec = np.array([1.0, 1.0, 1.0, 1.0])

    mapped = engine.apply_triune_self(vec)

    assert mapped[0] == pytest.approx(1.05)
    assert mapped[1] == pytest.approx(1.02)
    assert mapped[2] == pytest.approx(1.01)
    assert mapped[3] == pytest.approx(1.0)
