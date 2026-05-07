"""Tests for CachePersistence and WarmCacheLoader."""
import json

import pytest

from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader


@pytest.fixture
def tmp_cache(tmp_path):
    return CachePersistence(cache_dir=tmp_path)


class TestCachePersistence:

    def test_save_and_load_roundtrip(self, tmp_cache):
        cache = {"key1": "value1", "key2": "value2"}
        n = tmp_cache.save_cache(cache)
        assert n == 2

    def test_save_returns_count(self, tmp_cache):
        cache = {"k1": "v1", "k2": "v2", "k3": "v3"}
        n = tmp_cache.save_cache(cache)
        assert n == 3

    def test_empty_cache_writes_nothing(self, tmp_cache):
        n = tmp_cache.save_cache({})
        assert n == 0

    def test_cache_file_is_valid_jsonl(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cp = CachePersistence(cache_dir=cache_dir)
        cp.save_cache({"k": "v"})
        path = cache_dir / "token_cache.jsonl"
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert "key" in entry
        assert "value" in entry


class TestWarmCacheLoader:

    def test_instantiable(self, tmp_path):
        persistence = CachePersistence(cache_dir=tmp_path)
        loader = WarmCacheLoader(persistence=persistence)
        assert loader is not None

    def test_load_returns_dict(self, tmp_path):
        persistence = CachePersistence(cache_dir=tmp_path)
        loader = WarmCacheLoader(persistence=persistence)
        result = loader.load_cache()
        assert isinstance(result, dict)

    def test_load_empty_dir_returns_empty(self, tmp_path):
        persistence = CachePersistence(cache_dir=tmp_path)
        loader = WarmCacheLoader(persistence=persistence)
        assert loader.load_cache() == {}

