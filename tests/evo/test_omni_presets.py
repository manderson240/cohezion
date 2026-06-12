"""Tests for Cohezion-Omni-Lite / Cohezion-Omni-Dense preset factories."""

from unittest.mock import MagicMock, patch

class TestOmniPresets:
    def test_build_omni_lite_tier_planner(self):
        """Lite preset uses Gemma-4-E4B planner."""
        from cohezion.inference.triune_orchestrator import build_omni_lite_tier, OMNI_LITE_MODEL_ID

        tier = build_omni_lite_tier()
        assert tier._planner_model == "Gemma-4-E4B-it-GGUF"
        assert tier._image_model == "SD-Turbo"
        assert tier.model_id == OMNI_LITE_MODEL_ID

    def test_build_omni_dense_tier_planner(self):
        """Dense preset uses Qwen3.6-35B planner."""
        from cohezion.inference.triune_orchestrator import build_omni_dense_tier, OMNI_DENSE_MODEL_ID

        tier = build_omni_dense_tier()
        assert tier._planner_model == "Qwen3.6-35B-A3B-MTP-GGUF"
        assert tier._image_model == "Flux-2-Klein-9B-GGUF"
        assert tier.model_id == OMNI_DENSE_MODEL_ID

    def test_build_omni_tier_alias_returns_dense(self):
        """build_omni_tier() backwards-compat alias returns Dense preset."""
        from cohezion.inference.triune_orchestrator import (
            build_omni_tier,
            build_omni_dense_tier,
            OMNI_DENSE_MODEL_ID,
        )

        via_alias = build_omni_tier()
        via_dense = build_omni_dense_tier()
        assert via_alias._planner_model == via_dense._planner_model
        assert via_alias._image_model == via_dense._image_model
        assert via_alias.model_id == OMNI_DENSE_MODEL_ID

    def test_omni_constants_distinct(self):
        """Lite and Dense model IDs are different strings."""
        from cohezion.inference.triune_orchestrator import OMNI_LITE_MODEL_ID, OMNI_DENSE_MODEL_ID

        assert OMNI_LITE_MODEL_ID != OMNI_DENSE_MODEL_ID

    def test_omni_runnable_passes_image_model_to_request(self):
        """OmniRunnable.run() forwards image_model to OmniRequest."""
        from cohezion.inference.triune_orchestrator import OmniRunnable

        captured: list = []

        async def fake_run(req):
            captured.append(req.image_model)
            result = MagicMock()
            result.text = "ok"
            result.images = []
            result.audio = None
            result.transcript = None
            result.error = None
            return result

        runnable = OmniRunnable(image_model="SD-Turbo")
        fake_tier = MagicMock()
        fake_tier.run = fake_run
        runnable._tier = fake_tier  # inject pre-built tier

        import asyncio
        asyncio.run(runnable.run("hello"))
        assert captured == ["SD-Turbo"]

    def test_ram_gate_selects_lite_when_dense_insufficient(self):
        """build_triune_orchestrator selects Lite when RAM is 14 GB (< Dense 36 GB, ≥ Lite 12 GB)."""
        from cohezion.inference.triune_orchestrator import OMNI_LITE_MODEL_ID

        mock_snap = MagicMock()
        mock_snap.available_gb = 14.0  # enough for Lite, not Dense

        with patch(
            "cohezion.inference.direct_tier.build_router_npu_tier"
        ) as mock_npu, patch(
            "cohezion.inference.direct_tier.build_router_igpu_tier"
        ) as mock_igpu, patch(
            "cohezion.inference.direct_tier.build_router_cpu_tier"
        ) as mock_cpu, patch(
            "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"
        ) as MockMS:
            MockMS.capture.return_value = mock_snap
            mock_npu.return_value = MagicMock()
            mock_igpu.return_value = MagicMock()
            mock_cpu.return_value = None

            from cohezion.inference.triune_orchestrator import build_triune_orchestrator

            orch = build_triune_orchestrator(include_omni=True, include_cloud=False)
            # Find any omni tier in the tiers list
            omni_tiers = [
                t for t, _ in orch.tiers
                if hasattr(t, "model_id") and "Omni" in str(getattr(t, "model_id", ""))
            ]
            assert len(omni_tiers) >= 1
            assert omni_tiers[0].model_id == OMNI_LITE_MODEL_ID
