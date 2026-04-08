#!/usr/bin/env python3
"""Benchmark script for ResearchAgent session duration."""

import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cohezion.compound.models import ExecutionMetrics, ExecutionResult
from cohezion.research.agent import ResearchAgent, ResearchConfig


def benchmark_session(max_experiments: int = 1000) -> float:
    """Run benchmark and return session duration in seconds."""
    # Setup
    os.makedirs("data/research", exist_ok=True)
    config = ResearchConfig(
        max_experiments=max_experiments,
        experiment_log=Path("data/research/benchmark.jsonl"),
        train_file=Path("train.py"),
        enable_guardrails=False,  # Skip for benchmark
    )

    mock_executor = Mock()
    mock_executor.execute = lambda task: ExecutionResult(
        success=True,
        output="Complete",
        metrics=ExecutionMetrics(duration_seconds=0.01),
    )

    agent = ResearchAgent(config=config, executor=mock_executor)

    # Warmup
    agent_warmup = ResearchAgent(config=config, executor=mock_executor)
    agent_warmup.run_session(max_experiments=10)

    # Actual benchmark
    agent = ResearchAgent(config=config, executor=mock_executor)
    start = time.perf_counter()
    agent.run_session()
    elapsed = time.perf_counter() - start

    return elapsed


if __name__ == "__main__":
    duration = benchmark_session(1000)
    print(f"METRIC session_duration_s={duration:.6f}")
    print(f"Session completed: 1000 experiments")
    print(f"Per-experiment: {duration/1000*1e6:.2f} µs")
