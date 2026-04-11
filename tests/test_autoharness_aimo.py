import asyncio
import logging
import sys
from pathlib import Path
from cohezion.compound.autoharness import AutoHarnessSynthesizer
from cohezion.integrations.agentverse.llm_executor import LLMExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock Environment: Modular Arithmetic Solver
# Rules:
# 1. State is a dictionary: {"n": int, "mod": int}
# 2. Action is an integer X.
# 3. verify_action(state, action) returns True if (action % state['mod']) == state['n']
def mock_aimo_env(code_str: str) -> tuple[bool, str]:
    """
    Simulates the environment feedback by executing the generated code
    against test cases.
    """
    namespace = {}
    try:
        exec(code_str, {}, namespace)
        if "verify_action" not in namespace:
            return False, "Function 'verify_action' not found in code."

        verify_action = namespace["verify_action"]

        # Test Case 1: Simple match
        state = {"n": 3, "mod": 7}
        if not verify_action(state, 10):
            return (
                False,
                f"Failed Test 1: 10 mod 7 should be 3. verify_action({state}, 10) returned False.",
            )

        # Test Case 2: Negative number (should be handled correctly)
        if not verify_action(state, -4):
            return (
                False,
                f"Failed Test 2: -4 mod 7 should be 3. verify_action({state}, -4) returned False.",
            )

        # Test Case 3: Incorrect answer
        if verify_action(state, 5):
            return (
                False,
                f"Failed Test 3: 5 mod 7 is not 3. verify_action({state}, 5) returned True (should be False).",
            )

        return True, "All test cases passed."
    except Exception as e:
        return False, f"Execution Error: {e}"


async def run_autoharness_test():
    print("=== 🛠️ TESTING AUTOHARNESS SYNTHESIS (AIMO) ===")

    # Use local phi4 for fast iteration
    executor = LLMExecutor(model="phi4:latest")
    synthesizer = AutoHarnessSynthesizer(llm_executor=executor, max_iterations=3)

    env_desc = """
    The environment handles modular arithmetic verification.
    State is a dictionary with 'n' (the remainder) and 'mod' (the modulus).
    The action is a candidate integer answer.
    The function verify_action(state, action) must return True if action is congruent to n modulo mod.
    Formula: action % mod == n
    Important: Handle negative numbers correctly (Python's % operator does this, but ensure the logic is explicit).
    """

    generated_code = await synthesizer.synthesize_verifier(env_desc, mock_aimo_env)

    print("\n--- GENERATED VERIFIER CODE ---")
    print(generated_code)
    print("------------------------------")

    success, feedback = mock_aimo_env(generated_code)
    if success:
        print("✅ AutoHarness successfully synthesized a working AIMO verifier.")
    else:
        print(f"❌ Synthesis failed. Final feedback: {feedback}")


if __name__ == "__main__":
    asyncio.run(run_autoharness_test())
