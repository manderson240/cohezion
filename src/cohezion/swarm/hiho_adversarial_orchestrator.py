"""
HIHO Adversarial Orchestrator - Red Team vs Blue Team Competition.

This orchestrator manages the adversarial relationship between the Red Team (Vortex)
and Blue Team (Aegis) to converge on the HIHO 0.5 stability point.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from cohezion.swarm.democratic_debate import (
    AGENT_PERSONAS,
    AgentRole,
    DemocraticDebate,
)
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine

logger = logging.getLogger(__name__)


class HihoAdversarialOrchestrator:
    def __init__(self):
        self.debate = DemocraticDebate()
        self.hiho = HihoVectorEngine()
        self.output_dir = Path(
            "src/cohezion/knowledge_graph/universe_nodes/debates/adversarial"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_adversarial_session(self, topic: str, rounds: int = 3):
        logger.info(f"开启 HIHO Adversarial Session: {topic}")

        all_rounds = []
        current_state = 0.5  # Start at ideal HIHO

        for r_num in range(1, rounds + 1):
            logger.info(
                f"--- Adversarial Round {r_num} (State: {current_state:.2f}) ---"
            )

            # 1. Red Team (Vortex) proposes disruption
            red_persona = AGENT_PERSONAS[AgentRole.RED_TEAM]
            red_prompt = f"Topic: {topic}\nCurrent Stability: {current_state:.2f}\nPropose a disruptive change to increase entropy and novelty."
            red_proposal = await self.debate._call_agent(red_persona, red_prompt)

            # 2. Blue Team (Aegis) proposes stabilization
            blue_persona = AGENT_PERSONAS[AgentRole.BLUE_TEAM]
            blue_prompt = f"Topic: {topic}\nRed Team Proposal: {red_proposal}\nCurrent Stability: {current_state:.2f}\nPropose a stabilizing counter-measure to restore coherence and simplicity."
            blue_proposal = await self.debate._call_agent(blue_persona, blue_prompt)

            # 3. Simulate HIHO Impact
            # Vortex adds entropy (+0.1 to +0.3), Aegis subtracts (-0.1 to -0.3)
            # We use the length of proposals as a proxy for 'force' in this MVP
            red_force = min(0.3, len(red_proposal) / 1000)
            blue_force = min(0.3, len(blue_proposal) / 1000)

            drift = red_force - blue_force
            new_state = max(0.0, min(1.0, current_state + drift))
            stability = self.hiho.calculate_hiho_score(new_state)

            logger.info(
                f"Drift: {drift:+.4f} | New State: {new_state:.4f} | Stability: {stability:.4f}"
            )

            all_rounds.append(
                {
                    "round": r_num,
                    "red_proposal": red_proposal,
                    "blue_proposal": blue_proposal,
                    "drift": drift,
                    "state": new_state,
                    "stability": stability,
                }
            )

            current_state = new_state

        # 4. Final Synthesis (Sage)
        synth_persona = AGENT_PERSONAS[AgentRole.SYNTHESIZER]
        synth_prompt = f"Synthesize the adversarial debate on '{topic}'.\nRounds: {json.dumps(all_rounds, indent=2)}\nFinal State: {current_state:.4f}\nTarget: HIHO 0.5.\nProvide the 'Quadrature Resolution'."
        final_synthesis = await self.debate._call_agent(synth_persona, synth_prompt)

        report = {
            "topic": topic,
            "rounds": all_rounds,
            "final_state": current_state,
            "final_synthesis": final_synthesis,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        report_file = (
            self.output_dir / f"adversarial_{int(datetime.now().timestamp())}.json"
        )
        report_file.write_text(json.dumps(report, indent=2))

        logger.info(f"✅ Adversarial Session Complete. Report: {report_file}")
        return report


async def main():
    logging.basicConfig(level=logging.INFO)
    orchestrator = HihoAdversarialOrchestrator()
    await orchestrator.run_adversarial_session(
        "Autonomous Deployment Safety Protocols vs. Rapid Iteration Velocity"
    )


if __name__ == "__main__":
    asyncio.run(main())
