"""CLI for AgentVerse Compound Benchmark Loop.

Usage:
    python -m cohezion.integrations.agentverse.cli run \\
        --tasks tasks.json \\
        --max-iterations 5 \\
        --vault-url http://localhost:8360
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from cohezion.core.mcp_client import MCPClient, MCPConfig


logger = logging.getLogger(__name__)


class MockExecutorResult:
    """Mock result object."""

    def __init__(
        self,
        success: bool = True,
        output: str = "mock output",
        coherence: float = 0.5,
    ):
        self.success = success
        self.output = output
        self.metrics = {"coherence": coherence, "alignment": 0.7}
        self.duration_seconds = 1.0


class MockExecutor:
    """Mock executor for CLI demo mode."""

    def __init__(self):
        self.call_count = 0

    def execute_task(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str = "generate",
    ):
        """Mock execute_task that returns simulated results."""
        self.call_count += 1
        coherence = 0.5 + (self.call_count * 0.02)
        return MockExecutorResult(
            success=True,
            output=f"Mock output for: {task_description[:30]}...",
            coherence=min(coherence, 0.9),
        )

    def get_experience_guidance(self, query: str) -> dict:
        """Mock get_experience_guidance."""
        return {}


@dataclass
class CLIConfig:
    """Configuration for CLI."""

    vault_url: str = "http://localhost:8360"
    vault_api_key: str = os.getenv("CLOUD_VAULT_API_KEY", "")
    max_iterations: int = 5
    weak_skill_threshold: float = 0.4
    improvement_threshold: float = 0.1
    output_format: str = "text"


def load_tasks_from_file(path: str) -> list[dict[str, str]]:
    """Load benchmark tasks from JSON file.

    Parameters
    ----------
    path : str
        Path to JSON file containing tasks

    Returns
    -------
    list[dict[str, str]]
        List of task dicts with 'task' and 'skill' keys
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "tasks" in data:
        return data["tasks"]
    else:
        raise ValueError(f"Invalid task file format: {path}")


def create_mcp_client(config: CLIConfig) -> MCPClient:
    """Create and connect MCP client.

    Parameters
    ----------
    config : CLIConfig
        CLI configuration

    Returns
    -------
    MCPClient
        Connected MCP client
    """
    mcp_config = MCPConfig(
        server_url=config.vault_url,
        api_key=config.vault_api_key,
    )
    client = MCPClient(mcp_config)
    try:
        client.connect()
    except Exception as e:
        logger.warning("Could not connect to vault: %s", e)
    return client


async def run_compound_loop(
    tasks: list[dict[str, str]],
    config: CLIConfig,
) -> dict[str, Any]:
    """Run compound benchmark loop with given tasks.

    Parameters
    ----------
    tasks : list[dict[str, str]]
        List of tasks with 'task' and 'skill' keys
    config : CLIConfig
        CLI configuration

    Returns
    -------
    dict[str, Any]
        Loop result as dict
    """
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.integrations.agentverse import (
        AgentVerseBenchmarkRunner,
        CompoundBenchmarkLoop,
        LoopConfig,
    )

    mcp_client = create_mcp_client(config)

    try:
        runner = AgentVerseBenchmarkRunner(
            executor=MockExecutor(),
            mcp_client=mcp_client,
        )
        refiner = SkillRefiner(mcp_client=mcp_client)

        loop_config = LoopConfig(
            max_iterations=config.max_iterations,
            weak_skill_threshold=config.weak_skill_threshold,
            improvement_threshold=config.improvement_threshold,
        )

        loop = CompoundBenchmarkLoop(
            runner=runner,
            refiner=refiner,
            config=loop_config,
        )

        result = await loop.run_loop(tasks)

        return {
            "total_iterations": result.total_iterations,
            "final_coherence": result.final_coherence,
            "initial_coherence": result.initial_coherence,
            "total_improvement": result.total_improvement,
            "converged": result.converged,
            "refined_skills": list(result.refined_skills),
            "iterations": [
                {
                    "iteration": it.iteration,
                    "coherence_before": it.coherence_before,
                    "coherence_after": it.coherence_after,
                    "improvement": it.improvement,
                    "weak_skills": it.weak_skills,
                    "refined_skills": it.refined_skills,
                    "converged": it.converged,
                }
                for it in result.iterations
            ],
        }
    finally:
        mcp_client.close()


