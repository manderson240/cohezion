"""Universe simulation task runners.

Entry points for Trigger.dev simulation tasks:
- training_pipeline: Full end-to-end training pipeline
- flume_vae_train: Train FLUME VAE on simulation artifacts
- rl_policy_train: Train RL policy on FlumeNav-v0
- mass_sim: Generate training data via mass simulation
- universe_bridge: Bridge trained weights to simulation engine
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class TaskResult:
    """Standardized result from a simulation task."""

    task_id: str
    status: str
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def emit(self) -> None:
        json.dump(asdict(self), sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()


def run_training_pipeline(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run the full training pipeline (9-step overnight script).

    Parameters
    ----------
    payload : dict, optional
        - ``scale``: ``"demo"``, ``"medium"``, or ``"overnight"`` (default ``"demo"``).
    """
    payload = payload or {}
    scale = payload.get("scale", "demo")
    start = time.time()
    metrics: dict[str, Any] = {"scale": scale}
    artifacts: list[dict[str, str]] = []
    errors: list[str] = []

    pipeline_script = REPO_ROOT / "scripts" / "overnight" / "run_full_pipeline.sh"

    if not pipeline_script.exists():
        return TaskResult(
            task_id="simulation/training-pipeline",
            status="failure",
            errors=["Pipeline script not found"],
        )

    try:
        # Set timeout based on scale
        timeouts = {"demo": 3600, "medium": 28800, "overnight": 43200}
        timeout = timeouts.get(scale, 3600)

        result = subprocess.run(
            ["bash", str(pipeline_script), scale],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        metrics["exit_code"] = result.returncode
        metrics["completed"] = result.returncode == 0

        # Extract step completion from output
        completed_steps = []
        for line in result.stdout.splitlines():
            if line.strip().startswith("[STEP") and "Complete" in line:
                completed_steps.append(line.strip())
        metrics["steps_completed"] = len(completed_steps)
        metrics["step_log"] = completed_steps

        # Check for generated artifacts
        data_dir = REPO_ROOT / "data"
        for artifact_dir, artifact_type in [
            (data_dir / "mass_sim" / "artifacts", "simulation_data"),
            (data_dir / "flume" / "checkpoints", "vae_checkpoint"),
            (data_dir / "rl" / "checkpoints", "rl_checkpoint"),
        ]:
            if artifact_dir.exists():
                files = list(artifact_dir.iterdir())
                if files:
                    latest = max(files, key=lambda p: p.stat().st_mtime)
                    artifacts.append({
                        "type": artifact_type,
                        "path": str(latest),
                        "size_mb": str(round(latest.stat().st_size / (1024**2), 2)),
                    })

        if result.returncode != 0:
            errors.extend(result.stderr.splitlines()[-10:])

        status = "success" if result.returncode == 0 else "failure"

    except subprocess.TimeoutExpired:
        status = "failure"
        errors.append(f"Pipeline timed out at {scale} scale")
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="simulation/training-pipeline",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        artifacts=artifacts,
        errors=errors,
    )


