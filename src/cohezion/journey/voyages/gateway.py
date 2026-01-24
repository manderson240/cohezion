import asyncio
from rich.console import Console
from cohezion.journey.narrator import NarrativeEngine

async def run_gateway_voyage():
    """
    The Gateway Voyage: Introduction to Cohezion and Potential Realities.
    """
    engine = NarrativeEngine()
    console = Console()

    console.clear()
    await engine.typewrite("\n[bold #4facfe]VOYAGE: Gateway to Cohezion[/bold #4facfe]", speed=0.05)
    await asyncio.sleep(1)

    await engine.typewrite(
        "\nWelcome, Traveler. You have entered the [bold #00f2fe]Cohezion Orchestration Layer[/bold #00f2fe].",
        speed=0.04
    )

    await engine.typewrite(
        "\nThis is not a tool for building simple applications. "
        "It is a lattice for articulating the [italic]possible[/italic].",
        speed=0.04
    )

    await engine.narrate_panel(
        "The Core Mission",
        "Cohezion utilizes the [bold]FLUME[/bold] methodology to guide AI swarms through "
        "high-fidelity simulations of complex physics and reality precipitation.",
        border_style="#00f2fe"
    )

    await engine.prompt_continue()

    await engine.typewrite(
        "\nYou will explore concepts that challenge the standard substrate of reality. "
        "From the [bold #f6d365]0.5 HIHO Stability[/bold #f6d365] point of persistent structures "
        "to the [bold #f093fb]12-Dimensional Manifolds[/bold #f093fb] of the swarm mind.",
        speed=0.04
    )

    await engine.narrate_panel(
        "Your Journey Begins",
        "Use [bold]cohezion journey --list[/bold] to see your available paths.\n\n"
        "Curiosity is the first parameter. Awareness is the first quadrature.",
        border_style="#38ef7d"
    )

    await engine.typewrite("\n[dim]The Gateway is now open.[/dim]", speed=0.06)
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_gateway_voyage())
