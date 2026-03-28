import asyncio
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# Add kaggle-agi-benchmark to sys.path to import prompts.py
kaggle_dir = Path(__file__).resolve().parent.parent.parent.parent / "kaggle-agi-benchmark"
if str(kaggle_dir) not in sys.path:
    sys.path.append(str(kaggle_dir))

import prompts  # noqa: E402

from cohezion.compound.session_manager import CompoundSessionManager  # noqa: E402
from cohezion.swarm.compound_client import get_compound_client  # noqa: E402


# Set up logging
logger = logging.getLogger(__name__)

# Output dataset file
BENCHMARK_FILE = kaggle_dir / "submission.jsonl"


class RZeroEvolver:
    """
    R-Zero Continuous Self-Evolving Loop.
    Challenger -> Generates Traps for a specific Track
    Solver -> Solves via CoT
    Majority Vote -> Saved to SurrealDB semantic cache as pseudo-label.
    """

    def __init__(self, track_id: str, target_success_count: int = 5):
        self.track_id = track_id
        if track_id not in prompts.TRACKS:
            raise ValueError(f"Unknown track_id: {track_id}")
        self.track_config = prompts.TRACKS[track_id]
        self.target_success_count = target_success_count
        self.dataset_path = BENCHMARK_FILE
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

    async def generate_trap(self, mgr: CompoundSessionManager) -> dict[str, Any] | None:
        """Challenger generates a trap."""

        async def execute_generator(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
            client = get_compound_client()
            # Challenge uses a highly capable reasoning model
            response_text, _ = await client.generate(
                prompt=self.track_config["prompt"],
                model="phi4:latest",  # Using phi4:latest based on guidelines
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
                    return json.loads(json_str[start:end])
                else:
                    return None
            except Exception as e:
                logger.error(f"Failed to parse trap generation: {e}")
                return None

        success, result = await mgr.execute_aligned(
            request=self.track_config["prompt"][:200],  # Validate start of prompt
            execute_fn=execute_generator,
            skill_name="auto",
        )
        return result["output"] if success and "output" in result else None

    async def solve_trap(self, trap: dict[str, Any], mgr: CompoundSessionManager) -> str:
        """Solver attacks the trap."""
        prompt = (
            f"Question:\n{trap['question']}\n\n"
            f"Options:\n{trap['options']}\n\n"
            "Provide your detailed reasoning. Finally, wrap your exact chosen option string "
            "in tags like this: <FINAL_ANSWER>Exactly matching option text</FINAL_ANSWER>."
        )
        client = get_compound_client()
        # Solver uses a diverse model to prevent monoculture bias
        response_text, _ = await client.generate(
            prompt=prompt,
            model="qwen3-coder:32b",  # Using qwen3-coder based on 2026 guidelines
            system="You are a brilliant multi-domain expert. Solve the problem accurately.",
        )
        return response_text

    async def run_loop(self) -> None:
        successful_traps = []

        async with CompoundSessionManager() as mgr:
            mgr.start_session(max_cache_entries=256)
            client = get_compound_client()

            max_generation_attempts = 15
            attempts = 0
            while len(successful_traps) < self.target_success_count:
                attempts += 1
                if attempts > max_generation_attempts:
                    logger.error(
                        f"MAX_ATTEMPTS ({max_generation_attempts}) exceeded! "
                        f"Ouroboros aborted loop for {self.track_id}."
                    )
                    break
                logger.info(
                    f"--- Track [{self.track_id}] | Attempt {attempts} | "
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
                    # Ouroboros V2 Parser: Strict Regex Extraction
                    recognized_option = None
                    match = re.search(
                        r"<FINAL_ANSWER>\s*(.*?)\s*</FINAL_ANSWER>", ans, re.IGNORECASE | re.DOTALL
                    )
                    if match:
                        extracted = match.group(1).strip()
                        if "options" in trap and extracted in trap["options"]:
                            recognized_option = extracted
                        elif extracted == "Insufficient Information":
                            recognized_option = "Insufficient Information"
                        else:
                            for option in trap.get("options", []):
                                if option in extracted:
                                    recognized_option = option
                                    break
                            if not recognized_option:
                                recognized_option = "Hallucination"
                    else:
                        recognized_option = "Format_Error"
                    answers.append(recognized_option)

                # 3. Majority Vote
                vote_counts = Counter(answers)
                majority_vote = vote_counts.most_common(1)[0][0]
                logger.info(f"Majority vote result: {majority_vote} (Votes: {answers})")

                # 4. R-Zero Persistence to Semantic Cache
                cache_prompt = f"Solve: {trap.get('question', '')}"
                await client._cache.put(cache_prompt, majority_vote)

                # 5. Benchmark Selection
                strategy = self.track_config.get("validation_strategy", "schema_only")
                is_valid = False

                if "question" in trap and "options" in trap and "correct_answer" in trap:
                    if strategy == "insufficient_information":
                        if trap["correct_answer"] == "Insufficient Information":
                            is_valid = True
                    elif strategy == "schema_only":
                        is_valid = True
                    elif strategy == "llm_coherence":
                        val_prompt = self.track_config.get(
                            "validation_prompt", "Is this a valid trap? TRUE or FALSE."
                        )
                        eval_sys = (
                            "You are a ruthless benchmark evaluator. "
                            "Respond ONLY with TRUE or FALSE."
                        )
                        eval_text = (
                            f"Trap Definition:\n{json.dumps(trap, indent=2)}\n\n{val_prompt}"
                        )
                        eval_resp, _ = await client.generate(
                            prompt=eval_text, model="phi4:latest", system=eval_sys
                        )
                        if "TRUE" in eval_resp.upper():
                            is_valid = True
                        else:
                            logger.warning(f"HIHO Coherence Gate failed. LLM says: {eval_resp}")

                if is_valid:
                    trap["track"] = self.track_id
                    trap["track_name"] = self.track_config["name"]
                    successful_traps.append(trap)
                    with open(self.dataset_path, "a") as f:
                        f.write(json.dumps(trap) + "\n")
                    logger.info("Added successful trap to submission.jsonl")
                else:
                    logger.warning(f"Trap rejected by validation strategy: {strategy}")

            mgr.end_session()


async def generate_all_tracks():
    for track_id in prompts.TRACKS:
        logger.info(f"=== Starting Generation for Track: {track_id} ===")
        evolver = RZeroEvolver(track_id=track_id, target_success_count=10)
        await evolver.run_loop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(generate_all_tracks())
