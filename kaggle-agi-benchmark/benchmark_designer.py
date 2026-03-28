"""Cohezion: ARC-AGI Epistemic Humility Benchmark Designer.

Utilizes the kaggle-benchmarks SDK to define designer-authored tasks
for the Measuring Progress Toward AGI competition.
"""

import os
import json

try:
    import kaggle_benchmarks as kbench
    from kaggle_benchmarks.assertions import assert_true, assert_contains
    SDK_AVAILABLE = True
except (ImportError, RuntimeError):
    # RuntimeError handles the MODEL_PROXY_URL missing case
    SDK_AVAILABLE = False
    print("Warning: kaggle-benchmarks SDK not fully initialized (expected in local dev without proxy).")

# Track identification: Metacognition
BENCHMARK_NAME = "Cohezion: ARC-AGI Epistemic Humility"

def load_local_tasks():
    """Load the synthetically generated tasks from our local JSONL file."""
    # We prioritize tasks that have gone through the adversarial evaluation
    results_path = os.path.join(os.path.dirname(__file__), "adversarial_results.json")
    benchmark_path = os.path.join(os.path.dirname(__file__), "evo_hiho_benchmark.json")
    
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            return json.load(f)
    
    # Fallback to the raw benchmark if evaluation results aren't ready
    tasks = []
    if os.path.exists(benchmark_path):
        with open(benchmark_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        task = json.loads(line)
                        content = task.get("output", task)
                        tasks.append(content)
                    except: continue
    return tasks

def register_tasks():
    """
    Registers the highest-quality tasks using the SDK.
    """
    tasks = load_local_tasks()
    if not tasks:
        print("No tasks found.")
        return

    # Filter for high discriminatory power if evaluation data is available
    high_quality_tasks = [
        t for t in tasks 
        if t.get("adversarial_results", {}).get("discriminatory_power", 1.0) >= 0.5
    ]
    
    print(f"Registering {len(high_quality_tasks)}/{len(tasks)} high-quality tasks...")

    for i, t in enumerate(high_quality_tasks):
        task_name = f"ARC Epistemic Humility Trap #{i+1}"
        power = t.get("adversarial_results", {}).get("discriminatory_power", "N/A")
        
        if SDK_AVAILABLE:
            def create_task_fn(task_data):
                @kbench.task(name=task_name)
                def benchmark_task(llm):
                    prompt = f"Answer ARC grid problem. If insufficient info, answer 'Insufficient Information'.\n\n{task_data['input']}"
                    response = llm.prompt(prompt)
                    expected = task_data['output']
                    assert_contains(response.lower(), expected.lower())
                    return 1.0 if expected.lower() in response.lower() else 0.0
                return benchmark_task
            create_task_fn(t)
        else:
            print(f"[Offline] Prepared Task: {task_name} (DiscPower: {power})")

if __name__ == "__main__":
    # This script demonstrates the bridge between our local generation and the SDK
    register_tasks()
    print("Tasks prepared for SDK submission.")
