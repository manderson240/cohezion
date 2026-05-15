"""Coverage batch Z57: vector_pruning, usd_simulator."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/vector_pruning.py
# ---------------------------------------------------------------------------


class TestVectorPruningEngine:
    def _make_engine(self, decay_rate=0.1, prune_threshold=0.2, compaction_trigger=5):
        from cohezion.compound.vector_pruning import VectorPruningEngine

        return VectorPruningEngine(
            decay_rate=decay_rate,
            prune_threshold=prune_threshold,
            compaction_trigger=compaction_trigger,
        )

    def _make_vector(self, vector_id="v1", relevance=0.9):
        from cohezion.compound.vector_pruning import SemanticVector

        return SemanticVector(vector_id=vector_id, relevance=relevance)

    def test_semantic_vector_decay(self):
        vec = self._make_vector(relevance=0.5)
        vec.decay(0.1)
        assert vec.relevance == pytest.approx(0.4)

    def test_semantic_vector_decay_floor_at_zero(self):
        vec = self._make_vector(relevance=0.05)
        vec.decay(0.1)
        assert vec.relevance == pytest.approx(0.0)

    def test_pruning_report_dataclass(self):
        from cohezion.compound.vector_pruning import PruningReport

        report = PruningReport(vectors_pruned=2, vectors_remaining=8, avg_relevance=0.7)
        assert report.vectors_pruned == 2

    def test_add_vector(self):
        engine = self._make_engine()
        engine.add_vector("v1", relevance=0.9)
        assert "v1" in engine._vectors

    def test_run_cycle_decays_relevance(self):
        engine = self._make_engine(decay_rate=0.1, prune_threshold=0.05)
        engine.add_vector("v1", relevance=0.8)
        report = engine.run_cycle()
        assert engine._vectors["v1"].relevance < 0.8

    def test_run_cycle_prunes_low_relevance(self):
        engine = self._make_engine(decay_rate=0.5, prune_threshold=0.4)
        engine.add_vector("low", relevance=0.3)  # below threshold after decay
        report = engine.run_cycle()
        assert engine._vectors["low"].archived is True
        assert report.vectors_pruned == 1

    def test_run_cycle_report_has_correct_counts(self):
        engine = self._make_engine(decay_rate=0.1, prune_threshold=0.8)
        engine.add_vector("high", relevance=0.95)
        engine.add_vector("low", relevance=0.5)  # will be pruned (0.5 - 0.1 = 0.4 < 0.8)
        report = engine.run_cycle()
        assert report.vectors_remaining == 1

    def test_should_compact_below_trigger(self):
        engine = self._make_engine(compaction_trigger=5)
        assert engine.should_compact() is False

    def test_should_compact_after_enough_cycles(self):
        engine = self._make_engine(compaction_trigger=2)
        engine.add_vector("v1", relevance=0.9)
        engine.run_cycle()
        engine.run_cycle()
        assert engine.should_compact() is True

    def test_run_cycle_empty_engine(self):
        engine = self._make_engine()
        report = engine.run_cycle()
        assert report.vectors_pruned == 0
        assert report.vectors_remaining == 0
        assert report.avg_relevance == pytest.approx(0.0)

    def test_archive_grows_with_pruning(self):
        engine = self._make_engine(decay_rate=0.5, prune_threshold=0.4)
        engine.add_vector("v1", relevance=0.3)
        engine.add_vector("v2", relevance=0.35)
        engine.run_cycle()
        assert len(engine._archive) == 2


# ---------------------------------------------------------------------------
# Module 2: physics/usd_simulator.py
# ---------------------------------------------------------------------------


class TestUSDSimulator:
    def _make_sim(self, voltage_kv=10.0, pulse_duration_us=100.0, water_conductivity=0.05):
        from cohezion.physics.usd_simulator import USDSimulator

        return USDSimulator(
            voltage_kv=voltage_kv,
            pulse_duration_us=pulse_duration_us,
            water_conductivity=water_conductivity,
        )

    def test_itonic_cluster_dataclass(self):
        from cohezion.physics.usd_simulator import ItonicCluster

        cluster = ItonicCluster(
            coherence=0.5,
            charge=-1.6e-19,
            magnetic_moment=0.1,
            radius_nm=50.0,
            lifetime_us=100.0,
            num_electrons=1000,
        )
        assert cluster.coherence == pytest.approx(0.5)
        assert cluster.num_electrons == 1000

    def test_calculate_energy(self):
        sim = self._make_sim(voltage_kv=10.0, pulse_duration_us=100.0)
        energy = sim.calculate_energy()
        assert energy > 0

    def test_create_plasma_bubble(self):
        sim = self._make_sim()
        energy = sim.calculate_energy()
        bubble = sim.create_plasma_bubble(energy)
        assert bubble is not None

    def test_force_charge_clustering(self):
        sim = self._make_sim()
        energy = sim.calculate_energy()
        bubble = sim.create_plasma_bubble(energy)
        cluster = sim.force_charge_clustering(bubble)
        assert cluster is not None

    def test_form_itonic_cluster_check_coherence(self):
        sim = self._make_sim()
        cluster_data = {
            "coherence": 0.6,
            "charge_coulombs": -1e-17,
            "magnetic_moment": 0.5,
            "radius_nm": 100.0,
            "num_electrons": 100,
        }
        result = sim.form_itonic_cluster(cluster_data)
        assert result is not None

    def test_form_itonic_cluster_below_threshold_returns_none(self):
        sim = self._make_sim()
        cluster_data = {
            "coherence": 0.1,  # below HIHO threshold
            "charge": -1e-17,
            "magnetic_moment": 0.5,
            "radius_nm": 100.0,
            "num_electrons": 100,
        }
        result = sim.form_itonic_cluster(cluster_data)
        assert result is None

    def test_generate_spark_returns_value(self):
        sim = self._make_sim(voltage_kv=15.0)
        # Multiple attempts to find a spark
        result = sim.generate_spark(num_attempts=10)
        # May or may not produce a cluster depending on random probability
        assert result is None or hasattr(result, "coherence")
