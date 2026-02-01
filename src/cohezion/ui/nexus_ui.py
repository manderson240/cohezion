import time
from datetime import datetime

import psutil
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from cohezion.branding import Colors, Motifs


class NexusUI:
    """
    Abstracted UI toolkit for Cohezion CLI.
    Implements premium dashboard elements and animations.
    """

    def __init__(self, console=None):
        self.console = console or Console()

    def create_header(self, uptime: str) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)

        header_text = Text()
        header_text.append("COHEZION", style=f"bold {Colors.PLASMA_BLUE}")
        header_text.append(".IO ", style=f"bold {Colors.NEON_CYAN}")

        grid.add_row(
            header_text,
            Text("NEXUS COMMAND", style=f"bold {Colors.NEON_PURPLE}"),
            Text(f"UPTIME: {uptime}", style="bold yellow"),
        )
        return Panel(grid, border_style=Colors.PLASMA_BLUE)

    def create_pulse(self, coherence: float) -> Panel:
        intensity = min(1.0, max(0.0, coherence))
        color = "#f6d365" if intensity >= 0.5 else "#a1c4fd"

        progress = Progress(
            BarColumn(
                bar_width=None,
                complete_style=f"bold {color}",
                finished_style=f"bold {color}",
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            expand=True,
        )
        progress.add_task("Coherence", total=100, completed=intensity * 100)

        "⚡" if datetime.now().second % 2 == 0 else " "

    def create_lattice(self, expert_domains, expert_status) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("Expert Domain", style=f"bold {Colors.NEON_CYAN}")
        table.add_column("Status", justify="right")

        for key, name in expert_domains.items():
            status = expert_status[key]
            if status == "Ignited":
                color = "bold #38ef7d"
                status_text = "IGNITED"
            else:
                color = "dim white"
                status_text = "IDLE"
            table.add_row(name, Text(status_text, style=color))

        return Panel(
            table,
            title=f"[bold {Colors.NEON_CYAN}]Domain Expert Lattice",
            border_style=Colors.NEON_CYAN,
        )

    def create_metrics(self) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("Substrate", style=f"bold {Colors.PLASMA_BLUE}")
        table.add_column("Value", justify="right")

        vram = f"{psutil.virtual_memory().percent}%"
        table.add_row("Agent VRAM", vram)
        table.add_row("Slm Roster", "DeepSeek, Qwen")
        table.add_row("DB Status", "Surreal (Live)")
        table.add_row("Security", "PromptGuard 2.0")

        return Panel(
            table,
            title=f"[bold {Colors.PLASMA_BLUE}]Resource Guardrails",
            border_style=Colors.PLASMA_BLUE,
        )

    def create_discovery_ticker(self, discoveries) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("ID", style="dim", width=12)
        table.add_column("Discovery Hypothesis", ratio=1)
        table.add_column("Align", justify="right", style="bold #ff9a9e")

        for d in discoveries[-8:]:
            table.add_row(d["id"], d["text"], f"{d['align']:.2f}")

        return Panel(
            table,
            title=f"[bold {Colors.NEON_PURPLE}]Verification Pulse",
            border_style=Colors.NEON_PURPLE,
        )

    def create_avatar(self) -> Panel:
        """Creates the animated Nexus Singularity Avatar."""
        # Frame animation based on time
        frame_idx = int(time.time() * 2) % len(Motifs.NEXUS_AVATAR_FRAMES)
        frame = Motifs.NEXUS_AVATAR_FRAMES[frame_idx]

        return Panel(
            Align.center(Text.from_markup(frame)),
            title=f"[bold {Colors.EARTH_BLUE}]The Singularity",
            border_style=Colors.EARTH_BLUE,
            padding=(1, 2),
        )


class ConsciousnessIgnition:
    """Handles the startup boot sequence."""

    def __init__(self, console):
        self.console = console

    def ignite(self):
        """Runs the ignition sequence."""
        self.console.clear()

        # 1. Wall of Text
        self.console.print(Align.center(Text.from_markup(Motifs.WALL_OF_TEXT_LOGO)))
        time.sleep(1.0)

        # 2. Boot text
        steps = Motifs.IGNITION_SEQUENCE

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(style=Colors.SILICON_SILVER, complete_style=Colors.NEXUS_GREEN),
            transient=True,
            console=self.console,
        ) as progress:
            task = progress.add_task("[green]Igniting...", total=100)

            for step in steps:
                progress.update(task, description=step, advance=100 / len(steps))
                time.sleep(0.4)

        self.console.print(
            Align.center(
                f"[bold {Colors.NEXUS_GREEN}]SYSTEM IGNITION COMPLETE[/bold {Colors.NEXUS_GREEN}]"
            )
        )
        time.sleep(0.5)


def Layout_Mini_Split(text, progress, color, pulse_char):
    # Helper for mini-layout within pulse panel
    from rich.layout import Layout

    layout = Layout()
    layout.split_column(
        Text(
            f"{pulse_char} {text} {pulse_char}", style=f"bold {color}", justify="center"
        ),
        progress,
    )
    return layout
