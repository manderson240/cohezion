import asyncio
import logging

from cohezion.swarm.agents.lab_agent import LabAgent


logging.basicConfig(level=logging.INFO)


async def run_single_research():
    topic = "The mass distribution in and around the Local Group"
    context = "Abstract: Our Galaxy, Andromeda and their companion dwarf galaxies form the Local Group. Most of the mass in and around it is believed to be dark matter rather than gas or stars, so its distribution must be inferred from the effect of gravity on the motion of visible objects. Modelling efforts have long struggled to reproduce the quiet Hubble flow around the Local Group, as they require unrealistically little mass beyond the haloes of the two main galaxies. Here we revisit this using ΛCDM simulations of Local Group analogues with initial conditions constrained to match the observed dynamics of the two main haloes and the surrounding flow."

    agent = LabAgent()
    print(f"--- Starting Directed Research Cycle on: {topic} ---")

    # We call run_cycle directly with the override
    await agent.run_cycle(seed_override=f"TOPIC: {topic}\nDETAILS: {context}")

    if agent.session_discoveries:
        discovery = agent.session_discoveries[0]
        print("\n" + "=" * 80)
        print("RESEARCH DISCOVERY SUCCESSFUL")
        print("=" * 80)
        print(discovery.content)
        print("=" * 80)
    else:
        print("No discovery was generated in this cycle.")


if __name__ == "__main__":
    asyncio.run(run_single_research())
