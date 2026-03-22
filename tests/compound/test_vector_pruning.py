"""Tests for Vector Pruning & Compaction Engine (Story 3.6, FR8)."""

from __future__ import annotations

import pytest

from cohezion.compound.vector_pruning import VectorPruningEngine


class TestVectorPruningEngine:
    def test_add_vector(self):
        """Vectors can be added to the space."""
        engine = VectorPruningEngine()
        engine.add_vector("v1", relevance=1.0)
        assert engine.active_count == 1

    def test_decay_reduces_relevance(self):
        """Each cycle reduces relevance by decay rate."""
        engine = VectorPruningEngine(decay_rate=0.1, prune_threshold=0.0)
        vec = engine.add_vector("v1", relevance=0.5)
        engine.run_cycle()
        assert vec.relevance == pytest.approx(0.4)

    def test_low_relevance_pruned(self):
        """Vectors below threshold are archived."""
        engine = VectorPruningEngine(decay_rate=0.5, prune_threshold=0.3)
        engine.add_vector("v1", relevance=0.4)
        engine.run_cycle()  # 0.4 - 0.5 = 0.0, below 0.3
        assert engine.active_count == 0
        assert engine.archived_count == 1

    def test_access_refreshes_relevance(self):
        """Accessing a vector boosts its relevance."""
        engine = VectorPruningEngine(decay_rate=0.1, prune_threshold=0.0)
        engine.add_vector("v1", relevance=0.5)
        engine.access("v1")
        vec = engine._vectors["v1"]
        assert vec.relevance > 0.5
        assert vec.access_count == 1

    def test_pruning_report(self):
        """Pruning cycle returns a report."""
        engine = VectorPruningEngine(decay_rate=0.01, prune_threshold=0.1)
        engine.add_vector("v1", relevance=1.0)
        report = engine.run_cycle()
        assert report.vectors_pruned == 0
        assert report.vectors_remaining == 1

    def test_compaction_trigger(self):
        """Compaction triggers after N cycles."""
        engine = VectorPruningEngine(decay_rate=0.0, prune_threshold=0.0, compaction_trigger=3)
        engine.add_vector("v1")
        assert not engine.should_compact()
        for _ in range(3):
            engine.run_cycle()
        assert engine.should_compact()

    def test_relevance_clamped_at_zero(self):
        """Relevance doesn't go below 0."""
        engine = VectorPruningEngine(decay_rate=0.9, prune_threshold=0.0)
        vec = engine.add_vector("v1", relevance=0.1)
        engine.run_cycle()
        assert vec.relevance == 0.0

    def test_relevance_clamped_at_one(self):
        """Relevance doesn't exceed 1.0 on access."""
        engine = VectorPruningEngine()
        engine.add_vector("v1", relevance=0.99)
        engine.access("v1")
        assert engine._vectors["v1"].relevance <= 1.0
