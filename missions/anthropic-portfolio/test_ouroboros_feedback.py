"""
Acceptance Tests for the Ouroboros Feedback Loop.

Verifies:
1. Experience Replay: Agents learning from past similar intents.
2. Triune Consensus: Sovereign execution gating via 3-6-9 model.
"""

import asyncio
import importlib.util
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --- ROBUST MOCK DEPENDENCIES ---
def mock_package(name):
    mock = MagicMock()
    spec = importlib.util.spec_from_loader(name, loader=None)
    mock.__spec__ = spec
    sys.modules[name] = mock
    return mock


mock_package("pocket_tts")
mock_package("pocket_tts.modules.stateful_module")
mock_package("soundfile")
mock_package("transformers")

from cohezion.agents.analyst import AnalystAgent, Perspective
from cohezion.universe.engine import UniverseSimulationEngine


@pytest.mark.asyncio
class TestOuroborosFeedback:
    """Verifies recursive improvement and consensus layers."""

    async def test_experience_replay_injection(self):
        """Step 4.1: Agents should hydrate memory from past high-Phi journeys."""
        engine = UniverseSimulationEngine()

        # 1. Mock a past successful journey in the database
        past_experience = "EXPERIENCE REPLAY (Similarity: 0.95): Past Intent: Optimize VRAM"

        # Instantiate agent first, but manually re-sync after mocking
        agent = AnalystAgent(perspective=Perspective.TECHNICAL)
        agent._universe = engine

        with patch.object(engine, "get_experience_replay", return_value=past_experience):
            # 3. Trigger MRP Wake-Up (Synchronize Memory) manually to see the mock
            await agent._synchronize_mrp()

            # POLL for hydration (Max 2 seconds)
            hydrated = False
            for _ in range(20):
                if agent._metrics.get("mrp_hydrated") is True:
                    hydrated = True
                    break
                await asyncio.sleep(0.1)

            # 4. Verify memory is hydrated
            assert hydrated is True, "MRP should hydrate within 2 seconds"
            assert agent._mrp_experience == past_experience

    async def test_triune_execution_gate_success(self):
        """Step 4.2: Execution should proceed when Triune Consensus is high."""
        agent = AnalystAgent(perspective=Perspective.TECHNICAL)
        mock_universe = AsyncMock()

        # HIGH CONSENSUS: 0.9
        mock_universe.facilitate_triune_consensus.return_value = {
            "consensus_score": 0.9,
            "triad": {"3": {}, "6": {}, "9": {}},
            "harmonic_equilibrium": True,
        }
        mock_universe.start_journey.return_value = AsyncMock()

        agent._universe = mock_universe

        # Mock actual processing to return success
        async def mock_process(q):
            return "Success"

        result = await agent._execute_with_universe_tracking("Test Task", mock_process)
        assert result == "Success"
        assert mock_universe.facilitate_triune_consensus.called

    async def test_triune_execution_gate_block(self):
        """Step 4.3: Execution should be blocked when Triune Consensus is low."""
        agent = AnalystAgent(perspective=Perspective.TECHNICAL)
        mock_universe = AsyncMock()

        # LOW CONSENSUS: 0.4
        mock_universe.facilitate_triune_consensus.return_value = {
            "consensus_score": 0.4,
            "triad": {"3": {}, "6": {}, "9": {}},
            "harmonic_equilibrium": False,
        }
        mock_universe.start_journey.return_value = AsyncMock()

        agent._universe = mock_universe

        # Actual process should NOT be called
        mock_process = AsyncMock()

        result = await agent._execute_with_universe_tracking("Dangerous Task", mock_process)

        assert "blocked" in result.lower()
        assert result.security_level == "unstable"
        assert not mock_process.called
