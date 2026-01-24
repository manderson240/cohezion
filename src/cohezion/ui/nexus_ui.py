from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.align import Align
from datetime import datetime
import psutil

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
        header_text.append("COHEZION", style="bold #4facfe")
        header_text.append(".IO ", style="bold #00f2fe")

        grid.add_row(
            header_text,
            Text("NEXUS COMMAND", style="bold #f093fb"),
            Text(f"UPTIME: {uptime}", style="bold yellow"),
        )
        return Panel(grid, border_style="#4facfe")

    def create_pulse(self, coherence: float) -> Panel:
        intensity = min(1.0, max(0.0, coherence))
        color = "#f6d365" if intensity >= 0.5 else "#a1c4fd"
        pulse_text = "REALITY PRECIPITATION ACTIVE" if intensity >= 0.5 else "SUBSTRATE COHERENCE NOMINAL"

        progress = Progress(
            BarColumn(bar_width=None, complete_style=f"bold {color}", finished_style=f"bold {color}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            expand=True
        )
        progress.add_task("Coherence", total=100, completed=intensity*100)

        pulse_char = "⚡" if datetime.now().second % 2 == 0 else " "

    def create_lattice(self, expert_domains, expert_status) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("Expert Domain", style="bold #00f2fe")
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

        return Panel(table, title="[bold #00f2fe]Domain Expert Lattice", border_style="#00f2fe")

    def create_metrics(self) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("Substrate", style="bold #4facfe")
        table.add_column("Value", justify="right")

        vram = f"{psutil.virtual_memory().percent}%"
        table.add_row("Agent VRAM", vram)
        table.add_row("Slm Roster", "DeepSeek, Qwen")
        table.add_row("DB Status", "Surreal (Live)")
        table.add_row("Security", "PromptGuard 2.0")

        return Panel(table, title="[bold #4facfe]Resource Guardrails", border_style="#4facfe")

    def create_discovery_ticker(self, discoveries) -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("ID", style="dim", width=12)
        table.add_column("Discovery Hypothesis", ratio=1)
        table.add_column("Align", justify="right", style="bold #ff9a9e")

        for d in discoveries[-8:]:
            table.add_row(d["id"], d["text"], f"{d['align']:.2f}")

        return Panel(table, title="[bold #f093fb]Verification Pulse", border_style="#f093fb")

def Layout_Mini_Split(text, progress, color, pulse_char):
    # Helper for mini-layout within pulse panel
    from rich.layout import Layout
    l = Layout()
    l.split_column(
        Text(f"{pulse_char} {text} {pulse_char}", style=f"bold {color}", justify="center"),
        progress
    )
    return l
