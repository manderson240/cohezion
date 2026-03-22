import asyncio
import logging

from cohezion.swarm.controller_agent import ControllerAgent


logging.basicConfig(level=logging.INFO)


async def analyze_paper():
    topic = "The mass distribution in and around the Local Group"
    context_text = "Abstract: Our Galaxy, Andromeda and their companion dwarf galaxies form the Local Group. Most of the mass in and around it is believed to be dark matter rather than gas or stars, so its distribution must be inferred from the effect of gravity on the motion of visible objects. Modelling efforts have long struggled to reproduce the quiet Hubble flow around the Local Group, as they require unrealistically little mass beyond the haloes of the two main galaxies. Here we revisit this using ΛCDM simulations of Local Group analogues with initial conditions constrained to match the observed dynamics of the two main haloes and the surrounding flow."

    controller = ControllerAgent()
    print("--- Calling Expert Lattice for Analysis ---")

    result = await controller.ignite(
        {
            "query": f"Analyze this astrophysics abstract and identify implications for autonomous discovery: {context_text}",
            "context": {"topic": topic, "source": "Nature Astronomy"},
            "urgency": "medium",
        }
    )

    print("\n" + "=" * 80)
    print("EXPERT SYNTHESIS")
    print("=" * 80)
    print(result.get("synthesis", "No synthesis generated."))
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(analyze_paper())
