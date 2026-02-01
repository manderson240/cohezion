"""
HIHO Consensus Runner - Recursive Democratic Debate Orchestrator.

Implements Wilbert Smith's 12-parameter HIHO stability principle into a
recursive multi-agent consensus building loop.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from cohezion.swarm.democratic_debate import (
    AgentRole,
    DemocraticDebate,
)
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine
from cohezion.swarm.journey_tracker import (
    AgentType,
    JourneyMetrics,
    get_journey_tracker,
)

logger = logging.getLogger(__name__)


@dataclass
class DummySession:
    """Mock session for final synthesis."""

    rounds: list
    topic: str


class HihoConsensusRunner:
    def __init__(self):
        self.debate = DemocraticDebate()
        self.hiho = HihoVectorEngine()
        self.tracker = get_journey_tracker()
        self.output_dir = Path(
            "src/cohezion/knowledge_graph/universe_nodes/debates/hiho"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_consensus_mission(self, topic: str, rounds: int = 5):
        """
        Runs a recursive consensus mission.
        Each round's synthesis becomes a 'Lattice Constraint' for the next.
        """
        journey_id = self.tracker.start_journey(topic)
        logger.info(f"🚀 Starting HIHO Consensus Mission: {journey_id}")

        current_topic = topic
        lattice_constraint = ""
        all_rounds = []

        for r_num in range(1, rounds + 1):
            logger.info(f"--- Round {r_num} (Recursion: {r_num}/{rounds}) ---")

            # 1. Gather Proposals
            proposals = await self.debate._gather_proposals(
                f"{current_topic}\n[Lattice Constraint]: {lattice_constraint}",
                r_num,
                [],
            )

            # 2. Add HIHO Scoring
            # For each proposal, we estimate stability based on 'perceived coherence'
            # (In a real system, this would be derived from the FLUME trajectory)
            votes = await self.debate._voting_phase(current_topic, proposals)

            # Calculate recursive metrics
            round_coherence = self._calculate_round_coherence(votes)
            hiho_stability = self.hiho.calculate_hiho_score(round_coherence)

            logger.info(
                f"Round {r_num} Coherence: {round_coherence:.2f} | HIHO Stability: {hiho_stability:.2f}"
            )

            # 3. Record Step in Journey
            for role_val, prop in proposals.items():
                self.tracker.record_step(
                    agent_type=AgentType.ANALYST,
                    agent_name=role_val,
                    perspective=f"Round {r_num} Proposal",
                    input_text=current_topic,
                    output_text=prop,
                    physics_state={
                        "coherence": round_coherence,
                        "stability": hiho_stability,
                    },
                    duration_ms=100.0,  # Placeholder
                    metrics=JourneyMetrics(
                        latent_coherence=round_coherence,
                        capability_delta=hiho_stability,
                    ),
                )

            # 4. Synthesize Round
            round_data = {
                "round": r_num,
                "coherence": round_coherence,
                "stability": hiho_stability,
                "proposals": proposals,
                "votes": [v.__dict__ for v in votes],  # Simple serialization
            }
            all_rounds.append(round_data)

            # Recursive Step: Synthesize becoming the constraint for next round
            synthesis_prompt = f"Synthesize round {r_num} into a single technical constraint for round {r_num+1}."
            lattice_constraint = await self.debate._call_agent(
                self.debate.personas[AgentRole.SYNTHESIZER],
                f"{synthesis_prompt}\nFocus on aligning with HIHO stability point (0.5).",
            )

        # Final Synthesis
        final_synthesis = await self.debate._final_synthesis(
            DummySession(all_rounds, topic)
        )

        # End Journey
        await self.tracker.end_journey(
            final_response=final_synthesis["synthesis"],
            final_confidence=final_synthesis["positive_vote_rate"],
            aggregate_metrics=JourneyMetrics(
                latent_coherence=final_synthesis["positive_vote_rate"],
                capability_delta=sum(r["stability"] for r in all_rounds) / rounds,
            ),
        )

        # Save Mission Report
        report = {
            "mission_id": journey_id,
            "topic": topic,
            "rounds": all_rounds,
            "final_synthesis": final_synthesis,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_file = self.output_dir / f"{journey_id}_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))

        logger.info(f"✅ Mission Complete. Report saved to {report_file}")
        return report

    async def run_mass_simulation_mission(
        self, topic: str, num_rounds: int = 1_000_000
    ):
        """
        Runs a mass simulation mission using vectorized physics.
        Captures statistical patterns across 1M rounds.
        """
        journey_id = self.tracker.start_journey(
            f"MASS SIMULATION (N={num_rounds:,}): {topic}"
        )
        logger.info(f"🚀 Starting HIHO Mass Simulation: {journey_id}")

        # 1. Run Vectorized Simulation
        # This replaces 1M LLM calls with a single NumPy operation
        self.hiho.num_rounds = num_rounds
        results = self.hiho.run_simulation()

        # 2. Extract Journey Samples
        # We sample 10 representative states to log as 'agentic steps' in the journey
        samples = results["bright_spot_states"][:10]

        for i, state in enumerate(samples):
            # Map state back to 'agent-like' insight
            # state indices: 0:Awareness, 4:Tempic, 5:Electric, 6:Magnetic, 11:Precipitation
            coherence = float(np.mean(state[4:7]) * state[0])
            stability = self.hiho.calculate_hiho_score(coherence)

            self.tracker.record_step(
                agent_type=AgentType.ANALYST,
                agent_name=f"Probe_{i+1}",
                perspective="Manifold Probe",
                input_text=f"Sample state {i+1} analysis",
                output_text=f"Detected stability: {stability:.4f} @ coherence: {coherence:.4f}",
                physics_state={
                    "coherence": coherence,
                    "stability": stability,
                    "awareness": float(state[0]),
                    "precipitation": float(state[11]),
                },
                duration_ms=0.1,
                metrics=JourneyMetrics(
                    latent_coherence=coherence, capability_delta=stability
                ),
            )

        # 3. Final Synthesis (Expert Review of Mass Data)
        summary_prompt = f"""Review these mass simulation results for N={num_rounds:,} rounds:
