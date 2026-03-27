"""Benchmarks test configuration - gym registration trigger."""

from __future__ import annotations

import contextlib

import pytest


@pytest.fixture(scope="session", autouse=True)
def register_gym_environments():
    """Register Cohezion gym environments before running tests."""
    import gymnasium as gym

    with contextlib.suppress(Exception):
        gym.register("cohezion/FlumeNav-v0", entry_point="cohezion.rl.environment:FlumeNavEnv")
    yield
