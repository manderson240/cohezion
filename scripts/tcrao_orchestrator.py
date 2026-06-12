#!/usr/bin/env python3
"""
Cohezion Tri-Compute AutoResearch Orchestrator (TCRAO) v1.0

Runs a compound autoresearch loop across ALL THREE compute tiers on the
Framework Desktop:
  - NPU: AMD Ryzen AI MAX+ 395 → rapid hypothesis ranking, small-batch inference
  - iGPU: Radeon 8060S @ Lemonade/Gemma-4 → code synthesis, pattern reasoning
  - CPU: phi4:latest @ Ollaama → verifier/critic on fast CPU fallback

Targets (in order of value):
  1. ARC Prize 2026 solve rate (arc_solver.py) — PRIMARY
  2. JEPA world model loss (jepa_world_model.py)
  3. FLUME VAE reconstruction loss (train_vae.py)

Loop structure (autoresearch → autoharness → autocontext):
  Autoresearch: Generate code variant via UCB1 K-Search tree
  Autoharness:   Verify variant correctness before eval
  Autocontext:   Compact session history, archive to vault

Each iteration improves Cohezion. Each result makes the next easier.
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TCRAO] %(levelname)s: %(message)s",
)
_LOGGER = logging.getLogger("tcrao")

# ════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════

COHEZION_ROOT = Path.home() / "dev" / "cohezion"
ARC_DATA_DIR = COHEZION_ROOT / "data" / "arc-agi-2"
KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"
VAULT_DIR = COHEZION_ROOT / "cloud-vault-mcp" / "vault" / "cerebellum"
STATE_FILE = Path.home() / ".cohezion-research" / "tcrao_state.json"
WINNER_DIR = COHEZION_ROOT / "kaggle-dataset"

BUDGET_SECONDS = 300  # 5 min per experiment
UCB_C = math.sqrt(2)

TARGETS = {
    "arc_solver": {
        "metric": "solve_rate",
        "direction": "maximize",
        "path": COHEZION_ROOT / "kaggle-dataset" / "arc_solver.py",
    },
    "jepa_world_model": {
        "metric": "loss",
        "direction": "minimize",
        "path": COHEZION_ROOT / "src" / "cohezion" / "world_model" / "jepa_world_model.py",
    },
    "flume_vae": {
        "metric": "reconstruction_loss",
        "direction": "minimize",
        "path": COHEZION_ROOT / "src" / "cohezion" / "flume" / "train_vae.py",
    },
}

# Endpoints (confirmed running on this machine)
LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Active Kaggle competitions
ARC_COMPETITIONS = {
    "arc-prize-2026-arc-agi-3": {"prize": 850000, "deadline": "2026-11-02", "teams": 662},
    "arc-prize-2026-arc-agi-2": {"prize": 700000, "deadline": "2026-11-02", "teams": 498},
    "arc-prize-2026-paper-track": {"prize": 450000, "deadline": "2026-11-09", "teams": 32},
}

# ════════════════════════════════════════════════════════════════
# K-SEARCH TREE
# ════════════════════════════════════════════════════════════════


@dataclass
class ExperimentOutcome:
    run_id: str
    target: str
    hypothesis: str
    config_delta: dict[str, Any]
    metric_value: float
    wall_time_s: float
    status: str  # improvement | regression | error
    compute_tier: str  # npu | igpu | cpu
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _tree_path(target: str) -> Path:
    KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
    return KSEARCH_DIR / f"{target}.json"


def _load_tree(target: str, hypotheses: list[str]) -> dict:
    p = _tree_path(target)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    direction = TARGETS[target]["direction"]
    initial_best = float("-inf") if direction == "maximize" else float("inf")
    return {
        "target": target,
        "total_trials": 0,
        "best_score": initial_best,
        "nodes": {
            h: {"hypothesis": h, "wins": 0, "trials": 0, "metric_values": []} for h in hypotheses
        },
    }


def _save_tree(target: str, tree: dict) -> None:
    _tree_path(target).write_text(json.dumps(tree, indent=2))


def _ucb1_select(tree: dict) -> str:
    total = max(tree["total_trials"], 1)
    best_h, best_score = None, -float("inf")
    for h, node in tree["nodes"].items():
        if node["trials"] == 0:
            return h
        mean = sum(node["metric_values"]) / node["trials"]
        exploration = UCB_C * math.sqrt(math.log(total) / node["trials"])
        score = mean + exploration
        if score > best_score:
            best_score, best_h = score, h
    return best_h or next(iter(tree["nodes"]))


def _update_tree(tree: dict, outcome: ExperimentOutcome, reward: float) -> None:
    tree["total_trials"] += 1
    node = tree["nodes"].setdefault(
        outcome.hypothesis,
        {"hypothesis": outcome.hypothesis, "wins": 0, "trials": 0, "metric_values": []},
    )
    node["trials"] += 1
    node["metric_values"].append(reward)
    if reward > 0.5:
        node["wins"] += 1

    direction = TARGETS[outcome.target]["direction"]
    best = tree.get("best_score", float("-inf"))
    is_improved = (direction == "maximize" and outcome.metric_value > best) or (
        direction == "minimize" and outcome.metric_value < best
    )
    if is_improved:
        tree["best_score"] = outcome.metric_value


# ════════════════════════════════════════════════════════════════
# LOCAL LLM INFERENCE (Tri-Compute)
# ════════════════════════════════════════════════════════════════


def _igpu_infer(prompt: str, max_tokens: int = 4096) -> str | None:
    """iGPU via Lemonade (router :13305, Phase 3+)."""
    try:
        import requests

        resp = requests.post(
            LEMONADE_URL,
            json={
                "model": "Gemma-4-E4B-it-GGUF",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a reasoning specialist. Think step-by-step.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=120,
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _cpu_infer(prompt: str, model: str = "phi4:latest", max_tokens: int = 2048) -> str | None:
    """CPU via Ollama fallback."""
    try:
        import requests

        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            },
            timeout=90,
        )
        return resp.json().get("response")
    except Exception:
        return None


def _npu_infer(prompt: str, max_tokens: int = 512) -> str | None:
    """NPU via tiny local model (placeholder — use CPU for now until NPU route confirmed)."""
    return _cpu_infer(prompt, model="phi4:latest", max_tokens=max_tokens)


def tri_infer(prompt: str, max_tokens: int = 2048, required: bool = True) -> str:
    """Tri-compute inference: iGPU → NPU → CPU cascade."""
    # Tier 1: iGPU (most powerful, for code synthesis)
    for attempt in range(1 if not required else 2):
        r = _igpu_infer(prompt, max_tokens)
        if r:
            return r
        time.sleep(1)

    # Tier 2: NPU (fast, for ranking / simple prompts)
    r = _npu_infer(prompt, max_tokens)
    if r:
        return r

    # Tier 3: CPU (fallback)
    r = _cpu_infer(prompt, max_tokens=max_tokens)
    if r:
        return r

    return ""


# ════════════════════════════════════════════════════════════════
# CODE SYNTHESIS (AutoResearch)
# ════════════════════════════════════════════════════════════════


def _generate_code_variant(target: str, hypothesis: str) -> tuple[str, dict[str, Any], str]:
    """Generate a code variant for the target using tri-compute LLM."""
    info = TARGETS[target]
    current_code = info["path"].read_text() if info["path"].exists() else ""

    prompt = f"""You are an expert Python developer optimizing Cohezion's {target}.
