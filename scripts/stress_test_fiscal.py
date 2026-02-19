import asyncio
import logging
import time
from cohezion.compound.telemetry import TokenEfficiencyTracker
from cohezion.compound.optimizer import get_guided_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress_test_fiscal")

async def stress_test_budget():
    logger.info("Starting Stress Test: Budget Bypass & Race Conditions")
    
    # 1. Force a clean tracker with a small budget
    # Using a different budget value to avoid singleton reuse if it persists across test runs
    # But it's a singleton, so I need to reset it.
    tracker = TokenEfficiencyTracker(budget=0.05)
    router = get_guided_router()
    
    # 2. Rapid fire calls to record_call (Stress auto-persist)
    logger.info("Triggering rapid-fire record_call to test auto-persist logic...")
    for i in range(25):
        tracker.record_call(
            model="phi3:mini", # cheap
            input_tokens=100,
            output_tokens=100,
            task_type="stress_test"
        )
    
    # 3. Exhaust budget
    logger.info("Exhausting budget...")
    tracker.record_call(
        model="gemini-3-pro",
        input_tokens=5000,
        output_tokens=5000, # $10 * 0.01 = $0.10 (Exhausts $0.05 budget)
        task_type="exhaustion"
    )
    
    status = tracker.get_budget_status()
    logger.info(f"Final Status: {status}")
    
    # 4. Attempt multiple concurrent routing calls (Test for bypass)
    logger.info("Attempting concurrent routing calls to check for budget bypass...")
    tasks = []
    for _ in range(5):
        tasks.append(router.get_routing_recommendation(task_type="critical_reasoning", context="High stakes decision"))
    
    results = await asyncio.gather(*tasks)
    
    fail_count = 0
    for r in results:
        if r["suggested_model"] == "gemini-3-pro":
            logger.error(f"❌ BUDGET BYPASS DETECTED: Suggested '{r['suggested_model']}' despite budget exhaustion!")
            fail_count += 1
        else:
            logger.info(f"✅ Correct Throttling: Suggested '{r['suggested_model']}' (Reason: {r['reason']})")
    
    if fail_count == 0:
        logger.info("✅ SUCCESS: Fiscal guardrails held under concurrent pressure.")
    else:
        logger.error(f"❌ FAILURE: {fail_count}/5 calls bypassed budget guardrails!")

if __name__ == "__main__":
    asyncio.run(stress_test_budget())
