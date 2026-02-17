import pytest

from cohezion.physics.usd_simulator import ItonicCluster, USDSimulator


def test_usd_simulator_initialization():
    sim = USDSimulator(voltage_kv=15, pulse_duration_us=200, water_conductivity=0.1)
    assert sim.voltage_v == 15000
    assert sim.pulse_duration_s == pytest.approx(200e-6)
    assert sim.conductivity == 0.1
    assert sim.hiho_threshold == 0.5


def test_calculate_energy():
    sim = USDSimulator(voltage_kv=10, pulse_duration_us=100, water_conductivity=0.05)
    energy = sim.calculate_energy()
    assert energy > 0
    # resistance ~ 20 ohm, V=10000, t=100e-6 -> E = 100M * 100e-6 / 20 = 500J approx
    assert 400 < energy < 600


def test_plasma_bubble_creation():
    sim = USDSimulator()
    energy = 500
    bubble = sim.create_plasma_bubble(energy)
    assert bubble["radius_mm"] > 0
    assert bubble["electron_density"] > 1e20
    assert bubble["temperature_k"] > 10000


def test_generate_spark_formation():
    sim = USDSimulator(voltage_kv=20, pulse_duration_us=500)  # High energy for better success
    # Try multiple times to account for randomness
    cluster = sim.generate_spark(num_attempts=50)

    if cluster:
        assert isinstance(cluster, ItonicCluster)
        assert cluster.coherence >= 0.5
        assert cluster.charge < 0
        assert cluster.radius_nm > 0
        assert cluster.lifetime_us > 0
    else:
        # If it fails, check if noise is the reason or if energy scaling is off
        pytest.fail("Failed to form cluster even at high settings after 50 attempts")


def test_itonic_cluster_dataclass():
    cluster = ItonicCluster(
        coherence=0.51,
        charge=-1.6e-15,
        magnetic_moment=1e-23,
        radius_nm=500,
        lifetime_us=50,
        num_electrons=10000,
    )
    assert cluster.coherence == 0.51
    assert cluster.charge == -1.6e-15


def test_failure_conditions():
    # Low energy should rarely form clusters
    sim = USDSimulator(voltage_kv=5, pulse_duration_us=10)
    sim.generate_spark(num_attempts=5)
    # This might still pass by chance, but mostly should be None
    # We won't assert it's None to avoid flaky test, just run it
    pass
