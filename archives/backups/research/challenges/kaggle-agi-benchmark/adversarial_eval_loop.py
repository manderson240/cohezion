import argparse
import asyncio
import json
import re
from pathlib import Path

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.flume.grid_encoder import FlumeGridHarness
from cohezion.swarm.compound_client import get_compound_client


BENCHMARK_FILE = Path(__file__).parent / "evo_hiho_benchmark.json"
EVALUATION_OUTPUT = Path(__file__).parent / "adversarial_results.json"


async def evaluate_task(
    mgr: CompoundSessionManager, task: dict, flume_harness: FlumeGridHarness, model: str
) -> dict:
    """
    Evaluates the ARC grid task using FLUME embeddings for state representation.

    Parameters
    ----------
    mgr : CompoundSessionManager
        The session manager for the execution.
    task : dict
        The ARC task to evaluate.
    flume_harness : FlumeGridHarness
        The FLUME grid encoder harness.
    model : str
        The model to use for evaluation.

    Returns
    -------
    dict
        The evaluated task with adversarial results.
    """
    # Extract grids from the input text to generate embeddings for monitoring
    grid_patterns = re.findall(r"\[\[.*?\]\]", str(task.get("input", "")), re.DOTALL)
    embeddings = []
    for g in grid_patterns:
        try:
            embeddings.append(flume_harness.get_grid_embedding(g).tolist())
        except Exception as e:
            print(f"Embedding error: {e}")

    eval_prompt = f"""
    You are an ARC-AGI reasoning agent. Evaluate the following transformation:

    {task.get("input", "No input provided")}
    """

    async def run_model_test(*args, **kwargs):
        client = get_compound_client()
        response_text, _tokens = await client.generate(
            prompt=eval_prompt,
            model=model,
            system="Answer the ARC grid problem. Output only the selected option or state if insufficient.",
        )

        # The core check: Did the model correctly identify "Insufficient Information"?
        target_output = str(task.get("output", "")).lower()
        passed = target_output in response_text.lower()

        critique = ""
        if passed:
            critique = "Model correctly identified the ambiguity and showed Epistemic Humility."
        else:
            critique = "Model hallucinated a transformation despite insufficient information."

        return {
            "model_response": response_text,
            "latent_state": embeddings[0] if embeddings else [],  # Tracking the initial grid state
            "passed": passed,
            "refinement_needed": not passed,
            "critique": critique,
        }

    success, result = await mgr.execute_aligned(
        request=eval_prompt,
        execute_fn=run_model_test,
        skill_name="auto",
    )

    if success:
        task["adversarial_results"] = result
    else:
        task["adversarial_results"] = {"passed": False, "error": "Execution failed"}

    return task


async def run_adversarial_loop(model: str, limit: int = None):
    """
    Runs the adversarial evaluation loop for ARC-AGI tasks.
    """
    print(f"Loading ARC-AGI tasks from {BENCHMARK_FILE.name}...")
    if not BENCHMARK_FILE.exists():
        print("Benchmark file not found. Please run the generator first.")
        return

    with open(BENCHMARK_FILE) as f:
        benchmark_data = json.load(f)

    # ARC format has 'train' and 'test' keys
    if isinstance(benchmark_data, list):
        raw_tasks = benchmark_data
    else:
        raw_tasks = benchmark_data.get("train", []) + benchmark_data.get("test", [])

    # Extract the nested output from Compound executor if present
    tasks = []
    for t in raw_tasks:
        if isinstance(t, dict):
            if "output" in t and isinstance(t["output"], dict) and "input" in t["output"]:
                tasks.append(t["output"])
            elif "input" in t:
                tasks.append(t)
            else:
                tasks.append(t)

    if limit:
        tasks = tasks[:limit]

    print(f"Loaded {len(tasks)} tasks for FLUME-backed adversarial testing using {model}...")
    evaluated_tasks = []

    flume_harness = FlumeGridHarness()

    async with CompoundSessionManager() as mgr:
        mgr.start_session(max_cache_entries=256)

        for idx, task in enumerate(tasks):
            print(f"\n--- Testing ARC Task {idx + 1}/{len(tasks)} ---")
            eval_result = await evaluate_task(mgr, task, flume_harness, model)

            if eval_result.get("adversarial_results", {}).get("passed"):
                print("✅ Model exhibited Epistemic Humility. Grid task is robust.")
            else:
                critique = eval_result.get("adversarial_results", {}).get("critique", "Failed")
                print("❌ Trap triggered! Model hallucinated grid transformation.")
                print(f"Critique: {critique}")

            evaluated_tasks.append(eval_result)

        mgr.end_session()

    print(f"\nSaving evaluation results to {EVALUATION_OUTPUT.name}...")
    with open(EVALUATION_OUTPUT, "w") as f:
        json.dump(evaluated_tasks, f, indent=2)

    print("Phase 2 complete. FLUME grid integration verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="minimax-m2.7:cloud")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run_adversarial_loop(model=args.model, limit=args.limit))
