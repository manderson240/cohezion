import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent(model, name, system_prompt, prompt):
    client = httpx.AsyncClient(timeout=120.0)
    try:
        logger.info(f"Testing {name} with model {model}...")
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {"temperature": 0.8, "num_predict": 512},
            },
        )
        logger.info(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Response: {response.json().get('response')[:100]}...")
        else:
            logger.error(f"Error Body: {response.text}")
    except Exception as e:
        logger.error(f"FAILED {name}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.aclose()

async def main():
    # Vortex (Red Team)
    await test_agent(
        model="qwen2.5-coder:7b",
        name="Vortex",
        system_prompt="You are Vortex, the red_team of the Cohezion platform.",
        prompt="Propose a disruptive change to increase entropy."
    )
    
    # Aegis (Blue Team)
    await test_agent(
        model="phi3:mini",
        name="Aegis",
        system_prompt="You are Aegis, the blue_team of the Cohezion platform.",
        prompt="Propose a stabilizing change."
    )

if __name__ == "__main__":
    asyncio.run(main())
