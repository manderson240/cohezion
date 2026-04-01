from unittest.mock import AsyncMock, patch

import pytest

from cohezion.swarm.r_zero_evolver import RZeroEvolver


class TestRZeroEvolver:
    """Tests for r_zero_evolver.py — updated to match current API (no track_name)."""

    @pytest.fixture
    def evolver(self, tmp_path):
        ev = RZeroEvolver(target_success_count=1)
        ev.dataset_path = tmp_path / "test_submission.jsonl"
        return ev

    @pytest.mark.fast
    def test_init_default(self):
        """Test initialization with default parameters."""
        evolver = RZeroEvolver(target_success_count=3)
        assert evolver.target_success_count == 3

    @pytest.mark.fast
    def test_init_custom_count(self):
        """Test initialization with custom success count."""
        evolver = RZeroEvolver(target_success_count=10)
        assert evolver.target_success_count == 10

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_generate_trap_success(self, evolver):
        """Test trap generation returns dict on success."""
        mock_mgr = AsyncMock()
        mock_mgr.execute_aligned.return_value = (
            True,
            {"question": "test?", "options": ["A"], "correct_answer": "A"},
        )
        trap = await evolver.generate_trap(mock_mgr)
        assert trap is not None
        assert trap["question"] == "test?"

    @pytest.mark.fast
    @pytest.mark.asyncio
    @patch("cohezion.swarm.r_zero_evolver.get_compound_client")
    async def test_solve_trap(self, mock_client_factory, evolver):
        """Test solving a trap returns string answer."""
        mock_client = AsyncMock()
        mock_client_factory.return_value = mock_client
        mock_client.generate.return_value = ("I believe the answer is A", 50)

        mock_mgr = AsyncMock()
        trap = {"question": "test?", "options": ["A", "B"]}
        answer = await evolver.solve_trap(trap, mock_mgr)
        assert answer == "I believe the answer is A"
