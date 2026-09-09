import asyncio
import httpx
import json
import re

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"

async def main():
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    task = challenges["00576224"]
    
    prompt = (
        "Solve this ARC Prize reasoning task by writing a Python function `def transform(grid)`.\n"
        f"Input 1: {task['train'][0]['input']}\nOutput 1: {task['train'][0]['output']}\n\n"
        f"Input 2: {task['train'][1]['input']}\nOutput 2: {task['train'][1]['output']}\n\n"
        "Notice that the input is a 2x2 grid and output is 6x6. Output rows 0-1 and 4-5 are horizontal repetitions of the input. Rows 2-3 are horizontal flips.\n"
        "Write ONLY the function `def transform(grid):` using numpy in ```python ```."
    )
    
    payload = {
        "model": "qwen3.5:397b-cloud",
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": 400, "temperature": 0.0}
    }
    
    print("▶ Prompting Qwen 397B Cloud...")
    full = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as r:
            async for line in r.aiter_lines():
                if line:
                    c = json.loads(line)
                    text = c.get("response", "")
                    full.append(text)
                    print(text, end="", flush=True)
                    if c.get("done"): break
    print("\n\n✓ Finished generation.")

asyncio.run(main())
