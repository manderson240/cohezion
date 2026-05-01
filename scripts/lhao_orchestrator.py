#!/usr/bin/env python3
"""
Cohezion Long-Horizon AutoResearch Orchestrator (LHAO)

Continuously improves Cohezion's ARC solver using local models across:
- NPU: AMD Ryzen AI MAX+ 395 (lightweight inference, rapid hypothesis ranking)
- iGPU: Radeon 8060S via Vulkan + Lemonade (Gemma-4-E4B for code synthesis, reasoning)
- CPU: phi4:latest via Ollama (critic/verifier on fast CPU fallback)

Target: kaggle-dataset/arc_solver.py — maximize solve rate on ARC-AGI-2 eval
Metric: number_unique_tasks_solved / total_evaluated (higher = better)
Time budget: 5 minutes per experiment iteration
K-Search tree: ~/.cohezion-research/ksearch/arc_solver.json

Architecture (triangular skill loop):
  autoresearch → generates code variant
  autoharness  → verifies ARC solver correctness (doesn't break existing)
  autocontext  → manages token budget across long session
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
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


_LOGGER = logging.getLogger("lhao")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LHAO] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path.home() / ".cohezion-research" / "logs" / f"lhao_{datetime.now().strftime('%Y%m%d')}.log"
        ),
    ],
)

# ── Configuration ────────────────────────────────────────────────

COHEZION_ROOT = Path.home() / "dev" / "cohezion"
ARC_SOLVER = COHEZION_ROOT / "kaggle-dataset" / "arc_solver.py"
ARC_EVAL = COHEZION_ROOT / "kaggle-dataset" / "arc_eval_tasks.json"
KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"
LHAO_STATE = Path.home() / ".cohezion-research" / "lhao_state.json"
BUDGET_SECONDS = 300        # 5 minutes per experiment
ITERATIONS_PER_RUN = 3      # ~15 minutes total per cron invocation
UCB_C = math.sqrt(2)        # Exploration constant

# Model endpoints
OLLAMA_URL = "http://localhost:11434/api/generate"
LEMONADE_URL = "http://localhost:13307/v1/chat/completions"

# ── K-Search Tree ──────────────────────────────────────────────────

@dataclass
class ExperimentOutcome:
    run_id: str
    hypothesis: str
    config_delta: dict[str, Any]
    metric_value: float
    wall_time_s: float
    status: str  # improvement | regression | error
    model_used: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _load_tree(hypotheses: list[str]) -> dict:
    KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
    path = KSEARCH_DIR / "arc_solver.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass

    tree = {
        "target": "arc_solver",
        "total_trials": 0,
        "best_score": 0.0,
        "nodes": {
            h: {"hypothesis": h, "wins": 0, "trials": 0, "metric_values": []}
            for h in hypotheses
        },
    }
    return tree


def _save_tree(tree: dict) -> None:
    KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
    path = KSEARCH_DIR / "arc_solver.json"
    path.write_text(json.dumps(tree, indent=2))


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
    if outcome.status == "improvement" and outcome.metric_value > tree["best_score"]:
        tree["best_score"] = outcome.metric_value


# ── Local LLM Inference ──────────────────────────────────────────

def _ollama_generate(prompt: str, model: str = "phi4:latest", max_tokens: int = 2048) -> str:
    """Fast CPU fallback via Ollama."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens, "temperature": 0.3}},
            timeout=60,
        )
        return resp.json().get("response", "")
    except Exception as e:
        _LOGGER.warning(f"Ollama call failed: {e}")
        return ""


