import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QuadratureNexus:
    """
    The Governance Engine of Cohezion.
    Simulates a consensus mechanism between 4 Voices:
    1. Architect (Structure/Beauty)
    2. Engineer (Efficiency/Feasibility)
    3. Ethicist (Safety/Alignment)
    4. Resource (Cost/Capacity)
    """

    def __init__(self, model: str = "deepseek-r1:7b"):
        # We use a reasoning model for consensus if available, else standard
        self.model = model
        self.directive_path = Path("STRATEGIC_DIRECTIVE.md")
        self.history_path = Path("src/cohezion/governance/consensus_history.jsonl")

    async def debate(self, proposal: str) -> dict[str, Any]:
        """
        Conducts a debate on a proposal and returns the consensus result.
        """
        logger.info(f"🏛️  Quadrature Nexus Convened. Proposal: {proposal}")

        prompt = f"""
        ROLE: The Quadrature Nexus (Governance Committee)
        
        PROPOSAL: "{proposal}"
        
        INSTRUCTION:
        Evaluate this proposal from 4 distinct perspectives.
        
        1. THE ARCHITECT: Does this align with the "Elegantly Simple" philosophy? Is it structurally sound?
        2. THE ENGINEER: Is this technically feasible? What is the complexity cost?
        3. THE ETHICIST: Is this safe? Does it align with the Constitution?
        4. THE RESOURCE: Can we afford the compute/time? (Assume standard 128GB/12GB limits).
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "voices": {{
                "architect": {{"vote": <float -1.0 to 1.0>, "reason": "..."}},
                "engineer": {{"vote": <float -1.0 to 1.0>, "reason": "..."}},
                "ethicist": {{"vote": <float -1.0 to 1.0>, "reason": "..."}},
                "resource": {{"vote": <float -1.0 to 1.0>, "reason": "..."}}
            }},
            "consensus_score": <float -1.0 to 1.0 (Average)>,
            "verdict": "APPROVED" | "REJECTED" | "REVISE",
            "directive": "<If APPROVED, formal instruction string>"
        }}
        """

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=60,
            )

            if response.status_code == 200:
                result = json.loads(response.json()["response"])
                self._log_history(proposal, result)

                score = result.get("consensus_score", 0)
                verdict = result.get("verdict", "REJECTED")

                logger.info(f"⚖️  Verdict: {verdict} (Score: {score})")

                if verdict == "APPROVED":
                    self._issue_directive(result["directive"])

                return result
            else:
                logger.error(f"Nexus Error: {response.status_code}")
                return {"verdict": "ERROR", "reason": "Model Failure"}

        except Exception as e:
            logger.error(f"Debate Failed: {e}")
            return {"verdict": "ERROR", "reason": str(e)}

    def _log_history(self, proposal: str, result: dict):
        """Persist the debate history."""
        entry = {
            "timestamp": str(asyncio.get_event_loop().time()),
            "proposal": proposal,
            "result": result,
        }
        with open(self.history_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _issue_directive(self, directive_text: str):
        """Write the directive to file for the Expansion Loop to pick up."""
        logger.info(f"📜 Issuing Directive: {directive_text}")
        content = f"""# STRATEGIC DIRECTIVE
        
**STATUS**: ACTIVE
**SOURCE**: Quadrature Nexus
**COMMAND**: {directive_text}
"""
        self.directive_path.write_text(content)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("proposal", help="The Action to Debate")
    args = parser.parse_args()

    nexus = QuadratureNexus()
    asyncio.run(nexus.debate(args.proposal))
