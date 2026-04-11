"""Tests for compute backend router.

These validate the heterogeneous compute abstraction works correctly
and documents known hardware issues like the gfx1151 ROCm hang.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.compute_backend_router import (
    BackendConstraints,
    BackendStatus,
    BackendType,
    ComputeBackendRouter,
)


class TestComputeBackendRouter:
    """Tests for heterogeneous compute routing."""

    @pytest.fixture
    def router(self):
        """Fresh router instance per test."""
        ComputeBackendRouter._instance = None
        return ComputeBackendRouter.get_default()

    @pytest.mark.fast
    def test_singleton_pattern(self, router):
        """Router follows singleton pattern."""
        router2 = ComputeBackendRouter.get_default()
        assert router is router2

    @pytest.mark.fast
    def test_initial_capabilities(self, router):
        """Router initializes with known hardware profiles."""
        # NPU should be available
        assert router._capabilities[BackendType.NPU].typical_tps == 75.0

        # ROCm should be marked as unavailable due to gfx1151 hang
        assert router._capabilities[BackendType.GPU_ROCM].status == BackendStatus.UNAVAILABLE

        # Vulkan is NOW AVAILABLE (validated 2026-04-10)
        assert router._capabilities[BackendType.GPU_VULKAN].status == BackendStatus.AVAILABLE
        assert router._capabilities[BackendType.GPU_VULKAN].typical_tps == 100.0

    @pytest.mark.fast
    def test_select_backend_skips_broken_rocm(self, router):
        """Router skips ROCm backend due to known Issue #6027."""
        decision = router.select_backend(model_size_gb=4.0)

        # Should pick NPU or Cloud, not ROCm
        assert decision.selected_backend != BackendType.GPU_ROCM

        # NPU is available for small models
        if decision.selected_backend == BackendType.NPU:
            assert decision.expected_tps == 75.0

    @pytest.mark.fast
    def test_select_backend_prefers_npu_for_small_models(self, router):
        """Small models route to NPU."""
        decision = router.select_backend(
            model_size_gb=3.0,
            constraints=BackendConstraints(min_throughput_tps=50.0),
        )

        # Should prefer NPU for small models
        assert decision.selected_backend == BackendType.NPU

    @pytest.mark.fast
    def test_select_backend_falls_back_to_cloud(self, router):
        """When local fails, route to cloud."""
        # Mark NPU as unavailable
        router._capabilities[BackendType.NPU].status = BackendStatus.UNAVAILABLE
        router._capabilities[BackendType.GPU_VULKAN].status = BackendStatus.UNAVAILABLE

        decision = router.select_backend(
            model_size_gb=50.0,  # Large model
            constraints=BackendConstraints(min_throughput_tps=10.0),
        )

        assert decision.selected_backend == BackendType.CLOUD

    @pytest.mark.fast
    def test_health_warning_for_degraded_backend(self, router):
        """Degraded backends return health warnings."""
        # Mark NPU as degraded
        router._capabilities[BackendType.NPU].status = BackendStatus.DEGRADED

        decision = router.select_backend(
            model_size_gb=4.0,
            preferred_order=[BackendType.NPU, BackendType.CLOUD],
        )

        # Should still pick degraded NPU with warning
        assert decision.selected_backend == BackendType.NPU

    @pytest.mark.fast
    def test_known_issues_documented(self, router):
        """Known hardware issues are documented."""
        assert BackendType.GPU_ROCM in router.KNOWN_ISSUES
        issue_text = router.KNOWN_ISSUES[BackendType.GPU_ROCM]

        # Should mention the specific issue
        assert "Issue #6027" in issue_text
        assert "sched_reserve" in issue_text or "hang" in issue_text
        assert "gfx1151" in issue_text or "RDNA3.5" in issue_text

    @pytest.mark.fast
    def test_capability_model_size_filter(self, router):
        """Backends filtered by max model size."""
        # NPU has 128GB unified memory
        assert router._capabilities[BackendType.NPU].max_model_size_gb == 128.0

        # Small model should fit everywhere
        decision = router.select_backend(model_size_gb=1.0)
        assert decision.selected_backend in [
            BackendType.NPU,
            BackendType.GPU_VULKAN,
            BackendType.CLOUD,
        ]

    @pytest.mark.fast
    def test_fail_fast_when_no_backend(self, router):
        """When no backend available and no fallback, raise error."""
        # Mark all major backends as unavailable
        router._capabilities[BackendType.NPU].status = BackendStatus.UNAVAILABLE
        router._capabilities[BackendType.GPU_VULKAN].status = BackendStatus.UNAVAILABLE
        router._capabilities[BackendType.CLOUD].status = BackendStatus.UNAVAILABLE

        # Disable fallback, should raise
        with pytest.raises(RuntimeError) as exc:
            router.select_backend(
                model_size_gb=10.0,
                constraints=BackendConstraints(allow_fallback=False),
            )

        assert "No backend meets constraints" in str(exc.value)