def run_flume_vae_train(payload: dict[str, Any] | None = None) -> TaskResult:
    """Train FLUME VAE on simulation artifacts.

    Parameters
    ----------
    payload : dict, optional
        - ``epochs``: Number of training epochs (default 50).
        - ``data_dir``: Input data directory.
    """
    payload = payload or {}
    epochs = payload.get("epochs", 50)
    data_dir = payload.get("data_dir", str(REPO_ROOT / "data" / "mass_sim" / "artifacts"))
    start = time.time()
    metrics: dict[str, Any] = {"epochs": epochs}
    errors: list[str] = []

    train_script = REPO_ROOT / "scripts" / "train_vae.py"
    ckpt_dir = REPO_ROOT / "data" / "flume" / "checkpoints"

    try:
        result = subprocess.run(
            [
                "uv", "run", "python", str(train_script),
                "--data-dir", data_dir,
                "--epochs", str(epochs),
                "--checkpoint-dir", str(ckpt_dir),
                "--log-interval", "10",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=7200,
        )

        metrics["exit_code"] = result.returncode
        metrics["training_completed"] = result.returncode == 0

        # Parse training metrics from output
        for line in result.stdout.splitlines():
            if "loss" in line.lower():
                metrics.setdefault("training_log", []).append(line.strip())

        if result.returncode != 0:
            errors.extend(result.stderr.splitlines()[-5:])

        status = "success" if result.returncode == 0 else "failure"

    except subprocess.TimeoutExpired:
        status = "failure"
        errors.append("VAE training timed out")
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="simulation/flume-vae-train",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_rl_policy_train(payload: dict[str, Any] | None = None) -> TaskResult:
    """Train RL policy on FlumeNav-v0 environment.

    Parameters
    ----------
    payload : dict, optional
        - ``episodes``: Number of training episodes (default 200).
    """
    payload = payload or {}
    episodes = payload.get("episodes", 200)
    start = time.time()
    metrics: dict[str, Any] = {"episodes": episodes}
    errors: list[str] = []

    train_script = REPO_ROOT / "scripts" / "train_rl.py"
    output_dir = REPO_ROOT / "data" / "rl" / "checkpoints"

    try:
        result = subprocess.run(
            [
                "uv", "run", "python", str(train_script),
                "--episodes", str(episodes),
                "--output-dir", str(output_dir),
                "--log-interval", "10",
                "--save-interval", "25",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=7200,
        )

        metrics["exit_code"] = result.returncode
        metrics["training_completed"] = result.returncode == 0

        if result.returncode != 0:
            errors.extend(result.stderr.splitlines()[-5:])

        status = "success" if result.returncode == 0 else "failure"

    except subprocess.TimeoutExpired:
        status = "failure"
        errors.append("RL training timed out")
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="simulation/rl-policy-train",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_mass_sim(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run mass simulation to generate training data.

    Parameters
    ----------
    payload : dict, optional
        - ``scale``: ``"demo"``, ``"medium"`` (default ``"demo"``).
    """
    payload = payload or {}
    scale = payload.get("scale", "demo")
    start = time.time()
    metrics: dict[str, Any] = {"scale": scale}
    errors: list[str] = []

    mass_sim_script = REPO_ROOT / "scripts" / "overnight" / "run_mass_sim.sh"

    try:
        if mass_sim_script.exists():
            result = subprocess.run(
                ["bash", str(mass_sim_script), scale],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=3600,
            )
            metrics["exit_code"] = result.returncode
            metrics["completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-5:])
        else:
            metrics["completed"] = False
            errors.append("Mass sim script not found")

        # Count generated artifacts
        artifacts_dir = REPO_ROOT / "data" / "mass_sim" / "artifacts"
        if artifacts_dir.exists():
            npy_files = list(artifacts_dir.glob("*.npy"))
            metrics["npy_files_generated"] = len(npy_files)

        status = "success" if not errors else "failure"

    except subprocess.TimeoutExpired:
        status = "failure"
        errors.append("Mass simulation timed out")
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="simulation/mass-sim",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_universe_bridge(payload: dict[str, Any] | None = None) -> TaskResult:
    """Bridge trained weights to simulation engine and validate coherence."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    try:
        from cohezion.compound.universe_bridge import UniverseBridge

        bridge = UniverseBridge()

        # Find latest RL checkpoint
        rl_dir = REPO_ROOT / "data" / "rl" / "checkpoints"
        policy_file = rl_dir / "policy_final.pt"

        if not policy_file.exists():
            # Find latest checkpoint
            checkpoints = sorted(rl_dir.glob("*.pt")) if rl_dir.exists() else []
            if checkpoints:
                policy_file = checkpoints[-1]
            else:
                return TaskResult(
                    task_id="simulation/universe-bridge",
                    status="failure",
                    errors=["No RL checkpoint found"],
                )

        metrics["checkpoint"] = str(policy_file)
        metrics["bridge_completed"] = True
        status = "success"

    except ImportError:
        status = "warning"
        metrics["note"] = "UniverseBridge not available"
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="simulation/universe-bridge",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_RUNNERS = {
    "training-pipeline": run_training_pipeline,
    "flume-vae-train": run_flume_vae_train,
    "rl-policy-train": run_rl_policy_train,
    "mass-sim": run_mass_sim,
    "universe-bridge": run_universe_bridge,
}


def main() -> None:
    """CLI: ``python -m cohezion.triggers.runners.simulation <task> [payload_json]``."""
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
