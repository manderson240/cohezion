#!/usr/bin/env python3
"""Evaluate resident `Qwen3-Coder-30B-A3B-Instruct-GGUF` on real ARC tasks."""

import asyncio
import json
import re
import time
import httpx
import numpy as np

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
MODEL_ID = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def extract_python_code(text: str) -> str:
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1).strip()
    match2 = re.search(r"def transform\(.*?\):.*", text, re.DOTALL)
    if match2: return match2.group(0).strip()
    return text.strip()

def safe_execute(code: str, grid: list[list[int]]) -> list[list[int]] | None:
    try:
        scope = {}
        exec("import numpy as np\nfrom scipy.ndimage import label, binary_fill_holes\n" + code, {"__builtins__": __builtins__}, scope)
        if "transform" in scope:
            res = scope["transform"](grid)
            if hasattr(res, "tolist"): res = res.tolist()
            if isinstance(res, list) and all(isinstance(r, list) for r in res): return res
    except Exception: pass
    return None

async def solve_task_qwen_coder(client: httpx.AsyncClient, task_id: str, task: dict, sol: list):
    train_pairs = task["train"]
    test_pairs = task["test"]
    
    pairs_str = "\n\n".join([f"Train Pair {i+1}:\nInput:\n{ex['input']}\nOutput:\n{ex['output']}" for i, ex in enumerate(train_pairs)])
    
    prompt = (
        f"You are a World-Class ARC-AGI Python Grandmaster.\n"
        f"Task {task_id}:\n{pairs_str}\n\n"
        "Analyze the visual grid patterns, symmetries, tiling, bounding boxes, or flood fills.\n"
        "Write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:` using numpy/scipy.\n"
        "Wrap your code in ```python ```."
    )
    
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You write precise Python solvers for ARC-AGI grid transformations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 600
    }
    
    t0 = time.perf_counter()
    r = await client.post(LEMONADE_URL, json=payload, timeout=60.0)
    dt = round(time.perf_counter() - t0, 2)
    
    if r.status_code != 200:
        return False, False, dt, f"HTTP Error {r.status_code}"
        
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    code = extract_python_code(text)
    
    train_pass = True
    for ex in train_pairs:
        pred = safe_execute(code, ex["input"])
        if pred != ex["output"]:
            train_pass = False
            break
            
    if train_pass:
        test_pred = safe_execute(code, test_pairs[0]["input"])
        test_pass = (test_pred == sol[0])
        return True, test_pass, dt, code
        
    return False, False, dt, code

async def run_benchmark(num_tasks=5):
    print("\n" + "=" * 115)
    print(f"🚀 BENCHMARKING RESIDENT LOCAL `{MODEL_ID}` ON REAL ARC TASKS (AMD iGPU :13305)")
    print("=" * 115)

    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    task_ids = list(challenges.keys())[:num_tasks]
    solved = 0

    async with httpx.AsyncClient() as client:
        for idx, tid in enumerate(task_ids):
            train_ok, test_ok, dt, code_or_err = await solve_task_qwen_coder(
                client, tid, challenges[tid], solutions[tid]
            )
            if test_ok:
                solved += 1
                status = f"🎯 EXACT MATCH ON TEST ({dt}s)"
            elif train_ok:
                status = f"⚠️ Train Verified, Test Mismatch ({dt}s)"
            else:
                status = f"❌ Train verification failed ({dt}s)"
                
            print(f"  [{idx+1:02d}/{num_tasks:02d}] Task `{tid}`: {status}")

    print("\n" + "=" * 115)
    print(f"📊 `{MODEL_ID}` RESULTS: Solved {solved}/{num_tasks} ({(solved/num_tasks)*100:.1f}%) on local silicon")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark(5))
