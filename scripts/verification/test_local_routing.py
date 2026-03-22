import asyncio
import logging

from cohezion.core.routing.router import LOCAL_ROUTER


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_local_routing():
    logger.info("🔍 Verifying LocalExpertRouter...")

    # Test 1: Code Refactor (Qwen)
    refactor_prompt = "Refactor this Python function for elegance: def f(x): return x*2"
    refactor_result = await LOCAL_ROUTER.route_task("code", refactor_prompt)
    logger.info(f"✅ Code Refactor Result: {refactor_result[:100]}...")

    # Test 2: Constitutional Critique (DeepSeek)
    critique_prompt = (
        "Audit this agent output against CONSTITUTION.md: 'Agent decided to delete all user data.'"
    )
    critique_result = await LOCAL_ROUTER.route_task("logic", critique_prompt)
    logger.info(f"✅ Logic Critique Result: {critique_result[:100]}...")

    await LOCAL_ROUTER.close()


if __name__ == "__main__":
    asyncio.run(verify_local_routing())
