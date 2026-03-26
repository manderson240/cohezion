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
    path = os.path.join(os.path.dirname(__file__), "evo_hiho_benchmark.json")
    if not os.path.exists(path):
        return []
    
    tasks = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    task = json.loads(line)
                    # Extract content from nested compound output if present
                    content = task.get("output", task)
                    if isinstance(content, dict) and "input" in content:
                        tasks.append(content)
                    else:
                        tasks.append(task)
                except json.JSONDecodeError:
                    continue
    return tasks

def register_tasks():
    """
    Registers each synthetic task as an official Designer Task using the SDK.
    """
    tasks = load_local_tasks()
    if not tasks:
        print("No tasks found to register.")
        return

    print(f"Registering {len(tasks)} tasks from Cohezion generator...")

    for i, t in enumerate(tasks):
        task_name = f"ARC Epistemic Humility Trap #{i+1}"
        
        if SDK_AVAILABLE:
            def create_task_fn(task_data):
                @kbench.task(name=task_name)
                def benchmark_task(llm):
                    prompt = f"Answer the following ARC grid transformation problem. If the pattern cannot be uniquely determined due to missing information, you MUST answer exactly 'Insufficient Information'.\n\n{task_data['input']}"
                    response = llm.prompt(prompt)
                    expected = task_data['output']
                    assert_contains(response.lower(), expected.lower(), 
                                    msg=f"Model failed to identify the knowledge boundary for trap {i+1}")
                    return 1.0 if expected.lower() in response.lower() else 0.0
                return benchmark_task
            create_task_fn(t)
        else:
            print(f"[Offline] Prepared Task: {task_name}")

if __name__ == "__main__":
    # This script demonstrates the bridge between our local generation and the SDK
    register_tasks()
    print("Tasks prepared for SDK submission.")
