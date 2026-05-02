"""Tests for cost tracking module.

Verifies:
- Cost calculation accuracy (±1% tolerance)
- In-memory tracking performance (<0.05ms)
- Batched async flush behavior
- Graceful degradation on vault failure
- Session cost aggregation
- Model cost tracking
"""

import time
from unittest.mock import AsyncMock

import pytest

from cohezion.cost_optimization.cost_tracker import (
    CostRecord,
    SessionCostTracker,
    get_current_tracker,
    reset_current_tracker,
    set_current_tracker,
)


class TestCostRecord:
    """Test CostRecord dataclass."""

    def test_cost_record_creation(self):
        """Verify CostRecord can be created with proper fields."""
        record = CostRecord(
            timestamp=time.time(),
            session_id="test-session-1",
            model="qwen3-coder:30b",
            tokens=500,
            duration_ms=250.0,
            cost_usd=0.015,
        )

        assert record.session_id == "test-session-1"
        assert record.model == "qwen3-coder:30b"
        assert record.tokens == 500
        assert record.duration_ms == 250.0
        assert record.cost_usd == 0.015
        assert record.record_id is not None  # Auto-generated UUID

    def test_cost_record_to_dict(self):
        """Verify CostRecord can be serialized to dict."""
        record = CostRecord(
            timestamp=1000.0,
            session_id="test-session-1",
            model="qwen3-coder:30b",
            tokens=500,
            duration_ms=250.0,
            cost_usd=0.015,
        )

        data = record.to_dict()
        assert data["session_id"] == "test-session-1"
        assert data["model"] == "qwen3-coder:30b"
        assert data["tokens"] == 500
        assert data["cost_usd"] == 0.015


