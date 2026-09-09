#!/usr/bin/env python3
"""Object-Decomposition & Execution-Feedback Self-Correction Harness for ARC-AGI.

Pipeline:
1. Spatial & Object Pre-Processing:
   - Decomposes raw 2D integer grids into discrete connected-component objects (`scipy.ndimage.label`).
   - Extracts bounding boxes, color palettes, background counts, and shape centroids.
2. Execution Feedback Loop (Refinement):
   - When a generated `transform(grid)` fails on training examples, the exact input, expected output,
     and erroneous actual output diff are fed back to local silicon (`gpt-oss-20b-mxfp4` / `Qwen3-Coder-30B`).
3. AutoHarness Deterministic Verification:
   - 100% test-pair execution only occurs after all training pairs pass without error.
"""

import asyncio
import json
import os
import re
import time
import httpx
import numpy as np
from scipy.ndimage import label

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

COLOR_NAMES = {
    0: "black (0)", 1: "blue (1)", 2: "red (2)", 3: "green (3)", 4: "yellow (4)",
    5: "grey (5)", 6: "magenta (6)", 7: "orange (7)", 8: "azure (8)", 9: "maroon (9)"
}

def analyze_grid_objects(grid: list[list[int]], bg_val: int = 0) -> str:
    arr = np.array(grid)
    h, w = arr.shape
    unique_colors = [COLOR_NAMES.get(int(c), str(c)) for c in np.unique(arr)]
    
    # Extract connected components
    objects_summary = []
    for c in np.unique(arr):
        if c == bg_val:
            continue
        labeled, num_features = label(arr == c)
        for obj_idx in range(1, num_features + 1):
            mask = (labeled == obj_idx)
            rows, cols = np.where(mask)
            rmin, rmax = rows.min(), rows.max()
            cmin, cmax = cols.min(), cols.max()
            pixel_count = int(np.sum(mask))
            objects_summary.append(
                f"- Object {len(objects_summary)+1}: Color {COLOR_NAMES.get(int(c), str(c))}, "
                f"Size {pixel_count}px, BBox: rows [{rmin}..{rmax}], cols [{cmin}..{cmax}]"
            )
            
    summary = (
        f"Grid Shape: {h}x{w}\n"
        f"Colors Present: {', '.join(unique_colors)}\n"
        f"Detected Discrete Objects:\n" + ("\n".join(objects_summary[:8]) if objects_summary else "None (monochromatic/background)")
    )
    return summary

def extract_python_code(text: str) -> str:
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match2 = re.search(r"def transform\(.*?\):.*", text, re.DOTALL)
    if match2:
        return match2.group(0).strip()
    return text.strip()

def safe_execute_program(code: str, grid: list[list[int]]) -> list[list[int]] | None:
    try:
        local_scope = {}
        exec("import numpy as np\nfrom scipy.ndimage import label, binary_fill_holes\n" + code, {"__builtins__": __builtins__}, local_scope)
        if "transform" in local_scope:
            res = local_scope["transform"](grid)
            if isinstance(res, np.ndarray):
                res = res.tolist()
            if isinstance(res, list) and all(isinstance(r, list) for r in res):
                return res
    except Exception:
        pass
    return None

