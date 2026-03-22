#!/usr/bin/env python
"""Example: Multi-Agent Team Execution with Vault Coordination.

Demonstrates intelligent team orchestration with:
  1. Task dependency resolution (topological sorting)
  2. Parallel execution of independent tasks
  3. Vault-guided skill selection
  4. Composite scoring and team metrics
  5. Error handling and partial success

This example shows:
  - Sequential pipeline (A → B → C)
  - Fan-out pattern (gather → parallel analysis)
  - Diamond DAG (A → B,C → D)
  - Skill selection from vault history
"""

import asyncio
import logging
import sys

from cohezion.compound import AgentTask, CompoundExecutor, TeamExecutor
from cohezion.core.mcp_client import MCPClient, MCPConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run multi-agent team execution example."""
    # Initialize MCP client for vault access
    config = MCPConfig(
        server_url="http://localhost:8360/mcp",
        api_key="",  # No auth for local vault
    )
    mcp_client = MCPClient(config)

    # Create agents (each agent is a CompoundExecutor)
    # In production, these might be specialized agents
    logger.info("=" * 70)
    logger.info("MULTI-AGENT TEAM EXECUTION EXAMPLE")
    logger.info("=" * 70)
    logger.info("")

    # Create 3 agents for the team
    logger.info("Step 1: Creating agent team...")
    logger.info("-" * 70)
    agents = {
        "researcher": CompoundExecutor(mcp_client=mcp_client),
        "analyst": CompoundExecutor(mcp_client=mcp_client),
        "writer": CompoundExecutor(mcp_client=mcp_client),
    }
    logger.info("Created %d agents: %s", len(agents), ", ".join(agents.keys()))
    logger.info("")

    # Create team executor
    team_executor = TeamExecutor(agents, mcp_client, project="cohezion")
    logger.info("Step 2: Initialized TeamExecutor")
    logger.info("-" * 70)
    logger.info("")

    # Example 1: Sequential Pipeline
    logger.info("Example 1: Sequential Pipeline (A → B → C)")
    logger.info("-" * 70)

    sequential_tasks = [
        AgentTask(
            task_id="research",
            agent_id="researcher",
            description="Research machine learning trends",
            operation_type="search",
            dependencies=[],  # No dependencies
        ),
        AgentTask(
            task_id="analyze",
            agent_id="analyst",
            description="Analyze research findings",
            operation_type="analyze",
            dependencies=["research"],  # Depends on research
        ),
        AgentTask(
            task_id="report",
            agent_id="writer",
            description="Write summary report",
            operation_type="generate",
            dependencies=["analyze"],  # Depends on analysis
        ),
    ]

    logger.info("Sequential task order:")
    for task in sequential_tasks:
        deps = f" (depends on {task.dependencies})" if task.dependencies else ""
        logger.info("  %s: %s%s", task.task_id, task.description, deps)
    logger.info("")

    # Execute sequential pipeline
    logger.info("Executing sequential pipeline...")
    result_seq = await team_executor.execute_team(sequential_tasks, parallel_degree=1)

    logger.info("Sequential execution complete:")
    logger.info("  Success: %s", result_seq.success)
    logger.info("  Tasks executed: %d", result_seq.tasks_executed)
    logger.info("  Tasks failed: %d", result_seq.tasks_failed)
    logger.info("  Compound score: %.3f", result_seq.compound_score)
    logger.info("  Execution time: %.2f seconds", result_seq.execution_time_seconds)
    logger.info("")

    # Example 2: Fan-Out Pattern (Parallel Analysis)
    logger.info("Example 2: Fan-Out Pattern (gather → parallel analysis)")
    logger.info("-" * 70)

    fanout_tasks = [
        AgentTask(
            task_id="gather",
            agent_id="researcher",
            description="Gather customer feedback",
            operation_type="search",
            dependencies=[],
        ),
        AgentTask(
            task_id="analyze_sentiment",
            agent_id="analyst",
            description="Analyze sentiment of feedback",
            operation_type="analyze",
            dependencies=["gather"],
        ),
        AgentTask(
            task_id="analyze_trends",
            agent_id="analyst",
            description="Analyze trends in feedback",
            operation_type="analyze",
            dependencies=["gather"],
        ),
        AgentTask(
            task_id="analyze_topics",
            agent_id="writer",
            description="Identify key topics",
            operation_type="analyze",
            dependencies=["gather"],
        ),
        AgentTask(
            task_id="consolidate",
            agent_id="writer",
            description="Consolidate all analyses",
            operation_type="transform",
            dependencies=["analyze_sentiment", "analyze_trends", "analyze_topics"],
        ),
    ]

    logger.info("Fan-out task structure:")
    logger.info("  gather")
    logger.info("    ├─ analyze_sentiment")
    logger.info("    ├─ analyze_trends")
    logger.info("    └─ analyze_topics")
    logger.info("        └─ consolidate")
    logger.info("")

    logger.info("Executing fan-out workflow (parallelism=3)...")
    result_fanout = await team_executor.execute_team(fanout_tasks, parallel_degree=3)

    logger.info("Fan-out execution complete:")
    logger.info("  Success: %s", result_fanout.success)
    logger.info("  Tasks executed: %d", result_fanout.tasks_executed)
    logger.info("  Tasks failed: %d", result_fanout.tasks_failed)
    logger.info("  Compound score: %.3f", result_fanout.compound_score)
    logger.info("  Execution time: %.2f seconds", result_fanout.execution_time_seconds)
    logger.info("")

    # Example 3: Diamond DAG
    logger.info("Example 3: Diamond DAG (A → B,C → D)")
    logger.info("-" * 70)

    diamond_tasks = [
        AgentTask(
            task_id="task_a",
            agent_id="researcher",
            description="Collect base data",
            operation_type="search",
            dependencies=[],
        ),
        AgentTask(
            task_id="task_b",
            agent_id="analyst",
            description="Process path B",
            operation_type="analyze",
            dependencies=["task_a"],
        ),
        AgentTask(
            task_id="task_c",
            agent_id="analyst",
            description="Process path C",
            operation_type="analyze",
            dependencies=["task_a"],
        ),
        AgentTask(
            task_id="task_d",
            agent_id="writer",
            description="Merge results from B and C",
            operation_type="transform",
            dependencies=["task_b", "task_c"],
        ),
    ]

    logger.info("Diamond DAG structure:")
    logger.info("      task_a")
    logger.info("      /    \\")
    logger.info("  task_b  task_c")
    logger.info("      \\    /")
    logger.info("      task_d")
    logger.info("")

    logger.info("Executing diamond DAG (parallelism=4)...")
    result_diamond = await team_executor.execute_team(diamond_tasks, parallel_degree=4)

    logger.info("Diamond execution complete:")
    logger.info("  Success: %s", result_diamond.success)
    logger.info("  Tasks executed: %d", result_diamond.tasks_executed)
    logger.info("  Tasks failed: %d", result_diamond.tasks_failed)
    logger.info("  Compound score: %.3f", result_diamond.compound_score)
    logger.info("  Execution time: %.2f seconds", result_diamond.execution_time_seconds)
    logger.info("")

    # Show detailed results for one example
    logger.info("Example 4: Detailed Results Breakdown")
    logger.info("-" * 70)
    logger.info("Results from Sequential Pipeline:")
    logger.info("")

    for i, task_result in enumerate(result_seq.results, 1):
        logger.info("  Task %d: %s", i, task_result.task_id)
        logger.info("    Success: %s", task_result.success)
        logger.info("    Agent: %s", task_result.agent_id)
        logger.info("    Selected Skill: %s", task_result.selected_skill)
        logger.info("    Metrics: %s", task_result.metrics)
        if task_result.error:
            logger.info("    Error: %s", task_result.error)
        logger.info("")

    # Show composite score calculation
    logger.info("Example 5: Composite Score Calculation")
    logger.info("-" * 70)
    logger.info("Composite Score = (success × 0.60) + (coherence × 0.25) + (efficiency × 0.15)")
    logger.info("")

    if result_seq.results:
        successful = sum(1 for r in result_seq.results if r.success)
        success_rate = successful / len(result_seq.results) if result_seq.results else 0

        coherence_scores = [r.metrics.get("coherence", 0.5) for r in result_seq.results if r.success]
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0

        efficiency_scores = []
        for r in result_seq.results:
            if r.execution_result and r.execution_result.token_metrics:
                cache_hit_rate = r.execution_result.token_metrics.get("cache_hit_rate", 0.0)
                efficiency_scores.append(cache_hit_rate)

        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.5

        logger.info(
            "  Success rate: %.2f (%d/%d tasks)",
            success_rate,
            successful,
            len(result_seq.results),
        )
        logger.info("  Average coherence: %.2f", avg_coherence)
        logger.info("  Average efficiency: %.2f", avg_efficiency)
        logger.info("")
        logger.info("  Calculation:")
        logger.info(
            "    = (%.2f × 0.60) + (%.2f × 0.25) + (%.2f × 0.15)",
            success_rate,
            avg_coherence,
            avg_efficiency,
        )
        logger.info(
            "    = %.3f + %.3f + %.3f",
            success_rate * 0.60,
            avg_coherence * 0.25,
            avg_efficiency * 0.15,
        )
        logger.info("    = %.3f", result_seq.compound_score)

    logger.info("")

    # Show skill selection process
    logger.info("Example 6: Vault-Guided Skill Selection")
    logger.info("-" * 70)
    logger.info("For each task, TeamExecutor:")
    logger.info("  1. Queries vault for similar past executions")
    logger.info("  2. Extracts performance metrics (coherence, efficiency, success)")
    logger.info("  3. Ranks candidate skills by composite score")
    logger.info("  4. Selects best-performing skill")
    logger.info("")
    logger.info("Selected skills in sequential pipeline:")
    for task_result in result_seq.results:
        logger.info("  %s → %s", task_result.task_id, task_result.selected_skill)
    logger.info("")

    # Show comparison of execution patterns
    logger.info("Example 7: Execution Pattern Comparison")
    logger.info("-" * 70)

    results_by_pattern = [
        ("Sequential (parallelism=1)", result_seq),
        ("Fan-Out (parallelism=3)", result_fanout),
        ("Diamond DAG (parallelism=4)", result_diamond),
    ]

    logger.info("Pattern | Tasks | Success | Score | Time (s)")
    logger.info("--------|-------|---------|-------|--------")
    for pattern_name, result in results_by_pattern:
        success_pct = (
            f"{(1 - result.tasks_failed / result.tasks_executed) * 100:.0f}%" if result.tasks_executed > 0 else "N/A"
        )
        logger.info(
            "%-30s | %5d | %7s | %.3f | %.2f",
            pattern_name,
            result.tasks_executed,
            success_pct,
            result.compound_score,
            result.execution_time_seconds,
        )

    logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Key Concepts Demonstrated:")
    logger.info("  ✓ Sequential pipelines (dependencies)")
    logger.info("  ✓ Parallel execution (fan-out)")
    logger.info("  ✓ Complex DAGs (diamond)")
    logger.info("  ✓ Vault-guided skill selection")
    logger.info("  ✓ Composite scoring (team performance)")
    logger.info("  ✓ Error handling (graceful degradation)")
    logger.info("")
    logger.info("Benefits of Multi-Agent Team Execution:")
    logger.info("  • Coordinate complex workflows across multiple agents")
    logger.info("  • Automatic skill selection from vault history")
    logger.info("  • Parallel execution with dependency management")
    logger.info("  • Comprehensive team performance metrics")
    logger.info("  • Vault-enabled institutional learning")
    logger.info("")
    logger.info("Use Cases:")
    logger.info("  • Research → Analysis → Report generation")
    logger.info("  • Customer feedback → Sentiment/Trends/Topics → Consolidation")
    logger.info("  • Data gathering → Parallel processing → Results merge")
    logger.info("  • Complex workflows with task dependencies")
    logger.info("")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        sys.exit(1)
