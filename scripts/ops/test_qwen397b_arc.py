#!/usr/bin/env python3
"""Evaluate `qwen3.5:397b-cloud` (Frontier 397B Math/Code) on ARC."""

import asyncio
import json
import re
import time
import httpx

OLLAMA_API_URL = "http://localhost:11434/api/generate"
CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

MODEL = "qwen3.5:397b-cloud"

def extract_python_code(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
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

async def run_qwen_test():
    print(f"\n▶ Evaluating `{MODEL}` on Task 00576224...")
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    task = challenges["00576224"]
    sol = solutions["00576224"]

    prompt = (
        "You are an expert ARC-AGI Python solver. Write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:`.\n\n"
        f"Train Pair 1:\nInput: {task['train'][0]['input']}\nOutput: {task['train'][0]['output']}\n\n"
        f"Train Pair 2:\nInput: {task['train'][1]['input']}\nOutput: {task['train'][1]['output']}\n\n"
        "Explain your logic and return the code in ```python ```."
    )

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 700}
    }

    t0 = time.perf_counter()
    chunks = []
    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream("POST", OLLAMA_API_URL, json=payload) as r:
            if r.status_code == 200:
                async for line in r.aiter_lines():
                    if line:
                        try:
                            c = json.loads(line)
                            chunks.append(c.get("response", ""))
                            if c.get("done", False): break
                        except Exception: pass
    
    dt = round(time.perf_counter() - t0, 2)
    raw = "".join(chunks).strip()
    code = extract_python_code(raw)
    
    print(f"✓ Model completed in {dt}s. Code length: {len(code)} chars")
    
    # Verify train 0
    p0 = safe_execute(code, task["train"][0]["input"])
    p1 = safe_execute(code, task["train"][1]["input"])
    
    t0_match = (p0 == task["train"][0]["output"])
    t1_match = (p1 == task["train"][1]["output"])
    print(f"  • Train Pair 1 Match: {t0_match}")
    print(f"  • Train Pair 2 Match: {t1_match}")
    
    if t0_match and t1_match:
        test_pred = safe_execute(code, task["test"][0]["input"])
        print(f"  🎯 TEST EXACT MATCH: {test_pred == sol[0]}")
    else:
        print("\nExtracted Code Snippet:\n" + code[:400])

if __name__ == "__main__":
    asyncio.run(run_qwen_test())
