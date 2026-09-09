r"""Mermaid-Style 2D Colored Box Layout Engine for Terminal.
===========================================================
Renders true 2D box-and-arrow flowcharts with full ANSI 24-bit TrueColor styling.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MermaidBoxCanvas:
    """Renders 2D colored Mermaid-style block diagrams in terminal."""

    def __init__(self) -> None:
        self.console = Console(force_terminal=True, color_system="truecolor")

    def render_v_model_mermaid(self) -> None:
        # Create Table Layout representing the V-Model
        grid = Table.grid(padding=(1, 2))
        grid.add_column(justify="center")

        # Header Title
        title_panel = Panel(
            Text("V_Model_Engineering_Sweep\n\"Systems Engineering V-Model Rigor & Compound Loop\"", justify="center", style="bold bright_white"),
            border_style="bright_blue",
            style="on blue",
            padding=(0, 4),
        )
        grid.add_row(title_panel)
        grid.add_row(Text("│\n▼", justify="center", style="bold bright_white"))

        # Main 3-Phase Blocks Layout (Side by Side & Bottom)
        left_box = Panel(
            Text(
                "Top_Left_Specs (1. Architecture)\n\n"
                "• V1: FLUME 12D Poincaré Metric\n"
                "      & Levi-Civita Geodesic Flow\n"
                "• V2: Matsumoto ENC Debye Collapse\n"
                "      & Heim Metron Tiling",
                style="bright_green",
            ),
            title="[bold magenta]Top_Left_Specs[/bold magenta]",
            border_style="magenta",
            width=42,
        )

        right_box = Panel(
            Text(
                "Top_Right_VV (3. Verification)\n\n"
                "• V5: Write Budget Governor\n"
                "      & ZFS Storage Manager\n"
                "• V6: Google Workspace Bridge\n"
                "• V7: 100% Deterministic Proofs",
                style="bright_cyan",
            ),
            title="[bold cyan]Top_Right_VV[/bold cyan]",
            border_style="cyan",
            width=42,
        )

        top_row = Table.grid(padding=(0, 4))
        top_row.add_column()
        top_row.add_column()
        top_row.add_row(left_box, right_box)
        grid.add_row(top_row)

        # Arrows down to bottom
        grid.add_row(Text("│                                                      ▲\n▼                                                      │", justify="center", style="bold bright_yellow"))

        # Bottom DataMesh Box
        bottom_box = Panel(
            Text(
                "Bottom_DataMesh (2. Domain Topology & Hardware)\n\n"
                "• V3: EventBus Pub/Sub & Inter-Session Bridge (SurrealDB + Obsidian)\n"
                "• V4: AMD GAIA SDK Native Tool Mixins & AutoHarness AST Defense",
                style="bright_yellow",
                justify="center",
            ),
            title="[bold red]Bottom_DataMesh[/bold red]",
            border_style="dark_orange",
            width=88,
        )
        grid.add_row(bottom_box)

        wrapper = Panel(
            grid,
            title="[bold bright_white on dark_green] 🧜 Mermaid 2D Terminal Flowchart Canvas [/bold bright_white on dark_green]",
            border_style="bright_green",
            padding=(1, 2),
        )
        self.console.print(wrapper)


def main() -> None:
    canvas = MermaidBoxCanvas()
    canvas.render_v_model_mermaid()


if __name__ == "__main__":
    main()