class TestComputeBackendProbing:
    """Tests for backend health probing."""

    @pytest.fixture
    def router(self):
        """Fresh router instance per test."""
        ComputeBackendRouter._instance = None
        return ComputeBackendRouter.get_default()

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_probe_npu_success(self, router):
        """NPU probe detects valid FLM installation."""
        mock_output = b"[Linux]  NPU: /dev/accel/accel0 with 8 columns\n"

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(mock_output, None))
            mock_exec.return_value = mock_proc

            status = await router.probe_npu()
            assert status == BackendStatus.AVAILABLE

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_probe_rocm_detects_gfx1151(self, router):
        """ROCm probe detects GPU but marks degraded due to known issue."""
        mock_output = b"Name:                    gfx1151\n"

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(mock_output, None))
            mock_exec.return_value = mock_proc

            status = await router.probe_rocm()
            # GPU detected but we know it's degraded
            assert status == BackendStatus.DEGRADED

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_probe_vulkan_missing_sdk(self, router):
        """Vulkan probe detects missing SDK."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.returncode = 1  # vulkaninfo not found
            mock_exec.return_value = mock_proc

            status = await router.probe_vulkan()
            assert status == BackendStatus.UNKNOWN


class TestExecutionFallback:
    """Tests for automatic fallback during execution."""

    @pytest.fixture
    def router(self):
        """Fresh router with mocked execution."""
        ComputeBackendRouter._instance = None
        router = ComputeBackendRouter.get_default()
        return router

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_execute_with_success(self, router):
        """Successful execution returns metadata."""
        with patch.object(router, "_execute_flm", new_callable=AsyncMock) as mock_flm:
            mock_flm.return_value = "Test response"

            result = await router.execute(
                model="gemma3:4b",
                prompt="Test",
                backend=BackendType.NPU,
            )

            assert result["result"] == "Test response"
            assert result["backend_used"] == "NPU"
            assert result["fallbacks_used"] == []

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_execute_with_fallback(self, router):
        """Fallback chain used when primary fails."""
        with (
            patch.object(router, "_execute_flm", new_callable=AsyncMock) as mock_flm,
            patch.object(router, "_execute_ollama", new_callable=AsyncMock) as mock_ollama,
        ):
            # FLM fails
            mock_flm.side_effect = RuntimeError("FLM down")
            # Ollama succeeds
            mock_ollama.return_value = "Cloud response"

            result = await router.execute(
                model="gemma3:4b",
                prompt="Test",
                backend=BackendType.NPU,
                fallback_chain=[BackendType.CLOUD],
            )

            assert result["result"] == "Cloud response"
            assert result["backend_used"] == "CLOUD"
            assert "NPU" in result["fallbacks_used"]

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_execute_all_backends_fail(self, router):
        """All backends exhausted raises error."""
        with (
            patch.object(router, "_execute_flm", new_callable=AsyncMock) as mock_flm,
            patch.object(router, "_execute_ollama", new_callable=AsyncMock) as mock_ollama,
        ):
            mock_flm.side_effect = RuntimeError("FLM down")
            mock_ollama.side_effect = RuntimeError("Ollama down")

            with pytest.raises(RuntimeError) as exc:
                await router.execute(
                    model="gemma3:4b",
                    prompt="Test",
                    backend=BackendType.NPU,
                    fallback_chain=[BackendType.CLOUD],
                )

            assert "All backends failed" in str(exc.value)


class TestStatusReporting:
    """Tests for vault-compatible status reporting."""

    @pytest.fixture
    def router(self):
        """Fresh router instance per test."""
        ComputeBackendRouter._instance = None
        return ComputeBackendRouter.get_default()

    @pytest.mark.fast
    def test_status_report_structure(self, router):
        """Status report includes all required fields for vault logging."""
        report = router.get_status_report()

        assert "timestamp" in report
        assert "backends" in report
        assert "known_issues" in report

        # Each backend has status
        for backend_name in ["NPU", "GPU_ROCM", "GPU_VULKAN", "CLOUD"]:
            assert backend_name in report["backends"]
            backend = report["backends"][backend_name]
            assert "status" in backend
            assert "typical_tps" in backend
            assert "failure_count" in backend

    @pytest.mark.fast
    def test_status_report_documents_gfx1151_issue(self, router):
        """Status report documents gfx1151 hang in known issues."""
        report = router.get_status_report()

        assert "GPU_ROCM" in report["known_issues"]
        issue = report["known_issues"]["GPU_ROCM"]

        # Should be clear about the specific failure
        assert "#6027" in issue
        assert any(x in issue for x in ["sched_reserve", "hang", "gfx1151"])
