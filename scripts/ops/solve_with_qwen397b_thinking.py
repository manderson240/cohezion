import asyncio
import httpx
import json
import re

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

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

def extract_python_code(text: str) -> str:
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1).strip()
    match2 = re.search(r"def transform\(.*?\):.*", text, re.DOTALL)
    if match2: return match2.group(0).strip()
    return text.strip()

async def main():
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    task = challenges["00576224"]
    
    prompt = (
        "You are an expert Python ARC-AGI Solver.\n"
        f"Input 1: {task['train'][0]['input']}\nOutput 1: {task['train'][0]['output']}\n\n"
        f"Input 2: {task['train'][1]['input']}\nOutput 2: {task['train'][1]['output']}\n\n"
        "Analyze the transformation rule and write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:` using numpy.\n"
        "Return the code in ```python ```."
    )
    
    payload = {
        "model": "qwen3.5:397b-cloud",
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": 1500, "temperature": 0.1}
    }

    print("▶ Generating with Qwen 3.5 397B (parsing thinking + response)...")
    content_chunks = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as r:
            async for line in r.aiter_lines():
                if line:
                    c = json.loads(line)
                    # When thinking finishes, response contains the actual output
                    resp = c.get("response", "")
                    content_chunks.append(resp)
                    if c.get("done"): break

    full_output = "".join(content_chunks).strip()
    code = extract_python_code(full_output)
    
    print("\n--- Extracted Python Code ---")
    print(code)
    print("-----------------------------\n")

    p0 = safe_execute(code, task["train"][0]["input"])
    p1 = safe_execute(code, task["train"][1]["input"])
    
    t0_match = (p0 == task["train"][0]["output"])
    t1_match = (p1 == task["train"][1]["output"])
    print(f"• Train Pair 1 Match: {t0_match}")
    print(f"• Train Pair 2 Match: {t1_match}")
    
    if t0_match and t1_match:
        test_pred = safe_execute(code, task["test"][0]["input"])
        print(f"🎯 TEST EXACT MATCH: {test_pred == solutions['00576224'][0]}")

asyncio.run(main())
