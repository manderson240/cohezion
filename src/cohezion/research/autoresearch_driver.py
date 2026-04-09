"""Autoresearch driver — andyluo7/autoresearch integration for Cohezion.

Bridges the autoresearch pattern (program.md → hypothesis → run → eval → iterate)
into Cohezion's existing ResearchAgent + SurrealDB persistence + K-Search tree.

K-Search tree: JSON file at ~/.cohezion-research/ksearch/{target}.json
  Each node: {"hypothesis": str, "wins": int, "trials": int, "metric_values": list[float]}
  Selection: UCB1 = mean_metric + C * sqrt(log(total_trials) / node_trials)

SurrealDB: persists to `experiments` table in cohezion:vault database.
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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
}

# Hypothesis space sourced from program.md (populated by parse_program)
_DEFAULT_HYPOTHESES: list[str] = [
    "learning_rate=1e-4",
    "learning_rate=3e-4",
    "learning_rate=1e-3",
    "batch_size=16",
    "batch_size=32",
    "batch_size=64",
    "hidden_dim=128",
    "hidden_dim=256",
    "hidden_dim=512",
]

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
    # Initialise with hypothesis nodes
    tree = {
        "target": target,
        "total_trials": 0,
        "nodes": {
            h: {"hypothesis": h, "wins": 0, "trials": 0, "metric_values": []} for h in hypotheses
        },
    }
    path.write_text(json.dumps(tree, indent=2))
    return tree


def _save_tree(target: str, tree: dict) -> None:
    path = KSEARCH_DIR / f"{target}.json"
    path.write_text(json.dumps(tree, indent=2))


def _ucb1_select(tree: dict) -> str:
    """Select hypothesis by UCB1 — prefers unexplored nodes, then best upper bound."""
    total = max(tree["total_trials"], 1)
    best_h, best_score = None, -float("inf")
    for h, node in tree["nodes"].items():
        if node["trials"] == 0:
            return h  # Always explore unvisited first
        mean = sum(node["metric_values"]) / node["trials"]
        score = mean + UCB_C * math.sqrt(math.log(total) / node["trials"])
        if score > best_score:
            best_score, best_h = score, h
    return best_h or next(iter(tree["nodes"]))


def _update_tree(tree: dict, hypothesis: str, reward: float) -> None:
    """Update node statistics and global trial count."""
    tree["total_trials"] += 1
    node = tree["nodes"].setdefault(
        hypothesis, {"hypothesis": hypothesis, "wins": 0, "trials": 0, "metric_values": []}
    )
    node["trials"] += 1
    node["metric_values"].append(reward)
    if reward > 0:
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
                    z_vector_512 = [],
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
        driver = AutoresearchDriver(target="jepa", budget_seconds=60)
        results = await driver.run_loop(n_iterations=5)
    """

    def __init__(
        self,
        target: str = "jepa",
        budget_seconds: int = 300,
        hypotheses: list[str] | None = None,
        patch_fn: Callable[[str, dict], dict] | None = None,
    ):
        if target not in TRAINING_TARGETS:
            raise ValueError(f"Unknown target '{target}'. Valid: {list(TRAINING_TARGETS)}")
        self.target = target
        self.budget_seconds = budget_seconds
        self.script, self.metric_name, self.direction = TRAINING_TARGETS[target]
        self.hypotheses = hypotheses or _DEFAULT_HYPOTHESES
        self.patch_fn = patch_fn  # optional config patcher
        self._baseline: float | None = None

    def _metric_to_reward(self, value: float) -> float:
        """Convert raw metric to a reward signal for UCB1 (higher = better)."""
        if self.direction == "minimize":
            # Invert: lower loss → higher reward. Clip to [0,1].
            return max(0.0, 1.0 - value) if value <= 1.0 else max(0.0, 1.0 / (1.0 + value))
        return min(1.0, value)  # maximize: clip at 1

    async def run_experiment(self, hypothesis: str) -> ExperimentOutcome:
        """Run one experiment for the given hypothesis string."""
        import uuid

        run_id = f"ar_{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()

        env_override = {}
        if "=" in hypothesis:
            key, val = hypothesis.split("=", 1)
            env_override[key.upper()] = val

        try:
            import os

            proc_env = {**os.environ, **env_override}
            proc = subprocess.run(
                ["uv", "run", "python", self.script, "--budget", str(self.budget_seconds)],
                capture_output=True,
                text=True,
                timeout=self.budget_seconds + 30,
                env=proc_env,
                cwd=str(Path(__file__).parents[4]),  # repo root
            )
            stdout = proc.stdout + proc.stderr
            metric_val = _extract_metric(stdout, self.metric_name)

            if metric_val is None:
                logger.debug(
                    f"[autoresearch] No metric found for {hypothesis}; stdout[:200]: {stdout[:200]}"
                )
                metric_val = float("nan")
                status = "error"
            else:
                if self._baseline is None:
                    self._baseline = metric_val
                    status = "improvement"
                elif self.direction == "minimize":
                    status = "improvement" if metric_val < self._baseline * 0.995 else "regression"
                else:
                    status = "improvement" if metric_val > self._baseline * 1.005 else "regression"
                if status == "improvement":
                    self._baseline = metric_val

        except subprocess.TimeoutExpired:
            metric_val, status = float("nan"), "error"
            stdout = ""
        except Exception as exc:
            logger.warning(f"[autoresearch] run_experiment failed: {exc}")
            metric_val, status = float("nan"), "error"

        wall_time = time.perf_counter() - start
        outcome = ExperimentOutcome(
            run_id=run_id,
            target=self.target,
            hypothesis=hypothesis,
            metric_name=self.metric_name,
            metric_value=metric_val,
            wall_time_s=wall_time,
            status=status,
        )
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
            reward = (
                self._metric_to_reward(outcome.metric_value)
                if not math.isnan(outcome.metric_value)
                else 0.0
            )
            _update_tree(tree, hypothesis, reward)
            _save_tree(self.target, tree)
            results.append(outcome)
            logger.info(
                f"[autoresearch] {outcome.status} — {self.metric_name}={outcome.metric_value:.4f} "
                f"({outcome.wall_time_s:.1f}s)"
            )

        improvements = sum(1 for r in results if r.improved())
        logger.info(
            f"[autoresearch] done: {improvements}/{n_iterations} improvements for target={self.target}"
        )
        return results
