"""Tests for ZVOL Swap Pipeline (Story 1.8)."""

from __future__ import annotations

import pytest

from cohezion.core.zvol_swap import (
    KVCacheEntry,
    SwapEventType,
    ZVOLSwapPipeline,
)


class TestZVOLSwapPipeline:
    def test_pages_lowest_priority_first(self):
        pipeline = ZVOLSwapPipeline()
        pipeline.register_agent_context(KVCacheEntry("high-priority", 1024, priority=0.9))
        pipeline.register_agent_context(KVCacheEntry("low-priority", 1024, priority=0.1))
        event = pipeline.page_to_zvol()
        assert "low-priority" in event.detail

    def test_page_to_zvol_event_type(self):
        pipeline = ZVOLSwapPipeline()
        pipeline.register_agent_context(KVCacheEntry("agent-1", 1024 * 1024, priority=0.5))
        event = pipeline.page_to_zvol()
        assert event.event_type == SwapEventType.PAGED_TO_ZVOL

    def test_zvol_full_triggers_apoptosis(self):
        # Small ZVOL buffer to trigger overflow
        pipeline = ZVOLSwapPipeline(zvol_capacity_bytes=100)
        pipeline.register_agent_context(KVCacheEntry("low-agent", 200, priority=0.1))
        pipeline.register_agent_context(KVCacheEntry("another-agent", 200, priority=0.2))
        # First page: fits
        event1 = pipeline.page_to_zvol()
        assert event1.event_type == SwapEventType.ZVOL_FULL_APOPTOSIS

    def test_no_hard_oom_kill_invariant(self):
        pipeline = ZVOLSwapPipeline()
        assert pipeline.is_oom_safe() is True

    def test_terminated_agents_tracked(self):
        pipeline = ZVOLSwapPipeline(zvol_capacity_bytes=10)
        pipeline.register_agent_context(KVCacheEntry("doomed", 1000, priority=0.1))
        pipeline.page_to_zvol()
        assert "doomed" in pipeline.terminated_agents

    def test_no_entries_raises(self):
        pipeline = ZVOLSwapPipeline()
        with pytest.raises(RuntimeError, match="No KV cache entries"):
            pipeline.page_to_zvol()

    def test_zvol_utilization_increases(self):
        pipeline = ZVOLSwapPipeline()
        assert pipeline.zvol_utilization() == 0.0
        pipeline.register_agent_context(KVCacheEntry("a", 1024 * 1024 * 1024, priority=0.5))
        pipeline.page_to_zvol()
        assert pipeline.zvol_utilization() > 0.0
