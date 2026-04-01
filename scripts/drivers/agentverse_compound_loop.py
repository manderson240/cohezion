#!/usr/bin/env python3
"""Example: Run AgentVerse Compound Benchmark Loop.

This script demonstrates how to use the CompoundBenchmarkLoop
with live services to improve Cohezion skills through iterative
benchmarking and refinement.

Usage:
    python scripts/drivers/agentverse_compound_loop.py

Or via CLI:
    python -m cohezion.integrations.agentverse.cli run \\
        --tasks src/cohezion/integrations/agentverse/tasks/python_benchmark.json
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.core.mcp_client import MCPClient, MCPConfig
from cohezion.integrations.agentverse import (
    AgentVerseBenchmarkRunner,
    CompoundBenchmarkLoop,
    LoopConfig,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


DEFAULT_TASKS = [
    {"task": "Write a factorial function", "skill": "python_PRIME"},
    {"task": "Write pytest tests for factorial", "skill": "testing_PRIME"},
]


def main() -> None:
    """Run the example."""
    logger.info("Starting AgentVerse Compound Benchmark Loop")

    config = MCPConfig(
        server_url="http://localhost:8360",
        api_key=os.getenv("CLOUD_VAULT_API_KEY", ""),
    )

    mcp_client = MCPClient(config)

    try:
        mcp_client.connect()
        logger.info("Connected to vault")
    except Exception as e:
        logger.warning("Could not connect to vault: %s. Continuing with mocks.", e)

    try:
        runner = AgentVerseBenchmarkRunner(
            executor=_MockExecutor(),
            mcp_client=mcp_client,
        )

        refiner = SkillRefiner(mcp_client=mcp_client)

        loop_config = LoopConfig(
            max_iterations=3,
            weak_skill_threshold=0.4,
            improvement_threshold=0.1,
            enable_parallel_refinement=True,
        )

        loop = CompoundBenchmarkLoop(
            runner=runner,
            refiner=refiner,
            config=loop_config,
        )

        result = asyncio.run(loop.run_loop(DEFAULT_TASKS))

        logger.info("=" * 60)
        logger.info("Compound Loop Complete")
        logger.info("=" * 60)
        logger.info("Total Iterations: %d", result.total_iterations)
        logger.info("Initial Coherence: %.3f", result.initial_coherence)
        logger.info("Final Coherence: %.3f", result.final_coherence)
        logger.info("Improvement: %+.3f", result.total_improvement)
        logger.info("Converged: %s", result.converged)
        logger.info("Refined Skills: %s", list(result.refined_skills))

        for iteration in result.iterations:
            logger.info(
                "  Iter %d: %.3f -> %.3f (Δ %.3f) weak=%s refined=%s",
                iteration.iteration,
                iteration.coherence_before,
                iteration.coherence_after,
                iteration.improvement,
                iteration.weak_skills,
                iteration.refined_skills,
            )

        if result.converged:
            logger.info("SUCCESS: Loop converged!")
            sys.exit(0)
        else:
            logger.info("Loop did not converge within max iterations")
            sys.exit(1)

    finally:
        mcp_client.close()
        logger.info("Vault connection closed")


class _MockExecutor:
    """Mock executor for demo purposes."""

    def execute_task(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str = "generate",
    ):
        """Mock execute_task that returns simulated results."""
        import time

        time.sleep(0.01)

        mock_result = type(
            "MockResult",
            (),
            {
                "success": True,
                "output": f"Mock output for: {task_description[:30]}...",
                "metrics": {
                    "coherence": 0.5,
                    "alignment": 0.7,
                    "anomaly_score": 0.1,
                },
                "duration_seconds": 1.0,
            },
        )()

        return mock_result

    def get_experience_guidance(self, query: str) -> dict:
        """Mock get_experience_guidance."""
        return {}


if __name__ == "__main__":
    main()
