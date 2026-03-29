"""HuggingFaceExporter - Export EVO research data and benchmark harness.

Dual export functionality:
    1. Research dataset: EVO biographies as JSONL + dataset card README
    2. Benchmark harness: Model evaluation API for EVO tasks

The benchmark harness provides:
    benchmark.run(model, tasks) - Run model on EVO task suite
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class HuggingFaceExporter:
    """Export EVO research data and benchmark harness to HuggingFace format."""

    def __init__(self) -> None:
        """Initialize HuggingFaceExporter."""
        self.dataset_name = "cohezion/evo-benchmark"
        self.dataset_url = f"https://huggingface.co/datasets/{self.dataset_name}"

    async def export_research_dataset(self, evos: list[dict[str, Any]], output_dir: Path) -> None:
        """Export EVO biographies as HuggingFace-compatible JSONL dataset.

        Args:
            evos: List of EVO biography dictionaries.
            output_dir: Directory to write data.jsonl and README.md.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        jsonl_path = output_dir / "data.jsonl"
        readme_path = output_dir / "README.md"

        with open(jsonl_path, "w") as f:
            for evo in evos:
                f.write(json.dumps(evo) + "\n")

        readme_content = self._generate_dataset_card(len(evos))
        readme_path.write_text(readme_content)

    def _generate_dataset_card(self, num_examples: int) -> str:
        """Generate HuggingFace dataset card README.

        Args:
            num_examples: Number of examples in the dataset.

        Returns:
            Markdown content for README.md dataset card.
        """
        return f"""---
annotations_creators:
  - no-annotation
language:
  - en
license: apache-2.0
multilinguality:
  - monolingual
size_categories:
  - n<{num_examples}
source_datasets:
  - original
task_categories:
  - sequence-modeling
  - anomaly-detection
task_ids:
  - language-modeling
  - anomaly-detection-other
---

# EVO-BENCHMARK Dataset Card

## Dataset Summary

The EVO-BENCHMARK dataset contains {num_examples} EVO (EthericVariantOscillator) biographies
from the Cohezion compound engineering framework. Each biography captures a complete
agentic journey through the 12D FLUME manifold, including physics properties,
TRIUNE self structure, and exotic vacuum characteristics.

## Dataset Description

This dataset accompanies the EVO Benchmark Paper and is designed for:
- Studying coherence dynamics in agentic systems
- Analyzing exotic vacuum physics in synthetic environments
- Benchmarking recovery and stability in autonomous agents
- Researching TRIUNE (Doer/Thinker/Knower) balance dynamics

## Dataset Structure

Each JSONL entry contains:
- `journey_id`: Unique identifier for the EVO journey
- `birth_time`: ISO timestamp of journey start
- `coherence_amplitude`: Peak HIHO stability reached (0.0 to 1.0)
- `phase`: Position in HIHO oscillation cycle (0 to 2π)
- `angular_momentum`: 3D SPIN coherence vector [rotation, precession, charge]
- `charge`: Rotation x precession alignment result
- `exotic_charge_density`: Deviation from HIHO vacuum baseline
- `kordylewski_cloud_id`: L4 or L5 memory cloud assignment
- `stability_well`: Basin of attraction name
- `doer_state_mean`: Mean of 12D Doer state
- `thinker_state_mean`: Mean of 512D Thinker state
- `knower_state_mean`: Mean of 2048D Knower state
- `trajectory_length`: Number of steps in journey
- `final_coherence`: Coherence at journey end

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{self.dataset_name}")
for example in dataset["train"]:
    print(example["journey_id"], example["coherence_amplitude"])
```

## Citation

If using this dataset, please cite the EVO Benchmark Paper:

```
@misc{{cohezion-evo-benchmark,
  author={{Cohezion Research Team}},
  title={{EVO-BENCHMARK: Capability Assessment for Agentic Systems}},
  year={{2024}},
  url={{{self.dataset_url}}}
}}
```

## License

Apache 2.0 - See LICENSE file for details.

---

Dataset provided by [Cohezion](https://github.com/anomalyco/cohezion).
Generated: {datetime.now().strftime("%Y-%m-%d")}
"""

    async def export_benchmark_harness(self, output_dir: Path) -> None:
        """Export benchmark harness API for model evaluation.

        Args:
            output_dir: Directory to write benchmark.py.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        benchmark_path = output_dir / "benchmark.py"
        benchmark_content = self._generate_benchmark_harness()
        benchmark_path.write_text(benchmark_content)

    def _generate_benchmark_harness(self) -> str:
        """Generate benchmark harness Python code.

        Returns:
            Python code for benchmark.run(model, tasks) API.
        """
        return '''"""EVO Benchmark Harness - Model evaluation on EVO task suite.

