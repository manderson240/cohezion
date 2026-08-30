import asyncio
import httpx
import json

async def main():
    payload = {
        "model": "qwen3.5:397b-cloud",
        "prompt": "Write a python function `def transform(grid):` that returns `grid` unchanged.",
        "stream": True,
        "options": {"num_predict": 200}
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as r:
            async for line in r.aiter_lines():
                if line:
                    c = json.loads(line)
                    print(c.get("response", ""), end="", flush=True)
                    if c.get("done"): break
    print()

asyncio.run(main())
