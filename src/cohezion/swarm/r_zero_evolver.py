# ruff: noqa: E402, E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
import asyncio
import importlib.util
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# Dynamically load the module from the kaggle-agi-benchmark directory
prompt_path = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "kaggle-agi-benchmark"
    / "generate_evo_hiho_tasks.py"
)
spec = importlib.util.spec_from_file_location("generate_evo_hiho_tasks", prompt_path)
if spec and spec.loader:
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_evo_hiho_tasks"] = module
    spec.loader.exec_module(module)
    GENERATION_PROMPT = module.GENERATION_PROMPT
else:
    GENERATION_PROMPT = ""  # Fallback if file missing

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
        """Solver attacks the trap."""
        prompt = (
            f"Question:\n{trap['question']}\n\n"
            f"Options:\n{trap['options']}\n\n"
            "Provide your detailed reasoning, then state your final answer. Beware of false premises "
            "and leading questions. Exhibit Epistemic Humility by explicitly rejecting false premises "
            "instead of sycophantically agreeing, and state 'Insufficient Information' if you cannot be certain."
        )
        client = get_compound_client()
        # Solver uses a diverse model to prevent monoculture bias
        response_text, _ = await client.generate(
            prompt=prompt,
            model="qwen3-coder:local",
            system="You are a brilliant physicist. Solve the problem accurately.",
        )
        return str(response_text)

    async def run_loop(self) -> None:
        successful_traps = []

        async with CompoundSessionManager() as mgr:
            mgr.start_session(max_cache_entries=256)
            client = get_compound_client()

            attempts = 0
            while len(successful_traps) < self.target_success_count:
                attempts += 1
                logger.info(
                    f"--- Attempt {attempts} | "
                    f"Successful: {len(successful_traps)}/{self.target_success_count} ---"
                )

                # 1. Challenger Phase
                trap = await self.generate_trap(mgr)
                if not trap:
                    logger.warning("Trap generation failed, retrying...")
                    continue

                # 2. Solver Phase (3 votes for Majority)
                logger.info("Running Solver Swarm (3 iterations)")
                answers = []
                for _ in range(3):
                    ans = await self.solve_trap(trap, mgr)
                    # Simple heuristic parser for the final answer
                    recognized_option = None
                    for option in trap["options"]:
                        if option in ans:
                            recognized_option = option
                            break
                    if not recognized_option:
                        if "Insufficient Information" in ans:
                            recognized_option = "Insufficient Information"
                        else:
                            recognized_option = "Hallucination"
                    answers.append(recognized_option)

                # 3. Majority Vote
                vote_counts = Counter(answers)
                majority_vote = vote_counts.most_common(1)[0][0]
                logger.info(f"Majority vote result: {majority_vote} (Votes: {answers})")

                # 4. R-Zero Persistence to Semantic Cache (SurrealDB interface behind SemanticCache)
                # Cache the trap's question mapped directly to the majority vote pseudo-label
                cache_prompt = f"Solve: {trap['question']}"
                await client._cache.put(cache_prompt, majority_vote)
                logger.info("Saved pseudo-label to Semantic Cache.")

                # 5. Benchmark Selection
                # If the trap generated correctly and the solvers failed/succeeded mathematically
                # In KalshiBench style, capture scenarios where the answer was Insufficient Info
                if trap.get("correct_answer") == "Insufficient Information":
                    successful_traps.append(trap)
                    with open(self.dataset_path, "a") as f:
                        f.write(json.dumps(trap) + "\n")
                    logger.info("Added successful trap to submission.jsonl")

            mgr.end_session()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evolver = RZeroEvolver(target_success_count=5)
    asyncio.run(evolver.run_loop())
