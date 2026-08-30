import asyncio
import httpx
import json

async def main():
    payload = {
        "model": "qwen3.5:397b-cloud",
        "prompt": "Explain in one sentence what 2+2 is.",
        "stream": True,
        "options": {"num_predict": 100}
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as r:
            async for line in r.aiter_lines():
                if line:
                    c = json.loads(line)
                    print(c)
                    if c.get("done"): break

asyncio.run(main())
