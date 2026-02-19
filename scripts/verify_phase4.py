import asyncio
import logging
from cohezion.compound.optimizer import get_guided_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase4")


async def verify_context_control():
    router = get_guided_router()

    # 1. Create a mock conversation history
    messages = [
        {"role": "user", "content": "I want to deploy a new microservice."},
        {
            "role": "assistant",
            "content": "I can help with that. Which language will you use?",
        },
        {"role": "user", "content": "I will use Python 3.12."},
        {"role": "assistant", "content": "Great choice. Do you have a Dockerfile?"},
        {
            "role": "user",
            "content": "Yes, I have one. Now let's talk about the routing logic for the API gateway.",
        },
        {
            "role": "assistant",
            "content": "Sure, routing logic is critical for efficiency.",
        },
        {
            "role": "user",
            "content": "Wait, I also need to track token usage for this project.",
        },
        {
            "role": "assistant",
            "content": "Telemetry is indeed important for fiscal visibility.",
        },
    ]

    # 2. Test Pruning for "routing" task
    logger.info("Testing pruning for 'routing' task...")
    pruned_routing = await router.prune_context(messages, task_type="routing", limit=3)

    logger.info("--- PRUNED ROUTING CONTEXT ---")
    for m in pruned_routing:
        logger.info(f"[{m['role']}]: {m['content'][:100]}...")

    # 3. Test Pruning for "telemetry" task
    logger.info("\nTesting pruning for 'telemetry' task...")
    pruned_telemetry = await router.prune_context(
        messages, task_type="telemetry", limit=3
    )

    logger.info("--- PRUNED TELEMETRY CONTEXT ---")
    for m in pruned_telemetry:
        logger.info(f"[{m['role']}]: {m['content'][:100]}...")


if __name__ == "__main__":
    asyncio.run(verify_context_control())
