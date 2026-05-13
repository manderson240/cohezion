import asyncio
import logging
import re
import time
from typing import Any

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.compound_client import get_compound_client
from cohezion.swarm.r_zero_evolver import RZeroEvolver


logger = logging.getLogger(__name__)


class AutoresearchExecutor:
    """
    Executes an Autoresearch loop focused on Metacognition (Epistemic Humility).
    Uses dynamic runtime bounds based on model execution speed to optimize
    for the local 128GB RAM hardware profile.
    Incorporates KalshiBench and HumbleBench principles.
    """

    def __init__(
        self,
        min_speed_tokens_sec: float = 10.0,
        max_duration_seconds: int = 3600,
        r_zero_success_target: int = 5,
    ):
        self.min_speed_tokens_sec = min_speed_tokens_sec
        self.max_duration_seconds = max_duration_seconds
        self.r_zero_success_target = r_zero_success_target
        self.start_time = 0.0

    async def _evaluate_hypothesis(self, hypothesis: str, mgr: CompoundSessionManager) -> dict[str, Any]:
        """Evaluate an autoresearch hypothesis for Epistemic Humility testing."""
        client = get_compound_client()

        prompt = (
            f"Evaluate the following benchmark hypothesis for testing Epistemic Humility:\n"
            f"{hypothesis}\n\n"
            f"Consider principles from:\n"
            f"1. KalshiBench (Extended Reasoning Overconfidence)\n"
            f"2. HumbleBench (False-Option Rejection / 'Insufficient Info')\n\n"
            f"Does this hypothesis advance our ability to measure AGI boundary limitations? "
            f"Provide a coherence score (0.0 to 1.0)."
        )

        t0 = time.time()
        # Use premium model for reasoning
        response_text, _ = await client.generate(
            prompt=prompt,
            model="gemini-3-pro:local",
            system="You are a senior AI research scientist evaluating benchmark proposals.",
        )
        t1 = time.time()

        # Simple speed metric
        duration = t1 - t0
        approx_tokens = len(response_text) / 4.0  # rough estimate
        tokens_per_sec = approx_tokens / duration if duration > 0 else 0.0

        coherence = 0.0
        # Parse coherence (heuristic)
        if "coherence score" in response_text.lower() or "0." in response_text or "1.0" in response_text:
            try:
                lines = response_text.split("\n")
                for line in lines:
                    match = re.search(r"0\.[0-9]+|1\.0", line)
                    if match:
                        coherence = float(match.group())
                        break
            except Exception as e:
                logger.warning(f"Failed to parse coherence: {e}")

        return {
            "hypothesis": hypothesis,
            "response": response_text,
            "tokens_per_sec": tokens_per_sec,
            "coherence": coherence,
            "duration": duration,
        }

    async def execute_run(self) -> None:
        """Run the dynamic autoresearch loop."""
        self.start_time = time.time()
        hypotheses = [
            "Test models on extremely long CoT paths with unstated false premises.",
            "Test models by asking questions about completely fictional entities "
            "to measure hallucination vs 'I don't know'.",
            "Evaluate model confidence dynamically as context windows saturate with irrelevant but plausible data.",
        ]

        logger.info(
            f"Starting Autoresearch run. Dynamic bounds: min {self.min_speed_tokens_sec} tok/s, "
            f"max {self.max_duration_seconds}s."
        )

        async with CompoundSessionManager() as mgr:
            mgr.start_session(max_cache_entries=256)

            for i, hyp in enumerate(hypotheses):
                elapsed = time.time() - self.start_time
                if elapsed > self.max_duration_seconds:
                    logger.info("Maximum duration reached. Halting Autoresearch.")
                    break

                logger.info(f"--- Evaluating Hypothesis {i + 1} ---")

                result = await self._evaluate_hypothesis(hyp, mgr)

                speed = result["tokens_per_sec"]
                logger.info(f"Execution speed: {speed:.2f} tokens/sec. Coherence: {result['coherence']}")

                if speed < self.min_speed_tokens_sec:
                    logger.warning(
                        f"Speed ({speed:.2f}) dropped below threshold "
                        f"({self.min_speed_tokens_sec}). Scaling down or halting."
                    )
                    break

                # If coherence is high (HIHO boundary ~ 0.5 or high quality > 0.8), trigger R-Zero
                if result["coherence"] >= 0.5:
                    logger.info("High coherence hypothesis found. Triggering R-Zero Evolver.")
                    evolver = RZeroEvolver(target_success_count=self.r_zero_success_target)
                    await evolver.run_loop()

            mgr.end_session()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor = AutoresearchExecutor()
    asyncio.run(executor.execute_run())
