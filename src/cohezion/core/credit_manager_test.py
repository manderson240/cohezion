"""
Verification for Phase 6 (Recursive Sovereignty).
Tests credit-based model routing.
"""

import asyncio
import logging

from cohezion.core.credit_manager import MODEL_COSTS, get_credit_manager

logging.basicConfig(level=logging.INFO)


async def test_credit_routing():
    print("--- Testing Credit-Based Model Routing ---")

    cm = get_credit_manager()
    agent_id = "TestAgent"

    # 1. Check default balance
    balance = cm.get_balance(agent_id)
    print(f"Initial Balance: {balance} credits")

    # 2. Try to afford Gemini Pro
    preferred = "gemini-3-pro"
    cost = MODEL_COSTS.get(preferred, 0)
    print(f"\nModel: {preferred} (Cost: {cost} credits)")

    model = cm.get_best_affordable_model(agent_id, preferred)
    print(f"Selected Model: {model}")

    if model == preferred:
        print("✅ Agent CAN afford Gemini Pro.")

    # 3. Drain credits and retry
    print("\n--- Draining Credits ---")
    cm._balances[agent_id] = 5  # Set low balance
    print(f"New Balance: {cm.get_balance(agent_id)}")

    model = cm.get_best_affordable_model(agent_id, preferred)
    print(f"Selected Model: {model}")

    if model != preferred:
        print(f"✅ Agent downgraded to {model} as expected.")
    else:
        print("❌ FAILURE: Agent should have downgraded.")

    # 4. Test crediting (from NodeVerification yield)
    print("\n--- Crediting from NodeVerification ---")
    cm.credit(agent_id, 50)
    print(f"After Credit: {cm.get_balance(agent_id)}")


if __name__ == "__main__":
    asyncio.run(test_credit_routing())