async def solve_with_feedback_loop(client: httpx.AsyncClient, task_id: str, task_data: dict, sol_list: list, max_refinements: int = 4):
    train_pairs = task_data["train"]
    test_pairs = task_data["test"]
    
    # 1. Build initial object-decomposed prompt
    decomposed_train = []
    for idx, ex in enumerate(train_pairs):
        in_analysis = analyze_grid_objects(ex["input"])
        out_analysis = analyze_grid_objects(ex["output"])
        decomposed_train.append(
            f"=== Training Pair {idx+1} ===\n"
            f"[Input Grid]:\n{ex['input']}\n{in_analysis}\n\n"
            f"[Expected Output Grid]:\n{ex['output']}\n{out_analysis}"
        )
    decomposed_context = "\n\n".join(decomposed_train)

    system_prompt = (
        "You are an expert Python AGI program synthesis engine for the ARC-AGI Prize 2026.\n"
        "Analyze the discrete objects, shapes, colors, and transformations between input and output.\n"
        "Write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:` using numpy/scipy."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Here are the object-decomposed training pairs for task {task_id}:\n\n{decomposed_context}\n\nWrite ONLY the Python code for `def transform(grid):`.\n```python\n"}
    ]

    for attempt in range(1, max_refinements + 1):
        payload = {
            "model": "gpt-oss-20b-mxfp4-GGUF",
            "messages": messages,
            "temperature": 0.15 + (attempt * 0.1),
            "max_tokens": 500
        }
        
        try:
            r = await client.post(LEMONADE_URL, json=payload, timeout=50.0)
            if r.status_code != 200:
                continue
            raw_text = (r.json()["choices"][0]["message"].get("content") or "").strip()
            code = extract_python_code(raw_text)

            # AutoHarness verification on training examples
            all_passed = True
            failure_feedback = None

            for ex_idx, ex in enumerate(train_pairs):
                actual_out = safe_execute_program(code, ex["input"])
                if actual_out != ex["output"]:
                    all_passed = False
                    failure_feedback = (
                        f"Execution Failure on Training Pair {ex_idx+1}:\n"
                        f"Input: {ex['input']}\n"
                        f"Expected: {ex['output']}\n"
                        f"Actual Output of your transform: {actual_out}\n"
                        "Please analyze the discrepancy, fix your logic, and output the corrected `def transform(grid):`."
                    )
                    break

            if all_passed:
                # 100% Training Verified! Run on test pair
                pred_test = safe_execute_program(code, test_pairs[0]["input"])
                is_correct = (pred_test == sol_list[0])
                return True, is_correct, attempt, code

            # Append assistant response and feedback for next iteration
            messages.append({"role": "assistant", "content": f"```python\n{code}\n```"})
            messages.append({"role": "user", "content": failure_feedback})

        except Exception as e:
            continue

    return False, False, max_refinements, None

async def run_object_feedback_benchmark(num_tasks: int = 5):
    print("\n" + "=" * 115)
    print("🔬 RUNNING OBJECT-DECOMPOSITION + EXECUTION FEEDBACK LOOP ON REAL ARC TASKS (AMD SILICON)")
    print("=" * 115)

    with open(CHALLENGES_PATH) as f:
        challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:num_tasks]
    print(f"Evaluating {num_tasks} real ARC tasks with multi-turn self-correction...\n")

    train_verified = 0
    test_solved = 0
    t0 = time.perf_counter()

    async with httpx.AsyncClient() as client:
        for idx, tid in enumerate(task_ids):
            t_task = time.perf_counter()
            verified, solved, attempts, code = await solve_with_feedback_loop(
                client, tid, challenges[tid], solutions[tid], max_refinements=3
            )
            dt = round(time.perf_counter() - t_task, 2)
            
            if verified:
                train_verified += 1
            if solved:
                test_solved += 1
                status = f"🎯 SOLVED (Refinement {attempts}, {dt}s)"
            elif verified:
                status = f"⚠️ TRAIN VERIFIED (Refinement {attempts}, {dt}s)"
            else:
                status = f"❌ Refinements exhausted ({attempts} turns, {dt}s)"

            print(f"  [{idx+1:02d}/{num_tasks:02d}] Task `{tid}`: {status}")

    total_time = round(time.perf_counter() - t0, 2)
    print("\n" + "=" * 115)
    print("📊 OBJECT-DECOMPOSITION & FEEDBACK BENCHMARK RESULTS:")
    print(f"  • Tasks Evaluated: {num_tasks}")
    print(f"  • Train-Verified Solutions: {train_verified}/{num_tasks} ({(train_verified/num_tasks)*100:.1f}%)")
    print(f"  • Test-Set Exact Matches: {test_solved}/{num_tasks} ({(test_solved/num_tasks)*100:.1f}%)")
    print(f"  • Total Execution Time: {total_time}s ({round(total_time/num_tasks, 2)}s/task)")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_object_feedback_benchmark(5))
