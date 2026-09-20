"""Unit tests for GAIA SDK Autonomous Kaggle Competition Daemon & Agent Swarm.

Tests:
1. Strict filtering of active competitions (exclusion of closed competitions and Pokémon TCG).
2. GAIA SDK agent initialization and configuration.
3. AutoHarness deterministic action verification (<10ms).
4. Agent cycle execution, EventBus publishing, and dual-store payload creation.
5. Swarm daemon multi-track portfolio markdown synthesis.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.competitions.gaia_kaggle_daemon import (
    ACTIVE_KAGGLE_TRACKS,
    AgentCycleReport,
    GaiaKaggleCompetitionAgent,
    GaiaKaggleSwarmDaemon,
    KaggleTrackSpec,
)
from cohezion.core.event_bus import EventBus


def test_active_kaggle_tracks_filter() -> None:
    """Ensure only active, unexpired competitions are tracked, and Pokemon TCG is strictly excluded."""
    # Must have our active portfolio
    expected_slugs = {
        "arc-prize-2026-arc-agi-2",
        "arc-prize-2026-arc-agi-3",
        "arc-prize-2026-paper-track",
        "rsna-knee-abnormality-detection",
        "biohub-cell-tracking-during-development",
        "kaggriculture-crop-yield-prediction",
        "enveda-casmi-2026",
    }
    assert set(ACTIVE_KAGGLE_TRACKS.keys()) == expected_slugs

    # Strict exclusion: Pokemon TCG and closed tracks must NEVER be present
    for slug in ACTIVE_KAGGLE_TRACKS:
        assert "pokemon" not in slug.lower()
        assert "tcg" not in slug.lower()


def test_gaia_kaggle_agent_initialization() -> None:
    """Verify that GAIA agent initializes cleanly with assigned hardware and models."""
    spec = ACTIVE_KAGGLE_TRACKS["biohub-cell-tracking-during-development"]
    agent = GaiaKaggleCompetitionAgent(spec)

    assert agent.agent_id == "gaia_agent_biohub_cell_tracking_during_development"
    assert agent.spec.assigned_model == "Qwen3-Coder-30B-A3B-Instruct-GGUF"
    assert agent.spec.hardware_target == "Strix Halo iGPU (RDNA 3.5 / Vulkan)"
    assert agent.cycle_count == 0
    assert agent.last_report is None


def test_autoharness_action_verification() -> None:
    """Verify AutoHarness deterministic AST validation executes quickly without LLM."""
    spec = ACTIVE_KAGGLE_TRACKS["rsna-knee-abnormality-detection"]
    agent = GaiaKaggleCompetitionAgent(spec)

    action = "Maintain non-overlapping TTA speedup and layer multi-resolution CoatNet-Raptor attention."
    res = agent.verify_action_autoharness(action)

    assert res.valid is True
    assert res.latency_ms < 50.0  # Typically <1ms AST inspection


@pytest.mark.asyncio
async def test_agent_run_cycle_mocked() -> None:
    """Test full agent cycle with mocked external network and subprocess calls."""
    bus = EventBus()
    spec = ACTIVE_KAGGLE_TRACKS["arc-prize-2026-arc-agi-2"]
    agent = GaiaKaggleCompetitionAgent(spec, event_bus=bus)

    with (
        patch.object(agent, "poll_kaggle_status", return_value={"status": "COMPLETE", "score": 29.03}),
        patch.object(
            agent,
            "reason_tactical_action",
            return_value="Expand Quad-L4x4 dynamic CUDA batching with AutoHarness shape preservation.",
        ),
        patch("cohezion.competitions.gaia_kaggle_daemon.surreal_query", return_value=[{"status": "OK"}]),
        patch("cohezion.competitions.gaia_kaggle_daemon.persist_item", return_value={"surreal": True, "vault": True}),
    ):
        report = await agent.run_cycle()

    assert isinstance(report, AgentCycleReport)
    assert report.track_slug == "arc-prize-2026-arc-agi-2"
    assert report.submission_status == "COMPLETE"
    assert report.latest_score == 29.03
    assert report.autoharness_verified is True
    assert agent.cycle_count == 1
    assert agent.last_report == report


def test_swarm_daemon_portfolio_markdown() -> None:
    """Verify markdown portfolio formatting contains all active tracks."""
    daemon = GaiaKaggleSwarmDaemon()
    mock_reports = [
        AgentCycleReport(
            track_slug=slug,
            display_name=spec.display_name,
            timestamp="2026-09-19T01:00:00Z",
            assigned_model=spec.assigned_model,
            hardware_target=spec.hardware_target,
            submission_status="COMPLETE",
            latest_score=spec.sota_benchmark,
            tactical_recommendation="Optimize weights",
            autoharness_verified=True,
            autoharness_latency_ms=0.5,
            execution_latency_ms=10.0,
        )
        for slug, spec in ACTIVE_KAGGLE_TRACKS.items()
    ]

    md = daemon.generate_portfolio_markdown(mock_reports)
    assert "# 🏆 GAIA SDK Autonomous Kaggle Competition Portfolio" in md
    assert "Active Tracks**: `7`" in md
    for spec in ACTIVE_KAGGLE_TRACKS.values():
        assert spec.display_name in md
