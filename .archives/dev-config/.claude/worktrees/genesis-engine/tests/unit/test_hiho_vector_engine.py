"""Tests for the HihoVectorEngine (cohezion.swarm.hiho_vector_engine)."""

from __future__ import annotations

from cohezion.swarm.hiho_vector_engine import HihoVectorEngine


class TestHihoVectorEngine:
    def setup_method(self):
        self.engine = HihoVectorEngine()

    def test_peak_at_half(self):
        assert self.engine.calculate_hiho_score(0.5) == 1.0

    def test_symmetric_around_half(self):
        score_low = self.engine.calculate_hiho_score(0.3)
        score_high = self.engine.calculate_hiho_score(0.7)
        assert abs(score_low - score_high) < 1e-10

    def test_zero_coherence(self):
        score = self.engine.calculate_hiho_score(0.0)
        assert 0.0 < score < 0.1  # Very low but nonzero

    def test_one_coherence(self):
        score = self.engine.calculate_hiho_score(1.0)
        assert 0.0 < score < 0.1

    def test_monotonic_toward_half(self):
        s1 = self.engine.calculate_hiho_score(0.1)
        s2 = self.engine.calculate_hiho_score(0.3)
        s3 = self.engine.calculate_hiho_score(0.5)
        assert s1 < s2 < s3

    def test_custom_sigma(self):
        wide = HihoVectorEngine(sigma=1.0)
        narrow = HihoVectorEngine(sigma=0.1)
        # At coherence=0.3, wide sigma should give higher score
        assert wide.calculate_hiho_score(0.3) > narrow.calculate_hiho_score(0.3)

    def test_batch_scores(self):
        scores = self.engine.batch_scores([0.0, 0.25, 0.5, 0.75, 1.0])
        assert len(scores) == 5
        assert scores[2] == 1.0  # Peak at 0.5
        assert abs(scores[1] - scores[3]) < 1e-10  # Symmetric
