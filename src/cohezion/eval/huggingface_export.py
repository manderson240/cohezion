"""HuggingFace dataset export for FLUME EVO physics research.

Provides:
1. HuggingFaceExporter — Exports benchmark results as a HuggingFace dataset
2. HuggingFaceDatasetSpec — Specification for dataset metadata
3. generate_dataset_card — Generates a model card for the dataset

Output format: JSONL with one record per episode, plus dataset_card.md.
Compatible with HuggingFace evaluate and torchtext datasets.

Example:
    exporter = HuggingFaceExporter(
        dataset_name="cohezion/flume-journey-bench-v0",
        dataset_version="1.0.0",
    )
    exporter.export(
        episodes=[episode_result, ...],
        output_dir="data/huggingface/",
    )
    card = generate_dataset_card(exporter)
    exporter.push_to_hub(token="hf_...")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class HuggingFaceDatasetSpec:
    """Metadata specification for a FLUME EVO physics dataset.

    Attributes:
        dataset_name: Short name for the dataset (e.g., "cohezion/flume-journey-bench-v0").
        version: Semantic version string.
        description: One-paragraph dataset description.
        task_tags: List of task category tags.
        model_architecture: Name of the policy architecture used.
        hardware: Hardware platform used for data collection.
        total_episodes: Number of episodes in the dataset.
        total_runs: Number of independent benchmark runs.
        license: License identifier (e.g., "apache-2.0").
        arxiv_id: Optional arXiv preprint identifier.
        paper_title: Optional title of the associated paper.
    """

    dataset_name: str
    version: str = "1.0.0"
    description: str = ""
    task_tags: tuple[str, ...] = ("evoloader", "reinforcement-learning", "autonomous-agents", "flume")
    model_architecture: str = "TRIUNEPolicy"
    hardware: str = "AMD Ryzen AI MAX+ 395"
    total_episodes: int = 0
    total_runs: int = 0
    license: str = "apache-2.0"
    arxiv_id: str | None = None
    paper_title: str | None = None


class HuggingFaceExporter:
    """Exports FLUME EVO physics benchmark results as a HuggingFace dataset.

    Produces:
    - data.jsonl: One JSON record per episode with full biography + metrics
    - metadata.json: Dataset metadata (spec + aggregated statistics)
    - dataset_card.md: Human-readable model card

    Example:
        exporter = HuggingFaceExporter(
            dataset_name="cohezion/flume-journey-bench-v0",
            dataset_version="1.0.0",
        )
        result = exporter.export(
            episodes=episode_results,
            output_dir="data/huggingface/",
        )
        print(result["num_episodes"], "episodes exported")
    """

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str = "1.0.0",
        spec: HuggingFaceDatasetSpec | None = None,
    ) -> None:
        self.dataset_name = dataset_name
        self.dataset_version = dataset_version
        self.spec = spec or HuggingFaceDatasetSpec(dataset_name=dataset_name)
        self._exported: list[dict[str, Any]] = []

    def export(
        self,
        episodes: list[dict[str, Any]],
        output_dir: str | Path,
        include_biographies: bool = True,
        include_metrics: bool = True,
    ) -> dict[str, Any]:
        """Export episodes to JSONL format compatible with HuggingFace datasets.

        Args:
            episodes: List of episode result dicts (from EvalPipeline or BenchmarkSuite).
            output_dir: Directory to write output files.
            include_biographies: If True, include full EVO biography per episode.
            include_metrics: If True, include per-metric scores per episode.

        Returns:
            Dictionary with export statistics (num_episodes, num_runs, output_path).
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        data_lines: list[str] = []

        for ep in episodes:
            record: dict[str, Any] = {
                "episode_id": ep.get("episode_id", ep.get("episode", "unknown")),
                "run_id": ep.get("run_id", "unknown"),
                "task_name": ep.get("task_name", "unknown"),
                "archetype": ep.get("archetype", _infer_archetype(ep)),
                "difficulty": ep.get("difficulty", "medium"),
                "reward": float(ep.get("reward", ep.get("episode_reward", 0.0))),
                "mean_coherence": float(ep.get("mean_coherence", ep.get("coherence", 0.5))),
                "final_coherence": float(ep.get("final_coherence", 0.5)),
                "success": bool(ep.get("success", False)),
                "steps": int(ep.get("steps", 0)),
                "duration_seconds": float(ep.get("duration_seconds", 0.0)),
                "timestamp": ep.get("timestamp", time.time()),
            }

            if include_metrics:
                record["metrics"] = _sanitize_for_json(ep.get("metrics", {}))

            if include_biographies:
                bio = ep.get("biography", [])
                if bio:
                    record["biography_length"] = len(bio)
                    record["biography"] = _sanitize_for_json(bio)

            data_lines.append(json.dumps(record, default=str))

        jsonl_path = out_dir / "data.jsonl"
        with open(jsonl_path, "w") as f:
            f.write("\n".join(data_lines) + "\n")

        metadata = self._build_metadata(episodes, len(data_lines))
        metadata_path = out_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        spec_dict = {
            "dataset_name": self.spec.dataset_name,
            "version": self.spec.version,
            "description": self.spec.description,
            "task_tags": list(self.spec.task_tags),
            "model_architecture": self.spec.model_architecture,
            "hardware": self.spec.hardware,
            "total_episodes": self.spec.total_episodes,
            "total_runs": self.spec.total_runs,
            "license": self.spec.license,
            "arxiv_id": self.spec.arxiv_id,
            "paper_title": self.spec.paper_title,
        }
        spec_path = out_dir / "spec.json"
        with open(spec_path, "w") as f:
            json.dump(spec_dict, f, indent=2)

        self._exported = [json.loads(line) for line in data_lines]

        return {
            "num_episodes": len(data_lines),
            "num_runs": len({ep.get("run_id", "unknown") for ep in episodes}),
            "output_dir": str(out_dir),
            "jsonl_path": str(jsonl_path),
            "metadata_path": str(metadata_path),
        }

    def _build_metadata(self, episodes: list[dict[str, Any]], num_episodes: int) -> dict[str, Any]:
        """Build aggregated metadata from episodes."""
        rewards = [float(ep.get("reward", 0.0)) for ep in episodes]
        coherences = [float(ep.get("coherence", 0.5)) for ep in episodes]
        successes = [float(ep.get("success", False)) for ep in episodes]
        steps = [int(ep.get("steps", 0)) for ep in episodes]

        metrics_agg: dict[str, Any] = {}
        all_metrics = [ep.get("metrics", {}) for ep in episodes if ep.get("metrics")]
        if all_metrics:
            for key in all_metrics[0]:
                vals = [m.get(key, {}).get("mean", 0.0) for m in all_metrics if key in m]
                if vals:
                    metrics_agg[key] = {
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
                        "min": float(np.min(vals)),
                        "max": float(np.max(vals)),
                    }

        run_ids = {ep.get("run_id", "unknown") for ep in episodes}
        archetypes = {ep.get("task_name", "unknown") for ep in episodes}

        return {
            "dataset_name": self.dataset_name,
            "version": self.dataset_version,
            "num_episodes": num_episodes,
            "num_runs": len(run_ids),
            "reward": {
                "mean": float(np.mean(rewards)) if rewards else 0.0,
                "std": float(np.std(rewards, ddof=1)) if len(rewards) > 1 else 0.0,
                "min": float(np.min(rewards)) if rewards else 0.0,
                "max": float(np.max(rewards)) if rewards else 0.0,
            },
            "coherence": {
                "mean": float(np.mean(coherences)) if coherences else 0.5,
                "std": float(np.std(coherences, ddof=1)) if len(coherences) > 1 else 0.0,
            },
            "success_rate": float(np.mean(successes)) if successes else 0.0,
            "mean_steps": float(np.mean(steps)) if steps else 0.0,
            "archetypes": sorted(str(a) for a in archetypes),
            "aggregate_metrics": metrics_agg,
            "export_timestamp": time.time(),
        }

    def push_to_hub(
        self,
        output_dir: str | Path,
        token: str,
        private: bool = False,
        exist_ok: bool = True,
    ) -> dict[str, Any]:
        """Push exported dataset to HuggingFace Hub.

        Args:
            output_dir: Directory with exported JSONL files.
            token: HuggingFace API token.
            private: Whether the dataset should be private.
            exist_ok: Whether to overwrite existing dataset.

        Returns:
            Dictionary with hub response (dataset_url, repo_id).
        """
        try:
            from huggingface_hub import HfApi, create_repo

            api = HfApi()
            repo_id = self.dataset_name

            try:
                create_repo(
                    repo_id=repo_id,
                    token=token,
                    private=private,
                    repo_type="dataset",
                    exist_ok=exist_ok,
                )
            except Exception:
                pass

            out_dir = Path(output_dir)
            for file_path in out_dir.glob("*.jsonl"):
                api.upload_file(
                    path_or_fileobj=str(file_path),
                    path_in_repo=f"data/{file_path.name}",
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=token,
                )

            for file_path in out_dir.glob("*.json"):
                if file_path.name != "spec.json":
                    api.upload_file(
                        path_or_fileobj=str(file_path),
                        path_in_repo=f"{file_path.name}",
                        repo_id=repo_id,
                        repo_type="dataset",
                        token=token,
                    )

            return {
                "dataset_url": f"https://huggingface.co/datasets/{repo_id}",
                "repo_id": repo_id,
            }

        except ImportError:
            raise ImportError(
                "huggingface_hub is required for push_to_hub. Install with: pip install huggingface_hub"
            ) from None


