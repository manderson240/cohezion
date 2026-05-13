import asyncio
import logging

from cohezion.compound.autoharness import AutoHarnessSynthesizer
from cohezion.integrations.agentverse.llm_executor import LLMExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock Environment: ARC Grid Connectivity
# Rules:
# 1. State is a list of lists (the input grid).
# 2. Action is a list of lists (the predicted output grid).
# 3. verify_action(state, action) returns True if the output grid has the SAME SHAPE as the input grid.
# (This is a simplified ARC rule: many tasks preserve shape).
def mock_arc_env(code_str: str) -> tuple[bool, str]:
    namespace = {}
    try:
        exec(code_str, {}, namespace)
        if "verify_action" not in namespace:
            return False, "Function 'verify_action' not found."

        verify_action = namespace["verify_action"]

        # Test Case 1: Same shape
        grid_in = [[1, 2], [3, 4]]
        grid_out = [[5, 6], [7, 8]]
        if not verify_action(grid_in, grid_out):
            return False, "Failed Test 1: Grids have same shape (2x2), should return True."

        # Test Case 2: Different shape
        grid_diff = [[1, 2, 3], [4, 5, 6]]
        if verify_action(grid_in, grid_diff):
            return (
                False,
                "Failed Test 2: Grids have different shapes (2x2 vs 2x3), should return False.",
            )

        return True, "ARC shape-consistency check passed."
    except Exception as e:
        return False, f"Execution Error: {e}"


async def run_arc_harness():
    print("=== 🧩 TESTING AUTOHARNESS SYNTHESIS (ARC PRIZE) ===")
    executor = LLMExecutor(model="qwen2.5-coder:7b")
    synthesizer = AutoHarnessSynthesizer(llm_executor=executor, max_iterations=3)

    env_desc = """
    The environment is the ARC-AGI-2 challenge.
    A common constraint is that the output grid must have the exact same dimensions as the input grid.
    The state is the input grid (list of lists of integers).
    The action is the proposed output grid (list of lists of integers).
    Write a function verify_action(state, action) that returns True if shapes match, False otherwise.
    """

    generated_code = await synthesizer.synthesize_verifier(env_desc, mock_arc_env)

    print("\n--- GENERATED ARC VERIFIER ---")
    print(generated_code)
    print("------------------------------")

    success, feedback = mock_arc_env(generated_code)
    if success:
        print("✅ AutoHarness successfully synthesized an ARC grid verifier.")
    else:
        print(f"❌ ARC Synthesis failed: {feedback}")


if __name__ == "__main__":
    asyncio.run(run_arc_harness())
