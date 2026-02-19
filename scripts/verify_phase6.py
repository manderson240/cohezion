import asyncio
import logging
from cohezion.compound.telemetry import TokenEfficiencyTracker
from cohezion.compound.optimizer import get_guided_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase6")


async def verify_fiscal_sovereignty():
    # 1. Initialize tracker with a tiny budget
    # budget = $0.01 (1 cent)
    tracker = TokenEfficiencyTracker(budget=0.01)
    router = get_guided_router()

    logger.info(f"Initial Budget Status: {tracker.get_budget_status()}")

    # 2. Simulate a call that uses context to reach 'critical' or 'exhausted'
    # Gemini Pro: $10 / 1M tokens.
    # $0.01 = $10 * (1000 tokens / 1,000,000)
    # So 1000 tokens should exhaust the 1 cent budget.

    logger.info("Recording a call to exhaust budget...")
    tracker.record_call(
        model="gemini-3-pro",
        input_tokens=500,
        output_tokens=600,  # Total 1100 tokens -> $0.011 (Exhausts budget)
        task_type="reasoning",
    )

    status = tracker.get_budget_status()
    logger.info(f"Updated Budget Status: {status}")

    # 3. Check Routing Recommendation
    logger.info("Checking routing recommendation after exhaustion...")
    rec = await router.get_routing_recommendation(
        task_type="reasoning", context="Complex architecture planning"
    )

    logger.info(f"Recommendation: {rec}")

    if rec["suggested_model"] == "phi3:mini" and rec["offload_recommended"]:
        logger.info(
            "✅ SUCCESS: Throttling to economy model (phi3:mini) triggered by budget exhaustion."
        )
    else:
        logger.error("❌ FAILURE: Throttling not triggered as expected.")


if __name__ == "__main__":
    asyncio.run(verify_fiscal_sovereignty())