def generate_dataset_card(exporter: HuggingFaceExporter) -> str:
    """Generate a HuggingFace dataset card (README.md) for a FLUME EVO dataset.

    Args:
        exporter: HuggingFaceExporter with a spec.

    Returns:
        Multi-line string suitable for use as a dataset README.
    """
    spec = exporter.spec
    year_str = time.strftime("%Y")
    version_str = exporter.dataset_version.replace(".", "")

    citation_lines = [
        "@misc{cohezion_flume_journey_bench_" + version_str + ",",
        "  title={FLUME Journey Benchmark: EVO Physics Agent Evaluation},",
        "  author={Cohezion Research},",
        "  year={" + year_str + "},",
        "  version={" + exporter.dataset_version + "},",
    ]
    if spec.arxiv_id:
        citation_lines.append("  url={https://arxiv.org/abs/" + spec.arxiv_id + "},")
    citation_lines.append("  publisher={Cohezion},")
    citation_lines.append("}")
    citation_block = "\n".join(citation_lines).replace("{", "{{").replace("}", "}}")

    card = f"""---
annotations_creators:
- no-annotation
language_creators:
- machine-generated
languages:
- en
licenses:
- {spec.license}
multilinguality:
- monolingual
pretty_name: FLUME Journey Benchmark v{exporter.dataset_version}
size_categories:
- n<1K
source_datasets:
- original
task_categories:
- sequence-modeling
- reinforcement-learning
task_ids:
- multi-goal-reinforcement-learning
- continuous-control
---

# FLUME Journey Benchmark Dataset

## Dataset Description

**{spec.dataset_name}** v{spec.version} — A multi-episode benchmark dataset for
FLUME (Federated Learning Universe with Multiple Equilibria) EVO physics agents,
collected on {spec.hardware}.

This dataset contains multi-episode trajectories from FLUME EVO physics
benchmark evaluations. Episodes are generated by autonomous RL agents
(TRIUNEPolicy) navigating the FLUME manifold with Hamiltonian dynamics,
accumulating TRIUNE SELF states and exotic charge over 200-step episodes.

## Dataset Structure

Each record in `data.jsonl` represents one episode with:
- **Episode metadata**: episode_id, run_id, task_name, archetype, difficulty
- **Performance**: reward, mean_coherence, final_coherence, success, steps
- **Biography**: Full EVO physics trajectory (per-step TRIUNE states, charge, phase)
- **Metrics**: Per-metric BootstrapResult (mean, std, CI, p-value, effect size)

## Metric Families

| Axis | Description |
|------|-------------|
| HIHO Coherence | Ability to maintain coherence near 0.5 (HIHO attractor) |
| TRIUNE Balance | Equal Doer/Thinker/Knower activation |
| Stability | Low variance, consistent HIHO proximity |
| Exotic Charge | Sustained high charge accumulation |
| Kordylewski Orbit | Stable L4/L5 Lagrange orbit maintenance |
| SPIN Phase | Monotonic phase accumulation |

## Hardware

Data collected on **{spec.hardware}** using **{spec.model_architecture}** policy.

## Citation

```
{citation_block}
```
"""

    return card


