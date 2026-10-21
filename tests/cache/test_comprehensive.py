"""Comprehensive tests for cache modules.

Generated for P2 coverage of cache/ modules.
Tests semantic cache and cache statistics.
"""

from __future__ import annotations

import pytest

from cohezion.cache.semantic_cache import SemanticCache


class TestSemanticCache:
    """[P1] Tests for SemanticCache."""

    @pytest.fixture()
    def cache(self):
        """Create SemanticCache."""
        return SemanticCache(similarity_threshold=0.9)

    def test_cache_initialization(self, cache):
        """[P0] Should initialize cache."""
        assert cache is not None
        assert cache.similarity_threshold == 0.9

    def test_cache_with_defaults(self, monkeypatch):
        """[P1] Should use default values.

        The default threshold is not a constant: a saved calibration profile wins, otherwise it
        is calibrated to the active encoder's dimension (768D 0.58, 384D 0.80, 256D 0.45;
        exp_OOOO2/BBBB/RRRR). Both sources are stubbed so the result does not depend on which
        encoder or profile this machine happens to have.
        """
        monkeypatch.setattr(SemanticCache, "_load_profile_threshold", lambda self: None)
        monkeypatch.setattr(
            SemanticCache, "_auto_tune_threshold_for_encoder", staticmethod(lambda: 0.123)
        )
        cache = SemanticCache()
        assert cache.similarity_threshold == 0.123  # no profile: encoder calibration
        assert cache.max_l1_size == 512
        assert cache.max_l2_size == 1024

        monkeypatch.setattr(SemanticCache, "_load_profile_threshold", lambda self: 0.66)
        assert SemanticCache().similarity_threshold == 0.66  # a saved profile takes precedence

    def test_cache_stats_initially_zero(self, cache):
        """[P1] Should start with zero stats."""
        stats = cache.get_stats()
        assert stats["l1_hits"] == 0
        assert stats["l2_hits"] == 0

    def test_cache_get_stats_returns_dict(self, cache):
        """[P0] Should return stats dict."""
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "l1_hits" in stats
        assert "l2_hits" in stats


class TestSemanticCacheConfiguration:
    """[P1] Tests for cache configuration."""

    def test_custom_similarity_threshold(self):
        """[P1] Should accept custom threshold."""
        cache = SemanticCache(similarity_threshold=0.95)
        assert cache.similarity_threshold == 0.95

    def test_custom_cache_sizes(self):
        """[P1] Should accept custom cache sizes."""
        cache = SemanticCache(max_l1_size=256, max_l2_size=512)
        assert cache.max_l1_size == 256
        assert cache.max_l2_size == 512

    def test_adaptive_threshold_enabled(self):
        """[P1] Should enable adaptive threshold."""
        cache = SemanticCache(enable_adaptive_threshold=True)
        assert cache.enable_adaptive_threshold is True
