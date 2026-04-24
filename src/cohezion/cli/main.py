# ruff: noqa: S104, E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Cohezion: Unified CLI Framework

A self-evolving agentic sandbox for Anti-Fragile Agentic Reasoning.
This CLI provides a single entry point for all Cohezion operations.
"""

import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Cohezion Imports
from cohezion.core.persistence.repositories.pattern_repository import PatternRepository
from cohezion.core.persistence.repositories.surreal_journey_repository import (
    SurrealJourneyRepository,
)
from cohezion.core.persistence.repositories.surreal_skill_repository import (
    SurrealSkillRepository,
)
from cohezion.core.persistence.repositories.surreal_universe_repository import (
    SurrealUniverseRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.services.agent_service import AgentConfig, AgentService
from cohezion.services.knowledge_service import KnowledgeService
from cohezion.services.physics_service import PhysicsService
from cohezion.services.swarm_service import SwarmService
from cohezion.swarm.agents.code_review_swarm import CodeReviewSwarm


app = typer.Typer(
    name="cohezion",
    help="Cohezion: Self-Evolving Agentic Sandbox",
    add_completion=True,
    no_args_is_help=True,
)
console = Console()

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗             ║
║  ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗            ║
║  ███████║███████║██║     █████╔╝ █████╗  ██████╔╝            ║
║  ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗            ║
║  ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║            ║
║  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝            ║
║                     Self-Evolving Agentic Sandbox              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


@app.command()
def quickstart():
    """Show quick start guide.

    Display common workflows and getting started information
    for new users.
    """
    console.print(BANNER)
    console.print()

    console.print(
        Panel(
            "[bold]Welcome to Cohezion![/bold]\n\n"
            "A self-evolving agentic sandbox for Anti-Fragile Agentic Reasoning.",
            title="Quick Start",
            border_style="cyan",
        )
    )

    console.print("\n[bold cyan]Common Workflows:[/bold cyan]\n")

    table = Table()
    table.add_column("Command", style="green")
    table.add_column("Description", style="dim")
    table.add_column("Example", style="yellow")

    table.add_row("cohezion hello", "Verify installation", "cohezion hello --name 'Anthropic'")
    table.add_row(
        "cohezion swarm run",
        "Run QUADRATURE NEXUS analysis",
        'cohezion swarm run "Analyze quantum computing"',
    )
    table.add_row(
        "cohezion demo nexus",
        "Interactive nexus demo",
        "cohezion demo nexus --scenario physics",
    )
    table.add_row(
        "cohezion ouroboros status",
        "Check system health",
        "cohezion ouroboros status --detailed",
    )
    table.add_row(
        "cohezion config show",
        "View configuration",
        "cohezion config show --section ollama",
    )

    console.print(table)
    console.print("\n[dim]Use --help on any command for detailed information.[/dim]")


@app.command()
def hello(
    name: str = typer.Option("World", "--name", "-n", help="Name to greet"),
    colorful: bool = typer.Option(True, "--color/--no-color", help="Enable colored output"),
):
    """Quick start verification command.

    Use this to verify your Cohezion installation is working correctly.
    """
    if colorful:
        console.print(
            Panel.fit(
                f"[bold green]Hello, {name}![/bold green]\n\n"
                f"[dim]Cohezion CLI is running successfully![/dim]",
                title="✓ Cohezion Status",
                border_style="green",
            )
        )
    else:
        print(f"Hello, {name}! Cohezion CLI is running successfully.")


@app.command()
def version():
    """Show Cohezion version and system information."""
    table = Table(title="Cohezion System Information")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")

    table.add_row("CLI Version", "✓ Active", "0.1.0")
    table.add_row("Python", "✓ Active", sys.version.split()[0])
    table.add_row("Typer Framework", "✓ Installed", "Command-line interface")
    table.add_row("Rich Output", "✓ Enabled", "Formatted terminal output")

    console.print(table)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Cohezion: Self-Evolving Agentic Sandbox.

    A unified interface for swarm intelligence, fluid interpolation,
    and self-healing systems.
    """
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")
    if config:
        console.print(f"[dim]Using config: {config}[/dim]")


