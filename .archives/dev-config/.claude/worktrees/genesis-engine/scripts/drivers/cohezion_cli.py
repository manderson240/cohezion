import argparse
import asyncio
import contextlib
import os
import re
import sys
from datetime import datetime

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from cohezion.branding import Colors
from cohezion.ui.nexus_ui import ConsciousnessIgnition, NexusUI


# Configuration
LOG_PATH = "logs/lab_driver.log"
EXPERT_DOMAINS = {
    "architect": "Architect",
    "engineer": "Engineer",
    "biologist": "Biologist",
    "quantum_hw": "Quantum HW",
    "quantum_algo": "Quantum Algo",
}
EXPERTS_STATUS = dict.fromkeys(EXPERT_DOMAINS.keys(), "Idle")


class SimulationDriver:
    """Handles the state simulation and log digestion."""

    def __init__(self):
        self.discoveries = []
        self.coherence = 0.45
        self.experts_status = dict.fromkeys(EXPERT_DOMAINS.keys(), "Idle")

    async def cool_down_expert(self, expert):
        await asyncio.sleep(5)
        self.experts_status[expert] = "Idle"

    async def digest_logs(self):
        """Yields state updates based on logs."""
        if not os.path.exists(LOG_PATH):
            return

        with open(LOG_PATH) as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    yield  # Heartbeat yield
                    continue

                # Check for expert ignition
                for key in EXPERT_DOMAINS:
                    if f"route: {key}" in line.lower():
                        self.experts_status[key] = "Ignited"
                        asyncio.create_task(self.cool_down_expert(key))

                # Check for discoveries
                if "Discovery persisted" in line:
                    match = re.search(r"discovery_(\d+)", line)
                    disc_id = match.group(0) if match else "DISC_NEW"
                    self.discoveries.append(
                        {
                            "id": disc_id,
                            "text": "New Lab Discovery synthesized from Nexus analysis.",
                            "align": 0.85 + (hash(line) % 10 / 100),
                        }
                    )

                # Update coherence randomly around seed
                self.coherence += (hash(line) % 11 - 5) / 100
                self.coherence = max(0.1, min(0.95, self.coherence))
                yield


