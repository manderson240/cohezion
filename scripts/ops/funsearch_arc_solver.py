#!/usr/bin/env python3
"""DeepMind FunSearch + Local LLM Program Synthesis for ARC Prize 2026.

Uses local silicon (`gpt-oss-20b-mxfp4-GGUF` / `Qwen3-Coder-30B` on Lemonade :13305):
1. Ingests real ARC training/evaluation tasks.
2. Prompts local LLM to generate executable Python solver functions.
3. Deterministically verifies generated functions against all training pairs (AutoHarness verification).
4. Solves test inputs and computes empirical accuracy.
"""

import asyncio
import json
import os
import re
import time
import httpx
import numpy as np

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

PROMPT_TEMPLATE = """You are an expert AGI program synthesis engine for the ARC-AGI Prize 2026.
Given input-output grid pairs, write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:` that transforms the input grid into the output grid.

Task Training Pairs:
{train_pairs_str}

Rules:
1. Write ONLY the Python code for `transform`.
2. Do not use external libraries other than `numpy`.
3. Return the exact 2D list of integers.

```python
"""

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
        exec("import numpy as np\n" + code, {"__builtins__": __builtins__}, local_scope)
        if "transform" in local_scope:
            res = local_scope["transform"](grid)
            if isinstance(res, np.ndarray):
                res = res.tolist()
            if isinstance(res, list) and all(isinstance(r, list) for r in res):
                return res
    except Exception:
        pass
    return None

async def solve_arc_task_with_llm(client: httpx.AsyncClient, task_id: str, task_data: dict, sol_list: list, max_attempts: int = 3):
    train_pairs = task_data["train"]
    test_pairs = task_data["test"]
    
    # Format train pairs
    train_str_parts = []
    for idx, ex in enumerate(train_pairs):
        train_str_parts.append(f"Pair {idx+1}:\nInput: {ex['input']}\nOutput: {ex['output']}")
    train_pairs_str = "\n\n".join(train_str_parts)

    prompt = PROMPT_TEMPLATE.format(train_pairs_str=train_pairs_str)
    
    for attempt in range(max_attempts):
        payload = {
            "model": "gpt-oss-20b-mxfp4-GGUF",
            "messages": [
                {"role": "system", "content": "You are a competitive ARC-AGI Python program synthesis solver."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2 + (attempt * 0.2),
            "max_tokens": 450
        }
        
        try:
            r = await client.post(LEMONADE_URL, json=payload, timeout=45.0)
            if r.status_code != 200:
                continue
            raw_text = r.json()["choices"][0]["message"].get("content") or ""
            code = extract_python_code(raw_text)
            
            # AutoHarness Verification against all training pairs
            train_pass = True
            for ex in train_pairs:
                pred_train = safe_execute_program(code, ex["input"])
                if pred_train != ex["output"]:
                    train_pass = False
                    break
            
            if train_pass:
                # Training verified! Apply to test pair
                pred_test = safe_execute_program(code, test_pairs[0]["input"])
                is_correct = (pred_test == sol_list[0])
                return True, is_correct, attempt + 1, code
                
        except Exception:
            continue

    return False, False, max_attempts, None

async def run_funsearch_benchmark(num_tasks: int = 10):
    print("\n" + "=" * 115)
    print("🧬 RUNNING DEEPMIND FUNSEARCH + LOCAL SILICON PROGRAM SYNTHESIS ON REAL ARC TASKS")
    print("=" * 115)

    with open(CHALLENGES_PATH) as f:
        challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:num_tasks]
    print(f"Evaluating {num_tasks} real ARC tasks using LLM synthesis on AMD Strix Halo (:13305)...\n")

    train_verified = 0
    test_solved = 0
    t0 = time.perf_counter()

    async with httpx.AsyncClient() as client:
        for idx, tid in enumerate(task_ids):
            t_task = time.perf_counter()
            verified, solved, attempts, code = await solve_arc_task_with_llm(
                client, tid, challenges[tid], solutions[tid]
            )
            dt = round(time.perf_counter() - t_task, 2)
            
            if verified:
                train_verified += 1
            if solved:
                test_solved += 1
                status = f"🎯 SOLVED ON TEST (Attempt {attempts}, {dt}s)"
            elif verified:
                status = f"⚠️ TRAIN VERIFIED BUT TEST MISMATCH (Attempt {attempts}, {dt}s)"
            else:
                status = f"❌ Train verification failed ({attempts} attempts, {dt}s)"

            print(f"  [{idx+1:02d}/{num_tasks:02d}] Task `{tid}`: {status}")

    total_time = round(time.perf_counter() - t0, 2)
    print("\n" + "=" * 115)
    print("📊 REAL FUNSEARCH ARC SYNTHESIS RESULTS:")
    print(f"  • Tasks Evaluated: {num_tasks}")
    print(f"  • Train-Verified Programs (AutoHarness): {train_verified}/{num_tasks} ({(train_verified/num_tasks)*100:.1f}%)")
    print(f"  • Real Test Accuracy: {test_solved}/{num_tasks} ({(test_solved/num_tasks)*100:.1f}%)")
    print(f"  • Total Time: {total_time}s ({round(total_time/num_tasks, 2)}s/task)")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_funsearch_benchmark(10))