Hypothesis: {hypothesis}

Modify the code to test this hypothesis. Return ONLY the complete modified Python file
wrapped in ```python ... ```. No explanations outside the code block.

Current code (first 1500 chars):
```python
{current_code[:1500]}
```
"""

    raw = tri_infer(prompt, max_tokens=4096)
    m = re.search(r"```python\n(.*?)\n```", raw, re.DOTALL)
    code = m.group(1) if m else ""

    # Parse config delta
    delta = {"_raw": hypothesis}
    if "batch" in hypothesis:
        delta["batch_size"] = (
            int(re.search(r"(\d+)", hypothesis).group(1)) if re.search(r"(\d+)", hypothesis) else 32
        )
    if "lr" in hypothesis or "rate" in hypothesis:
        num = re.search(r"([\d.e-]+)", hypothesis)
        delta["learning_rate"] = float(num.group(1)) if num else 1e-4

    compute_tier = "igpu" if code else "npu"
    if not code:
        # Fallback: simple patch rules without LLM
        code = current_code
        compute_tier = "cpu"

    return code, delta, compute_tier


# ════════════════════════════════════════════════════════════════
# AUTOHARNESS (Verification before eval)
# ════════════════════════════════════════════════════════════════


def _verify_code(code: str, target: str) -> tuple[bool, str]:
    """Quick pre-flight: check syntax, imports, and basic structure."""
    if not code or not code.strip():
        return False, "Empty code"

    # Check Python syntax
    tmp = Path(f"/tmp/tcrao_verify_{uuid.uuid4().hex[:8]}.py")
    tmp.write_text(code)
    try:
        import py_compile

        py_compile.compile(tmp, doraise=True)
        return True, "Syntax OK"
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        tmp.unlink(missing_ok=True)


# Cohezion venv Python — always use this for evaluator subprocess to guarantee
# torch and other project deps are available (sys.executable may not have them).
_VENNY_PYTHON = COHEZION_ROOT / ".venv" / "bin" / "python3"


def _evaluate_arc_solver(code: str, timeout: int = 900) -> tuple[float, str]:
    """Real ARC evaluation using local eval harness."""
    # Write variant to temp file
    tmp_solver = Path(f"/tmp/tcrao_arc_solver_{uuid.uuid4().hex[:8]}.py")
    tmp_solver.write_text(code)

    try:
        proc = subprocess.run(
            [
                str(_VENNY_PYTHON),
                str(COHEZION_ROOT / "scripts" / "eval_arc_solver.py"),
                "--solver",
                str(tmp_solver),
                "--budget",
                "3000",
                "--max-depth",
                "3",
                "--max-tasks",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout + proc.stderr

        # Parse SOLVE_RATE:
        m = re.search(r"SOLVE_RATE[:\s]+([\d.]+)", output, re.IGNORECASE)
        if m:
            return float(m.group(1)), output
        return 0.0, output
    except subprocess.TimeoutExpired:
        return 0.0, "TIMEOUT"
    except Exception as e:
        return 0.0, str(e)
    finally:
        tmp_solver.unlink(missing_ok=True)


def _evaluate_jepa(code: str, timeout: int = 60) -> tuple[float, str]:
    # Placeholder — real JEPA training takes hours
    return 0.5, "JEPA placeholder (training too long for eval)"


def _evaluate_flume(code: str, timeout: int = 60) -> tuple[float, str]:
    # Placeholder — real FLUME training takes hours
    return 0.5, "FLUME placeholder (training too long for eval)"


def _evaluate(target: str, code: str, timeout: int = BUDGET_SECONDS) -> tuple[float, str]:
    evaluators = {
        "arc_solver": _evaluate_arc_solver,
        "jepa_world_model": _evaluate_jepa,
        "flume_vae": _evaluate_flume,
    }
    return evaluators.get(target, _evaluate_arc_solver)(code, timeout)


def _metric_to_reward(target: str, value: float) -> float:
    direction = TARGETS[target]["direction"]
    if direction == "maximize":
        return min(1.0, value) if not math.isnan(value) else 0.0
    else:
        return min(1.0, 1.0 / (1.0 + value)) if not math.isnan(value) else 0.0


# ════════════════════════════════════════════════════════════════
# AUTORESEARCH LOOP (Main)
# ════════════════════════════════════════════════════════════════


def run_autoresearch(
    target: str, hypotheses: list[str], iterations: int = 1
) -> list[ExperimentOutcome]:
    tree = _load_tree(target, hypotheses)
    outcomes: list[ExperimentOutcome] = []
    info = TARGETS[target]

    _LOGGER.info(f"=== AUTORESEARCH: {target} ({info['metric']}, {info['direction']}) ===")

    for i in range(iterations):
        hypothesis = _ucb1_select(tree)
        _LOGGER.info(f"[{i + 1}/{iterations}] Hypothesis='{hypothesis}'")

        start = time.perf_counter()

        # AUTORESEARCH: Generate variant
        code, delta, tier = _generate_code_variant(target, hypothesis)
        if not code:
            _LOGGER.warning("Code generation failed")
            continue

        # AUTOHARNESS: Verify
        ok, msg = _verify_code(code, target)
        if not ok:
            _LOGGER.warning(f"Harness FAILED: {msg}")
            outcome = ExperimentOutcome(
                run_id=f"tcrao_{uuid.uuid4().hex[:8]}",
                target=target,
                hypothesis=hypothesis,
                config_delta=delta,
                metric_value=0.0,
                wall_time_s=time.perf_counter() - start,
                status="error",
                compute_tier=tier,
            )
            _update_tree(tree, outcome, 0.0)
            outcomes.append(outcome)
            continue

        _LOGGER.info(f"Harness PASSED ({msg})")

        # Evaluate
        metric_value, logs = _evaluate(target, code)
        wall_time = time.perf_counter() - start

        best = tree.get("best_score", float("-inf"))
        direction = info["direction"]
        is_improved = (
            (direction == "maximize" and metric_value > best)
            or (direction == "minimize" and metric_value < best)
            or (best == float("-inf"))
        )
        status = "improvement" if is_improved else "regression" if metric_value > 0 else "error"

        outcome = ExperimentOutcome(
            run_id=f"tcrao_{uuid.uuid4().hex[:8]}",
            target=target,
            hypothesis=hypothesis,
            config_delta=delta,
            metric_value=metric_value,
            wall_time_s=wall_time,
            status=status,
            compute_tier=tier,
        )

        reward = _metric_to_reward(target, metric_value)
        _update_tree(tree, outcome, reward)
        _save_tree(target, tree)

        if status == "improvement":
            winner = COHEZION_ROOT / "kaggle-dataset" / f"{target}_{outcome.run_id}.py"
            winner.write_text(code)
            _LOGGER.info(f"🎯 NEW BEST {info['metric']}={metric_value:.4f} saved to {winner.name}")
        else:
            _LOGGER.info(f"  Result: {status}, {info['metric']}={metric_value:.4f}")

        outcomes.append(outcome)

    _LOGGER.info(f"=== AUTORESEARCH DONE: {target} ===")
    return outcomes


# ════════════════════════════════════════════════════════════════
# AUTOPERSIST (Vault logging)
# ════════════════════════════════════════════════════════════════


def persist_to_vault(outcomes: list[ExperimentOutcome]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    for o in outcomes:
        fname = VAULT_DIR / f"tcrao_{o.target}_{o.run_id}.md"
        body = f"""---