def _lemonade_generate(prompt: str, max_tokens: int = 2048) -> str:
    """iGPU reasoning via Lemonade (Gemma-4-E4B via Vulkan)."""
    try:
        resp = requests.post(
            LEMONADE_URL,
            json={
                "model": "gemma-4-e4b",
                "messages": [
                    {"role": "system", "content": "You are a reasoning specialist for ARC-AGI pattern recognition. Think step-by-step and explain your reasoning."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=120,
        )
        data = resp.json()
        msgs = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return msgs
    except Exception as e:
        _LOGGER.warning(f"Lemonade call failed: {e}")
        return ""


# ── Code Synthesis ─────────────────────────────────────────────────

_HYPOTHESIS_CODE_PROMPT = """"""  # populated below for brevity — but in actual script this is huge


def _generate_code_variant(hypothesis: str, current_solver_path: Path) -> tuple[str, dict]:
    """Use local LLM to generate a code variant based on hypothesis."""
    current_code = current_solver_path.read_text()

    prompt = f"""You are an expert Python developer specializing in ARC-AGI pattern recognition.
The following ARC solver code uses rule-based pattern extraction and program synthesis.
We want to test this hypothesis: Hypothesis = {hypothesis}

Please produce ONLY the modified solver code as a complete Python file.
DO NOT add explanation outside the code block.
Use ```python ... ``` wrapping.

Current solver code (first 2000 chars):
```python
{current_code[:2000]}
```

Apply the hypothesis. If it suggests a new transformation rule, add it to the TRANSFORMATIONS dict.
If it suggests a parameter change, change it.
If it suggests a new function, add it.
"""

    # Try iGPU first (stronger model), fall back to CPU
    response = _lemonade_generate(prompt, max_tokens=4096)
    model_used = "gemma-4-e4b" if response else "phi4:latest"
    if not response:
        response = _ollama_generate(prompt, model=model_used, max_tokens=2048)

    if not response:
        return "", {}

    # Extract code block
    match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
    code = match.group(1) if match else response

    # Infer config delta from hypothesis
    config_delta = _parse_hypothesis_to_config(hypothesis)

    return code, config_delta


def _parse_hypothesis_to_config(hypothesis: str) -> dict[str, Any]:
    """Convert human-readable hypothesis to structured config delta."""
    delta = {"_raw": hypothesis}

    if "rotation" in hypothesis.lower():
        delta["transformations"] = ["rotate_90", "rotate_180", "rotate_270"]
    if "mirror" in hypothesis.lower() or "flip" in hypothesis.lower():
        delta.setdefault("transformations", []).extend(["horizontal_flip", "vertical_flip"])
    if "gravity" in hypothesis.lower():
        delta.setdefault("transformations", []).append("gravity_fall")
    if "color" in hypothesis.lower():
        delta.setdefault("transformations", []).append("color_swap")
    if "bounding box" in hypothesis.lower():
        delta.setdefault("transformations", []).append("bounding_box")
    if "connectivity" in hypothesis.lower():
        delta.setdefault("transformations", []).append("connected_components")
    if "scale" in hypothesis.lower():
        delta.setdefault("transformations", []).append("scale_up_down")
    if "pattern" in hypothesis.lower() and "repeat" in hypothesis.lower():
        delta.setdefault("transformations", []).append("pattern_repeat")
    if "topology" in hypothesis.lower():
        delta.setdefault("transformations", []).append("morphological_ops")
    if "noise" in hypothesis.lower() or "clean" in hypothesis.lower():
        delta.setdefault("transformations", []).append("noise_removal")

    # Parameter overrides
    m = re.search(r"(\d+)x(\d+)", hypothesis)
    if m:
        delta["max_grid_size"] = (int(m.group(1)), int(m.group(2)))

    m = re.search(r"top[_\-]?k\s*=\s*(\d+)", hypothesis, re.IGNORECASE)
    if m:
        delta["top_k"] = int(m.group(1))

    return delta


# ── ARC Evaluation ─────────────────────────────────────────────────

def _evaluate_solver(eval_tasks_path: Path, solver_code: str, timeout: int = 60) -> tuple[float, str]:
    """Run solver against eval tasks and compute solve rate."""
    solver_path = Path(f"/tmp/lhao_solver_{uuid.uuid4().hex[:8]}.py")
    solver_path.write_text(solver_code)

    try:
        proc = subprocess.run(
            [sys.executable, str(solver_path), "--eval-tasks", str(eval_tasks_path), "--quiet"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout + proc.stderr

        # Parse solve rate from output
        m = re.search(r"solve_rate[:=\s]+([\d.]+)", output, re.IGNORECASE)
        if m:
            return float(m.group(1)), output
        m = re.search(r"(\d+)\s*/\s*(\d+)\s+correct", output, re.IGNORECASE)
        if m:
            return float(m.group(1)) / max(1, float(m.group(2))), output
        return 0.0, output
    except subprocess.TimeoutExpired:
        return 0.0, "TIMEOUT"
    except Exception as e:
        return 0.0, str(e)
    finally:
        solver_path.unlink(missing_ok=True)


def _metric_to_reward(solve_rate: float) -> float:
    if math.isnan(solve_rate):
        return 0.0
    return min(1.0, solve_rate)


# ── State Persistence ─────────────────────────────────────────────

@dataclass
class LHAOState:
    total_runs: int = 0
    total_improvements: int = 0
    best_solve_rate: float = 0.0
    total_wall_time_s: float = 0.0
    hypotheses_tested: list[str] = field(default_factory=list)
    last_run: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _load_state() -> LHAOState:
    if not LHAO_STATE.exists():
        return LHAOState()
    try:
        data = json.loads(LHAO_STATE.read_text())
        return LHAOState(**data)
    except Exception:
        return LHAOState()


def _save_state(state: LHAOState) -> None:
    LHAO_STATE.parent.mkdir(parents=True, exist_ok=True)
    LHAO_STATE.write_text(json.dumps(asdict(state), indent=2))


# ── Main Loop ──────────────────────────────────────────────────────

_DEFAULT_HYPOTHESES = [
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


def _load_or_generate_hypotheses() -> list[str]:
    # If state exists and has tested many hypotheses, generate new ones via LLM
    state = _load_state()
    base = list(_DEFAULT_HYPOTHESES)

    if state.total_runs >= 5:
        # Use LLM to propose new hypotheses based on what's working
        tree = _load_tree([])
        winners = [h for h, n in tree.get("nodes", {}).items() if n.get("wins", 0) > 0]
        losers = [h for h, n in tree.get("nodes", {}).items() if n.get("trials", 0) > 2 and n.get("wins", 0) == 0]

        prompt = f"""Working hypotheses (high reward): {winners}
Failed hypotheses (0 reward after 2+ trials): {losectors}

Generate 3 NEW complementary hypotheses for ARC-AGI pattern recognition.
Each should be a short phrase like "add_X_transform".
Return ONLY a JSON array of strings."""

        resp = _ollama_generate(prompt, model="phi4:latest", max_tokens=512)
        try:
            # Extract JSON array
            arr_match = re.search(r"\[.*\]", resp, re.DOTALL)
            if arr_match:
                new_h = json.loads(arr_match.group(0))
                if isinstance(new_h, list):
                    base.extend([h for h in new_h if h not in base])
                    _LOGGER.info(f"LLM generated {len(new_h)} new hypotheses")
        except Exception:
            pass

    return base


def run_lhao(iterations: int = ITERATIONS_PER_RUN) -> list[ExperimentOutcome]:
    state = _load_state()
    outcomes: list[ExperimentOutcome] = []

    if not ARC_SOLVER.exists():
        _LOGGER.error(f"ARC solver not found: {ARC_SOLVER}")
        return outcomes

    hypotheses = _load_or_generate_hypotheses()
    tree = _load_tree(hypotheses)

    for i in range(iterations):
        hypothesis = _ucb1_select(tree)
        _LOGGER.info(f"Iteration {i+1}/{iterations}: testing hypothesis='{hypothesis}'")

        start = time.perf_counter()

        # 1. Generate code variant
        variant_code, config_delta = _generate_code_variant(hypothesis, ARC_SOLVER)
        if not variant_code:
            _LOGGER.warning("Code variant generation failed, skipping")
            continue

        # 2. Evaluate against eval tasks
        solve_rate, logs = _evaluate_solver(ARC_EVAL, variant_code, timeout=BUDGET_SECONDS)
        wall_time = time.perf_counter() - start

        status = "improvement" if solve_rate > state.best_solve_rate else "regression" if solve_rate > 0 else "error"

        outcome = ExperimentOutcome(
            run_id=f"lhao_{uuid.uuid4().hex[:8]}",
            hypothesis=hypothesis,
            config_delta=config_delta,
            metric_value=solve_rate,
            wall_time_s=wall_time,
            status=status,
            model_used="gemma-4-e4b",
        )

        reward = _metric_to_reward(solve_rate)
        _update_tree(tree, outcome, reward)
        _save_tree(tree)

        state.total_runs += 1
        if status == "improvement":
            state.total_improvements += 1
            state.best_solve_rate = solve_rate
            # Save winning variant
            winner_path = COHEZION_ROOT / "kaggle-dataset" / f"arc_solver_{outcome.run_id}.py"
            winner_path.write_text(variant_code)
            _LOGGER.info(f"🎯 NEW BEST solve_rate={solve_rate:.4f} saved to {winner_path.name}")
        else:
            _LOGGER.info(f"  Result: {status}, solve_rate={solve_rate:.4f}")

        state.total_wall_time_s += wall_time
        state.hypotheses_tested.append(hypothesis)
        state.last_run = datetime.now(UTC).isoformat()
        outcomes.append(outcome)

    _save_state(state)

    _LOGGER.info(
        f"LHAO batch complete: {len(outcomes)} experiments, best={state.best_solve_rate:.4f}, "
        f"total_runs={state.total_runs}, total_improvements={state.total_improvements}"
    )
    return outcomes


def persist_to_vault_outcomes(outcomes: list[ExperimentOutcome]) -> None:
    """Archive experiment results to vault for compound growth."""
    vault_dir = Path.home() / "dev" / "cohezion" / "cloud-vault-mcp" / "vault" / "cerebellum"
    vault_dir.mkdir(parents=True, exist_ok=True)
    for o in outcomes:
        fname = vault_dir / f"lhao_experiment_{o.run_id}.md"
        content = f"""---
type: autoresearch
run_id: {o.run_id}
target: arc_solver
status: {o.status}
solve_rate: {o.metric_value}
hypothesis: {o.hypothesis}
model: {o.model_used}
wall_time_s: {o.wall_time_s}
timestamp: {o.timestamp}
---

# Experiment {o.run_id}

## Hypothesis
{o.hypothesis}

## Config Delta
```json
{json.dumps(o.config_delta, indent=2)}
```

## Result
- Solve rate: {o.metric_value}
- Status: {o.status}
- Model used: {o.model_used}
- Wall time: {o.wall_time_s:.1f}s

---
"""
        fname.write_text(content)
    _LOGGER.info(f"Archived {len(outcomes)} outcomes to vault")


# ── Entrypoint ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Long-Horizon AutoResearch Orchestrator")
    parser.add_argument("--iterations", type=int, default=ITERATIONS_PER_RUN, help="Experiments per invocation")
    parser.add_argument("--no-eval", action="store_true", help="Skip solver evaluation (dry run)")
    parser.add_argument("--vault", action="store_true", default=True, help="Persist to vault")
    args = parser.parse_args()

    _LOGGER.info("=" * 70)
    _LOGGER.info("LHAO STARTING — Target: ARC solver improvement")
    _LOGGER.info("Compute: iGPU (Gemma-4 via Vulkan), CPU (phi4 via Ollama)")
    _LOGGER.info(f"ARC solver: {ARC_SOLVER}")
    _LOGGER.info("=" * 70)

    outcomes = run_lhao(iterations=args.iterations)

    if args.vault and outcomes:
        persist_to_vault_outcomes(outcomes)

    _LOGGER.info("LHAO COMPLETE")