def format_result_text(result: dict[str, Any]) -> str:
    """Format result as human-readable text.

    Parameters
    ----------
    result : dict[str, Any]
        Loop result

    Returns
    -------
    str
        Formatted text
    """
    lines = [
        "=== Compound Benchmark Loop Results ===",
        f"Total Iterations: {result['total_iterations']}",
        f"Initial Coherence: {result['initial_coherence']:.3f}",
        f"Final Coherence: {result['final_coherence']:.3f}",
        f"Improvement: {result['total_improvement']:+.3f}",
        f"Converged: {result['converged']}",
        f"Refined Skills: {', '.join(result['refined_skills']) or 'none'}",
        "",
        "Per-Iteration Details:",
    ]

    for it in result["iterations"]:
        lines.append(
            f"  Iter {it['iteration']}: "
            f"coherence {it['coherence_before']:.3f} -> {it['coherence_after']:.3f} "
            f"(Δ {it['improvement']:+.3f}) "
            f"weak={it['weak_skills']} refined={it['refined_skills']}"
        )

    return "\n".join(lines)


def format_result_json(result: dict[str, Any]) -> str:
    """Format result as JSON.

    Parameters
    ----------
    result : dict[str, Any]
        Loop result

    Returns
    -------
    str
        JSON string
    """
    return json.dumps(result, indent=2)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None:
    """AgentVerse Compound Benchmark Loop CLI."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option(
    "--tasks",
    "-t",
    required=True,
    type=click.Path(exists=True),
    help="Path to tasks JSON file",
)
@click.option(
    "--max-iterations",
    "-i",
    default=5,
    type=int,
    help="Maximum loop iterations (default: 5)",
)
@click.option(
    "--vault-url",
    "-u",
    default="http://localhost:8360",
    help="Vault MCP server URL",
)
@click.option(
    "--vault-api-key",
    "-k",
    default="",
    help="Vault API key",
)
@click.option(
    "--weak-threshold",
    "-w",
    default=0.4,
    type=float,
    help="Weak skill coherence threshold (default: 0.4)",
)
@click.option(
    "--improvement-threshold",
    "-d",
    default=0.1,
    type=float,
    help="Improvement threshold for convergence (default: 0.1)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def run(
    tasks: str,
    max_iterations: int,
    vault_url: str,
    vault_api_key: str,
    weak_threshold: float,
    improvement_threshold: float,
    format: str,
) -> None:
    """Run compound benchmark loop on tasks."""
    config = CLIConfig(
        vault_url=vault_url,
        vault_api_key=vault_api_key,
        max_iterations=max_iterations,
        weak_skill_threshold=weak_threshold,
        improvement_threshold=improvement_threshold,
        output_format=format,
    )

    try:
        task_list = load_tasks_from_file(tasks)
        logger.info("Loaded %d tasks from %s", len(task_list), tasks)

        result = asyncio.run(run_compound_loop(task_list, config))

        if format == "json":
            print(format_result_json(result))
        else:
            print(format_result_text(result))

        sys.exit(0 if result["converged"] else 1)

    except Exception as e:
        logger.error("Error running compound loop: %s", e)
        if logging.getLogger().level == logging.DEBUG:
            raise
        sys.exit(1)


@cli.command()
@click.option(
    "--tasks-dir",
    "-d",
    default=None,
    type=click.Path(exists=True),
    help="Directory containing task JSON files",
)
def list_tasks(tasks_dir: str | None) -> None:
    """List available benchmark task suites."""
    base = Path(tasks_dir) if tasks_dir else Path(__file__).parent / "tasks"

    if not base.exists():
        print("No tasks directory found")
        return

    for task_file in sorted(base.glob("*.json")):
        with open(task_file) as f:
            data = json.load(f)
        task_count = len(data) if isinstance(data, list) else len(data.get("tasks", []))
        print(f"{task_file.stem}: {task_count} tasks")


@cli.command()
@click.option(
    "--skill",
    "-s",
    required=True,
    help="Skill name to check",
)
@click.option(
    "--vault-url",
    "-u",
    default="http://localhost:8360",
    help="Vault MCP server URL",
)
@click.option(
    "--vault-api-key",
    "-k",
    default="",
    help="Vault API key",
)
@click.option(
    "--limit",
    "-l",
    default=10,
    type=int,
    help="Number of historical runs to show",
)
def history(skill: str, vault_url: str, vault_api_key: str, limit: int) -> None:
    """Show trajectory history for a skill."""
    config = CLIConfig(vault_url=vault_url, vault_api_key=vault_api_key)
    client = create_mcp_client(config)

    try:
        vault_path = "/vault/benchmarks/"
        paths = client.vault_list(directory=vault_path, recursive=False)

        skill_runs = []
        for path in paths[:limit]:
            if not path.endswith(".json"):
                continue
            try:
                content = client.vault_read(path)
                data = json.loads(content)
                if any(skill in r.get("skill", "") for r in data.get("results", [])):
                    skill_runs.append(data)
            except Exception as e:
                logger.debug("Failed to read vault file %s: %s", path, e)
                continue

        if not skill_runs:
            print(f"No historical runs found for skill: {skill}")
            return

        print(f"=== Historical runs for {skill} ===")
        for i, run in enumerate(skill_runs):
            avg_coherence = sum(r.get("coherence", 0) for r in run.get("results", [])) / max(
                len(run.get("results", [])), 1
            )
            print(f"  Run {i + 1}: avg_coherence={avg_coherence:.3f}")

    finally:
        client.close()


if __name__ == "__main__":
    cli()


@cli.command()
@click.option(
    "--skills-dir",
    "-s",
    default="src/cohezion/skills",
    help="Directory containing PRIME skill files",
)
@click.option(
    "--vault-url",
    "-u",
    default="http://localhost:8360",
    help="Vault MCP server URL",
)
@click.option(
    "--vault-api-key",
    "-k",
    default="",
    help="Vault API key",
)
@click.option(
    "--model",
    "-m",
    default="qwen3.5:cloud",
    help="Ollama cloud model for execution",
)
@click.option(
    "--weak-threshold",
    "-w",
    default=0.4,
    type=float,
    help="Coherence threshold for weak skills (default: 0.4)",
)
@click.option(
    "--max-refinements",
    "-r",
    default=2,
    type=int,
    help="Maximum refinements per skill (default: 2)",
)
@click.option(
    "--limit",
    "-l",
    default=10,
    type=int,
    help="Limit number of skills to benchmark (default: 10)",
)
def autonomous(
    skills_dir: str,
    vault_url: str,
    vault_api_key: str,
    model: str,
    weak_threshold: float,
    max_refinements: int,
    limit: int,
) -> None:
    """Run autonomous compound loop with LLM-based execution.

    Auto-discovers skills, benchmarks via Ollama cloud,
    and refines weak skills automatically.
    """
    from pathlib import Path

    from cohezion.core.mcp_client import MCPConfig
    from cohezion.integrations.agentverse.autonomous_loop import AutonomousCompoundLoop
    from cohezion.integrations.agentverse.llm_executor import LLMExecutor

    config = MCPConfig(server_url=vault_url, api_key=vault_api_key)
    mcp_client = MCPClient(config)

    try:
        mcp_client.connect()
        logger.info("Connected to vault")
    except Exception as e:
        logger.warning("Could not connect to vault: %s", e)

    async def run_async():
        executor = LLMExecutor(model=model)
        loop = AutonomousCompoundLoop(
            skills_dir=Path(skills_dir),
            mcp_client=mcp_client,
            llm_executor=executor,
            weak_threshold=weak_threshold,
            max_refinements=max_refinements,
        )

        skills = loop.discover_skills()[:limit]
        logger.info("Discovered %d skills (limited from total)", len(skills))

        results = await loop.benchmark_all()
        weak = [s for s in results if s.coherence < weak_threshold]
        logger.info("Benchmarked %d skills: %d weak", len(results), len(weak))

        if weak:
            await loop.refine_weak_skills(weak)

        await loop.persist_results()

        print("\n=== Autonomous Benchmark Results ===")
        print(f"Skills benchmarked: {len(results)}")
        print(f"Weak skills: {len(weak)}")
        for s in results:
            status = "REFINED" if s.refined else "OK"
            print(f"  [{status}] {s.skill_name}: {s.coherence:.3f}")

        await executor.close()
        return results

    asyncio.run(run_async())

    mcp_client.close()
