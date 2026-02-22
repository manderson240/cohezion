"""Research lab task runners.

Entry points for Trigger.dev research tasks:
- model_scout: Discover and evaluate new models
- paper_ingest: Ingest research papers and surface relevant findings
- experiment_analysis: Analyze recent experiment data and extract insights
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class TaskResult:
    """Standardized result from a research task."""

    task_id: str
    status: str
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def emit(self) -> None:
        json.dump(asdict(self), sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()


def run_model_scout(payload: dict[str, Any] | None = None) -> TaskResult:
    """Scout for new models via Ollama registry and local availability.

    Checks installed models, evaluates storage budget, and recommends
    upgrades or new installations.
    """
    start = time.time()
    metrics: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        # Storage check
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        metrics["storage_free_gb"] = round(free_gb, 2)
        can_expand = free_gb >= 20.0

        # Check Ollama for installed models
        try:
            import httpx

            resp = httpx.get("http://localhost:11434/api/tags", timeout=10)
            resp.raise_for_status()
            installed_models = resp.json().get("models", [])
            metrics["installed_models"] = len(installed_models)
            metrics["model_names"] = [m.get("name", "") for m in installed_models]
        except Exception:
            installed_models = []
            metrics["installed_models"] = 0
            metrics["ollama_available"] = False
            errors.append("Ollama not reachable")

        # Model recommendations based on current landscape
        target_models = [
            {"name": "qwen3-coder:30b", "purpose": "code generation", "size_gb": 18},
            {"name": "deepseek-r1:70b", "purpose": "reasoning/analysis", "size_gb": 40},
            {"name": "phi3:mini", "purpose": "fast inference", "size_gb": 2.3},
            {"name": "gemma3:4b", "purpose": "debate/evaluation", "size_gb": 2.5},
        ]

        installed_names = {m.get("name", "") for m in installed_models}
        for target in target_models:
            base = target["name"].split(":")[0]
            is_installed = any(base in name for name in installed_names)
            if not is_installed and can_expand and target["size_gb"] < free_gb:
                findings.append({
                    "type": "recommendation",
                    "action": "install",
                    "model": target["name"],
                    "purpose": target["purpose"],
                    "size_gb": target["size_gb"],
                })
            elif is_installed:
                findings.append({
                    "type": "status",
                    "action": "installed",
                    "model": target["name"],
                    "purpose": target["purpose"],
                })

        metrics["recommendations"] = len([f for f in findings if f.get("action") == "install"])
        status = "success"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="research/model-scout",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        findings=findings,
        errors=errors,
    )


def run_paper_ingest(payload: dict[str, Any] | None = None) -> TaskResult:
    """Ingest research papers and index for retrieval.

    Checks configured paper feeds, downloads new papers, and stores
    metadata in the vault for searchable access.
    """
    payload = payload or {}
    start = time.time()
    metrics: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        # Check for research ingestion script
        ingest_script = REPO_ROOT / "scripts" / "ingest_research.py"
        if ingest_script.exists():
            import subprocess

            result = subprocess.run(
                ["uv", "run", "python", str(ingest_script)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
            metrics["exit_code"] = result.returncode
            metrics["ingestion_completed"] = result.returncode == 0

            # Parse output for findings
            for line in result.stdout.splitlines():
                if line.strip().startswith("{"):
                    try:
                        findings.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        else:
            metrics["ingestion_completed"] = False
            metrics["note"] = "No ingestion script configured"

        # Check vault for recent research entries
        vault_dir = Path.home() / "vaults" / "cohezion-vault" / "experiments"
        if vault_dir.exists():
            recent_files = sorted(vault_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)[-5:]
            metrics["recent_vault_entries"] = len(recent_files)
        else:
            metrics["recent_vault_entries"] = 0

        status = "success"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="research/paper-ingest",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        findings=findings,
        errors=errors,
    )


def run_experiment_analysis(payload: dict[str, Any] | None = None) -> TaskResult:
    """Analyze recent experiment results and extract insights.

    Scans experiment logs, computes trends, and surfaces actionable
    insights for the compound engineering loop.
    """
    start = time.time()
    metrics: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        # Scan for recent experiment data
        data_dir = REPO_ROOT / "data"
        if data_dir.exists():
            # Pipeline runs
            pipeline_dir = data_dir / "pipeline_runs"
            if pipeline_dir.exists():
                runs = sorted(pipeline_dir.iterdir())
                metrics["total_pipeline_runs"] = len(runs)
                if runs:
                    latest = runs[-1]
                    comparison_file = latest / "comparison.json"
                    if comparison_file.exists():
                        with open(comparison_file) as f:
                            comparison = json.load(f)
                        findings.append({
                            "type": "pipeline_comparison",
                            "run": latest.name,
                            "data": comparison,
                        })

            # FLUME checkpoints
            flume_dir = data_dir / "flume" / "checkpoints"
            if flume_dir.exists():
                checkpoints = list(flume_dir.glob("*.pt"))
                metrics["flume_checkpoints"] = len(checkpoints)

            # RL checkpoints
            rl_dir = data_dir / "rl" / "checkpoints"
            if rl_dir.exists():
                rl_checkpoints = list(rl_dir.glob("*.pt"))
                metrics["rl_checkpoints"] = len(rl_checkpoints)

        # Check vault experiments
        vault_dir = Path.home() / "vaults" / "cohezion-vault" / "experiments"
        if vault_dir.exists():
            experiments = list(vault_dir.glob("*.md"))
            metrics["vault_experiments"] = len(experiments)

        status = "success"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="research/experiment-analysis",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        findings=findings,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_RUNNERS = {
    "model-scout": run_model_scout,
    "paper-ingest": run_paper_ingest,
    "experiment-analysis": run_experiment_analysis,
}


def main() -> None:
    """CLI: ``python -m cohezion.triggers.runners.research <task> [payload_json]``."""
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <{'|'.join(_RUNNERS)}> [payload_json]", file=sys.stderr)
        sys.exit(1)

    task_name = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None

    runner = _RUNNERS.get(task_name)
    if not runner:
        print(f"Unknown task: {task_name}. Available: {list(_RUNNERS)}", file=sys.stderr)
        sys.exit(1)

    result = runner(payload)
    result.emit()
    sys.exit(0 if result.status != "failure" else 1)


if __name__ == "__main__":
    main()
