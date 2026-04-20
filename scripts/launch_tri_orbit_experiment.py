import httpx
import asyncio
import json

API_URL = "http://localhost:8080/api/eigent/workforce"

async def launch_journey(role, task, duration=7.0):
    print(f"Launching journey for {role}...")
    payload = {
        "role": role,
        "task": task,
        "duration_days": duration
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(API_URL, json=payload)
            response.raise_for_status()
            print(f"Success: {response.json()}")
            return response.json()
        except Exception as e:
            print(f"Failed to launch {role}: {e}")
            return None

async def main():
    tasks = [
        ("Manifold Analyst", "Simulate and map 12D topological drift over 168 hours.", 7.0),
        ("Code Surgeon", "Audit src/ for anti-patterns and propose self-healing mutations.", 7.0),
        ("HIHO Simulator", "Validate 0.5 coherence stability in a toroidal vortex manifold.", 7.0)
    ]
    
    # Run for a shorter duration in this script for verification, 
    # but the API handles the requested 7 days in the background.
    results = await asyncio.gather(*[launch_journey(r, t, d) for r, t, d in tasks])
    
    print("\nTri-Orbit Experiment Launch Summary:")
    for res in results:
        if res:
            print(f" - {res['agent_id']}: {res['status']}")

if __name__ == "__main__":
    asyncio.run(main())
