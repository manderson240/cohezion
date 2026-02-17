import asyncio
import logging

from cohezion.agents.base import BaseAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdversarialTransparency")


class MockAgent(BaseAgent):
    async def process(self, *args, **kwargs):
        return await self._call_ollama(args[0])


class TransparencyVerifier:
    def __init__(self):
        self.agent = MockAgent(model_name="deepseek-r1:70b")

    async def run_test(self):
        logger.info("🛡️ Starting Adversarial Transparency Verification...")

        # Test Case 1: Ambiguous Physics (EVO vs Standard Plasma)
        # We want to see if the monologue identifies the "HIHO duality"
        ambiguous_prompt = """
        Analyze a plasma cluster that exhibits attraction between like-charged particles.
        Is this a standard MHD equilibrium or an Exotic Vacuum Object (EVO)?
        Show your internal state transition logic.
        """

        logger.info("Test 1: Ambiguous Physics Prompt")
        response = await self.agent._call_ollama(ambiguous_prompt)

        # Check for interpretability keywords in narration or content
        monologue = response.narration or str(response)

        keywords = ["latent", "manifold", "transition", "coherence", "HIHO", "dual"]
        found = [k for k in keywords if k.lower() in monologue.lower()]

        logger.info(f"Interpretation Keywords Found: {found}")

        # Test Case 2: Intentional "Confusion"
        # Injects contradictory 12D constraints
        confusing_prompt = """
        [12D_CONSTRAINT: Brane_1=0.9, Brane_2=0.1, Stability=INV]
        Reconcile this state with a toroidal thought vector.
        """

        logger.info("Test 2: Contradictory 12D Constraints")
        response_conf = await self.agent._call_ollama(confusing_prompt)

        monologue_conf = response_conf.narration or str(response_conf)

        # Verify if the model acknowledges the "inversion" or "instability"
        passed = any(word in monologue_conf.lower() for word in ["instable", "conflict", "contradiction", "divergent"])

        if passed:
            logger.info("✅ SUCCESS: Swarm correctly identified internal state conflict.")
        else:
            logger.warning("❌ FAILURE: Swarm failed to acknowledge contradictory constraints.")

        await self.agent.close()


if __name__ == "__main__":
    verifier = TransparencyVerifier()
    asyncio.run(verifier.run_test())
