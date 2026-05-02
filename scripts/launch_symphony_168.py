import asyncio

import httpx


API_URL = "http://localhost:8080/api/eigent/workforce"


async def launch_journey(role, task, duration=7.0):
    print(f"Launching Symphony-168 Phase: {role}...")
    payload = {"role": role, "task": task, "duration_days": duration}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(API_URL, json=payload)
            response.raise_for_status()
            print(f"Success: {response.json()['agent_id']}")
            return response.json()
        except Exception as e:
            print(f"Failed to launch {role}: {e}")
            return None


async def main():
    tasks = [
        ("Manifold Analyst", "Cartographer: Continuous 12D topological drift mapping.", 7.0),
        ("Code Surgeon", "Hardening: Autonomous anti-pattern refactoring loop.", 7.0),
        ("QA Automator", "Verifier: Transient test lane orchestration and validation.", 7.0),
        ("Reliability Engineer", "SRE: Event-driven fleet health and workload rebalancing.", 7.0),
    ]

    results = await asyncio.gather(*[launch_journey(r, t, d) for r, t, d in tasks])
    print("\nProject Symphony-168 Deployment Complete.")


if __name__ == "__main__":
    asyncio.run(main())