- Bright Spots Found: {results['bright_spot_count']:,}
- Mean Stability: {results['mean_stability']:.4f}
- Max Reality Precipitation: {results['max_reality']:.4f}

As Sage, synthesize what this statistical pattern tells us about Cohezion's Recursive Self-Alignment strategy.
Focus on the HIHO 0.5 point as the target for Anthropic-tier alignment."""

        final_synthesis = await self.debate._call_agent(
            self.debate.personas[AgentRole.SYNTHESIZER], summary_prompt
        )

        # End Journey
        await self.tracker.end_journey(
            final_response=final_synthesis,
            final_confidence=results["mean_stability"],
            aggregate_metrics=JourneyMetrics(
                context_utilization=1.0,
                latent_coherence=results["mean_stability"],
                capability_delta=results["max_reality"],
            ),
        )

        # Save Mission Report
        report = {
            "mission_id": journey_id,
            "topic": topic,
            "num_rounds": num_rounds,
            "results": {
                "bright_spot_count": results["bright_spot_count"],
                "mean_stability": float(results["mean_stability"]),
                "max_reality": float(results["max_reality"]),
                "duration_sec": results["duration"],
            },
            "final_synthesis": final_synthesis,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_file = self.output_dir / f"{journey_id}_mass_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))

        logger.info(f"✅ Mass Simulation Complete. Report saved to {report_file}")
        return report


async def main():
    logging.basicConfig(level=logging.INFO)
    runner = HihoConsensusRunner()
    topic = "How should Cohezion implement 'Recursive Self-Alignment' to exceed Anthropic's transparency standards?"

    # 1. Run Expert Debate (Small N for narrative)
    # await runner.run_consensus_mission(topic, rounds=3)

    # 2. Run Mass Simulation (1M rounds for statistical significance)
    await runner.run_mass_simulation_mission(topic, num_rounds=1_000_000)


if __name__ == "__main__":
    asyncio.run(main())
