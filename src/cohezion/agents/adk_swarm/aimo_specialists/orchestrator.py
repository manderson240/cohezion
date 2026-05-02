from google import adk

from .agent import agent as algebraist
from .number_theorist import agent as number_theorist


class AIMOOrchestrator(adk.Agent):
    """Main orchestrator for the AIMO Mathematical Reasoning Swarm."""

    def __init__(self, **kwargs):
        super().__init__(
            name="AIMOOrchestrator",
            instructions=(
                "You coordinate a team of mathematical specialists to solve AIMO problems. "
                "1. Analyze the problem to determine the best specialist (Algebraist or NumberTheorist). "
                "2. Delegate the problem to the specialist. "
                "3. If the first attempt fails verification, ask for a second opinion. "
                "4. Provide the final consensus answer in \\boxed{X} format."
            ),
            # ADK A2A: Register specialists as sub-agents
            agents=[algebraist, number_theorist],
            **kwargs,
        )


orchestrator = AIMOOrchestrator()