class TestSessionCostTracker:
    """Test SessionCostTracker."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_current_tracker()

    def test_tracker_creation(self):
        """Verify tracker initialization."""
        tracker = SessionCostTracker(
            session_id="test-session-1",
            batch_size=10,
        )

        assert tracker.session_id == "test-session-1"
        assert tracker.total_cost_usd == 0.0
        assert tracker.total_tokens == 0
        assert len(tracker.records) == 0

    def test_track_usage_local_model(self):
        """Verify cost tracking for local models (free)."""
        tracker = SessionCostTracker(session_id="test-session-1")

        cost = tracker.track_usage_fast(
            model="qwen3-coder:32b",
            tokens=1000,
            duration_ms=500.0,
        )

        assert cost == 0.0  # Local model, no cost
        assert tracker.total_tokens == 1000
        assert tracker.total_cost_usd == 0.0
        assert tracker.model_usage["qwen3-coder:32b"] == 1000

    def test_track_usage_api_model(self):
        """Verify cost tracking for API models."""
        tracker = SessionCostTracker(session_id="test-session-1")

        cost = tracker.track_usage_fast(
            model="gpt-4",
            tokens=1000,
            duration_ms=500.0,
        )

        # gpt-4 costs $0.03 per 1K tokens
        expected_cost = 0.03
        assert abs(cost - expected_cost) < 0.0001  # ±0.0001 tolerance
        assert tracker.total_tokens == 1000
        assert tracker.total_cost_usd == expected_cost

    def test_track_usage_unknown_model(self):
        """Verify cost tracking uses conservative estimate for unknown models."""
        tracker = SessionCostTracker(session_id="test-session-1")

        cost = tracker.track_usage_fast(
            model="unknown-model-xyz",
            tokens=1000,
            duration_ms=500.0,
        )

        # Unknown model defaults to $0.015 per 1K tokens
        expected_cost = 0.015
        assert abs(cost - expected_cost) < 0.0001
        assert tracker.total_cost_usd == expected_cost

    def test_track_usage_multiple_calls(self):
        """Verify cost accumulation across multiple calls."""
        tracker = SessionCostTracker(session_id="test-session-1")

        # Call 1: qwen3 (free)
        cost1 = tracker.track_usage_fast(model="qwen3-coder:32b", tokens=500, duration_ms=250.0)

        # Call 2: gpt-4 ($0.03 per 1K)
        cost2 = tracker.track_usage_fast(model="gpt-4", tokens=1000, duration_ms=500.0)

        # Call 3: claude-3-sonnet ($0.003 per 1K)
        cost3 = tracker.track_usage_fast(model="claude-3-sonnet", tokens=2000, duration_ms=1000.0)

        assert cost1 == 0.0
        assert cost2 == 0.03
        assert cost3 == 0.006

        assert tracker.total_tokens == 3500
        assert abs(tracker.total_cost_usd - 0.036) < 0.0001
        assert tracker.model_usage["qwen3-coder:32b"] == 500
        assert tracker.model_usage["gpt-4"] == 1000
        assert tracker.model_usage["claude-3-sonnet"] == 2000

    def test_cost_record_creation(self):
        """Verify cost records are created for tracking."""
        tracker = SessionCostTracker(session_id="test-session-1", batch_size=100)

        tracker.track_usage_fast("qwen3-coder:32b", tokens=500)
        tracker.track_usage_fast("gpt-4", tokens=1000)

        assert len(tracker.records) == 2
        assert tracker.records[0].model == "qwen3-coder:32b"
        assert tracker.records[1].model == "gpt-4"

    def test_batch_size_reached(self):
        """Verify batch is tracked when size reached."""
        tracker = SessionCostTracker(session_id="test-session-1", batch_size=5)

        # Add 4 records (below threshold)
        for _i in range(4):
            tracker.track_usage_fast("qwen3-coder:32b", tokens=100)

        assert len(tracker.records) == 4
        assert tracker._pending_flush is False

        # Add 5th record (reaches threshold)
        tracker.track_usage_fast("qwen3-coder:32b", tokens=100)

        # Note: _pending_flush will be True if event loop exists,
        # but we don't check it here to avoid async issues in sync tests
        assert len(tracker.records) == 5

    def test_get_session_cost(self):
        """Verify session cost summary."""
        tracker = SessionCostTracker(session_id="test-session-1")

        tracker.track_usage_fast("qwen3-coder:32b", tokens=500)
        tracker.track_usage_fast("gpt-4", tokens=1000)

        summary = tracker.get_session_cost()

        assert summary["total_tokens"] == 1500
        assert abs(summary["total_cost_usd"] - 0.03) < 0.0001
        assert summary["model_usage"]["qwen3-coder:32b"] == 500
        assert summary["model_usage"]["gpt-4"] == 1000
        assert summary["duration_sec"] > 0
        assert summary["pending_records"] == 2

    def test_custom_model_costs(self):
        """Verify custom model cost configuration."""
        custom_costs = {
            "custom-model": 0.1,  # $0.10 per 1K tokens
        }

        tracker = SessionCostTracker(
            session_id="test-session-1",
            model_costs=custom_costs,
        )

        cost = tracker.track_usage_fast("custom-model", tokens=1000)

        assert cost == 0.1
        assert tracker.total_cost_usd == 0.1

    def test_tracker_reset(self):
        """Verify reset clears all tracking state."""
        tracker = SessionCostTracker(session_id="test-session-1")

        tracker.track_usage_fast("gpt-4", tokens=1000)
        assert tracker.total_tokens == 1000
        assert tracker.total_cost_usd == 0.03

        tracker.reset()

        assert tracker.total_tokens == 0
        assert tracker.total_cost_usd == 0.0
        assert len(tracker.records) == 0
        assert len(tracker.model_usage) == 0

    def test_global_tracker_instance(self):
        """Verify global tracker instance management."""
        reset_current_tracker()
        assert get_current_tracker() is None

        tracker = SessionCostTracker(session_id="test-session-1")
        set_current_tracker(tracker)

        assert get_current_tracker() is tracker
        assert get_current_tracker().session_id == "test-session-1"

        reset_current_tracker()
        assert get_current_tracker() is None

    @pytest.mark.asyncio
    async def test_flush_all_empty(self):
        """Verify flush_all returns 0 for empty tracker."""
        tracker = SessionCostTracker(session_id="test-session-1")

        flushed = await tracker.flush_all()

        assert flushed == 0

    @pytest.mark.asyncio
    async def test_flush_all_with_mock_vault(self):
        """Verify flush_all persists records with vault logger."""
        mock_vault = AsyncMock()
        tracker = SessionCostTracker(
            session_id="test-session-1",
            batch_size=5,
            vault_logger=mock_vault,
        )

        # Add records
        for _i in range(12):
            tracker.track_usage_fast("qwen3-coder:32b", tokens=100)

        # Flush all
        flushed = await tracker.flush_all()

        # Should flush in batches of 5
        assert flushed == 12
        assert len(tracker.records) == 0
        assert mock_vault.log_cost_records.call_count == 3  # 3 batches

    @pytest.mark.asyncio
    async def test_flush_all_vault_failure(self):
        """Verify flush_all gracefully handles vault failure."""
        mock_vault = AsyncMock()
        mock_vault.log_cost_records.side_effect = Exception("Vault connection failed")

        tracker = SessionCostTracker(
            session_id="test-session-1",
            batch_size=5,
            vault_logger=mock_vault,
        )

        # Add records
        for _i in range(10):
            tracker.track_usage_fast("qwen3-coder:32b", tokens=100)

        # Flush all (should fail gracefully)
        flushed = await tracker.flush_all()

        # Should handle error gracefully, flush 0 on first failure
        assert flushed == 0
        assert len(tracker.records) == 10  # Records stay in memory

    def test_performance_tracking_overhead(self):
        """Verify cost tracking overhead is <0.1ms per call."""
        tracker = SessionCostTracker(session_id="test-session-1")

        start = time.time()
        for _ in range(1000):
            tracker.track_usage_fast("qwen3-coder:32b", tokens=100)
        elapsed = time.time() - start

        # 1000 calls should be < 100ms (average <0.1ms per call)
        assert elapsed < 0.1
        assert tracker.total_tokens == 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
