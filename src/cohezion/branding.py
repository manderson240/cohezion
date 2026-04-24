# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
"""
Cohezion Branding API - The Single Source of Truth for the Nexus Identity.
Implements the "Organic Modularity" aesthetic.
"""

from typing import Any


class Colors:
    """The Nexus Color Palette."""

    NEXUS_GREEN = "#00FF00"  # The Lattice / Life
    MATTE_BLACK = "#0A0A0A"  # The Void / Hardware
    SILICON_SILVER = "#C0C0C0"  # The Chassis / Conductor
    EARTH_BLUE = "#0077BE"  # The Singularity
    CRITICAL_RED = "#FF3B3B"  # Instability
    WARNING_GOLD = "#F6D365"  # Transient State

    # Extended Palette (Adversarial Review Additions)
    PLASMA_BLUE = "#4facfe"  # Header Border
    NEON_CYAN = "#00f2fe"  # Accents
    NEON_PURPLE = "#f093fb"  # Mystery / Discovery


class Identity:
    NAME = "COHEZION"
    SIGN_OFF = "QUADRATURE NEXUS"
    TAGLINE = "The Nexus of Coherence"
    PHILOSOPHY = "Organic Modularity"
    ORCHESTRATOR_NAME = "Quadrature Nexus Orchestration"
    LATTICE_NAME = "Expert Domain Lattice"
    EXPERTS = [
        "Architect (Design)",
        "Engineer (Physics)",
        "Biologist (Life)",
        "Quantum Hardware (Hardware)",
        "Quantum Algo (Compute)",
    ]


class Motifs:
    """ASCII Art and Text Motifs."""

    # The "C" Lattice Logo in ASCII
    NEXUS_LOGO = r"""
      [bold #00FF00]      .:[/bold #00FF00][bold #C0C0C0]X[/bold #C0C0C0][bold #00FF00]:.[/bold #00FF00]
      [bold #00FF00]    .::[/bold #00FF00][bold #C0C0C0]XXX[/bold #C0C0C0][bold #00FF00]::.[/bold #00FF00]
      [bold #00FF00]   :::[/bold #00FF00][bold #0077BE]( @ )[/bold #0077BE][bold #00FF00]:::[/bold #00FF00]
      [bold #00FF00]   '::[/bold #00FF00][bold #C0C0C0]XXX[/bold #C0C0C0][bold #00FF00]::'[/bold #00FF00]
      [bold #00FF00]     ':::'[/bold #00FF00]
    """

    WALL_OF_TEXT_LOGO = r"""
 [bold #00FF00]   ______      __  __           _                 [/bold #00FF00]
 [bold #00FF00]  / ____/___  / /_/_/___  ____(_)___  ____       [/bold #00FF00]
 [bold #00FF00] / /   / __ \/ __ \/ _ \/_  / / __ \/ __ \      [/bold #00FF00]
 [bold #00FF00]/ /___/ /_/ / / / /  __/ / /_/ / /_/ / / / /      [/bold #00FF00]
 [bold #00FF00]\____/\____/_/ /_/\___/ /___/_/\____/_/ /_/       [/bold #00FF00]
    """

    NEXUS_AVATAR_FRAMES = [
        r"""
       [bold #00f2fe]  .::.[/bold #00f2fe]
       [bold #00f2fe].::::::.[/bold #00f2fe]
       [bold #00f2fe]:::::::[/bold #00f2fe]
       [bold #00f2fe]'::::::'[/bold #00f2fe]
       [bold #00f2fe]  '::'[/bold #00f2fe]
        """,
        r"""
       [bold #00f2fe]   ::[/bold #00f2fe]
       [bold #00f2fe] .::::.[/bold #00f2fe]
       [bold #00f2fe]:::::::[/bold #00f2fe]
       [bold #00f2fe] '::::'[/bold #00f2fe]
       [bold #00f2fe]   ::[/bold #00f2fe]
        """,
        r"""
       [bold #00f2fe]    :[/bold #00f2fe]
       [bold #00f2fe]  .::.[/bold #00f2fe]
       [bold #00f2fe] :::::[/bold #00f2fe]
       [bold #00f2fe]  '::'[/bold #00f2fe]
       [bold #00f2fe]    :[/bold #00f2fe]
        """,
    ]

    LATTICE_BORDER = "heavy"  # Rich border style

    IGNITION_SEQUENCE = [
        "Initializing Quantum Substrate...",
        "Loading 12D Manifold Vectors...",
        "Synchronizing with Expert Domain Lattice...",
        "Calibrating HIHO Stability...",
    ]


def get_theme() -> dict[str, Any]:
    """Returns the Rich theme configuration."""
    from rich.theme import Theme

    return Theme(
        {
            "info": Colors.SILICON_SILVER,
            "warning": Colors.WARNING_GOLD,
            "danger": Colors.CRITICAL_RED,
            "success": Colors.NEXUS_GREEN,
            "primary": Colors.NEXUS_GREEN,
            "secondary": Colors.EARTH_BLUE,
            "background": Colors.MATTE_BLACK,
        }
    )
