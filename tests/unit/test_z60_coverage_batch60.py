"""Coverage batch Z60: cache_persistence, substrate_governor."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/cache_persistence.py
# ---------------------------------------------------------------------------


class TestCachePersistence:
    def _make_persistence(self, tmp_path):
        from cohezion.compound.cache_persistence import CachePersistence

        return CachePersistence(cache_dir=tmp_path)

    def test_save_cache_writes_jsonl(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        cache = {"key1": "value1", "key2": "value2"}
        count = persistence.save_cache(cache)
        assert count == 2
        path = tmp_path / "token_cache.jsonl"
        assert path.exists()
        lines = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert len(lines) == 2

    def test_save_cache_with_dict_value_obj(self, tmp_path):
        persistence = self._make_persistence(tmp_path)

        class HasToDict:
            def to_dict(self):
                return {"answer": 42}

        cache = {"k1": HasToDict()}
        count = persistence.save_cache(cache)
        assert count == 1

    def test_save_cache_with_dunder_dict_obj(self, tmp_path):
        persistence = self._make_persistence(tmp_path)

        class HasDunderDict:
            def __init__(self):
                self.x = 1
                self.y = 2

        cache = {"k1": HasDunderDict()}
        count = persistence.save_cache(cache)
        assert count == 1

    def test_save_cache_with_metadata(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        cache = {"k1": "v1"}
        count = persistence.save_cache(cache, metadata={"session": "s123"})
        assert count == 1
        lines = [json.loads(line) for line in (tmp_path / "token_cache.jsonl").read_text().strip().splitlines()]
        assert lines[0]["session"] == "s123"

    def test_load_cache_empty_dir(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        result = persistence.load_cache()
        assert result == {}

    def test_load_cache_round_trip(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        cache = {"k1": "v1", "k2": "v2", "k3": "v3"}
        persistence.save_cache(cache)
        loaded = persistence.load_cache(max_entries=10)
        assert "k1" in loaded
        assert loaded["k1"] == "v1"

    def test_load_cache_respects_max_entries(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        cache = {f"k{i}": f"v{i}" for i in range(10)}
        persistence.save_cache(cache)
        loaded = persistence.load_cache(max_entries=3)
        assert len(loaded) == 3

    def test_get_cache_stats_no_file(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        stats = persistence.get_cache_stats()
        assert stats["exists"] is False
        assert stats["entries"] == 0

    def test_get_cache_stats_with_file(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        persistence.save_cache({"k1": "v1", "k2": "v2"})
        stats = persistence.get_cache_stats()
        assert stats["exists"] is True
        assert stats["entries"] == 2

    def test_warm_cache_loader(self, tmp_path):
        from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader

        persistence = CachePersistence(cache_dir=tmp_path)
        persistence.save_cache({"key1": "val1", "key2": "val2"})

        loader = WarmCacheLoader(persistence=persistence)
        mock_client = MagicMock()
        mock_client._cache = {}
        mock_client._cache_max_size = 10
        loaded = loader.warm_client(mock_client, max_entries=5)
        assert loaded == 2


# ---------------------------------------------------------------------------
# Module 2: core/substrate_governor.py
# ---------------------------------------------------------------------------


class TestSubstrateGovernor:
    def _make_governor(self):
        from cohezion.core.substrate_governor import SubstrateGovernor

        return SubstrateGovernor()

    def test_dilation_state_to_dict(self):
        from cohezion.core.substrate_governor import DilationState, PressureLevel

        state = DilationState(factor=1.5, pressure=0.92, level=PressureLevel.ELEVATED)
        d = state.to_dict()
        assert d["factor"] == pytest.approx(1.5)
        assert d["level"] == "elevated"

    def test_governor_event_dataclass(self):
        from cohezion.core.substrate_governor import GovernorEvent

        ev = GovernorEvent(event_type="dilation_start", pressure=0.91, dilation_factor=1.2)
        assert ev.event_type == "dilation_start"

    def test_normal_pressure_no_dilation(self):
        from cohezion.core.substrate_governor import PressureLevel

        governor = self._make_governor()
        state = governor.update_pressure(0.5)
        assert state.factor == pytest.approx(1.0)
        assert state.level == PressureLevel.NORMAL

    def test_elevated_pressure_triggers_dilation(self):
        from cohezion.core.substrate_governor import PressureLevel

        governor = self._make_governor()
        state = governor.update_pressure(0.92)
        assert state.factor > 1.0
        assert state.level == PressureLevel.ELEVATED

    def test_critical_pressure_triggers_emergency(self):
        from cohezion.core.substrate_governor import PressureLevel

        governor = self._make_governor()
        state = governor.update_pressure(0.96)
        assert state.level == PressureLevel.CRITICAL

    def test_recovery_removes_dilation(self):
        from cohezion.core.substrate_governor import PressureLevel

        governor = self._make_governor()
        governor.update_pressure(0.92)  # elevate
        assert governor._state.factor > 1.0
        state = governor.update_pressure(0.80)  # below recovery target
        assert state.factor == pytest.approx(1.0)
        assert state.level == PressureLevel.NORMAL

    def test_get_pulse_interval_scales_with_dilation(self):
        governor = self._make_governor()
        governor.update_pressure(0.92)
        interval = governor.get_pulse_interval(base_interval_ms=100.0)
        assert interval > 100.0

    def test_get_pulse_interval_normal(self):
        governor = self._make_governor()
        interval = governor.get_pulse_interval(100.0)
        assert interval == pytest.approx(100.0)

    def test_events_accumulate(self):
        governor = self._make_governor()
        governor.update_pressure(0.92)
        governor.update_pressure(0.80)
        events = governor._events
        assert len(events) >= 2  # at least dilation_start + recovery