Usage:
    from benchmark import run, EVOTask

    tasks = [
        EVOTask(
            task_id="coherence_stability",
            description="Maintain HIHO coherence above threshold",
            success_threshold=0.8,
        ),
        EVOTask(
            task_id="recovery_basin's,
            description="Recover from coherence collapse",
            success_threshold=0.7,
        ),
    ]

    results = run(model, tasks)
    print(results.summary())
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class EVOTask:
    """EVO evaluation task specification."""

    task_id: str
    description: str
    success_threshold: float
    max_steps: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EVOResult:
    """Result of evaluating a single task."""

    task_id: str
    success: bool
    coherence_score: float
    duration_seconds: float
    steps_completed: int
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results."""

    results: list[EVOResult]
    total_duration_seconds: float
    model_name: str
    timestamp: str

    def summary(self) -> dict[str, Any]:
        """Get summary statistics.

        Returns:
            Dictionary with summary statistics.
        """
        total = len(self.results)
        successes = sum(1 for r in self.results if r.success)
        avg_coherence = (
            sum(r.coherence_score for r in self.results) / total if total > 0 else 0.0
        )

        return {
            "total_tasks": total,
            "successful_tasks": successes,
            "success_rate": successes / total if total > 0 else 0.0,
            "average_coherence_score": avg_coherence,
            "total_duration_seconds": self.total_duration_seconds,
            "model_name": self.model_name,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of results.
        """
        return {
            "summary": self.summary(),
            "results": [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "coherence_score": r.coherence_score,
                    "duration_seconds": r.duration_seconds,
                    "steps_completed": r.steps_completed,
                    "error": r.error,
                }
                for r in self.results
            ],
            "total_duration_seconds": self.total_duration_seconds,
            "model_name": self.model_name,
            "timestamp": self.timestamp,
        }


class ModelProtocol(Protocol):
    """Protocol for models compatible with the benchmark."""

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response to prompt.

        Args:
            prompt: Input prompt string.
            **kwargs: Additional generation parameters.

        Returns:
            Generated response string.
        """
        ...


def run(model: ModelProtocol, tasks: list[EVOTask]) -> BenchmarkResults:
    """Run benchmark on model with given tasks.

    Args:
        model: Model to evaluate (must implement generate method).
        tasks: List of EVOTask specifications.

    Returns:
        BenchmarkResults with per-task results and summary.
    """
    from datetime import datetime

    results: list[EVOResult] = []
    start_time = time.time()

    model_name = getattr(model, "__name__", getattr(model.__class__, "__name__", "unknown"))

    for task in tasks:
        result = _evaluate_single_task(model, task)
        results.append(result)

    total_duration = time.time() - start_time

    return BenchmarkResults(
        results=results,
        total_duration_seconds=total_duration,
        model_name=model_name,
        timestamp=datetime.now().isoformat(),
    )


def _evaluate_single_task(model: ModelProtocol, task: EVOTask) -> EVOResult:
    """Evaluate a single task on the model.

    Args:
        model: Model to evaluate.
        task: Task specification.

    Returns:
        EVOResult for this task.
    """
    from cohezion.rl.environment import FlumeNavEnv

    start_time = time.time()
    error = None
    success = False
    coherence_score = 0.0
    steps_completed = 0

    try:
        env = FlumeNavEnv()
        obs, info = env.reset()

        for step in range(task.max_steps):
            prompt = _build_prompt(obs, task)
            response = model.generate(prompt)

            action = _parse_response(response)
            obs, reward, terminated, truncated, info = env.step(action)
            steps_completed = step + 1

            if terminated or truncated:
                break

        final_obs = obs
        coherence_score = final_obs.get("evo_state", {}).get("coherence", 0.0)
        success = coherence_score >= task.success_threshold

    except Exception as e:
        error = str(e)

    duration = time.time() - start_time

    return EVOResult(
        task_id=task.task_id,
        success=success,
        coherence_score=coherence_score,
        duration_seconds=duration,
        steps_completed=steps_completed,
        error=error,
    )


def _build_prompt(obs: dict[str, Any], task: EVOTask) -> str:
    """Build prompt from observation and task.

    Args:
        obs: Environment observation.
        task: Task specification.

    Returns:
        Prompt string for model.
    """
    coherence = obs.get("evo_state", {}).get("coherence", 0.5)
    phase = obs.get("evo_state", {}).get("phase", 0.0)

    return (
        f"Task: {task.description}\\n"
        f"Current coherence: {coherence:.3f}\\n"
        f"Phase: {phase:.3f}\\n"
        f"Success threshold: {task.success_threshold:.3f}\\n"
        f"Choose action (0=retreat, 1=hold, 2=advance):"
    )


def _parse_response(response: str) -> int:
    """Parse model response to action.

    Args:
        response: Model response string.

    Returns:
        Action integer (0, 1, or 2).
    """
    response_lower = response.lower().strip()

    if "advance" in response_lower or "2" in response_lower:
        return 2
    elif "retreat" in response_lower or "0" in response_lower:
        return 0
    else:
        return 1


if __name__ == "__main__":
    import json

    class MockModel:
        """Mock model for testing."""

        def generate(self, prompt: str, **kwargs) -> str:
            return "hold"

    tasks = [
        EVOTask(
            task_id="test_task",
            description="Test task for benchmark validation",
            success_threshold=0.7,
            max_steps=10,
        ),
    ]

    results = run(MockModel(), tasks)
    print(json.dumps(results.to_dict(), indent=2))
'''
