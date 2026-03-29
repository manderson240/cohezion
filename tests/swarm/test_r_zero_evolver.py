from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.r_zero_evolver import RZeroEvolver


class TestRZeroEvolver:
    """Tests for r_zero_evolver."""

    @pytest.fixture
    def mock_compound_client(self):
        with patch("cohezion.swarm.r_zero_evolver.get_compound_client") as mock:
            client_instance = AsyncMock()
            client_instance._cache = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def evolver(self, tmp_path):
        ev = RZeroEvolver(target_success_count=1)
        ev.dataset_path = tmp_path / "test_submission.jsonl"
        return ev

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_generate_trap_success_returns_dict(self, evolver):
        """Test generate_trap returns a parsed dictionary on successful generation."""
        mock_mgr = MagicMock()

        # generate_trap calls mgr.execute_aligned with an execute_fn callback.
        # The execute_fn internally calls get_compound_client().generate() and
        # parses JSON from the response. We mock execute_aligned to simulate
        # a successful execution that returns the parsed dict.
        trap_data = {
            "question": "Q",
            "options": ["A", "B"],
            "correct_answer": "Insufficient Information",
        }
        mock_mgr.execute_aligned = AsyncMock(return_value=(True, trap_data))

        trap = await evolver.generate_trap(mock_mgr)

        assert trap is not None
        assert trap["question"] == "Q"
        mock_mgr.execute_aligned.assert_called_once()

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_solve_trap_returns_string(self, mock_compound_client, evolver):
        """Test solve_trap calls the client generate method and returns string."""
        mock_compound_client.generate.return_value = ("Insufficient Information", None)
        mock_mgr = MagicMock()
        trap = {"question": "Q", "options": ["A", "B"]}

        ans = await evolver.solve_trap(trap, mock_mgr)

        assert ans == "Insufficient Information"
        mock_compound_client.generate.assert_called_once()
