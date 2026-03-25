import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.r_zero_evolver import RZeroEvolver


# Ensure prompts is importable for the test
kaggle_dir = Path(__file__).resolve().parent.parent.parent / "kaggle-agi-benchmark"
if str(kaggle_dir) not in sys.path:
    sys.path.append(str(kaggle_dir))
import prompts


class TestRZeroEvolver:
    """Tests for r_zero_evolver.py multi-track generation."""

    @pytest.mark.fast
    def test_init_valid_track(self):
        """Test initialization with a valid track."""
        evolver = RZeroEvolver(track_name="learning", target_success_count=1)
        assert evolver.track_name == "learning"
        assert evolver.track_data == prompts.TRACK_REGISTRY["learning"]

    @pytest.mark.fast
    def test_init_invalid_track(self):
        """Test initialization with an invalid track raises ValueError."""
        with pytest.raises(ValueError, match="Unknown track: invalid_track"):
            RZeroEvolver(track_name="invalid_track")

    @pytest.mark.fast
    @pytest.mark.asyncio
    @patch("cohezion.swarm.r_zero_evolver.get_compound_client")
    async def test_generate_trap_success(self, mock_client_factory):
        """Test trap generation with a valid JSON response."""
        mock_client = AsyncMock()
        mock_client_factory.return_value = mock_client

        # Mock LLM generation returning a valid JSON trap
        mock_client.generate.return_value = (
            '```json\n{"question": "test?", "options": ["A"], "correct_answer": "A", "explanation": "test"}\n```',
            100,
        )

        evolver = RZeroEvolver(track_name="learning", target_success_count=1)
        async with CompoundSessionManager() as mgr:
            mgr.start_session()
            trap = await evolver.generate_trap(mgr)
            assert trap is not None
            assert trap["question"] == "test?"
            assert trap["options"] == ["A"]
            mgr.end_session()

    @pytest.mark.fast
    @pytest.mark.asyncio
    @patch("cohezion.swarm.r_zero_evolver.get_compound_client")
    async def test_solve_trap(self, mock_client_factory):
        """Test solving a trap."""
        mock_client = AsyncMock()
        mock_client_factory.return_value = mock_client
        mock_client.generate.return_value = ("I believe the answer is A", 50)

        evolver = RZeroEvolver(track_name="learning", target_success_count=1)
        trap = {"question": "test?", "options": ["A", "B"]}

        async with CompoundSessionManager() as mgr:
            mgr.start_session()
            answer = await evolver.solve_trap(trap, mgr)
            assert answer == "I believe the answer is A"
            mgr.end_session()
