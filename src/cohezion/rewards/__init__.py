"""Reward system — XP, achievements, streaks, and agent progression."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.rewards.calculator import RewardCalculator as RewardCalculator

with contextlib.suppress(Exception):
    from cohezion.rewards.ratchet import RatchetMechanism as RatchetMechanism

with contextlib.suppress(Exception):
    from cohezion.rewards.system import RewardSystem as RewardSystem
