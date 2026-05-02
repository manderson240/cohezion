"""Tests for compound cache persistence, metrics persistence, and session management."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader
from cohezion.compound.metrics_persistence import MetricsPersistence
from cohezion.compound.session_manager import (
    CompoundSessionManager,
    SessionSummary,
)


# ---------------------------------------------------------------------------
# CachePersistence tests
# ---------------------------------------------------------------------------


class TestCachePersistence:
    """Tests for CachePersistence save/load."""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cache = {"abc123": "response one", "def456": "response two"}
        saved = cp.save_cache(cache)
        assert saved == 2

        loaded = cp.load_cache()
        assert loaded == cache

    def test_save_returns_count(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        assert cp.save_cache({}) == 0
        assert cp.save_cache({"k": "v"}) == 1

    def test_load_empty_file(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        (tmp_path / "token_cache.jsonl").write_text("")
        assert cp.load_cache() == {}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        assert cp.load_cache() == {}

    def test_load_max_entries(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cache = {f"key_{i}": f"val_{i}" for i in range(10)}
        cp.save_cache(cache)

        loaded = cp.load_cache(max_entries=3)
        assert len(loaded) == 3

    def test_load_handles_corrupt_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "token_cache.jsonl"
        path.write_text(
            '{"key": "k1", "value": "v1", "timestamp": 1.0}\n'
            "NOT VALID JSON\n"
            '{"key": "k2", "value": "v2", "timestamp": 2.0}\n'
        )
        cp = CachePersistence(cache_dir=tmp_path)
        loaded = cp.load_cache()
        assert len(loaded) == 2
        assert loaded["k1"] == "v1"
        assert loaded["k2"] == "v2"

    def test_load_skips_entries_without_key_or_value(self, tmp_path: Path) -> None:
        path = tmp_path / "token_cache.jsonl"
        path.write_text(
            '{"key": "k1", "value": "v1", "timestamp": 1.0}\n'
            '{"key": "k2", "timestamp": 2.0}\n'
            '{"value": "v3", "timestamp": 3.0}\n'
        )
        cp = CachePersistence(cache_dir=tmp_path)
        loaded = cp.load_cache()
        assert len(loaded) == 1
        assert loaded["k1"] == "v1"

    def test_save_with_metadata(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({"k": "v"}, metadata={"model": "phi3:mini"})

        path = tmp_path / "token_cache.jsonl"
        line = json.loads(path.read_text().strip())
        assert line["model"] == "phi3:mini"

    def test_get_cache_stats_no_file(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        stats = cp.get_cache_stats()
        assert stats["exists"] is False
        assert stats["entries"] == 0

    def test_get_cache_stats_with_data(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({"a": "b", "c": "d"})
        stats = cp.get_cache_stats()
        assert stats["exists"] is True
        assert stats["entries"] == 2
        assert stats["file_size_bytes"] > 0
        assert "last_modified" in stats


# ---------------------------------------------------------------------------
# WarmCacheLoader tests
# ---------------------------------------------------------------------------


class TestWarmCacheLoader:
    """Tests for WarmCacheLoader."""

    def test_warm_client(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({"k1": "v1", "k2": "v2"})

        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512

        loader = WarmCacheLoader(persistence=cp)
        loaded = loader.warm_client(client)
        assert loaded == 2
        assert client._cache["k1"] == "v1"
        assert client._cache["k2"] == "v2"

    def test_warm_client_respects_max_size(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({f"k{i}": f"v{i}" for i in range(10)})

        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 3

        loader = WarmCacheLoader(persistence=cp)
        loaded = loader.warm_client(client)
        assert loaded == 3
        assert len(client._cache) == 3

    def test_warm_client_empty_cache(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512

        loader = WarmCacheLoader(persistence=cp)
        loaded = loader.warm_client(client)
        assert loaded == 0


# ---------------------------------------------------------------------------
# MetricsPersistence tests
# ---------------------------------------------------------------------------


class TestMetricsPersistence:
    """Tests for MetricsPersistence snapshot and score history."""

    def test_save_load_snapshot_roundtrip(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)

        collector = MagicMock()
        collector.to_snapshot.return_value = {
            "executions": [
                {
                    "skill_name": "test",
                    "success": True,
                    "tokens_used": 100,
                    "duration_ms": 50.0,
                    "model_used": "phi3",
                    "timestamp": 1.0,
                }
            ],
            "refinements": [],
            "cycles": [],
        }

        path_str = mp.save_snapshot(collector)
        assert path_str != ""
        assert Path(path_str).exists()

        loaded = mp.load_latest_snapshot()
        assert loaded is not None
        assert len(loaded["executions"]) == 1
        assert loaded["executions"][0]["skill_name"] == "test"

    def test_load_latest_snapshot_no_dir(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path / "nonexistent")
        assert mp.load_latest_snapshot() is None

    def test_load_latest_snapshot_empty_dir(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)
        assert mp.load_latest_snapshot() is None

    def test_save_compound_scores(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)
        scores = [
            {
                "skill_name": "skill_a",
                "compound_score_delta": 0.05,
                "timestamp": time.time(),
            },
            {
                "skill_name": "skill_b",
                "compound_score_delta": -0.02,
                "timestamp": time.time(),
            },
        ]
        count = mp.save_compound_scores(scores)
        assert count == 2

    def test_load_compound_score_history(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)
        scores = [
            {
                "skill_name": f"skill_{i}",
                "compound_score_delta": 0.01 * i,
                "timestamp": 1000.0 + i,
            }
            for i in range(5)
        ]
        mp.save_compound_scores(scores)

        history = mp.load_compound_score_history(limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0]["timestamp"] > history[1]["timestamp"]

    def test_load_score_history_empty(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)
        assert mp.load_compound_score_history() == []


# ---------------------------------------------------------------------------
# SessionSummary tests
# ---------------------------------------------------------------------------


class TestSessionSummary:
    """Tests for SessionSummary Pydantic model."""

    def test_default_values(self) -> None:
        s = SessionSummary()
        assert s.session_id == ""
        assert s.start_time == 0.0
        assert s.cache_entries_loaded == 0
        assert s.metrics_restored is False

    def test_serialization(self) -> None:
        s = SessionSummary(
            session_id="test_123",
            start_time=1000.0,
            cache_entries_loaded=42,
            metrics_restored=True,
        )
        data = s.model_dump()
        assert data["session_id"] == "test_123"
        assert data["cache_entries_loaded"] == 42

        # Roundtrip
        s2 = SessionSummary.model_validate(data)
        assert s2 == s


# ---------------------------------------------------------------------------
# CompoundSessionManager tests
# ---------------------------------------------------------------------------


class TestCompoundSessionManager:
    """Tests for CompoundSessionManager lifecycle."""

    @patch("cohezion.swarm.compound_client.get_compound_client")
    def test_start_session(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512
        mock_get_client.return_value = client

        manager = CompoundSessionManager()
        summary = manager.start_session()
        assert summary.session_id.startswith("session_")
        assert summary.start_time > 0

    @patch("cohezion.swarm.compound_client.get_compound_client")
    def test_end_session(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client._cache = {"k": "v"}
        client._cache_max_size = 512
        mock_get_client.return_value = client

        manager = CompoundSessionManager()
        manager.start_session()
        summary = manager.end_session()
        assert summary.end_time > 0
        assert summary.session_id.startswith("session_")

    def test_get_current_session_none(self) -> None:
        manager = CompoundSessionManager()
        assert manager.get_current_session() is None

    @patch("cohezion.swarm.compound_client.get_compound_client")
    def test_get_current_session_active(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512
        mock_get_client.return_value = client

        manager = CompoundSessionManager()
        manager.start_session()
        session = manager.get_current_session()
        assert session is not None
        assert session.session_id.startswith("session_")


# ---------------------------------------------------------------------------
# CompoundMetricsCollector snapshot methods
# ---------------------------------------------------------------------------


class TestMetricsSnapshot:
    """Tests for to_snapshot / load_from_snapshot on CompoundMetricsCollector."""

    def test_to_snapshot_empty(self) -> None:
        from cohezion.compound.metrics import CompoundMetricsCollector

        c = CompoundMetricsCollector()
        snap = c.to_snapshot()
        assert snap["executions"] == []
        assert snap["refinements"] == []
        assert snap["cycles"] == []

    def test_snapshot_roundtrip(self) -> None:
        from cohezion.compound.metrics import CompoundMetricsCollector

        c = CompoundMetricsCollector()
        c.record_execution("skill_a", True, 100, 50.0, "phi3")
        c.record_refinement("skill_a", "1.0", "1.1", 2)
        c.record_cycle("skill_a", 1, 1, 0.05, 100, 50.0)

        snap = c.to_snapshot()
        assert len(snap["executions"]) == 1
        assert len(snap["refinements"]) == 1
        assert len(snap["cycles"]) == 1

        c2 = CompoundMetricsCollector()
        c2.load_from_snapshot(snap)
        assert c2.total_executions == 1
        assert c2.total_refinements == 1
        assert c2.total_cycles == 1
