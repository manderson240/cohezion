import asyncio
import httpx
import json

async def main():
    payload = {
        "model": "qwen3.5:397b-cloud",
        "prompt": "Write a python function `def transform(grid):` that returns the grid upside down. Output ONLY python code.",
        "stream": True,
        "options": {"num_predict": 300}
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as r:
            async for line in r.aiter_lines():
                if line:
                    c = json.loads(line)
                    if c.get("thinking"):
                        print("[THINK]", c.get("thinking"), end="")
                    if c.get("response"):
                        print("[RESP]", c.get("response"), end="")
                    if c.get("done"): break
    print()

asyncio.run(main())
