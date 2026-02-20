"""Tests for hook executor."""

from __future__ import annotations

import pytest

from cohezion.hooks import HookEvent, HookExecutor, HookRegistry


@pytest.mark.asyncio
async def test_execute_hooks():
    """Test executing hooks for an event."""
    registry = HookRegistry()
    executor = HookExecutor(registry)

    call_count = 0

    def my_hook(context):
        nonlocal call_count
        call_count += 1

    registry.register(HookEvent.SESSION_START, my_hook, "h1")
    registry.register(HookEvent.SESSION_START, my_hook, "h2")

    result = await executor.execute(HookEvent.SESSION_START)

    assert result["executed"] == 2
    assert call_count == 2
    assert len(result["failures"]) == 0


@pytest.mark.asyncio
async def test_hook_failure():
    """Test hook execution with failures."""
    registry = HookRegistry()
    executor = HookExecutor(registry)

    def failing_hook(context):
        raise ValueError("Hook failed")

    registry.register(HookEvent.POST_TOOL_USE, failing_hook, "failer")

    result = await executor.execute(HookEvent.POST_TOOL_USE, fail_fast=False)

    assert result["executed"] == 0
    assert len(result["failures"]) == 1


@pytest.mark.asyncio
async def test_async_hooks():
    """Test async hook execution."""
    registry = HookRegistry()
    executor = HookExecutor(registry)

    async_called = False

    async def async_hook(context):
        nonlocal async_called
        async_called = True

    registry.register(HookEvent.CONTEXT_CLEAR, async_hook, "async_h")

    await executor.execute(HookEvent.CONTEXT_CLEAR)

    assert async_called is True


@pytest.mark.asyncio
async def test_execution_stats():
    """Test execution statistics tracking."""
    registry = HookRegistry()
    executor = HookExecutor(registry)

    registry.register(HookEvent.SESSION_START, lambda c: None, "h1")

    await executor.execute(HookEvent.SESSION_START)
    await executor.execute(HookEvent.SESSION_START)

    stats = executor.get_execution_stats()
    assert stats[HookEvent.SESSION_START] == 2
