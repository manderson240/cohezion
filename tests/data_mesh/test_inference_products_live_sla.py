"""V-model verify for the gauntlet→datamesh wire (2026-07-17 doctrine).

Structural + behavioral checks, no network: live gauntlet measurements must
override static harness SLAs when present, fall back cleanly when absent, and
leaderboard publication must emit a DATA_PRODUCT_UPDATED event fail-open.
"""

from __future__ import annotations

import asyncio

import cohezion.data_mesh.inference_products as ip
from cohezion.data_mesh.data_product import DataQualityTier


class TestLiveSlaSourcing:
    def test_live_overrides_static_tier_and_advertises_measurements(self):
        # deepseek is statically SILVER; a measured 0.95 must promote to GOLD
        # and the schema must advertise the measured numbers.
        product = ip._build_product("deepseek-r1-0528-8b-FLM", None, {"quality": 0.95, "tps": 10.3})
        assert product.quality_tier == DataQualityTier.GOLD
        assert "0.950" in product.schema.fields["measured_quality"]
        assert "10.3" in product.schema.fields["measured_tps"]

    def test_live_can_demote_below_static(self):
        # Discriminating: llama3.2-1b is statically GOLD; a measured 0.58 must
        # DEMOTE to BRONZE — an implementation that only ever upgrades would
        # pass the promotion test but fail this one.
        product = ip._build_product("llama3.2-1b-FLM", None, {"quality": 0.58, "tps": 16.0})
        assert product.quality_tier == DataQualityTier.BRONZE

    def test_static_fallback_when_no_live_rows(self):
        product = ip._build_product("llama3.2-1b-FLM", None, None)
        assert product.quality_tier == DataQualityTier.GOLD  # static harness value
        assert "measured_quality" not in product.schema.fields

    def test_fetch_gauntlet_perf_fails_open(self, monkeypatch):
        monkeypatch.setattr(ip, "_SURREAL", "http://127.0.0.1:9/sql")
        assert ip._fetch_gauntlet_perf() == {}

    def test_tier_mapping_bounds(self):
        assert ip._tier_from_measured_quality(0.9) == DataQualityTier.GOLD
        assert ip._tier_from_measured_quality(0.7) == DataQualityTier.SILVER
        assert ip._tier_from_measured_quality(0.69) == DataQualityTier.BRONZE


class TestLeaderboardEventEmission:
    def test_publish_emits_data_product_updated(self, monkeypatch, tmp_path):
        import cohezion.core.event_bus as eb
        import cohezion.inference.npu_gauntlet as ng

        captured: list = []

        class _Bus:
            async def publish(self, event):
                captured.append(event)
                return True

        async def _fake_get_bus():
            # Discriminating: mirrors the REAL async get_event_bus signature
            # (event_bus.py:303). The original sync-lambda fake hid a blocking
            # bug — production called get_event_bus() without await; the
            # coroutine's missing .publish AttributeError was swallowed
            # fail-open (silent no-op). A sync-call regression now fails here.
            return _Bus()

        monkeypatch.setattr(eb, "get_event_bus", _fake_get_bus)
        monkeypatch.setattr(ng, "RUN_DIR", tmp_path)
        monkeypatch.setattr(ng, "VAULT", tmp_path / "vault")
        board = {
            "generated": "t",
            "entries": [
                {
                    "model": "m",
                    "role": "r",
                    "n": 1,
                    "accuracy": 1.0,
                    "mean_tps": 10.0,
                    "quality_per_s": 10.0,
                }
            ],
        }
        ng.publish(board)
        assert len(captured) == 1
        assert captured[0].type == eb.EventType.DATA_PRODUCT_UPDATED
        assert captured[0].source == "npu_gauntlet"
        assert captured[0].payload["entries"][0]["model"] == "m"

    def test_publish_survives_bus_failure(self, monkeypatch, tmp_path):
        import cohezion.core.event_bus as eb
        import cohezion.inference.npu_gauntlet as ng

        def _boom():
            raise RuntimeError("bus down")

        monkeypatch.setattr(eb, "get_event_bus", _boom)
        monkeypatch.setattr(ng, "RUN_DIR", tmp_path)
        monkeypatch.setattr(ng, "VAULT", tmp_path / "vault")
        ng.publish({"generated": "t", "entries": []})  # must not raise
        assert (tmp_path / "leaderboard.json").exists()
