r"""Terminal Mermaid-Style Color Graph & Flowchart Engine.
=========================================================
Renders vibrant, colorized Mermaid-style flowcharts directly in the Linux terminal
using ANSI 24-bit TrueColor box-drawing characters and Rich markup.
"""

from __future__ import annotations

import re

from rich.console import Console
from rich.panel import Panel


class TerminalMermaidColorRenderer:
    """Renders colorized Mermaid flowcharts and V-Models in CLI environments."""

    def __init__(self) -> None:
        self.console = Console(force_terminal=True, color_system="truecolor")

    def render_mermaid_v_model(self) -> None:
        """Render a colorful, stylized Mermaid flowchart in terminal."""
        content = [
            "[bold white on dark_blue]  flowchart TD  [/bold white on dark_blue]\n",
            "  [bold yellow]subgraph[/bold yellow] [bold bright_cyan]V_Model_Engineering_Sweep[/bold bright_cyan][dim][\"Systems Engineering V-Model Rigor & Compound Loop\"][/dim]",
            "",
            "    [bold yellow]subgraph[/bold yellow] [bold magenta]Top_Left_Specs[/bold magenta][dim][\"1. System Architecture & Invariants (Top-Left)\"][/dim]",
            "      [bold cyan]V1[/bold cyan][dim][\"[/dim][bold bright_green]FLUME 12D Poincaré Metric[/bold bright_green] [dim]&[/dim] [green]Levi-Civita Geodesic Flow[/green] [dim](poincare_neural_ode.py)\"][/dim]",
            "      [bold cyan]V2[/bold cyan][dim][\"[/dim][bold bright_green]Matsumoto ENC Debye Collapse[/bold bright_green] [dim]&[/dim] [green]Heim Metron Tiling[/green] [dim](matsumoto_enc_engine.py)\"][/dim]",
            "    [bold yellow]end[/bold yellow]",
            "",
            "    [bold yellow]subgraph[/bold yellow] [bold dark_orange]Bottom_DataMesh[/bold dark_orange][dim][\"2. Domain DataMesh & Event Topology (Bottom)\"][/dim]",
            "      [bold cyan]V3[/bold cyan][dim][\"[/dim][bold bright_yellow]EventBus Pub/Sub[/bold bright_yellow], [yellow]CrossSessionBridge & Kanban Sinks[/yellow] [dim](kanban_bridge.py)\"][/dim]",
            "      [bold cyan]V4[/bold cyan][dim][\"[/dim][bold bright_yellow]AMD GAIA Tool Mixins[/bold bright_yellow] [dim]&[/dim] [yellow]AutoHarness AST Defense[/yellow] [dim](amd_gaia_tool_mixins.py)\"][/dim]",
            "    [bold yellow]end[/bold yellow]",
            "",
            "    [bold yellow]subgraph[/bold yellow] [bold bright_magenta]Top_Right_VV[/bold bright_magenta][dim][\"3. Verification, Guardrails & Compound Velocity (Top-Right)\"][/dim]",
            "      [bold cyan]V5[/bold cyan][dim][\"[/dim][bold bright_cyan]Write Budget Governor[/bold bright_cyan], [cyan]ZFS Datasets & Workspace Bridge[/cyan] [dim](write_budget_governor.py)\"][/dim]",
            "    [bold yellow]end[/bold yellow]",
            "",
            "    [bold magenta]Top_Left_Specs[/bold magenta] [bold bright_white]═══►[/bold bright_white] [bold dark_orange]Bottom_DataMesh[/bold dark_orange]",
            "    [bold dark_orange]Bottom_DataMesh[/bold dark_orange] [bold bright_white]═══►[/bold bright_white] [bold bright_magenta]Top_Right_VV[/bold bright_magenta]",
            "  [bold yellow]end[/bold yellow]",
        ]

        diagram_text = "\n".join(content)
        panel = Panel(
            diagram_text,
            title="[bold bright_white on dark_green] 🧜 Mermaid Terminal Color Canvas [/bold bright_white on dark_green]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def render_custom_mermaid(self, mermaid_code: str) -> None:
        """Parse raw Mermaid code and colorize node definitions, subgraphs, and arrows."""
        lines = mermaid_code.strip().splitlines()
        colorized_lines = []

        for line in lines:
            # Colorize subgraphs
            if "subgraph" in line:
                line = re.sub(r"subgraph\s+([A-Za-z0-9_]+)", r"[bold yellow]subgraph[/bold yellow] [bold magenta]\1[/bold magenta]", line)
            elif line.strip() == "end":
                line = line.replace("end", "[bold yellow]end[/bold yellow]")

            # Colorize arrows
            line = line.replace("-->", "[bold bright_white]──►[/bold bright_white]")
            line = line.replace("==>", "[bold bright_yellow]══►[/bold bright_yellow]")

            # Colorize node brackets
            line = re.sub(r'\["([^"]+)"\]', r'[dim][\"[/dim][bold green]\1[/bold green][dim]\"][/dim]', line)

            colorized_lines.append(line)

        panel = Panel(
            "\n".join(colorized_lines),
            title="[bold green]Mermaid CLI Syntax Color View[/bold green]",
            border_style="bright_blue",
        )
        self.console.print(panel)


def main() -> None:
    renderer = TerminalMermaidColorRenderer()
    renderer.render_mermaid_v_model()


if __name__ == "__main__":
    main()
