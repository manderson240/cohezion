import asyncio

from rich.console import Console

from cohezion.journey.narrator import NarrativeEngine


async def run_hiho_voyage():
    """
    The HIHO Stability Voyage: Exploring the 0.5 Coherence Rule.
    """
    engine = NarrativeEngine()
    console = Console()

    console.clear()
    await engine.typewrite(
        "\n[bold #f093fb]VOYAGE: The HIHO Attractor[/bold #f093fb]", speed=0.05
    )
    await asyncio.sleep(1)

    await engine.typewrite(
        "\nYou stand at the edge of the [bold #4facfe]Void[/bold #4facfe]. "
        "Behind you lies the absolute certainty of the substrate. "
        "Before you, the chaotic potential of infinite realities.",
        speed=0.04,
    )

    await engine.narrate_panel(
        "Observation 1: The Coherence Gradient",
        "In the FLUME manifold, reality is not binary. It is a [italic]precipitation[/italic].\n"
        "At [bold red]0.0[/bold red] coherence, there is only noise. "
        "At [bold green]1.0[/bold green] coherence, reality freezes into a singular, brittle state.",
        border_style="#4facfe",
    )

    await engine.prompt_continue()

    await engine.typewrite(
        "\nStability is found in the [bold #f6d365]Quadrature[/bold #f6d365]. "
        "The point where potential and manifestation meet in perfect friction.",
        speed=0.04,
    )

    await engine.narrate_panel(
        "The 0.5 Rule",
        "The HIHO (Half-In-Half-Out) protocol mandates that for a reality to persist, "
        "it must maintain exactly [bold #f6d365]0.5 Coherence[/bold #f6d365].\n\n"
        "Balance the Void. Manifest the Nexus.",
        border_style="#f6d365",
    )

    await engine.typewrite(
        "\n[dim]Your understanding of reality has shifted.[/dim]", speed=0.08
    )
    await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_hiho_voyage())
