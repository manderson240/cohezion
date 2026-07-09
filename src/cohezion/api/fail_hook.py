import asyncio

import httpx


async def async_failure():
    # Simulate a brief backoff, then probe an external health endpoint asynchronously.
    await asyncio.sleep(1)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://google.com")
    return resp.status_code
