import time
import tempfile
from pathlib import Path
from unittest.mock import Mock
from cohezion.compound.core.executor import CompoundExecutor
from cohezion.compound.models import ExecutionMetrics, ExecutionResult
from cohezion.research import ResearchAgent, ResearchConfig


def run_benchmark():
    # Setup
    with tempfile.TemporaryDirectory(dir="data") as tmpdir:
        tmpdir_path = Path(tmpdir)
        config = ResearchConfig(
            max_experiments=1000,
            experiment_log=tmpdir_path / "experiments.jsonl",
            checkpoint_dir=tmpdir_path / "checkpoints",
            experiment_time_budget=10.0,
        )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = lambda task: ExecutionResult(
            success=True,
            output="Complete",
            metrics=ExecutionMetrics(duration_seconds=0.001),
        )

        agent = ResearchAgent(config=config, executor=mock_executor)

        start = time.time()
        agent.run_session()
        elapsed = time.time() - start

        print(f"METRIC session_duration_s={elapsed:.4f}")


if __name__ == "__main__":
    run_benchmark()
