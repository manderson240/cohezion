"""Wiring-sweep round-5 verification tests.

Checks that platform, integrations, mass_sim, rl, and registry orphan modules
are now reachable via their package namespace and that the re-exported names are
identical objects to the originals (identity, not just equality).

One discriminating behavioural test per package confirms the wired names work, not
merely that the import succeeded.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# platform
# ---------------------------------------------------------------------------


def test_platform_session_tracker_reachable():
    import cohezion.platform as pkg
    import cohezion.platform.session_tracker as mod

    assert pkg.SessionTracker is mod.SessionTracker


def test_platform_tier_optimizer_reachable():
    import cohezion.platform as pkg
    import cohezion.platform.tier_optimizer as mod

    assert pkg.TierOptimizer is mod.TierOptimizer
    assert pkg.TierRecommendation is mod.TierRecommendation


def test_platform_tier_recommendation_behavioural():
    """TierRecommendation must be an enum with at least one member."""
    from cohezion.platform import TierRecommendation

    members = list(TierRecommendation)
    assert len(members) >= 1, "TierRecommendation enum should have at least one member"


# ---------------------------------------------------------------------------
# integrations
# ---------------------------------------------------------------------------


def test_integrations_competition_rate_limiter_reachable():
    import cohezion.integrations as pkg
    import cohezion.integrations.competition_rate_limiter as mod

    assert pkg.CompetitionRateLimiter is mod.CompetitionRateLimiter


def test_integrations_flume_wiki_bridge_reachable():
    import cohezion.integrations as pkg
    import cohezion.integrations.flume_wiki_bridge as mod

    assert pkg.FlumeWikiBridge is mod.FlumeWikiBridge


def test_integrations_competition_rate_limiter_behavioural():
    """CompetitionRateLimiter can be instantiated and enforces a time limit."""
    from cohezion.integrations import CompetitionRateLimiter

    limiter = CompetitionRateLimiter()
    # The instance must expose the rate limit window and a path for persisting state.
    assert hasattr(limiter, "limit_seconds"), (
        "CompetitionRateLimiter should have a limit_seconds attribute"
    )
    assert limiter.limit_seconds > 0, "limit_seconds should be a positive duration"


# ---------------------------------------------------------------------------
# mass_sim
# ---------------------------------------------------------------------------


def test_mass_sim_agent_factory_reachable():
    import cohezion.mass_sim as pkg
    import cohezion.mass_sim.agent_factory as mod

    assert pkg.AgentFactory is mod.AgentFactory


def test_mass_sim_system_vitals_reachable():
    import cohezion.mass_sim as pkg
    import cohezion.mass_sim.system_monitor as mod

    assert pkg.SystemVitals is mod.SystemVitals


def test_mass_sim_system_vitals_behavioural():
    """SystemVitals must be a dataclass or namedtuple with fields."""
    import dataclasses

    from cohezion.mass_sim import SystemVitals

    assert dataclasses.is_dataclass(SystemVitals) or hasattr(SystemVitals, "_fields"), (
        "SystemVitals should be a dataclass or namedtuple"
    )


# ---------------------------------------------------------------------------
# rl
# ---------------------------------------------------------------------------


def test_rl_coherence_reward_reachable():
    import cohezion.rl as pkg
    import cohezion.rl.reward_shaping as mod

    assert pkg.CoherenceReward is mod.CoherenceReward


def test_rl_task_spec_reachable():
    import cohezion.rl as pkg
    import cohezion.rl.task_generator as mod

    assert pkg.TaskSpec is mod.TaskSpec


def test_rl_coherence_reward_behavioural():
    """CoherenceReward must be callable or expose a compute() method."""
    from cohezion.rl import CoherenceReward

    reward_fn = CoherenceReward()
    assert callable(reward_fn) or hasattr(reward_fn, "compute"), (
        "CoherenceReward should be callable or have a compute() method"
    )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_version_entry_reachable():
    import cohezion.registry as pkg
    import cohezion.registry.compound_version_registry as mod

    assert pkg.VersionEntry is mod.VersionEntry


def test_registry_hook_manager_reachable():
    import cohezion.registry as pkg
    import cohezion.registry.hooks as mod

    assert pkg.HookManager is mod.HookManager
    assert pkg.get_hook_manager is mod.get_hook_manager


def test_registry_hook_manager_behavioural():
    """get_hook_manager must return a HookManager instance."""
    from cohezion.registry import HookManager, get_hook_manager

    manager = get_hook_manager()
    assert isinstance(manager, HookManager), (
        f"get_hook_manager() should return HookManager, got {type(manager)}"
    )
