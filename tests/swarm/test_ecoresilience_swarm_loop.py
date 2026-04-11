"""Tests for the EcoResilience Swarm Resonance Loop.

Verifies the collaborative integration between Gemma 4 (EcoResilienceAgent),
Ollama (PhysicsAgent), and Mistral (BiologistAgent) within the Cohezion swarm.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.agents.ecoresilience_agent import EcoResilienceAgent
from cohezion.swarm.orchestrator import Agent, Task
from cohezion.swarm.resonance import SwarmOrchestrator, ResonanceProtocol, ResonanceState


class TestEcoResilienceSwarmLoop:
    @pytest.mark.asyncio
    async def test_swarm_resonance_loop(self):
        """Verify the 3-agent resonance loop for a complex ecosystem crisis."""
        # 1. Setup the SwarmOrchestrator and Resonance Protocol
        protocol = ResonanceProtocol()
        orchestrator = SwarmOrchestrator(resonance_protocol=protocol)

        # 2. Mock the Agents
        # EcoResilienceAgent (Gemma 4) - The Lead
        mock_gemma = AsyncMock()
        mock_gemma.analyze_ecosystem.return_value = (
            "Gemma 4: Identified HIHO instability in the soil microbiome."
        )

        # PhysicsAgent (Ollama)
        mock_physics_fn = lambda task: (
            "Physics: 12D Manifold shows gravitational divergence in the water table."
        )

        # BiologistAgent (Mistral)
        mock_biologist_fn = lambda task: (
            "Biology: Microbial diversity dropping below critical threshold."
        )

        # 3. Register Agents in Swarm
        orchestrator.register_agent(
            Agent(
                id="ecoresilience",
                name="EcoResilienceAgent",
                execute_fn=lambda t: asyncio.run(
                    mock_gemma.analyze_ecosystem(t.description, "traj-swarm")
                ),
                capabilities=["tek", "unified-physics", "resonance"],
            )
        )
        orchestrator.register_agent(
            Agent(
                id="physics",
                name="PhysicsAgent",
                execute_fn=mock_physics_fn,
                capabilities=["unified-physics", "manifold-analysis"],
            )
        )
        orchestrator.register_agent(
            Agent(
                id="biologist",
                name="BiologistAgent",
                execute_fn=mock_biologist_fn,
                capabilities=["microbiology", "ecosystem-analysis"],
            )
        )

        # 4. Define the Task
        task = Task(
            id="crisis-001",
            description="Sudden collapse of the Great Barrier Reef microbiome due to temperature spikes.",
            required_capabilities=["tek", "unified-physics", "microbiology"],
        )

        # 5. Execute the Resonance Loop
        results = await orchestrator.execute_resonance_loop(task, lead_agent_id="ecoresilience")

        # 6. Verify Results
        assert len(results) == 3
        assert all(r.success for r in results.values())

        outputs = [r.output for r in results.values()]
        assert any("Gemma 4" in o for o in outputs)
        assert any("Physics" in o for o in outputs)
        assert any("Biology" in o for o in outputs)

        # 7. Verify Resonance sharing
        collective_coherence = await protocol.calculate_collective_coherence()
        assert collective_coherence == 0.5  # Based on our successful mocks

    @pytest.mark.asyncio
    async def test_resonance_protocol_12d_sharing(self):
        """Verify the 'Resonance Protocol' for cross-agent 12D state vector sharing."""
        protocol = ResonanceProtocol()

        state_vector = ResonanceState(
            agent_id="ecoresilience",
            spatial=[0.1, 0.2, 0.3],
            time=0.4,
            brane=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
            coherence=0.5,
        )

        await protocol.share(state_vector)

        latest = await protocol.get_latest()
        assert latest.agent_id == "ecoresilience"
        assert latest.brane[0] == 0.5
        assert latest.coherence == 0.5
