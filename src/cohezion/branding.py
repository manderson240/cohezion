"""
Cohezion Branding API - The Single Source of Truth for the Nexus Identity.
Implements the "Organic Modularity" aesthetic.
"""

from typing import Dict, Any

class Colors:
    """The Nexus Color Palette."""
    NEXUS_GREEN = "#00FF00"      # The Lattice / Life
    MATTE_BLACK = "#0A0A0A"      # The Void / Hardware
    SILICON_SILVER = "#C0C0C0"   # The Chassis / Conductor
    EARTH_BLUE = "#0077BE"       # The Singularity
    CRITICAL_RED = "#FF3B3B"     # Instability
    WARNING_GOLD = "#F6D365"     # Transient State

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
        "Quantum Algo (Compute)"
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

    LATTICE_BORDER = "heavy"  # Rich border style

def get_theme() -> Dict[str, Any]:
    """Returns the Rich theme configuration."""
    from rich.theme import Theme
    return Theme({
        "info": Colors.SILICON_SILVER,
        "warning": Colors.WARNING_GOLD,
        "danger": Colors.CRITICAL_RED,
        "success": Colors.NEXUS_GREEN,
        "primary": Colors.NEXUS_GREEN,
        "secondary": Colors.EARTH_BLUE,
        "background": Colors.MATTE_BLACK
    })
