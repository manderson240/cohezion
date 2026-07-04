"""Tests for GaiaLoop — GAIA SDK local-model orchestration.

All inference is mocked so these run offline without touching :13305.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.gaia_loop import (
    GaiaLoop,
    GoalResult,
    _FAST_MODEL,
    _REASONING_MODEL,
)


@pytest.fixture()
def loop() -> GaiaLoop:
    return GaiaLoop()


# ---------------------------------------------------------------------------
# analyze_goal — happy path and discriminating checks
# ---------------------------------------------------------------------------


class TestAnalyzeGoal:
    def test_returns_goal_result_with_correct_goal_and_model(self, loop):
        """GoalResult.goal and GoalResult.model must reflect the actual inputs."""
        with patch.object(loop, "_chat", return_value="do X") as mock_chat:
            result = loop.analyze_goal("implement GaiaLoop", model="Bonsai-8B-gguf")

        assert isinstance(result, GoalResult)
        # Discriminating: goal and model must be threaded through, not left as defaults.
        assert result.goal == "implement GaiaLoop"
        assert result.model == "Bonsai-8B-gguf"
        assert result.analysis == "do X"
        mock_chat.assert_called_once()

    def test_reasoning_flag_switches_to_reasoning_model(self, loop):
        """reasoning=True must select _REASONING_MODEL, not _FAST_MODEL."""
        with patch.object(loop, "_chat", return_value="think harder") as mock_chat:
            result = loop.analyze_goal("deep task", reasoning=True)

        # Discriminating: a wrong impl that ignores reasoning= would use _FAST_MODEL.
        assert result.model == _REASONING_MODEL
        assert result.model != _FAST_MODEL
        # The chat call must have received the reasoning model, not the fast one.
        call_args = mock_chat.call_args
        assert call_args.kwargs.get("model") == _REASONING_MODEL or (
            len(call_args.args) >= 2 and call_args.args[1] == _REASONING_MODEL
        )

    def test_reasoning_false_keeps_fast_model(self, loop):
        """Default (reasoning=False) must keep _FAST_MODEL."""
        with patch.object(loop, "_chat", return_value="quick answer"):
            result = loop.analyze_goal("quick task")

        assert result.model == _FAST_MODEL


# ---------------------------------------------------------------------------
# is_available — failure path (N3-safe: no real :13305 calls in tests)
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_returns_false_on_connection_error(self, loop):
        """Connection refused must produce False, not raise."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.ConnectError("refused")
            )
            assert loop.is_available() is False

    def test_returns_true_on_200(self, loop):
        """200 response from /v1/models must produce True."""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            assert loop.is_available() is True


# ---------------------------------------------------------------------------
# prioritize_goals — ordering + fallback
# ---------------------------------------------------------------------------


class TestPrioritizeGoals:
    def test_empty_list_returns_empty(self, loop):
        assert loop.prioritize_goals([]) == []

    def test_reorders_by_parsed_response(self, loop):
        """Model response '3, 1, 2' should reorder the list accordingly."""
        goals = ["A", "B", "C"]
        with patch.object(loop, "_chat", return_value="3, 1, 2"):
            ordered = loop.prioritize_goals(goals)
        assert ordered == ["C", "A", "B"]

    def test_falls_back_to_original_on_bad_response(self, loop):
        """Unparseable model response must return original order."""
        goals = ["X", "Y"]
        with patch.object(loop, "_chat", return_value="the model said something weird"):
            ordered = loop.prioritize_goals(goals)
        assert ordered == goals
