"""Unit tests for FullSiliconTriTierEngine."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.full_silicon_tri_tier_engine import (
    FullSiliconExecutionResult,
    FullSiliconTriTierEngine,
)


@pytest.mark.asyncio
async def test_full_silicon_tri_tier_engine_execution():
    with patch(
        "cohezion.inference.full_silicon_tri_tier_engine.SpeculativeDecoderEngine"
    ) as mock_spec_cls:
        mock_spec = MagicMock()
        mock_spec_res = MagicMock()
        mock_spec_res.decode_speed_tok_s = 142.50
        mock_spec.generate_speculative = AsyncMock(return_value=mock_spec_res)
        mock_spec_cls.return_value = mock_spec

        engine = FullSiliconTriTierEngine()
        result = await engine.execute_tri_tier_silicon_pass("Test Strix Halo prompt")

        assert isinstance(result, FullSiliconExecutionResult)
        assert result.total_prefill_tok_s >= 1000.0
        assert result.total_decode_tok_s == 142.50
        assert result.ram_floor_gb == 20.0
        assert result.oom_fault_rate_pct == 0.0
        assert len(result.tri_tier_telemetry) == 3

        npu, igpu, cpu = result.tri_tier_telemetry
        assert "XDNA 2" in npu.silicon_tier
        assert npu.prefill_throughput_tok_s > 0
        assert "Radeon 8060S" in igpu.silicon_tier
        assert "Ryzen AI MAX+ 395" in cpu.silicon_tier