class TerminalNexus:
    def __init__(self):
        self.console = Console()
        self.ui = NexusUI(console=self.console)
        self.layout = Layout()
        self.driver = SimulationDriver()
        self.start_time = datetime.now()

    def make_layout(self):
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        self.layout["main"].split_row(
            Layout(name="lattice", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right_col", ratio=1),
        )
        self.layout["right_col"].split_column(
            Layout(name="avatar", size=8),
            Layout(name="metrics"),
        )
        self.layout["center"].split_column(
            Layout(name="discovery_ticker"),
            Layout(name="pulse", size=5),
        )

    def get_header(self) -> Panel:
        uptime = str(datetime.now() - self.start_time).split(".")[0]
        return self.ui.create_header(uptime)

    def get_lattice(self) -> Panel:
        return self.ui.create_lattice(EXPERT_DOMAINS, self.driver.experts_status)

    def get_avatar(self) -> Panel:
        return self.ui.create_avatar()

    def get_discovery_ticker(self) -> Panel:
        return self.ui.create_discovery_ticker(self.driver.discoveries)

    def get_concept_explorer(self) -> Panel:
        # We need to import it here or via NexusUI
        concepts = [
            ("HIHO Stability", "The 0.5 Coherence Rule for reality precipitation."),
            ("12D Manifold", "3 Spatial + 1 Time + 8 Brane dimensionality."),
            ("FLUME", "Fluid Latent Understanding through Manifold Encoding."),
            (
                "Vitrification",
                "The process of hardening knowledge into the Root of Trust.",
            ),
        ]
        import random

        concept, description = random.choice(concepts)
        text = Text()
        text.append(f"{concept}: ", style=f"bold {Colors.WARNING_GOLD}")
        text.append(description, style="italic")
        return Panel(
            text,
            title=f"[bold {Colors.WARNING_GOLD}]Concept Explorer",
            border_style=Colors.WARNING_GOLD,
        )

    def get_metrics(self) -> Panel:
        return self.ui.create_metrics()

    def get_footer(self) -> Panel:
        return Panel(
            Text(
                "SYSTEM: STABLE | SPRINT: ORGANIC MODULARITY | BRAND: NEXUS ACTIVE",
                justify="center",
                style=f"bold {Colors.NEXUS_GREEN}",
            ),
            border_style=Colors.NEXUS_GREEN,
        )

    def get_pulse(self) -> Panel:
        intensity = min(1.0, max(0.0, self.driver.coherence))
        # Gradient based on coherence
        if intensity >= 0.5:
            color = Colors.WARNING_GOLD  # Transient/Active
            pulse_text = "REALITY PRECIPITATION ACTIVE (0.5+)"
        else:
            color = Colors.EARTH_BLUE  # Stable
            pulse_text = "SUBSTRATE COHERENCE NOMINAL"

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

        # Add a subtle "pulse" animation character
        pulse_char = "⚡" if datetime.now().second % 2 == 0 else " "

        return Panel(
            Align.center(
                Layout().split_column(
                    Text(
                        f"{pulse_char} {pulse_text} {pulse_char}",
                        style=f"bold {color}",
                        justify="center",
                    ),
                    progress,
                )
            ),
            title=f"[bold {Colors.WARNING_GOLD}]HIHO Stability Pulse",
            border_style=color,
        )

    async def run(self):
        self.make_layout()

        with Live(self.layout, refresh_per_second=4, screen=True):
            async for _ in self.driver.digest_logs():
                self.layout["header"].update(self.get_header())
                self.layout["lattice"].update(self.get_lattice())
                self.layout["pulse"].update(self.get_pulse())

                # Switch between discovery ticker and concept explorer
                if datetime.now().second % 10 < 5:
                    self.layout["discovery_ticker"].update(self.get_discovery_ticker())
                else:
                    self.layout["discovery_ticker"].update(self.get_concept_explorer())

                self.layout["metrics"].update(self.get_metrics())
                self.layout["avatar"].update(self.get_avatar())
                self.layout["footer"].update(self.get_footer())

                await asyncio.sleep(0.1)


async def cmd_research(args):
    """Run the Nexus Research Miner."""
    from cohezion.branding import Colors
    from cohezion.swarm.agents.nexus_research_agent import NexusResearchAgent

    console = Console()
    console.print(
        Panel(
            f"[bold {Colors.EARTH_BLUE}]NEXUS RESEARCH MINER IGNITED",
            border_style=Colors.EARTH_BLUE,
        )
    )

    agent = NexusResearchAgent()
    try:
        if args.query:
            console.print(f"[dim]Searching for:[/dim] [bold #f093fb]{args.query}[/bold #f093fb]")
            res = await agent.search_and_rank(args.query)
        else:
            console.print("[dim]Executing comprehensive daily sweep...[/dim]")
            res = await agent.mine_daily(limit_per_source=args.limit)

        console.print(f"\n[bold {Colors.NEXUS_GREEN}]RESEARCH SYNTHESIS COMPLETE[/bold {Colors.NEXUS_GREEN}]")
        console.print(
            Panel(
                res,
                title=f"[bold {Colors.WARNING_GOLD}]Latest Frontier Insights",
                border_style=Colors.WARNING_GOLD,
            )
        )
    finally:
        await agent.close()


async def cmd_journey(args):
    """Run the interactive Cohezion Journey."""
    from cohezion.journey.registry import get_journey_registry

    registry = get_journey_registry()
    console = Console()

    if args.list:
        table = Table(title="Available Cohezion Journeys", border_style=Colors.EARTH_BLUE)
        table.add_column("Voyage", style=f"bold {Colors.NEXUS_GREEN}")
        table.add_column("Description", style="italic")
        for name, data in registry.list_voyages().items():
            table.add_row(name, data["description"])
        console.print(table)
        return

    voyage_name = args.start or "The HIHO Attractor"
    voyage = registry.get_voyage(voyage_name)

    if not voyage:
        console.print(f"[bold red]Error:[/bold red] Voyage '{voyage_name}' not found.")
        return

    console.print(f"[bold {Colors.EARTH_BLUE}]IGNITING VOYAGE:[/bold {Colors.EARTH_BLUE}] {voyage_name}")
    await voyage["entry_point"]()


async def main():
    parser = argparse.ArgumentParser(description="Cohezion CLI - Swarm Orchestration Utility")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Dash command
    subparsers.add_parser("dash", help="Launch Terminal Nexus Dashboard")

    # Research command
    res_parser = subparsers.add_parser("research", help="Run Nexus Research Miner")
    res_parser.add_argument("--query", type=str, help="Specific research query")
    res_parser.add_argument("--limit", type=int, default=5, help="Limit per source")

    # Browser command
    browser_parser = subparsers.add_parser("browser", help="Launch Cohezion Browser Agent")
    browser_parser.add_argument("url", type=str, help="URL to explore")
    browser_parser.add_argument("--screenshot", type=str, help="Path to save screenshot")
    browser_parser.add_argument("--headful", action="store_true", help="Launch in headful mode")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Run validation suite")
    verify_parser.add_argument("--adversarial", action="store_true", help="Run adversarial stress tests")

    # Journey command
    journey_parser = subparsers.add_parser("journey", help="Begin an interactive Cohezion Journey")
    journey_parser.add_argument("--list", action="store_true", help="List all available journeys")
    journey_parser.add_argument("--start", type=str, help="Start a specific journey")

    args = parser.parse_args()

    if args.command == "dash" or (args.command is None and len(sys.argv) == 1):
        console = Console()
        ignition = ConsciousnessIgnition(console)
        ignition.ignite()

        nexus = TerminalNexus()
        await nexus.run()
    elif args.command == "research":
        await cmd_research(args)
    elif args.command == "journey":
        await cmd_journey(args)
    elif args.command == "browser":
        from cohezion.browser import CohezionBrowserAgent

        agent = CohezionBrowserAgent(headless=not args.headful)
        try:
            console = Console()
            from cohezion.branding import Colors

            console.print(
                f"[bold {Colors.EARTH_BLUE}]Cohezion Browser Agent Ignited[/bold {Colors.EARTH_BLUE}] - URL: {args.url}"
            )
            if args.screenshot:
                await agent.capture_screenshot(args.url, args.screenshot)
                console.print(f"✅ Screenshot captured: [bold]{args.screenshot}[/bold]")
            else:
                page = await agent.navigate(args.url)
                title = await page.title()
                console.print(f"✅ Navigated to: [bold]{title}[/bold]")
                await page.close()
        finally:
            await agent.close()
    elif args.command == "verify":
        console = Console()
        from cohezion.branding import Colors

        console.print(f"[bold {Colors.NEXUS_GREEN}]Initializing Validation Suite...[/bold {Colors.NEXUS_GREEN}]")
        cmd = ["uv", "run", "tests/verify_context.py"]
        if args.adversarial:
            cmd.append("--adversarial")

        import subprocess

        result = subprocess.run(cmd, capture_output=True, text=True)
        console.print(result.stdout)
        if result.returncode != 0:
            console.print(f"[bold red]Validation FAILED[/bold red]\n{result.stderr}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
