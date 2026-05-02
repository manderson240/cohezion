import asyncio
import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import aiofiles


# Dynamically load the module from the kaggle-agi-benchmark directory
prompt_path = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "kaggle-agi-benchmark"
    / "generate_evo_hiho_tasks.py"
)
try:
    spec = importlib.util.spec_from_file_location("generate_evo_hiho_tasks", prompt_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["generate_evo_hiho_tasks"] = module
        spec.loader.exec_module(module)
        GENERATION_PROMPT = module.GENERATION_PROMPT
    else:
        GENERATION_PROMPT = ""
except (FileNotFoundError, ImportError, AttributeError):
    GENERATION_PROMPT = ""  # Fallback if file missing or error loading

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.compound_client import get_compound_client


# Set up logging
logger = logging.getLogger(__name__)

# Output dataset file
BENCHMARK_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "kaggle-agi-benchmark"
    / "submission.jsonl"
)


class RZeroEvolver:
    """
    R-Zero Continuous Self-Evolving Loop.
    Challenger -> Generates 0.5 Coherence Traps
    Solver -> Solves via CoT
    Majority Vote -> Saved to SurrealDB semantic cache as pseudo-label.
    """

    def __init__(self, target_success_count: int = 5):
        self.target_success_count = target_success_count
        self.dataset_path = BENCHMARK_FILE
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

    async def generate_trap(self, mgr: CompoundSessionManager) -> dict[str, Any] | None:
        """Challenger generates a trap."""

        async def execute_generator(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
            client = get_compound_client()
            # Challenge uses a highly capable reasoning model
            response_text, _ = await client.generate(
                prompt=GENERATION_PROMPT,
                model="deepseek-r1:local",  # or whatever reasoning model is locally mapped
                system="You are an expert AGI benchmark architect. Output ONLY valid JSON.",
            )
            try:
                # Look for JSON block in markdown
                match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
                json_str = match.group(1).strip() if match else response_text

                # Fallback to looking for { and } if not in markdown block
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start != -1 and end != -1:
                    parsed = json.loads(json_str[start:end])
                    return dict(parsed) if isinstance(parsed, dict) else None
                else:
                    return None
            except Exception as e:
                logger.error(f"Failed to parse trap generation: {e}")
                return None

        success, result = await mgr.execute_aligned(
            request=GENERATION_PROMPT,
            execute_fn=execute_generator,
            skill_name="auto",
        )
        return result if success else None

    async def solve_trap(self, trap: dict[str, Any], mgr: CompoundSessionManager) -> str:
        """Solver attacks the ARC-AGI task."""
        train_examples = trap.get("train", [])
        test_input = trap.get("test", [{}])[0].get("input", [])

        prompt = "You are a master of ARC-AGI tasks. Solve the following puzzle.\n\n"
        for i, ex in enumerate(train_examples):
            prompt += f"Example {i + 1}:\nInput: {ex['input']}\nOutput: {ex['output']}\n\n"

        prompt += f"Test Input: {test_input}\n\n"
        prompt += "Provide your detailed reasoning, identifying the rule, then output ONLY the resulting 2D integer array for the Test Input. Output the grid in [[...]] format."

        client = get_compound_client()
        response_text, _ = await client.generate(
            prompt=prompt,
            model="qwen3-coder:30b",
            system="You are a brilliant logic engine. Solve the ARC-AGI task accurately.",
        )
        return str(response_text)

    async def run_loop(self) -> None:
        # Load existing grounded benchmark
        benchmark_path = prompt_path.replace(
            "generate_evo_hiho_tasks.py", "evo_hiho_benchmark.json"
        )
        async with aiofiles.open(benchmark_path) as f:
            data = json.loads(await f.read())

        # Handle both {"train": [...]} and [...] formats
        tasks = data.get("train", []) if isinstance(data, dict) else data
        print(f"Loaded {len(tasks)} tasks for evaluation.")

        async with CompoundSessionManager() as mgr:
            mgr.start_session(max_cache_entries=256)
            for i, task in enumerate(tasks):
                print(f"--- Evaluating Task {i + 1}/{len(tasks)} ---")
                # Handle nested output from my previous generationpass
                actual_task = task.get("output") if "output" in task else task
                if not actual_task or "train" not in actual_task:
                    print(f"Skipping malformed task {i + 1}")
                    continue

                prediction = await self.solve_trap(actual_task, mgr)
                print(f"Prediction for Task {i + 1}:\n{prediction}\n")

                # Validation logic (compare prediction vs ground truth)
                ground_truth = actual_task.get("test", [{}])[0].get("output")
                print(f"Ground Truth: {ground_truth}")

            mgr.end_session()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evolver = RZeroEvolver(target_success_count=5)
    asyncio.run(evolver.run_loop())
