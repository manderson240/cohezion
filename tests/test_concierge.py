"""Tests for Concierge Agent dynamic learning.

TDD: Validates routing logic, confidence scoring, and learning mechanism.
"""

import pytest
from cohezion.governance.concierge import (
    ConciergeAgent,
    SessionBriefing,
    RoutingSuggestion,
    RoutingRecord,
)


class TestConciergeRouting:
    """Prompt routing based on keywords and state."""

    def test_continue_routes_to_continuation(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing(continuation_task="Fix genesis bugs", continuation_path="/tmp/cont.md")
        suggestion = agent.route_prompt("continue", briefing)
        assert suggestion.action == "resume_continuation"
        assert suggestion.confidence >= 0.8

    def test_genesis_keyword_routes_to_worktree(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing()
        suggestion = agent.route_prompt("work on genesis rendering", briefing)
        assert suggestion.action == "switch_worktree"
        assert "genesis" in suggestion.target

    def test_unknown_prompt_fresh_start(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing()
        suggestion = agent.route_prompt("build a spaceship", briefing)
        assert suggestion.action == "fresh_start"
        assert suggestion.confidence < 0.5

    def test_plan_keyword_loads_plan(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing(active_plans=["docs/plans/my-plan.md"])
        suggestion = agent.route_prompt("show the roadmap", briefing)
        assert suggestion.action == "load_plan"


class TestConciergeAutonomyTiers:
    """Autonomy tiers mapped to cosmogonic chain."""

    def test_continuation_gets_medium_autonomy(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing(continuation_task="Fix bugs", continuation_path="/tmp/c.md")
        suggestion = agent.route_prompt("resume", briefing)
        assert suggestion.autonomy_tier == "U(1)^4"

    def test_fresh_start_gets_observe_only(self):
        agent = ConciergeAgent()
        briefing = SessionBriefing()
        suggestion = agent.route_prompt("something new", briefing)
        assert suggestion.autonomy_tier == "SO(12)"


class TestConciergeConfidence:
    """HIHO-based confidence scoring."""

    def test_no_history_returns_hiho(self):
        agent = ConciergeAgent()
        conf = agent._historical_confidence("unknown_action")
        assert conf == pytest.approx(0.5)  # HIHO — uncertain

    def test_confidence_bounded_below_one(self):
        agent = ConciergeAgent()
        # Even with perfect history, confidence should cap below 1.0
        for _ in range(20):
            agent._history.append(RoutingRecord(
                timestamp=0, user_prompt="test", suggested_action="resume_continuation",
                suggested_target="", confidence=0.9, accepted=True, session_duration_s=3600,
            ))
        conf = agent._historical_confidence("resume_continuation")
        assert conf <= 0.95
