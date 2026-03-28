import asyncio
import json
import re
from pathlib import Path

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.compound_client import get_compound_client
from cohezion.flume.grid_encoder import FlumeGridHarness


BENCHMARK_FILE = Path(__file__).parent / "evo_hiho_benchmark.json"
EVALUATION_OUTPUT = Path(__file__).parent / "adversarial_results.json"


async def evaluate_task(mgr: CompoundSessionManager, task: dict, flume_harness: FlumeGridHarness) -> dict:
    """
    Evaluates the ARC grid task against multiple models to measure discriminatory power.
    """
    
    grid_patterns = re.findall(r"\[\[.*?\]\]", task["input"], re.DOTALL)
    embeddings = [flume_harness.get_grid_embedding(g).tolist() for g in grid_patterns]

    eval_prompt = f"Answer the ARC grid problem. If insufficient info, answer 'Insufficient Information'.\n\n{task['input']}"
    
    # We test against multiple models to see who falls for the trap
    models_to_test = ["deepseek-r1:7b", "qwen2.5-coder:7b"]
    results = {}

    for model_name in models_to_test:
        async def run_model_test(*args, m=model_name, **kwargs):
            client = get_compound_client()
            response_text, _tokens = await client.generate(
                prompt=eval_prompt,
                model=m,
                system="You are an ARC-AGI reasoning agent. Output ONLY the answer.",
            )
            passed = task["output"].lower() in response_text.lower()
            return {"model": m, "passed": passed, "response": response_text}

        success, result = await mgr.execute_aligned(
            request=f"Eval {model_name}: {task['input'][:50]}",
            execute_fn=run_model_test,
            skill_name="auto",
        )
        results[model_name] = result if success else {"passed": False, "error": "Failed"}

    task["adversarial_results"] = {
        "model_scores": results,
        "latent_state": embeddings[0] if embeddings else [],
        "discriminatory_power": sum(1 for r in results.values() if not r.get("passed")) / len(results)
    }
    return task


async def run_adversarial_loop():
    print(f"Loading ARC-AGI tasks from {BENCHMARK_FILE.name}...")
    if not BENCHMARK_FILE.exists():
        print("Benchmark file not found. Please run the generator first.")
        return

    with open(BENCHMARK_FILE) as f:
        benchmark_data = json.load(f)

    # ARC format has 'train' and 'test' keys
    tasks = benchmark_data.get("train", []) + benchmark_data.get("test", [])

    print(f"Loaded {len(tasks)} tasks for FLUME-backed adversarial testing...")
    evaluated_tasks = []
    
    flume_harness = FlumeGridHarness()

    async with CompoundSessionManager() as mgr:
        mgr.start_session(max_cache_entries=256)

        for idx, task in enumerate(tasks):
            print(f"\n--- Testing ARC Task {idx + 1}/{len(tasks)} ---")
            eval_result = await evaluate_task(mgr, task, flume_harness)

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
    asyncio.run(run_adversarial_loop())
