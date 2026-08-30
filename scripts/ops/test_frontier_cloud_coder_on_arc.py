#!/usr/bin/env python3
"""Evaluate Frontier Coding Models (`kimi-k2.7-code:cloud` & `qwen3.5:397b-cloud`) on ARC.

Uses Ollama Cloud streaming endpoint to solve the first 5 ARC training tasks
with multi-step program synthesis and deterministic AutoHarness verification.
"""

import asyncio
import json
import os
import re
import time
import httpx

OLLAMA_API_URL = "http://localhost:11434/api/generate"
CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

FRONTIER_MODEL = "kimi-k2.7-code:cloud" # 1.04T Coding Specialist

def extract_python_code(text: str) -> str:
    # Strip thinking tags if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1).strip()
    match2 = re.search(r"def transform\(.*?\):.*", text, re.DOTALL)
    if match2: return match2.group(0).strip()
    return text.strip()

def safe_execute_program(code: str, grid: list[list[int]]) -> list[list[int]] | None:
    try:
        local_scope = {}
        exec("import numpy as np\nfrom scipy.ndimage import label, binary_fill_holes\n" + code, {"__builtins__": __builtins__}, local_scope)
        if "transform" in local_scope:
            res = local_scope["transform"](grid)
            if hasattr(res, "tolist"): res = res.tolist()
            if isinstance(res, list) and all(isinstance(r, list) for r in res): return res
    except Exception:
        pass
    return None

async def query_frontier_model(client: httpx.AsyncClient, prompt: str) -> str:
    payload = {
        "model": FRONTIER_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 600}
    }
    chunks = []
    async with client.stream("POST", OLLAMA_API_URL, json=payload, timeout=90.0) as r:
        if r.status_code == 200:
            async for line in r.aiter_lines():
                if line:
                    try:
                        c = json.loads(line)
                        chunks.append(c.get("response", ""))
                        if c.get("done", False): break
                    except Exception: pass
    return "".join(chunks).strip()

async def evaluate_frontier_arc(num_tasks=3):
    print("\n" + "=" * 115)
    print(f"🌟 EVALUATING FRONTIER CLOUD MODEL `{FRONTIER_MODEL}` (1.04T) ON REAL ARC TASKS")
    print("=" * 115)

    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    task_ids = list(challenges.keys())[:num_tasks]
    solved = 0
    total = len(task_ids)

    async with httpx.AsyncClient() as client:
        for idx, tid in enumerate(task_ids):
            task = challenges[tid]
            sol_list = solutions[tid]
            
            # Format train pairs
            pairs_str = "\n\n".join([f"Train Pair {i+1}:\nInput:\n{ex['input']}\nOutput:\n{ex['output']}" for i, ex in enumerate(task["train"])])
            prompt = (
                f"You are a World-Class ARC-AGI Python Solver. Analyze the grid transformation rule for Task {tid}.\n\n"
                f"{pairs_str}\n\n"
                "Write ONLY the complete, executable Python function `def transform(grid: list[list[int]]) -> list[list[int]]:` using numpy or scipy.\n"
                "Wrap your code in ```python ```."
            )
            
            t0 = time.perf_counter()
            resp = await query_frontier_model(client, prompt)
            dt = round(time.perf_counter() - t0, 2)
            code = extract_python_code(resp)

            # AutoHarness verification on train
            train_pass = True
            for ex in task["train"]:
                pred = safe_execute_program(code, ex["input"])
                if pred != ex["output"]:
                    train_pass = False
                    break

            if train_pass:
                test_pred = safe_execute_program(code, task["test"][0]["input"])
                is_correct = (test_pred == sol_list[0])
                if is_correct:
                    solved += 1
                    status = f"🎯 SOLVED EXACT MATCH ({dt}s)"
                else:
                    status = f"⚠️ Train verified but test mismatch ({dt}s)"
            else:
                status = f"❌ Train verification failed ({dt}s)"

            print(f"  [{idx+1:02d}/{num_tasks:02d}] Task `{tid}`: {status}")

    print("\n" + "=" * 115)
    print(f"📊 FRONTIER MODEL RESULTS ({FRONTIER_MODEL}): Solved {solved}/{total} ({(solved/total)*100:.1f}%)")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(evaluate_frontier_arc(3))
