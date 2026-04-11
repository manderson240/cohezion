import os
import json
import asyncio
import logging
from pathlib import Path
from cohezion.compound.autoharness import AutoHarnessSynthesizer
from cohezion.integrations.agentverse.llm_executor import LLMExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArcGridLawSynthesis")


class ARCEvaluationEnv:
    def __init__(self, task_data):
        self.train_examples = task_data["train"]
        self.test_examples = task_data["test"]

    def test_law(self, code_str: str) -> tuple[bool, str]:
        """Tests the synthesized law against all training examples."""
        namespace = {}
        try:
            exec(code_str, {}, namespace)
            # We look for a 'transform' function synthesized by AutoHarness
            if "transform" not in namespace:
                return False, "Function 'transform(grid)' not found."

            transform = namespace["transform"]
            for i, ex in enumerate(self.train_examples):
                input_grid = ex["input"]
                expected_output = ex["output"]
                actual_output = transform(input_grid)

                if actual_output != expected_output:
                    return (
                        False,
                        f"Failed Example {i}: Expected {expected_output}, got {actual_output}",
                    )

            return True, "All training examples passed."
        except Exception as e:
            return False, f"Runtime Error: {e}"


async def synthesize_laws():
    print("=== 🧪 ARC-AGI-2: GRID LAW SYNTHESIS (AUTOHARNESS) ===")

    # Use qwen2.5-coder for high-fidelity code synthesis
    executor = LLMExecutor(model="qwen3-coder:30b")
    synthesizer = AutoHarnessSynthesizer(llm_executor=executor, max_iterations=5)

    training_dir = Path("data/arc-agi-2-repo/data/training")
    task_files = sorted(list(training_dir.glob("*.json")))[:10]

    grid_laws = {}

    for task_file in task_files:
        task_id = task_file.stem
        print(f"\n[Task {task_id}] Processing...")

        with open(task_file) as f:
            task_data = json.load(f)

        env = ARCEvaluationEnv(task_data)

        # Prepare the environment description from examples
        env_desc = f"ARC Task {task_id}:\n"
        for i, ex in enumerate(task_data["train"]):
            env_desc += f"Example {i}: Input {ex['input']} -> Output {ex['output']}\n"
        env_desc += "\nWrite a Python function `def transform(grid):` that perfectly reproduces this mapping for all examples."

        # Note: We use synthesize_policy here because we want the model to generate the rule, not just verify it.
        # This is 'Harness-as-Policy'.
        law_code = await synthesizer.synthesize_policy(env_desc, env.test_law)

        success, feedback = env.test_law(law_code)
        if success:
            print(f"✅ Task {task_id}: Law synthesized successfully.")
            grid_laws[task_id] = law_code
        else:
            print(f"❌ Task {task_id}: Synthesis failed. {feedback}")

    # Save the Grid Law Library
    output_path = Path("data/arc_grid_law_library.json")
    with open(output_path, "w") as f:
        json.dump(grid_laws, f, indent=2)
    print(f"\n🚀 Grid Law Library saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(synthesize_laws())
