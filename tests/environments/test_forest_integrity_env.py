"""Tests for ForestIntegrityEnv — forest patch conservation environment."""

import numpy as np
import pytest

from cohezion.environments.forest_integrity_env import (
    N_INDICATORS,
    N_PATCHES,
    OBS_DIM,
    ForestIntegrityEnv,
)


@pytest.fixture
def env():
    e = ForestIntegrityEnv(max_steps=50, seed=42)
    e.reset(seed=42)
    return e


def test_observation_space_shape():
    env = ForestIntegrityEnv()
    assert env.observation_space.shape == (OBS_DIM,)
    assert OBS_DIM == N_PATCHES * N_INDICATORS + 2  # 82


def test_action_space_discrete_48():
    env = ForestIntegrityEnv()
    assert env.action_space.n == N_PATCHES * 3  # 48


def test_reset_returns_correct_shape(env):
    obs, info = env.reset(seed=0)
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32
    assert isinstance(info, dict)


def test_step_returns_correct_tuple(env):
    action = env.action_space.sample()
    result = env.step(action)
    obs, reward, terminated, truncated, info = result
    assert obs.shape == (OBS_DIM,)
    assert isinstance(reward, float)
    assert isinstance(terminated, (bool, np.bool_))
    assert isinstance(truncated, (bool, np.bool_))
    assert "mean_integrity" in info


def test_restore_action_does_not_crash(env):
    """Restore action (type=1) should nudge integrity up without errors."""
    env.reset(seed=7)
    # pick patch 0, restore action: 0*3 + 1 = 1
    obs_before, _, _, _, info_before = env.step(0 * 3 + 1)
    obs_after, _, _, _, info_after = env.step(0 * 3 + 2)  # monitor same patch
    # No crash; integrity stays bounded
    assert 0.0 <= info_after["mean_integrity"] <= 1.0
