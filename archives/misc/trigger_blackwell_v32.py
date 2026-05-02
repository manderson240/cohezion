import asyncio
import logging
import os

from cohezion.integrations.kaggle_submission_improved import KaggleSubmissionOrchestrator


logging.basicConfig(level=logging.INFO)


async def main():
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")
    orchestrator = KaggleSubmissionOrchestrator(username=username, key=key)
    result = await orchestrator.run_baseline_flow(
        "nvidia-nemotron-model-reasoning-challenge", "nemotron-lora-blackwell-v32"
    )
    print(f"Sprint triggered successfully: {result}")


if __name__ == "__main__":
    asyncio.run(main())
