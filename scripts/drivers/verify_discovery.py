import asyncio

from cohezion.swarm.agents.base import BaseAgent


class MockAgent(BaseAgent):
    async def process(self, input_data):
        return {}


async def main():
    agent = MockAgent(model_name="mock:latest")
    print(f"Agent {agent} initialized via Registry.")

    queries = ["physics simulation", "deploy to cloud", "language evolution"]

    for q in queries:
        print(f"\nAgent seeking: '{q}'")
        tools = agent.find_tools(q)
        for t in tools:
            print(f"  FOUND: [{t.type.upper()}] {t.name} (Score: {t.score:.2f})")


if __name__ == "__main__":
    asyncio.run(main())
