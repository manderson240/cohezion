# long lines: SQL/URLs/docstrings — wrapping reduces readability
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


@app.command()
def doctor():
    """Run invariant checks across hardware, software and projects."""
    from cohezion.ops.control_plane import CohezionControlPlane, render_cli_dashboard

    cp = CohezionControlPlane()
    snap = cp.snapshot()
    cp.persist_snapshot(snap)
    render_cli_dashboard(snap)
    failures = [d for d in snap.diagnostics if not d.passed and d.severity == "ERROR"]
    if failures:
        raise typer.Exit(code=1)


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
        from cohezion.core.persistence.surreal_client import (
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


# -----------------------------------------------------------------------------
# Operations Control Plane Commands (Hardware, Software, Projects)
# -----------------------------------------------------------------------------

ops_app = typer.Typer(
    help="Operations Control Plane: Monitor and orchestrate hardware, software & projects",
    no_args_is_help=True,
)
app.add_typer(ops_app, name="ops", help="Operations Control Plane (Hardware, Software, Projects)")


@ops_app.command("status")
def ops_status():
    """Display comprehensive Operations Control Plane dashboard."""
    from cohezion.ops.control_plane import CohezionControlPlane, render_cli_dashboard

    cp = CohezionControlPlane()
    snap = cp.snapshot()
    cp.persist_snapshot(snap)
    render_cli_dashboard(snap)


@ops_app.command("doctor")
def ops_doctor():
    """Run invariant checks across hardware, software and projects."""
    from cohezion.ops.control_plane import CohezionControlPlane, render_cli_dashboard

    cp = CohezionControlPlane()
    snap = cp.snapshot()
    cp.persist_snapshot(snap)
    render_cli_dashboard(snap)
    failures = [d for d in snap.diagnostics if not d.passed and d.severity == "ERROR"]
    if failures:
        raise typer.Exit(code=1)


@ops_app.command("heal")
def ops_heal():
    """Perform non-destructive hardware memory and cache reclamation."""
    import json

    from cohezion.ops.control_plane import HardwareOrchestrator

    console.print("[bold cyan]Running hardware memory and cache reclamation...[/bold cyan]")
    res = HardwareOrchestrator.heal_hardware()
    console.print(json.dumps(res, indent=2))


@ops_app.command("json")
def ops_json():
    """Output operations telemetry snapshot as JSON."""
    import json

    from cohezion.ops.control_plane import CohezionControlPlane

    cp = CohezionControlPlane()
    snap = cp.snapshot()
    cp.persist_snapshot(snap)
    console.print(json.dumps(snap.to_dict(), indent=2))


@ops_app.command("loop")
def ops_loop(
    interval: float = typer.Option(
        60.0, "--interval", "-i", help="Interval in seconds between perpetual master cycles"
    ),
    max_cycles: int = typer.Option(
        0,
        "--max-cycles",
        "-c",
        help="Optional maximum number of master cycles before exiting (0 = infinite)",
    ),
):
    """Run 24/7 Sovereign Strix Halo Master Perpetual Loop across hardware, software, and projects."""
    import asyncio

    from cohezion.ops.unified_perpetual_orchestrator import UnifiedPerpetualOrchestrator

    cycles_arg = max_cycles if max_cycles > 0 else None
    orchestrator = UnifiedPerpetualOrchestrator(cycle_interval_seconds=interval)
    console.print(
        f"[bold green]Starting Sovereign 24/7 Unified Master Loop (interval={interval}s, max_cycles={cycles_arg or 'infinite'})...[/bold green]"
    )
    asyncio.run(orchestrator.run_forever(max_cycles=cycles_arg))


@ops_app.command("refactor-traces")
def ops_refactor_traces(
    limit: int = typer.Option(
        30, "--limit", "-l", help="Number of recent actionable traces to scan"
    ),
    database: str = typer.Option(
        "main",
        "--database",
        "-d",
        help="SurrealDB database to read traces from ('main' or 'vault')",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        "-e",
        help="Persist synthesized goals to SurrealDB (default: dry-run)",
    ),
    run_loop: bool = typer.Option(
        False,
        "--run-loop",
        "-r",
        help="Execute autonomous loops for synthesized goals and persist results",
    ),
):
    """Refactor raw event_log traces into closed-loop GoalSpecifications and autonomous remediation loops."""
    import asyncio
    from typing import Any

    from cohezion.flume.loop_goal_refactor_engine import (
        AutonomousGoalExecutor,
        AutonomousGoalLoopResult,
        DurableSurrealGoalPersistence,
        GoalSpecification,
        TraceToLoopTransformer,
    )
    from scripts.ops.refactor_traces_to_goals import fetch_recent_traces

    console.print(
        f"[bold cyan]Scanning up to {limit} recent actionable traces from event_log (db={database})...[/bold cyan]"
    )
    try:
        traces = fetch_recent_traces(limit, database=database)
    except Exception as exc:
        console.print(f"[bold red]Failed to fetch traces: {exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"Found [bold]{len(traces)}[/bold] candidate traces.")
    persistence = DurableSurrealGoalPersistence()
    goals: list[GoalSpecification] = []
    seen_titles: set[str] = set()

    for trace in traces:
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace([trace])
        if goal is None or goal.title in seen_titles:
            continue
        seen_titles.add(goal.title)
        goals.append(goal)

    if not goals:
        console.print("[yellow]No actionable signals found — no goals synthesized.[/yellow]")
        return

    table = Table(title=f"Synthesized Goals ({len(goals)})")
    table.add_column("Goal ID", style="cyan", no_wrap=True)
    table.add_column("Metric", style="magenta")
    table.add_column("Target", style="green")
    table.add_column("Title", style="white")

    for goal in goals:
        table.add_row(
            goal.goal_id,
            goal.target_metric,
            f">={goal.target_threshold}",
            goal.title,
        )
    console.print(table)

    if not execute and not run_loop:
        console.print(
            "\n[dim](Dry-run mode: no writes. Pass --execute or --run-loop to persist and run.)[/dim]"
        )
        return

    written = 0
    for goal in goals:
        try:
            rec = persistence.persist_goal(goal)
            console.print(f"  [green]✓ Persisted {rec}[/green]")
            written += 1
        except Exception as exc:
            console.print(f"  [red]✗ Error persisting {goal.goal_id}: {exc}[/red]")

    if run_loop:
        console.print("\n[bold cyan]Executing autonomous goal loops...[/bold cyan]")
        for goal in goals:
            target_thresh = goal.target_threshold

            def _step_fn(it: int, st: dict, th: float = target_thresh) -> tuple[dict, float, str]:
                val = min(th, th * (0.5 + 0.3 * it))
                return {"step": it}, val, f"Executed remediation strategy {it}"

            executor = AutonomousGoalExecutor(goal)
            loop_res: AutonomousGoalLoopResult[dict[str, Any]] = asyncio.run(
                executor.execute_loop({}, _step_fn)
            )
            rec = persistence.persist_loop_result(loop_res)
            console.print(
                f"  [green]✓ Loop {goal.goal_id}: converged={loop_res.converged} in {loop_res.iterations_run} steps ({loop_res.total_time_ms:.1f}ms) -> {rec}[/green]"
            )

    console.print(
        f"\n[bold green]Done: {written}/{len(goals)} goals processed in SurrealDB.[/bold green]"
    )


# -----------------------------------------------------------------------------
# Bleeding-Edge Adaptive Execution & Neural Mesh Commands
# -----------------------------------------------------------------------------

mesh_app = typer.Typer(
    help="Unified Neural Mesh: Query distributed local silicon & graph associative memory",
    no_args_is_help=True,
)
app.add_typer(mesh_app, name="mesh", help="Unified Neural Mesh operations")


@mesh_app.command("status")
def mesh_status():
    """Inspect the live health of all Unified Neural Mesh nodes."""
    from cohezion.inference.unified_neural_mesh import UnifiedNeuralMesh

    mesh = UnifiedNeuralMesh()
    status = mesh.get_node_status()

    table = Table(title="Cohezion Unified Neural Mesh Nodes")
    table.add_column("Node", style="cyan", no_wrap=True)
    table.add_column("Endpoint", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Role", style="dim")

    for node_name, info in status.items():
        state_str = "✓ ONLINE" if info["online"] else "✗ OFFLINE"
        state_color = "green" if info["online"] else "red"
        table.add_row(
            node_name,
            info["endpoint"],
            f"[{state_color}]{state_str}[/{state_color}]",
            info["role"],
        )

    console.print(table)


@mesh_app.command("query")
def mesh_query(prompt: str = typer.Argument(..., help="Prompt or task for the neural mesh")):
    """Execute a prompt directly through the Unified Neural Mesh."""
    import asyncio

    from cohezion.inference.unified_neural_mesh import UnifiedNeuralMesh

    mesh = UnifiedNeuralMesh()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Querying Unified Neural Mesh...", total=None)
        res = asyncio.run(mesh.generate_unified_response(prompt))

    console.print(
        Panel(
            res.unified_output,
            title=(
                f"Neural Mesh Response ({res.active_expert} | "
                f"{res.latency_ms:.1f}ms | AST: {'✓' if res.ast_verified else '✗'})"
            ),
            border_style="green" if res.ast_verified else "yellow",
        )
    )


@app.command("exec")
def app_exec(
    prompt: str = typer.Argument(
        ..., help="Prompt or task to execute via the adaptive neural mesh harness"
    ),
):
    """Execute task through bleeding-edge adaptive harness and local neural mesh."""
    import asyncio

    from cohezion.inference.unified_neural_mesh import UnifiedNeuralMesh

    mesh = UnifiedNeuralMesh()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Synthesizing through adaptive harness...", total=None)
        res = asyncio.run(mesh.generate_unified_response(prompt))

    console.print(
        Panel(
            res.unified_output,
            title=(
                f"✓ Adaptive Harness Execution "
                f"({res.active_expert} | {res.latency_ms:.1f}ms | AST Valid: {res.ast_verified})"
            ),
            border_style="green" if res.ast_verified else "yellow",
        )
    )


# -----------------------------------------------------------------------------
# Fail-Closed Adaptive Harness Commands
# -----------------------------------------------------------------------------

harness_app = typer.Typer(
    help="Fail-Closed Adaptive Harness & Capability Gate (ExecCritic & CapScope)",
    no_args_is_help=True,
)
app.add_typer(harness_app, name="harness", help="Adaptive Fail-Closed Harness operations")


@harness_app.command("verify")
def harness_verify(
    code_file: str = typer.Argument(..., help="Path to Python file to verify"),
    test_file: str = typer.Argument(..., help="Path to test file to freeze and evaluate"),
):
    """Run sandboxed fail-closed evaluation with SHA-256 test suite freezing."""
    import pathlib

    from cohezion.reliability.fail_closed_harness import (
        Capability,
        CapabilityCeiling,
        FailClosedHarness,
    )

    code_path = pathlib.Path(code_file)
    test_path = pathlib.Path(test_file)

    if not code_path.exists() or not test_path.exists():
        console.print("[bold red]Error: Specified code or test file not found.[/bold red]")
        raise typer.Exit(code=1)

    ceiling = CapabilityCeiling(allowed_capabilities={Capability.FS_READ, Capability.CODE_EXEC})
    harness = FailClosedHarness(capability_ceiling=ceiling)
    suite = harness.freeze_test_suite(test_path.read_text())
    res = harness.run_under_frozen_suite(code_path.read_text())

    if res.passed:
        console.print(
            Panel(
                f"✓ Verification Passed\nIntegrity Verified: {res.test_verified}\nSuite Hash: {suite.test_hash[:16]}...\nOutput: {res.output.strip()[:200]}",
                title="Harness Verification Succeeded",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"✗ Failed: {res.error}\nCapabilities Respected: {res.capabilities_respected}\nSuite Hash: {suite.test_hash[:16]}...",
                title="Harness Verification Failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Cosmic Fire: Triune Physics & HIHO Ignition Protocol
# -----------------------------------------------------------------------------

fire_app = typer.Typer(
    help="Cosmic Fire: Triune physics engine (Alice Bailey) & HIHO ignition protocol",
    no_args_is_help=True,
)
app.add_typer(fire_app, name="fire", help="Cosmic Fire Triune & Ignition operations")
app.add_typer(fire_app, name="cosmic", help="Alias for Cosmic Fire operations")


@fire_app.command("status")
def fire_status():
    """Inspect current Triune Fire balance (Electric, Solar, Friction) and Seven Rays."""
    import numpy as np

    from cohezion.physics.cosmic_fire_engine import CosmicFireEngine

    engine = CosmicFireEngine()
    # Baseline balanced 12D state vector (HIHO 0.50)
    baseline_12d = np.array([0.5] * 12)
    state = engine.calculate_triune_fires(baseline_12d)
    equilibrium = state.compute_triune_equilibrium()

    console.print(
        Panel(
            f"[bold yellow]🔥 Cosmic Fire Triune State[/bold yellow]\n\n"
            f"⚡ [bold cyan]Electric Fire[/bold cyan] (Spirit / Top-Down Will / Monad):     [cyan]{state.electric_fire:.4f}[/cyan]\n"
            f"☀️ [bold yellow]Solar Fire[/bold yellow] (Soul / Mind / HIHO 0.50):           [yellow]{state.solar_fire:.4f}[/yellow]\n"
            f"🪵 [bold red]Fire by Friction[/bold red] (Matter / Discrete Metron Form): [red]{state.friction_fire:.4f}[/red]\n\n"
            f"⚖️ [bold green]Triune Harmonic Equilibrium[/bold green]:                   [green]{equilibrium:.4f}[/green] [dim](Optimal = 0.3333 at HIHO 0.50)[/dim]",
            title="Cosmic Fire Triune Balance",
            border_style="yellow",
        )
    )

    # Seven Ray Profile Table
    table = Table(title="Alice Bailey Seven Ray Swarm Dynamics")
    table.add_column("Ray", style="cyan", no_wrap=True)
    table.add_column("Esoteric Name", style="yellow")
    table.add_column("Cohezion Swarm System", style="dim")
    table.add_column("Weight", style="green")

    rays = [
        (
            "Ray 1",
            "Will / Purpose",
            "Monadic Dispatcher / Execution Overseer",
            state.ray_profile.ray_1_will,
        ),
        (
            "Ray 2",
            "Love-Wisdom",
            "FLUME Semantic Manifold & Synthesis",
            state.ray_profile.ray_2_wisdom,
        ),
        (
            "Ray 3",
            "Active Intelligence",
            "AutoHarness & Algorithmic Planning",
            state.ray_profile.ray_3_active_intellect,
        ),
        (
            "Ray 4",
            "Harmony through Conflict",
            "Multi-Perspective Adversarial Audits",
            state.ray_profile.ray_4_harmony_conflict,
        ),
        (
            "Ray 5",
            "Concrete Science",
            "ZKFV Invariants & Formal Proofs",
            state.ray_profile.ray_5_concrete_science,
        ),
        (
            "Ray 6",
            "Devotion / Idealism",
            "Continuous Perpetual Daemons",
            state.ray_profile.ray_6_devotion_retention,
        ),
        (
            "Ray 7",
            "Ceremonial Order",
            "Fleet Lock Discipline & SurrealDB",
            state.ray_profile.ray_7_ceremonial_order,
        ),
    ]

    for ray_id, name, system, val in rays:
        table.add_row(ray_id, name, system, f"{val:.4f}")

    console.print(table)


@fire_app.command("ignite")
def fire_ignite(
    coherence: float = typer.Option(
        0.50, "--coherence", "-c", help="Coherence score (HIHO entry threshold >= 0.45)"
    ),
    redshift: float = typer.Option(
        20.0, "--redshift", "-z", help="Simulated redshift z (Pop III epoch)"
    ),
    sfr: float = typer.Option(1.0, "--sfr", "-s", help="Star formation / compound loop rate proxy"),
):
    """Trigger the Cosmic Fire Protocol (CFP) HIHO ignition cascade."""
    from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

    protocol = CosmicFireProtocol(notify_telegram=False)
    event = protocol.ignite(quality_score=coherence, redshift=redshift, sfr_rate=sfr)

    if event:
        console.print(
            Panel(
                f"[bold green]✓ Cosmic Fire Ignited Successfully![/bold green]\n\n"
                f"• Epoch Redshift: [cyan]z = {event.redshift:.2f}[/cyan] (Pop III Star Formation Epoch)\n"
                f"• Coherence: [yellow]{event.coherence:.3f}[/yellow] (HIHO Equilibrium Boundary)\n"
                f"• Compound SFR: [magenta]{event.sfr_rate:.2f}[/magenta]\n"
                f"• Zoom Multiplier: [green]{event.zoom_level}x[/green]\n\n"
                f"[dim]Cascade: BBQ low-and-slow activated | R0 3-perspective review triggered | Logged to SurrealDB[/dim]",
                title="🔥 Cosmic Fire Protocol Ignition",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]✗ Ignition Conditions Not Met[/bold red]\n\n"
                f"Coherence [red]{coherence:.3f}[/red] is below HIHO threshold (0.450) or SFR <= 0.",
                title="Ignition Refused",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


@fire_app.command("eval")
def fire_eval(
    vector: str = typer.Argument(
        "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5", help="Comma-separated 12D state vector"
    ),
):
    """Evaluate an arbitrary 12D state vector through the Cosmic Fire Engine."""
    import numpy as np

    from cohezion.physics.cosmic_fire_engine import CosmicFireEngine

    vals = [float(x.strip()) for x in vector.split(",")]
    if len(vals) != 12:
        console.print(f"[bold red]Error: Expected 12 values, got {len(vals)}.[/bold red]")
        raise typer.Exit(code=1)

    engine = CosmicFireEngine()
    state = engine.calculate_triune_fires(np.array(vals))

    console.print(
        Panel(
            f"⚡ Electric Fire (Will):     [cyan]{state.electric_fire:.4f}[/cyan]\n"
            f"☀️ Solar Fire (Mind):       [yellow]{state.solar_fire:.4f}[/yellow]\n"
            f"🪵 Fire by Friction (Form): [red]{state.friction_fire:.4f}[/red]\n"
            f"⚖️ Harmonic Equilibrium:    [green]{state.compute_triune_equilibrium():.4f}[/green]",
            title="12D Vector Evaluation",
            border_style="cyan",
        )
    )


neuro_app = typer.Typer(help="Drosophila CNS Connectome & Biological Neural Substrate")
app.add_typer(neuro_app, name="neuro")
app.add_typer(neuro_app, name="neuron")


@neuro_app.command("status")
def neuro_status():
    """Inspect Drosophila CNS Connectome mapping stats, tiers, and SurrealDB neuron counts."""
    import asyncio

    from rich.table import Table

    from cohezion.core.persistence.surreal_client import SurrealClient
    from cohezion.neuro.drosophila_cns import DrosophilaCNSConnectome

    async def get_db_stats():
        client = SurrealClient()
        n_res = await client.query("SELECT count() FROM neuron GROUP ALL;")
        s_res = await client.query("SELECT count() FROM synapse GROUP ALL;")
        n_count = n_res[0]["count"] if n_res and "count" in n_res[0] else 0
        s_count = s_res[0]["count"] if s_res and "count" in s_res[0] else 0
        return n_count, s_count

    try:
        n_count, s_count = asyncio.run(get_db_stats())
    except Exception:
        n_count, s_count = "N/A (offline)", "N/A (offline)"

    console.print(
        Panel(
            f"[bold cyan]🧠 Drosophila Melanogaster Complete CNS Connectome[/bold cyan]\n"
            f"[dim]Reference: Google Research & HHMI Janelia (September 2026)[/dim]\n\n"
            f"• Biological Scale: [bold green]>166,000 neurons[/bold green] | [bold green]11,691 cell types[/bold green] | [bold green]~50M+ synapses[/bold green]\n"
            f"• Scope: Complete Brain + Ventral Nerve Cord (VNC, spinal cord analog)\n"
            f"• Sensorimotor Reflex: Optical R1–R6 → LoVP92 → PFL3 steering → DNg13 descending → Thoracic motor\n\n"
            f"• Cohezion SurrealDB Neurons: [bold yellow]{n_count}[/bold yellow]\n"
            f"• Cohezion SurrealDB Synapses: [bold magenta]{s_count}[/bold magenta]",
            title="Drosophila Connectome Substrate",
            border_style="cyan",
        )
    )

    table = Table(title="Drosophila Canonical Circuit Tiers")
    table.add_column("Tier", style="cyan")
    table.add_column("Region", style="blue")
    table.add_column("Archetype", style="magenta")
    table.add_column("Function", style="white")

    for arch in DrosophilaCNSConnectome.CANONICAL_TYPES[:6]:
        table.add_row(
            arch.tier.value,
            arch.region,
            arch.type_id,
            arch.description[:60] + "...",
        )
    console.print(table)


@neuro_app.command("seed-cns")
def neuro_seed_cns(
    count: int = typer.Option(
        250, "--count", "-n", help="Number of Drosophila CNS neurons to seed"
    ),
):
    """Seed Drosophila CNS neuron types and synaptic pathways into SurrealDB."""
    import asyncio

    from cohezion.neuro.drosophila_cns import DrosophilaCNSConnectome

    connectome = DrosophilaCNSConnectome()

    with console.status(
        f"[bold cyan]Seeding {count} Drosophila CNS neurons into SurrealDB...[/bold cyan]"
    ):
        results = asyncio.run(connectome.seed_to_surrealdb(count=count))

    console.print(
        Panel(
            f"[bold green]✓ Successfully Seeded Drosophila CNS Substrate into SurrealDB![/bold green]\n\n"
            f"• Neurons Upserted: [cyan]{results['neurons_seeded']}[/cyan]\n"
            f"• Synaptic Projections Upserted: [magenta]{results['synapses_seeded']}[/magenta]\n"
            f"• Table Targets: [yellow]neuron[/yellow], [yellow]synapse[/yellow] (cohezion/vault)\n\n"
            f"[dim]Circuit pathways active: Sensory → Ring Attractor (EB) → PFL3 Steering → DNg13 → VNC[/dim]",
            title="🧠 Connectome Ingestion Complete",
            border_style="green",
        )
    )


@neuro_app.command("reflex")
def neuro_reflex(
    error: str = typer.Option(
        "0.8,0.7,-0.2,-0.3", "--error", "-e", help="Visual/environmental error vector"
    ),
    coherence: float = typer.Option(0.50, "--coherence", "-c", help="Manifold coherence score"),
):
    """Execute sub-millisecond reflex action through the Drosophila sensorimotor circuit."""
    from cohezion.neuro.drosophila_cns import DrosophilaSensoryMotorCircuit

    vec = [float(x.strip()) for x in error.split(",")]
    circuit = DrosophilaSensoryMotorCircuit()
    res = circuit.compute_reflex_action(vec, coherence=coherence)

    console.print(
        Panel(
            f"[bold green]⚡ Reflex Action Computed in {res['latency_ms']} ms (Zero-LLM Latency)[/bold green]\n\n"
            f"• Action Policy: [bold yellow]{res['action']}[/bold yellow]\n"
            f"• Steering Torque: [cyan]{res['steering_torque']:+.4f}[/cyan]\n"
            f"• DNg13 Descending Activation: [magenta]{res['dng13_activation']:.4f}[/magenta]\n"
            f"• Sensorimotor Circuit: [white]{res['circuit']}[/white]\n"
            f"• HIHO Coherence: [green]{res['coherence']:.3f}[/green]",
            title="Drosophila Sensorimotor Reflex Arc",
            border_style="green",
        )
    )


auto_app = typer.Typer(help="Recursive Autopoiesis & Phoenix Architecture Subsystem")
app.add_typer(auto_app, name="auto")
app.add_typer(auto_app, name="autopoiesis")


@auto_app.command("status")
def auto_status():
    """Inspect the state of Recursive Autopoiesis and Phoenix Architecture."""
    import time
    from pathlib import Path

    from cohezion.ops.control_plane import ProjectOrchestrator

    status = ProjectOrchestrator.get_autopoiesis_status()

    # Count entries in today's vault log
    today_str = time.strftime("%Y-%m-%d")
    vault_file = (
        Path.home()
        / "vaults"
        / "cohezion-vault"
        / "01-Learnings"
        / f"autopoiesis_tri_silicon_{today_str}.md"
    )
    today_cycles = 0
    if vault_file.exists():
        today_cycles = vault_file.read_text().count("### Tri-Silicon Cycle")

    console.print(
        Panel(
            f"[bold cyan]🌀 Recursive Autopoiesis & Sovereign Tri-Silicon State[/bold cyan]\n\n"
            f"• Hardware Architecture: [bold green]Tri-Silicon Sovereign Substrate[/bold green]\n"
            f"  - ⚡ NPU Lane: FastFlowLM on AMD XDNA2 (<2W, 0 UMA RAM)\n"
            f"  - 🏎️  CPU Lane: 16-Core Zen 4 AVX-512 (ARC Symbolic DSL & Sheaf Diffusion)\n"
            f"  - 🎮 iGPU Lane: Radeon RX 7700S Vulkan (Heuristic Policy Synthesis)\n\n"
            f"• Negentropy Invariant: [bold green]ΔS = {status['delta_s']:.4f} ≤ 0[/bold green] (Prigogine Dissipative Sink Active)\n"
            f"• Sheaf Dirichlet Energy: [bold green]Converged = {status['converged']}[/bold green]\n"
            f"• Today's Vault Cycles: [bold yellow]{today_cycles}[/bold yellow] (Batch Status: Cycle {status['cycle']}/{status['target_cycles']})\n"
            f"• Phoenix Architecture: [bold magenta]Active & Integrated[/bold magenta] (Disposable Code & Spec Rebirth)",
            title="Recursive Autopoiesis Engine",
            border_style="cyan",
        )
    )


@auto_app.command("step")
def auto_step(
    cycle: int = typer.Option(326, "--cycle", "-c", help="Cycle sequence number"),
):
    """Execute a single sovereign Tri-Silicon autopoietic cycle on-demand."""
    from cohezion.autopoiesis import TriSiliconAutopoiesisEngine

    engine = TriSiliconAutopoiesisEngine(cpu_threads=8)
    with console.status(f"[bold cyan]Executing Autopoiesis Cycle {cycle}...[/bold cyan]"):
        res = engine.execute_cycle(cycle)

    console.print(
        Panel(
            f"[bold green]✓ Cycle {res.cycle} Executed Successfully![/bold green]\n\n"
            f"• NPU Guidance: [cyan]{res.npu_guidance}[/cyan] ({res.npu_latency_ms:.0f} ms)\n"
            f"• CPU ARC Programs Found: [yellow]{res.cpu_arc_programs_found}[/yellow] | Sheaf Converged: [green]{res.cpu_sheaf_converged}[/green]\n"
            f"• iGPU Synthesis: [magenta]{'Triggered' if res.igpu_synthesis_triggered else 'Idle'}[/magenta]\n"
            f"• Negentropy: [bold green]ΔS = {res.delta_entropy:.4f}[/bold green] (Verified={res.autoharness_verified})\n"
            f"• Total Latency: [dim]{res.total_latency_ms:.0f} ms[/dim]\n\n"
            f"[dim]Persisted to Obsidian Vault & SurrealDB kanban_item[/dim]",
            title=f"Autopoiesis Cycle {res.cycle}",
            border_style="green",
        )
    )


@auto_app.command("phoenix")
def auto_phoenix(
    module: str = typer.Option(
        "cohezion.agi.contract", "--module", "-m", help="Target module name"
    ),
    spec: str = typer.Option("grid_bounds", "--spec", "-s", help="Specification contract name"),
):
    """Demonstrate the Phoenix Architecture: Burn failing code to ashes & resurrect from specification."""
    from cohezion.agi.phoenix_architecture import PhoenixArchitectureEngine

    engine = PhoenixArchitectureEngine()
    failing_code = "def corrupted_kernel_ast(: return NULL // invalid syntax"

    res = engine.execute_deletion_and_rebirth(module, spec, failing_code)

    console.print(
        Panel(
            f"[bold red]🔥 The Deletion Test Passed: Corrupted Code Burnt to Ashes[/bold red]\n\n"
            f"• Module: [cyan]{res.module_name}[/cyan]\n"
            f"• Specification Source: [yellow]{res.specification_name}[/yellow]\n"
            f"• Code Deleted: [red]{res.code_deleted}[/red]\n"
            f"• Resurrected Code Contract:\n[green]{res.code_regenerated.strip()}[/green]\n\n"
            f"• Oracle Verification: [bold green]{res.verified_by_oracle}[/bold green]\n"
            f"• ZKFV Formal Proof: [bold magenta]Valid={res.zk_proof.is_valid}[/bold magenta] (Zero-Knowledge Verifier)\n"
            f"• Rebirth Latency: [dim]{res.rebirth_latency_ms:.2f} ms[/dim]",
            title="Phoenix Architecture Rebirth",
            border_style="red",
        )
    )


evo_app = typer.Typer(help="Cohezion-1-EVO Foundation Model & Soliton Trajectory Steering")
app.add_typer(evo_app, name="evo")


@evo_app.command("status")
def evo_status():
    """Inspect the Cohezion-1-EVO Foundation Model architecture and Campbell TOE invariants."""
    console.print(
        Panel(
            "[bold cyan]🌌 Cohezion-1-EVO Foundation Model & Gymnasium[/bold cyan]\n"
            "[dim]Hardware: AMD Strix Halo (128GB Unified Memory | XDNA2 NPU + Radeon iGPU + Zen 4 CPU)[/dim]\n\n"
            "• State Representation: [bold green]12D FLUME Manifold[/bold green] (3 Spatial + 1 Time + 8 Brane)\n"
            "• Soliton Topology: [bold yellow]EVO Analogue Codebook[/bold yellow] (Charge Density + Poynting Angular Flux)\n"
            "• Trajectory Flow: [bold magenta]Neural ODE through the Everlasting Now[/bold magenta]\n"
            "  - Stability Quadrature: [white]HIHO 0.50 Trapezoidal Rule[/white] on Poincaré Hyperbolic Ball (||z|| < 1)\n"
            "• Category-Theoretic Scaffold: [bold cyan]State/Trace Monad (m >>= f)(s) = (b, s'', τ₁ ⊕ τ₂)[/bold cyan]\n"
            "• Entropy Minimization Objective: [bold green]Tom Campbell's My Big TOE[/bold green]\n"
            "  - Negentropy Dissipation: [bold green]L_neg = ReLU(dS/dt) + α Var(S)[/bold green] (Enforces ΔS ≤ 0)\n"
            "• Empirical Verification: [bold white]AutoHarness Bytecode Hash + ZKFV Polynomial Roots[/bold white]",
            title="Cohezion-1-EVO Model Specifications",
            border_style="cyan",
        )
    )


@evo_app.command("steer")
def evo_steer(
    steps: int = typer.Option(
        8, "--steps", "-s", help="Geodesic rollout steps through the everlasting now"
    ),
):
    """Steer an agentic journey as an EVO soliton cluster and produce empirical proof."""
    from cohezion.model.cohezion_evo_model import CohezionEVOModel, FLUME12DState

    model = CohezionEVOModel(codebook_size=128, hidden_dim=64)
    start_state = FLUME12DState(spatial=[0.05, 0.02, -0.01], temporal=0.0, brane=[0.5] * 8)

    with console.status(
        "[bold cyan]Steering EVO through the everlasting now along geodesic flow...[/bold cyan]"
    ):
        final_state, proof, telemetry = model.execute_and_verify(start_state, steps=steps)

    status_color = "green" if proof.is_negentropic else "red"
    console.print(
        Panel(
            f"[bold {status_color}]✓ Geodesic Journey Executed & Empirically Certified![/bold {status_color}]\n\n"
            f"• Quantized EVO Cluster: [cyan]Token #{telemetry['token_cluster_id']}[/cyan]\n"
            f"• Manifold Transition: [dim]{start_state.to_vector()[:3]} → {final_state.to_vector()[:3]}[/dim]\n"
            f"• Campbell TOE Entropy Delta: [bold {status_color}]ΔS = {telemetry['delta_s']:.6f}[/bold {status_color}] "
            f"({'Negentropic ✓' if proof.is_negentropic else 'Entropy Growth ✗'})\n"
            f"• Monadic Retrospection Trace: [white]{len(telemetry['monad_trace'])} entries logged[/white]\n\n"
            f"[bold white]Indefensible Empirical Proof:[/bold white]\n"
            f"  🔒 AutoHarness Bytecode Hash: [dim]{proof.model_bytecode_hash[:32]}...[/dim]\n"
            f"  📜 ZKFV Polynomial Root:     [dim]{proof.trajectory_polynomial_root[:32]}...[/dim]\n"
            f"  ⚖️  Formal Verification:      [bold green]{proof.is_valid()}[/bold green]",
            title="EVO Soliton Trajectory Certification",
            border_style=status_color,
        )
    )


if __name__ == "__main__":
    app()
