import asyncio
import httpx

async def check_minimax():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "minimax-m3:cloud",
                "messages": [{"role": "user", "content": "Hello, provide a 1-sentence response on competitive AGI architectures."}],
                "stream": False
            }
        )
        print("Status:", r.status_code)
        print("Raw JSON:", r.text)

asyncio.run(check_minimax())
