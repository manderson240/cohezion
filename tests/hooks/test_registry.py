"""Tests for hook registry."""

from __future__ import annotations

import pytest

from cohezion.hooks import HookEvent, HookRegistry


def test_register_hook():
    """Test registering a hook."""
    registry = HookRegistry()

    def my_hook(context):
        pass

    registry.register(
        event=HookEvent.SESSION_START,
        hook_fn=my_hook,
        hook_id="test_hook",
        blocking=False,
    )

    hooks = registry.get_hooks(HookEvent.SESSION_START)
    assert len(hooks) == 1
    assert hooks[0] == my_hook


def test_blocking_hook():
    """Test blocking hook configuration."""
    registry = HookRegistry()

    def blocking_hook(context):
        pass

    registry.register(
        event=HookEvent.PRE_TOOL_USE,
        hook_fn=blocking_hook,
        hook_id="blocker",
        blocking=True,
    )

    assert registry.is_blocking("blocker") is True


def test_list_hooks():
    """Test listing registered hooks."""
    registry = HookRegistry()

    registry.register(HookEvent.SESSION_START, lambda c: None, "h1")
    registry.register(HookEvent.SESSION_START, lambda c: None, "h2")
    registry.register(HookEvent.SESSION_END, lambda c: None, "h3")

    hook_counts = registry.list_hooks()
    assert hook_counts[HookEvent.SESSION_START] == 2
    assert hook_counts[HookEvent.SESSION_END] == 1