def _arxiv_block(arxiv_id: str | None) -> str:
    if arxiv_id:
        return f"  url={{https://arxiv.org/abs/{arxiv_id}}},\n"
    return ""


def _make_citation_key(exporter: HuggingFaceExporter) -> str:
    """Generate a BibTeX citation key from exporter version."""
    version_str = exporter.dataset_version.replace(".", "")
    return f"cohezion_flume_journey_bench_{version_str}"


def _sanitize_for_json(obj: Any) -> Any:
    """Convert numpy types and non-JSON types to JSON-serializable equivalents."""
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    return obj


def _infer_archetype(episode: dict[str, Any]) -> str:
    """Infer archetype from episode data."""
    task_name = str(episode.get("task_name", "")).lower()
    if "hiho" in task_name or "coherence" in task_name:
        return "HIHO_BASIN"
    if "triune" in task_name or "balance" in task_name:
        return "TRIUNE_BALANCE"
    if "exotic" in task_name or "charge" in task_name:
        return "EXOTIC_CHARGE"
    if "kordylewski" in task_name or "orbit" in task_name:
        return "KORDYLEWSKI_ORBIT"
    if "interruption" in task_name or "recovery" in task_name:
        return "INTERRUPTION_RECOVERY"
    return "HIHO_BASIN"