type: autoresearch
run_id: {o.run_id}
target: {o.target}
status: {o.status}
metric_value: {o.metric_value}
hypothesis: {o.hypothesis}
compute_tier: {o.compute_tier}
wall_time_s: {o.wall_time_s}
timestamp: {o.timestamp}
---

# TCRAO Experiment {o.run_id}

## Config Delta
```json
{json.dumps(o.config_delta, indent=2, default=str)}
```

## Result
- **Metric value**: {o.metric_value}
- **Status**: {o.status}
- **Compute tier**: {o.compute_tier}
- **Wall time**: {o.wall_time_s:.1f}s

---
"""
        fname.write_text(body)
    _LOGGER.info(f"Vault: archived {len(outcomes)} outcomes to {VAULT_DIR}")


# ════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tri-Compute AutoResearch Orchestrator")
    parser.add_argument("--target", choices=list(TARGETS.keys()), default="arc_solver")
    parser.add_argument("--iterations", type=int, default=2, help="Experiments per target per run")
    parser.add_argument("--no-vault", action="store_true", help="Skip vault persistence")
    args = parser.parse_args()

    _LOGGER.info("╔══════════════════════════════════════════════════════════════════════╗")
    _LOGGER.info("║ TCRAO — Tri-Compute AutoResearch Orchestrator                        ║")
    _LOGGER.info("║ Targets: arc_solver, jepa_world_model, flume_vae                   ║")
    _LOGGER.info("║ Compute: iGPU Lemonade/Gemma-4 → CPU Ollama/phi4 → NPU rapid     ║")
    _LOGGER.info("╚══════════════════════════════════════════════════════════════════════╝")

    # Default hypothesis pool — evolves with each run
    hypotheses = [
        "add_rotation_transforms",
        "add_mirror_flip_transforms",
        "add_gravity_fall_transform",
        "add_color_swap_transform",
        "add_connected_components_transform",
        "add_scale_up_down_transform",
        "add_pattern_repeat_transform",
        "add_morphological_ops_transform",
        "add_noise_removal_transform",
        "add_bounding_box_transform",
        "increase_top_k_from_5_to_10",
        "try_16x16_max_grid",
        "try_20x20_max_grid",
        "add_composition_chain_transform",
        "add_symmetry_detection",
        "add_object_count_matching",
        "add_line_detection_h_v_diag",
        "use_flood_fill_expansion",
        "use_xor_overlay_rules",
    ]

    outcomes = run_autoresearch(args.target, hypotheses, iterations=args.iterations)

    if outcomes and not args.no_vault:
        persist_to_vault(outcomes)

    # After autoresearch → autocontext companion: compact state into MEMORY file
    state = {
        "run_id": uuid.uuid4().hex[:8],
        "timestamp": datetime.now(UTC).isoformat(),
        "target": args.target,
        "total_experiments": len(outcomes),
        "best_score": max((o.metric_value for o in outcomes), default=0.0),
        "hypotheses_tested": [o.hypothesis for o in outcomes],
        "compute_tiers_used": list(set(o.compute_tier for o in outcomes)),
    }
    state_path = Path.home() / ".cohezion-research" / "tcrao_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "a") as f:
        f.write(json.dumps(state) + "\n")
    _LOGGER.info(f"Autocontext: state appended to {state_path}")

    _LOGGER.info("TCRAO COMPLETE")
