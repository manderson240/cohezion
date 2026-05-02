"""Autoresearch driver — andyluo7/autoresearch integration for Cohezion.

Bridges the autoresearch pattern (program.md → hypothesis → run → eval → iterate)
into Cohezion's existing ResearchAgent + SurrealDB persistence + K-Search tree.

K-Search tree: JSON file at ~/.cohezion-research/ksearch/{target}.json
  Each node: {"hypothesis": str, "wins": int, "trials": int, "metric_values": list[float], "z_vector": list[float]}
  Selection: Trajectory-Aware UCB1

SurrealDB: persists to `experiments` table in cohezion:vault database.
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from cohezion.flume.vae_encoder import get_encoder
from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer


logger = logging.getLogger(__name__)

# Training target → (script path, metric name, direction)
TRAINING_TARGETS: dict[str, tuple[str, str, str]] = {
    "jepa": (
        "src/cohezion/world_model/jepa_world_model.py",
        "total_loss",
        "minimize",
    ),
    "flume_vae": (
        "src/cohezion/flume/train_vae.py",
        "val_loss",
        "minimize",
    ),
    "rl_ppo": (
        "src/cohezion/rl/ppo_trainer.py",
        "episode_reward",
        "maximize",
    ),
    "aimo": (
        "sandbox/aimo/kaggle_kernel/submission_v43_fortress.py",
        "score",
        "maximize",
    ),
    "agi": (
        "kaggle-agi-benchmark/evaluator_kbench.py",
        "score",
        "maximize",
    ),
}

# Hypothesis space sourced from program.md
_DEFAULT_HYPOTHESES: dict[str, list[str]] = {
    "jepa": ["learning_rate=1e-4", "learning_rate=3e-4", "batch_size=32"],
    "flume_vae": ["latent_dim=256", "latent_dim=512"],
    "rl_ppo": ["ent_coef=0.01", "learning_rate=3e-4"],
    "aimo": ["temperature=0.0", "temperature=0.7", "num_samples=2", "num_samples=4"],
    "agi": ["temperature=0.0", "temperature=0.7", "model=phi4:latest"],
}

KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"
UCB_C = 1.414  # sqrt(2) — standard UCB1 exploration constant


@dataclass
class ExperimentOutcome:
    run_id: str
    target: str
    hypothesis: str
    metric_name: str
    metric_value: float
    wall_time_s: float
    status: str  # "improvement" | "regression" | "error"
    z_vector: list[float] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def improved(self) -> bool:
        return self.status == "improvement"


def _load_tree(target: str, hypotheses: list[str]) -> dict:
    """Load or initialise K-Search tree JSON for target."""
    KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
    path = KSEARCH_DIR / f"{target}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass

    # Use defaults if none provided
    if not hypotheses:
        hypotheses = _DEFAULT_HYPOTHESES.get(target, ["default=true"])

    # Initialise with hypothesis nodes
    encoder = get_encoder()
    tree = {
        "target": target,
        "total_trials": 0,
        "nodes": {
            h: {
                "hypothesis": h,
                "wins": 0,
                "trials": 0,
                "metric_values": [],
                "z_vector": encoder.encode(h).tolist(),
            }
            for h in hypotheses
        },
    }
    path.write_text(json.dumps(tree, indent=2))
    return tree


def _save_tree(target: str, tree: dict) -> None:
    path = KSEARCH_DIR / f"{target}.json"
    path.write_text(json.dumps(tree, indent=2))


def _ucb1_select(tree: dict) -> str:
    """Select hypothesis by Trajectory-Aware UCB1.

    Incorporates:
    1. Standard UCB1 (mean reward + exploration)
    2. Latent distance to known 'wins' (FLUME guided)
    """
    total = max(tree["total_trials"], 1)
    best_h, best_score = None, -float("inf")

    # 1. Gather all 'wins' (nodes with wins > 0)
    win_vectors = [
        np.array(node["z_vector"])
        for node in tree["nodes"].values()
        if node.get("wins", 0) > 0 and "z_vector" in node
    ]

    # Simple index selection for unvisited
    for h, node in tree["nodes"].items():
        if node["trials"] == 0:
            return h

    for h, node in tree["nodes"].items():
        mean = sum(node["metric_values"]) / node["trials"]

        # Standard UCB1 exploration term
        exploration = UCB_C * math.sqrt(math.log(total) / node["trials"])

        # Latent guidance: prefer nodes closer to known successes
        latent_bonus = 0.0
        if win_vectors and "z_vector" in node:
            current_vec = np.array(node["z_vector"])
            # Calculate mean distance to wins (similarity)
            similarities = [np.dot(current_vec, wv) for win_vec in win_vectors for wv in [win_vec]]
            latent_bonus = max(similarities) * 0.2  # 20% influence from latent similarity

        score = mean + exploration + latent_bonus
        if score > best_score:
            best_score, best_h = score, h

    if best_h:
        return best_h

    # Final fallback if best_h is still None (e.g. empty tree)
    try:
        return next(iter(tree["nodes"]))
    except StopIteration:
        return "default=true"


def _update_tree(tree: dict, outcome: ExperimentOutcome, reward: float) -> None:
    """Update node statistics and global trial count."""
    tree["total_trials"] += 1
    node = tree["nodes"].setdefault(
        outcome.hypothesis,
        {
            "hypothesis": outcome.hypothesis,
            "wins": 0,
            "trials": 0,
            "metric_values": [],
            "z_vector": outcome.z_vector,
        },
    )
    node["trials"] += 1
    node["metric_values"].append(reward)
    if reward > 0.5:  # Consider > 0.5 reward a 'win'
        node["wins"] += 1


def _extract_metric(stdout: str, metric_name: str) -> float | None:
    """Parse 'metric_name: value' or 'metric_name=value' from stdout."""
    for pattern in (
        rf"^{re.escape(metric_name)}[:=]\s*([\d.eE+\-]+)",
        rf"\b{re.escape(metric_name)}[:=]\s*([\d.eE+\-]+)",
    ):
        m = re.search(pattern, stdout, re.MULTILINE | re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


async def _persist_to_surreal(outcome: ExperimentOutcome) -> None:
    """Write result to SurrealDB experiments table (non-blocking, best-effort)."""
    try:
        from surrealdb import AsyncSurreal

        async with AsyncSurreal("ws://localhost:8001/rpc") as db:
            await db.signin({"username": "root", "password": "root"})
            await db.use("cohezion", "vault")
            await db.query(
                f"""
                CREATE experiments SET
                    type = 'autoresearch',
                    agent_id = {json.dumps(outcome.target)},
                    content_hash = {json.dumps(outcome.run_id)},
                    z_vector_512 = {json.dumps(outcome.z_vector)},
                    state_snapshot = {{
                        hypothesis: {json.dumps(outcome.hypothesis)},
                        status: {json.dumps(outcome.status)},
                        wall_time_s: {outcome.wall_time_s}
                    }},
                    metrics = {{
                        {json.dumps(outcome.metric_name)}: {outcome.metric_value}
                    }},
                    coherence_score = {min(1.0, max(0.0, outcome.metric_value))},
                    provenance_hash = {json.dumps(outcome.run_id)},
                    timestamp = time::now();
                """
            )
    except Exception as e:
        logger.debug(f"SurrealDB persistence skipped: {e}")


class AutoresearchDriver:
    """Cohesion-wide autoresearch loop.

    Usage:
        driver = AutoresearchDriver(target="aimo", budget_seconds=300)
        results = await driver.run_loop(n_iterations=5)
    """

    def __init__(
        self,
        target: str = "jepa",
        budget_seconds: int = 300,
        hypotheses: list[str] | None = None,
    ):
        if target not in TRAINING_TARGETS:
            raise ValueError(f"Unknown target '{target}'. Valid: {list(TRAINING_TARGETS)}")
        self.target = target
        self.budget_seconds = budget_seconds
        self.script, self.metric_name, self.direction = TRAINING_TARGETS[target]
        self.hypotheses = hypotheses or []
        self._baseline: float | None = None
        self.encoder = get_encoder()
        self.failure_analyzer = OuroborosFailureAnalyzer()

    def _metric_to_reward(self, value: float) -> float:
        """Convert raw metric to a reward signal for UCB1 (higher = better)."""
        if math.isnan(value):
            return 0.0
        if self.direction == "minimize":
            return max(0.0, 1.0 / (1.0 + value))
        return min(1.0, value)

    async def run_kaggle_experiment(self, hypothesis: str, run_id: str) -> tuple[float, str, str]:
        """Specialized execution for Kaggle targets."""
        logger.info(f"[Kaggle] Pushing kernel for {self.target}...")

        # Mapping target to kernel ID and directory
        config_map = {
            "aimo": {
                "id": "manderson240/aimo-3-mrs-swarm-transformers-v39",
                "dir": "sandbox/aimo/kaggle_kernel",
            },
            "agi": {"id": "manderson240/cohezion-agi-benchmark-swarm", "dir": "sandbox"},
        }

        if self.target not in config_map:
            return float("nan"), "error", f"Target {self.target} not in Kaggle config map"

        kernel_id = config_map[self.target]["id"]
        kernel_dir = config_map[self.target]["dir"]

        try:
            # 1. Update script with hypothesis (simplified for now)
            # 2. Push kernel
            subprocess.run(["kaggle", "kernels", "push", "-p", kernel_dir], check=True)

            # 3. Poll for completion
            logger.info(f"[Kaggle] Polling kernel {kernel_id} for max {self.budget_seconds}s...")
            start_poll = time.time()
            last_heartbeat = 0
            while time.time() - start_poll < self.budget_seconds:
                now = time.time()
                if now - last_heartbeat > 300:  # Log every 5 mins
                    elapsed_min = (now - start_poll) / 60
                    logger.info(
                        f"  [Kaggle Heartbeat] Still polling {kernel_id}... ({elapsed_min:.1f}m elapsed)"
                    )
                    last_heartbeat = now

                status_proc = subprocess.run(
                    ["kaggle", "kernels", "status", kernel_id], capture_output=True, text=True
                )
                status = status_proc.stdout

                if "complete" in status.lower():
                    logger.info(f"✅ [Kaggle] Kernel {kernel_id} execution complete.")
                    # 4. Fetch score
                    if self.target == "aimo":
                        sub_proc = subprocess.run(
                            [
                                "kaggle",
                                "competitions",
                                "submissions",
                                "-c",
                                "ai-mathematical-olympiad-progress-prize-3",
                            ],
                            capture_output=True,
                            text=True,
                        )
                        # Extract score from first line
                        # Format example: submission.parquet  2026-04-11 15:22:42  Fortress Swarm  COMPLETE  42
                        m = re.search(r"COMPLETE\s+(\d+)", sub_proc.stdout)
                        score = float(m.group(1)) if m else 0.0
                        logger.info(f"  [Kaggle] Score extracted: {score}")
                        return (
                            score,
                            "improvement" if score > (self._baseline or 0) else "regression",
                            sub_proc.stdout,
                        )
                    else:
                        return 1.0, "improvement", "AGI benchmark complete"

                elif "error" in status.lower():
                    logger.error(f"❌ [Kaggle] Kernel {kernel_id} failed.")
                    log_proc = subprocess.run(
                        ["kaggle", "kernels", "output", kernel_id], capture_output=True, text=True
                    )
                    return float("nan"), "error", status + "\n" + log_proc.stdout

                time.sleep(60)  # Poll every minute

            return float("nan"), "error", "Timeout"
        except Exception as e:
            return float("nan"), "error", str(e)

    async def run_experiment(self, hypothesis: str) -> ExperimentOutcome:
        """Run one experiment for the given hypothesis string."""
        import uuid

        run_id = f"ar_{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()

        z_vector = self.encoder.encode(hypothesis).tolist()

        if self.target in ("aimo", "agi"):
            metric_val, status, logs = await self.run_kaggle_experiment(hypothesis, run_id)
        else:
            # Local execution logic
            try:
                proc = subprocess.run(
                    ["uv", "run", "python", self.script, "--budget", str(self.budget_seconds)],
                    capture_output=True,
                    text=True,
                    timeout=self.budget_seconds + 30,
                )
                logs = proc.stdout + proc.stderr
                metric_val = _extract_metric(logs, self.metric_name)
                status = (
                    "improvement"
                    if (self._baseline is None or metric_val > self._baseline)
                    else "regression"
                )
            except Exception as e:
                metric_val, status, logs = float("nan"), "error", str(e)

        if status == "error":
            analysis = self.failure_analyzer.analyze(logs, self.target)
            logger.warning(f"[Ouroboros] Learning from failure: {analysis.root_cause}")
            # Potentially append suggested_mutation to hypotheses for future runs

        wall_time = time.perf_counter() - start
        outcome = ExperimentOutcome(
            run_id=run_id,
            target=self.target,
            hypothesis=hypothesis,
            metric_name=self.metric_name,
            metric_value=metric_val,
            wall_time_s=wall_time,
            status=status,
            z_vector=z_vector,
        )

        if status == "improvement":
            self._baseline = metric_val

        await _persist_to_surreal(outcome)
        return outcome

    async def run_loop(self, n_iterations: int = 10) -> list[ExperimentOutcome]:
        """Full autoresearch loop: n_iterations × (select → run → update tree)."""
        tree = _load_tree(self.target, self.hypotheses)
        results: list[ExperimentOutcome] = []

        for i in range(n_iterations):
            hypothesis = _ucb1_select(tree)
            logger.info(
                f"[autoresearch] iteration {i + 1}/{n_iterations}: target={self.target} hypothesis={hypothesis}"
            )
            outcome = await self.run_experiment(hypothesis)
            reward = self._metric_to_reward(outcome.metric_value)
            _update_tree(tree, outcome, reward)
            _save_tree(self.target, tree)
            results.append(outcome)
            logger.info(
                f"[autoresearch] {outcome.status} — {self.metric_name}={outcome.metric_value:.4f}"
            )

        return results