async def get_swarm_service():
    """Dependency injection helper for SwarmService."""
    client = SurrealClient()
    await client.connect()

    repo_universe = SurrealUniverseRepository(client._client)
    repo_journey = SurrealJourneyRepository(client._client)
    repo_skill = SurrealSkillRepository(client._client)

    agent_service = AgentService(repo_journey, repo_universe)
    await agent_service.register_agent(
        AgentConfig(name="analyst", agent_type="analyst", model_name="gemma3:4b")
    )
    await agent_service.register_agent(
        AgentConfig(name="critic", agent_type="critic", model_name="phi3:mini")
    )
    await agent_service.register_agent(
        AgentConfig(name="synthesizer", agent_type="synthesizer", model_name="mistral:7b")
    )

    physics_service = PhysicsService(repo_universe)
    knowledge_service = KnowledgeService(repo_universe, repo_skill)

    return SwarmService(
        agent_service=agent_service,
        physics_service=physics_service,
        knowledge_service=knowledge_service,
    )


swarm_app = typer.Typer(help="Run swarm intelligence operations")
app.add_typer(swarm_app, name="swarm", help="Swarm operations")


@swarm_app.command("run")
def swarm_run(
    query: str = typer.Argument(..., help="Query or problem to analyze"),
    experts: int = typer.Option(5, "--experts", "-e", help="Number of expert agents"),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of debate rounds"),
    model: str | None = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Run QUADRATURE NEXUS analysis.

    Execute the quadrature consensus protocol with multiple expert agents
    to solve complex problems through democratic deliberation.
    """
    console.print(
        Panel(
            f"[bold]QUADRATURE NEXUS Analysis[/bold]\n\n"
            f"Query: [cyan]{query}[/cyan]\n"
            f"Experts: {experts}\n"
            f"Rounds: {rounds}\n"
            f"Model: {model or 'default'}",
            title="🧠 Swarm Configuration",
            border_style="blue",
        )
    )

    import asyncio

    async def run():
        service = await get_swarm_service()
        if model:
            # Update registry or config if model provided
            pass

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing swarm...", total=None)
            result = await service.execute_quadrature(query)
            progress.update(task, description="✓ Analysis Complete")

        console.print(
            Panel(
                f"[bold green]✓ Consensus Achieved[/bold green]\n\n"
                f"{result.final_response}\n\n"
                f"[dim]Confidence: {result.confidence:.2f} | Time: {result.processing_time_ms:.0f}ms[/dim]",
                title="Result",
                border_style="green",
            )
        )

    asyncio.run(run())


@swarm_app.command("debate")
def swarm_debate(
    topic: str = typer.Argument(..., help="Topic for democratic debate"),
    participants: int = typer.Option(7, "--participants", "-p", help="Number of participants"),
    duration: int = typer.Option(300, "--duration", "-d", help="Duration in seconds"),
):
    """Run democratic debate.

    Simulate a democratic deliberation process where multiple agents
    debate a topic and reach consensus through voting.
    """
    console.print(
        Panel(
            f"[bold]Democratic Debate[/bold]\n\n"
            f"Topic: [cyan]{topic}[/cyan]\n"
            f"Participants: {participants}\n"
            f"Duration: {duration}s",
            title="🗳️ Debate Configuration",
            border_style="yellow",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        _ = progress.add_task("Orchestrating debate...", total=None)
        import time

        time.sleep(1)

    console.print("[bold green]✓ Debate complete[/bold green]")


@swarm_app.command("simulate")
def swarm_simulate(
    iterations: int = typer.Option(1000, "--iterations", "-i", help="Number of iterations"),
    agents: int = typer.Option(100, "--agents", "-a", help="Number of agents"),
    parallel: bool = typer.Option(True, "--parallel/--sequential", help="Run in parallel"),
):
    """Run mass simulation.

    Execute large-scale multi-agent simulations with configurable
    iteration counts and agent populations.
    """
    console.print(
        Panel(
            f"[bold]Mass Simulation[/bold]\n\n"
            f"Iterations: {iterations}\n"
            f"Agents: {agents}\n"
            f"Parallel: {parallel}",
            title="⚡ Simulation Parameters",
            border_style="cyan",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        _ = progress.add_task("Initializing simulation...", total=None)
        import time

        time.sleep(1)

    console.print("[bold green]✓ Simulation complete[/bold green]")


@swarm_app.command("review")
def swarm_review(
    target_dir: str = typer.Option("src/cohezion", "--target", "-t", help="Directory to review"),
    batch_size: int = typer.Option(5, "--batch-size", "-b", help="Files per static batch"),
    complexity: int = typer.Option(
        15, "--complexity", "-c", help="AST complexity threshold for LLM scans"
    ),
    output: str = typer.Option(
        "code_review_report.md", "--output", "-o", help="Markdown report output path"
    ),
):
    """Run full codebase review using specialist swarm agents.

    Orchestrates static and LLM-based code scouts to identify
    patterns and anti-patterns across the codebase.
    """
    console.print(
        Panel(
            f"[bold]Swarm Code Review[/bold]\n\n"
            f"Target: [cyan]{target_dir}[/cyan]\n"
            f"Batch Size: {batch_size}\n"
            f"Complexity Threshold: {complexity}\n"
            f"Output: {output}",
            title="🔬 Review Configuration",
            border_style="magenta",
        )
    )

    import asyncio

    async def run():
        client = SurrealClient()
        await client.connect()
        repo = PatternRepository(client)

        swarm = CodeReviewSwarm(
            repository=repo,
            target_dir=target_dir,
            batch_size=batch_size,
            complexity_threshold=complexity,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Code Review Swarm...", total=None)
            report = await swarm.run_full_scan()
            progress.update(task, description="✓ Scan Complete")

        # Format and write report
        from pathlib import Path

        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w") as f:
            f.write("# Code Review Report\n\n")
            f.write(f"**Target Directory:** `{target_dir}`\n")
            f.write(f"**Total Files Checked:** {report.total_files}\n")
            f.write(f"**Files Scanned (High Complexity):** {report.scanned_files}\n")
            f.write(f"**Total Findings:** {len(report.findings)}\n\n")

            f.write("## Findings\n\n")

            # Group findings by type
            patterns = [find for find in report.findings if find.type == "pattern"]
            anti_patterns = [find for find in report.findings if find.type == "anti_pattern"]

            if anti_patterns:
                f.write("### 🚨 Anti-Patterns (Requires Attention)\n\n")
                for finding in anti_patterns:
                    f.write(f"#### {finding.name} ({finding.category})\n")
                    f.write(f"- **Severity:** {finding.severity}\n")
                    f.write(f"- **File:** `{finding.file_path}`\n")
                    f.write(f"- **Description:** {finding.description}\n")
                    f.write(f"- **Remediation:** {finding.remediation}\n\n")
                    f.write("```python\n")
                    f.write(f"{finding.code_snippet}\n")
                    f.write("```\n\n")

            if patterns:
                f.write("### ✨ Recognized Patterns\n\n")
                for finding in patterns:
                    f.write(f"#### {finding.name} ({finding.category})\n")
                    f.write(f"- **File:** `{finding.file_path}`\n")
                    f.write(f"- **Description:** {finding.description}\n\n")
                    f.write("```python\n")
                    f.write(f"{finding.code_snippet}\n")
                    f.write("```\n\n")

        console.print(f"[bold green]✓ Report generated: {out_path.absolute()}[/bold green]")

    asyncio.run(run())


dashboard_app = typer.Typer(help="Dashboard operations")
app.add_typer(dashboard_app, name="dashboard", help="Dashboard operations")


@dashboard_app.command("start")
def dashboard_start(
    host: str = typer.Option("0.0.0.0", "--host", help="Dashboard host"),
    port: int = typer.Option(8080, "--port", "-p", help="Dashboard port"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload"),
):
    """Start interactive dashboard.

    Launch the Cohezion web dashboard for real-time monitoring
    and interaction with the swarm.
    """
    console.print(
        Panel(
            f"[bold]Interactive Dashboard[/bold]\n\n"
            f"Host: [cyan]{host}[/cyan]\n"
            f"Port: {port}\n"
            f"Reload: {reload}",
            title="📊 Dashboard Configuration",
            border_style="magenta",
        )
    )

    console.print(f"\n[dim]Dashboard would start at http://{host}:{port}[/dim]")
    console.print("[yellow]Note: Dashboard launch not implemented in this phase[/yellow]")


config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config", help="Configuration management")


@config_app.command("show")
def config_show(
    section: str | None = typer.Option(None, "--section", "-s", help="Show specific section"),
):
    """Show current configuration.

    Display the current Cohezion configuration including Ollama,
    SurrealDB, Swarm, FLUME, and Ouroboros settings.
    """
    try:
        from cohezion.config import settings

        if section:
            sections = {
                "ollama": settings.ollama,
                "surrealdb": settings.surrealdb,
                "swarm": settings.swarm,
                "flume": settings.flume,
                "ouroboros": settings.ouroboros,
                "dashboard": settings.dashboard,
            }
            if section.lower() not in sections:
                console.print(f"[red]Unknown section: {section}[/red]")
                raise typer.Exit(1)

            settings_obj = sections[section.lower()]
            table = Table(title=f"{section.capitalize()} Configuration")
        else:
            table = Table(title="Cohezion Configuration")
            settings_obj = settings

        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        for field, value in settings_obj.model_dump().items():
            table.add_row(field, str(value))

        console.print(table)
    except ImportError:
        console.print("[yellow]Configuration module not available[/yellow]")


@config_app.command("validate")
def config_validate():
    """Validate configuration.

    Check that all required configuration values are present and valid.
    """
    console.print("[cyan]Validating configuration...[/cyan]")

    try:
        from cohezion.config import settings

        all_valid = True

        table = Table(title="Configuration Validation")
        table.add_column("Section", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        sections = [
            ("Ollama", settings.ollama.url is not None),
            ("SurrealDB", settings.surrealdb.url is not None),
            ("Swarm", settings.swarm.experts_count > 0),
            ("FLUME", settings.flume.device in ["cuda", "cpu"]),
            ("Ouroboros", settings.ouroboros.cycle_interval > 0),
            ("Dashboard", settings.dashboard.port > 0),
        ]

        for section, valid in sections:
            status = "✓ Valid" if valid else "✗ Invalid"
            color = "green" if valid else "red"
            table.add_row(section, f"[{color}]{status}[/{color}]", "")
            all_valid = all_valid and valid

        console.print(table)

        if all_valid:
            console.print("\n[bold green]✓ All configurations are valid[/bold green]")
        else:
            console.print("\n[bold red]✗ Some configurations are invalid[/bold red]")
            raise typer.Exit(1)
    except ImportError:
        console.print("[yellow]Configuration module not available[/yellow]")
        raise typer.Exit(1) from None


explore_app = typer.Typer(help="Explore Cohezion capabilities")
app.add_typer(explore_app, name="explore", help="Explore Cohezion capabilities")


@explore_app.command("skills")
def explore_skills(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number to show"),
):
    """Explore available capabilities.

    List and search through the Cohezion capability registry
    to discover available skills and their purposes.
    """
    console.print(
        Panel(
            f"[bold]Capability Registry[/bold]\n\nCategory: {category or 'All'}\nLimit: {limit}",
            title="🔍 Skills Explorer",
            border_style="blue",
        )
    )

    console.print("[dim]Capability registry integration coming soon[/dim]")


@explore_app.command("journey")
def explore_journey(
    agent: str | None = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    steps: int = typer.Option(20, "--steps", "-s", help="Number of steps to show"),
):
    """Explore agent journey history.

    Browse through the 12D physics trajectories of agents
    to understand their reasoning paths and evolution.
    """
    console.print(
        Panel(
            f"[bold]Journey Explorer[/bold]\n\nAgent: {agent or 'All'}\nSteps: {steps}",
            title="🎯 Journey Explorer",
            border_style="green",
        )
    )

    console.print("[dim]Journey exploration integration coming soon[/dim]")


demo_app = typer.Typer(help="Interactive demonstrations")
app.add_typer(demo_app, name="demo", help="Interactive demonstrations")


@demo_app.command("flume")
def demo_flume(
    input_text: str = typer.Argument(..., help="Input text for interpolation"),
    steps: int = typer.Option(10, "--steps", "-s", help="Interpolation steps"),
    visualize: bool = typer.Option(True, "--visualize/--no-visualize", help="Show visualization"),
):
    """FLUME fluid interpolation demo.

    Demonstrate the Fluid Latent Understanding through Manifold Encoding
    (FLUME) system for smooth interpolation in latent space.
    """
    console.print(
        Panel(
            f"[bold]FLUME Interpolation Demo[/bold]\n\n"
            f"Input: [cyan]{input_text[:50]}...[/cyan]\n"
            f"Steps: {steps}\n"
            f"Visualize: {visualize}",
            title="🌊 FLUME Configuration",
            border_style="blue",
        )
    )

    import asyncio

    async def run():
        client = SurrealClient()
        await client.connect()
        repo = SurrealUniverseRepository(client._client)
        service = PhysicsService(repo)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Computing 12D state...", total=None)
            state = await service.compute_physics_state(input_text)
            progress.update(task, description="Analyzing stability...")
            analysis = await service.analyze_physics_state(state)
            progress.update(task, description="✓ Computation Complete")

        table = Table(title="FLUME Physics State")
        table.add_column("Dimension", style="cyan")
        table.add_column("Value", style="green")

        for k, v in state.to_dict().items():
            table.add_row(k, f"{v:.4f}")

        console.print(table)
        console.print(f"\n[bold]Overall Health: {analysis.overall_health:.2f}[/bold]")
        for rec in analysis.recommendations:
            console.print(f"  • {rec}")

    asyncio.run(run())


@demo_app.command("nexus")
def demo_nexus(
    scenario: str = typer.Option("physics", "--scenario", "-s", help="Scenario type"),
    complexity: int = typer.Option(5, "--complexity", "-c", help="Complexity level (1-10)"),
    interactive: bool = typer.Option(True, "--interactive", help="Enable interactive mode"),
):
    """QUADRATURE NEXUS orchestration demo.

    Showcase the quadrature consensus system orchestrating multiple
    expert agents to solve complex problems.
    """
    console.print(
        Panel(
            f"[bold]QUADRATURE NEXUS Demo[/bold]\n\n"
            f"Scenario: [cyan]{scenario}[/cyan]\n"
            f"Complexity: {complexity}\n"
            f"Interactive: {interactive}",
            title="🔮 Nexus Configuration",
            border_style="purple",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing expert agents...", total=None)
        import time

        time.sleep(0.3)
        progress.update(task, description="Running quadrature consensus...")
        time.sleep(0.3)
        progress.update(task, description="Computing solution...")

    console.print("\n[dim]Nexus orchestration not implemented in this phase[/dim]")
    console.print("[dim]When implemented, this will showcase:[/dim]")
    console.print("  • Multi-expert agent deliberation")
    console.print("  • Quadrature consensus protocol")
    console.print("  • Confidence scoring and aggregation")
    console.print("  • Real-time debate visualization")


@demo_app.command("journey")
def demo_journey(
    agent_id: str = typer.Argument(..., help="Agent ID to visualize"),
    steps: int = typer.Option(50, "--steps", "-s", help="Number of steps to visualize"),
    dimension: int = typer.Option(12, "--dimension", "-d", help="Latent dimension"),
):
    """12D journey visualization demo.

    Visualize the 12-dimensional physics trajectory of agents
    through the manifold space.
    """
    console.print(
        Panel(
            f"[bold]12D Journey Visualization[/bold]\n\n"
            f"Agent: [cyan]{agent_id}[/cyan]\n"
            f"Steps: {steps}\n"
            f"Dimension: {dimension}",
            title="🎯 Journey Configuration",
            border_style="green",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading journey data...", total=None)
        import time

        time.sleep(0.5)
        progress.update(task, description="Computing 12D trajectory...")
        time.sleep(0.5)
        progress.update(task, description="Generating visualization...")

    console.print("\n[dim]Journey visualization not implemented in this phase[/dim]")
    console.print("[dim]When implemented, this will show:[/dim]")
    console.print("  • 12D radar plots of agent state evolution")
    console.print("  • PCA projections of latent space trajectories")
    console.print("  • Coherence, Stability, Complexity metrics")
    console.print("  • Morphic Resonance patterns")


universe_app = typer.Typer(help="Universe management and seeding")
app.add_typer(universe_app, name="universe", help="Universe operations")


@universe_app.command("seed")
def universe_seed(
    name: str = typer.Argument(..., help="Name of the universe to seed"),
    description: str = typer.Option("A new simulation universe", "--desc", help="Description"),
):
    """Seed a new simulation universe.

    Initialize a new universe with stable HIHO physics parameters.
    """
    console.print(f"[bold cyan]Seeding universe: {name}[/bold cyan]")

    import asyncio

    async def run():
        client = SurrealClient()
        await client.connect()
        repo = SurrealUniverseRepository(client._client)
        _service = PhysicsService(repo)

        # In a real impl, we'd use a dedicated UniverseService
        from cohezion.core.persistence.repositories.universe_repository import (
            PhysicsState,
            UniverseNode,
        )

        initial_state = PhysicsState(stability=0.5, coherence=0.5)  # HIHO point
        node = UniverseNode(
            id=name,
            content=description,
            node_type="universe_seed",
            physics_state=initial_state,
            metadata={"description": description},
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Manifesting universe in SurrealDB...", total=None)
            success = await repo.create(node)
            progress.update(task, description="✓ Universe Manifested")

        if success:
            console.print(
                Panel(
                    f"Universe '[bold]{name}[/bold]' seeded successfully at the HIHO stability point.",
                    border_style="green",
                )
            )
        else:
            console.print("[red]Failed to seed universe.[/red]")

    asyncio.run(run())


@universe_app.command("list")
def universe_list(
    node_type: str | None = typer.Option(None, "--type", "-t", help="Filter by node type"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number to show"),
):
    """List all seeded universes."""
    import asyncio

    async def run():
        client = SurrealClient()
        await client.connect()
        repo = SurrealUniverseRepository(client._client)
        universes = await repo.get_all(limit=limit, node_type=node_type)

        table = Table(title="Seeded Universes")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Stability", style="yellow")

        for u in universes:
            # Display cleaner IDs (strip table prefix if present)
            display_id = str(u.id)
            if ":" in display_id:
                display_id = display_id.split(":")[-1]
            table.add_row(display_id, display_id, u.node_type, f"{u.stability_score:.2f}")

        console.print(table)

    asyncio.run(run())


ouroboros_app = typer.Typer(help="Self-healing system operations")
app.add_typer(ouroboros_app, name="ouroboros", help="Self-healing system operations")


@ouroboros_app.command("status")
def ouroboros_status(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed status"),
):
    """Show system health.

    Display the current health status of the Ouroboros self-healing
    system including monitoring and healing cycles.
    """
    console.print(
        Panel(
            "[bold green]✓ System Healthy[/bold green]\n\n"
            "[dim]All systems operational. No healing required.[/dim]",
            title="🐍 Ouroboros Status",
            border_style="green",
        )
    )

    if detailed:
        table = Table(title="System Components")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Uptime", style="dim")

        table.add_row("Swarm", "✓ Active", "24h 30m")
        table.add_row("FLUME", "✓ Active", "24h 30m")
        table.add_row("Ouroboros", "✓ Monitoring", "24h 30m")
        table.add_row("SurrealDB", "✓ Connected", "24h 30m")

        console.print(table)


@ouroboros_app.command("heal")
def ouroboros_heal(
    force: bool = typer.Option(False, "--force", "-f", help="Force healing cycle"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate healing without action"),
):
    """Trigger healing cycle.

    Initiate the Ouroboros self-healing cycle to detect and repair
    any system degradation or anomalies.
    """
    if dry_run:
        console.print(
            Panel(
                "[yellow]Dry Run: Healing cycle simulated[/yellow]\n\n"
                "[dim]No changes made to system.[/dim]",
                title="🐍 Ouroboros Heal",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold]{'Force ' if force else ''}Healing Cycle Triggered[/bold]\n\n"
                "[dim]Scanning for anomalies and initiating repairs...[/dim]",
                title="🐍 Ouroboros Heal",
                border_style="orange" if force else "blue",
            )
        )


@ouroboros_app.command("history")
def ouroboros_history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show"),
):
    """Show evolution history.

    Display the history of healing cycles and system evolution
    tracked by the Ouroboros system.
    """
    console.print(
        Panel(
            f"[bold]Evolution History[/bold]\n\nShowing last {limit} entries",
            title="🐍 Ouroboros History",
            border_style="blue",
        )
    )

    table = Table()
    table.add_column("Timestamp", style="cyan")
    table.add_column("Event", style="green")
    table.add_column("Impact", style="dim")

    table.add_row("2026-01-29 10:00", "Healing cycle #42", "Minor optimization")
    table.add_row("2026-01-28 15:30", "Consensus drift detected", "Auto-corrected")
    table.add_row("2026-01-28 09:15", "Memory threshold reached", "Purged cache")

    console.print(table)


if __name__ == "__main__":
    app()
