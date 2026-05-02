#!/usr/bin/env python3
"""
ARC Prize AutoResearch Orchestrator (ARPAO) v2.0

Continuously improves the ARC solver using local tri-compute (NPU/iGPU/CPU)
and submits to Kaggle for real leaderboard feedback.

Targets (in priority order):
  1. ARC Prize AGI-3 ($850K, 662 teams) — PRIMARY
  2. ARC Prize AGI-2 ($700K, 498 teams) — SECONDARY
  3. ARC Prize Paper Track ($450K, 32 teams) — EASIEST PLACE

Loop:
  1. Autoresearch: UCB1 selects hypothesis, LLM synthesizes code variant
  2. Autoharness: syntax check before running
  3. Local eval: eval_arc_solver.py on 120 eval tasks
  4. Kaggle gate: if solve_rate > threshold, push to Kaggle kernel
  5. Autocontext: archive to vault + update K-Search tree

Score-as-Reward: solve_rate feeds UCB1 directly
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ARPAO] %(levelname)s: %(message)s",
)
_LOGGER = logging.getLogger("arpao")

# ════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════

COHEZION_ROOT = Path.home() / "dev" / "cohezion"
ARC_DATA_DIR = COHEZION_ROOT / "data" / "arc-agi-2"
SOLVER_PATH = COHEZION_ROOT / "kaggle-dataset" / "arc_solver.py"
KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"
VAULT_DIR = COHEZION_ROOT / "cloud-vault-mcp" / "vault" / "cerebellum"
STATE_FILE = Path.home() / ".cohezion-research" / "arpao_state.json"
ARC_EVAL_SCRIPT = COHEZION_ROOT / "scripts" / "eval_arc_solver.py"
KAGGLE_SUBMIT_SCRIPT = COHEZION_ROOT / "scripts" / "kaggle_arc_submitter.py"

BUDGET_SECONDS = 300  # 5 min per experiment
UCB_C = math.sqrt(2)
KAGGLE_PUSH_THRESHOLD = 0.025  # Only push to Kaggle if solve_rate > 2.5%

LEMONADE_URL = "http://localhost:13307/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

# ════════════════════════════════════════════════════════════════
# STATE
# ════════════════════════════════════════════════════════════════


@dataclass
class ExperimentOutcome:
    run_id: str
    hypothesis: str
    solve_rate: float
    correct: int
    total: int
    wall_time_s: float
    status: str  # improvement | regression | error
    pushed_to_kaggle: bool
    kaggle_score: float | None
    model_used: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _tree_path() -> Path:
    KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
    return KSEARCH_DIR / "arc_prize.json"


def _load_tree() -> dict:
    p = _tree_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"target": "arc_prize", "total_trials": 0, "best_solve_rate": 0.0, "nodes": {}}


def _save_tree(tree: dict) -> None:
    _tree_path().write_text(json.dumps(tree, indent=2))


def _ucb1_select(tree: dict, hypotheses: list[str]) -> str:
    total = max(tree["total_trials"], 1)
    nodes = tree.get("nodes", {})
    best_h, best_score = None, -float("inf")

    for h in hypotheses:
        node = nodes.get(h, {"trials": 0, "metric_values": []})
        if node["trials"] == 0:
            return h
        mean = sum(node["metric_values"]) / node["trials"]
        exploration = UCB_C * math.sqrt(math.log(total) / node["trials"])
        score = mean + exploration
        if score > best_score:
            best_score, best_h = score, h
    return best_h or hypotheses[0]


def _update_tree(tree: dict, outcome: ExperimentOutcome) -> None:
    tree["total_trials"] += 1
    nodes = tree.setdefault("nodes", {})
    node = nodes.setdefault(
        outcome.hypothesis,
        {"hypothesis": outcome.hypothesis, "wins": 0, "trials": 0, "metric_values": []},
    )
    node["trials"] += 1
    node["metric_values"].append(outcome.solve_rate)
    if outcome.solve_rate > 0.5:
        node["wins"] += 1

    if outcome.solve_rate > tree.get("best_solve_rate", 0.0):
        tree["best_solve_rate"] = outcome.solve_rate


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            lines = STATE_FILE.read_text().strip().split("\n")
            if lines:
                return json.loads(lines[-1])
        except Exception:
            pass
    return {
        "total_experiments": 0,
        "best_solve_rate": 0.0,
        "total_pushed": 0,
        "last_hypothesis": "",
        "hypotheses_tested": [],
    }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "a") as f:
        f.write(json.dumps(state) + "\n")


# ════════════════════════════════════════════════════════════════
# LLM INFERENCE
# ════════════════════════════════════════════════════════════════


def _igpu_infer(prompt: str, max_tokens: int = 4096) -> str:
    try:
        import requests

        resp = requests.post(
            LEMONADE_URL,
            json={
                "model": "gemma-4-e4b-it",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Python expert specializing in ARC-AGI pattern recognition. Output ONLY code wrapped in ```python``` blocks.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=120,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        _LOGGER.debug(f"iGPU inference failed: {e}")
        return ""


def _cpu_infer(prompt: str, model: str = "phi4:latest", max_tokens: int = 2048) -> str:
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
        return resp.json().get("response", "")
    except Exception as e:
        _LOGGER.debug(f"CPU inference failed: {e}")
        return ""


def _generate_variant(hypothesis: str) -> tuple[str, str]:
    """Generate code variant from hypothesis using LLM."""
    base_code = SOLVER_PATH.read_text()[:3000]  # First 3K chars as context

    prompt = f"""Modify the ARC solver to test this hypothesis:

Hypothesis: {hypothesis}

Current solver (partial):
```python
{base_code}

...
```

Apply the hypothesis. Add new transform functions, modify search strategy, or adjust parameters. Return ONLY a complete self-contained Python file wrapped in ```python ... ```. The file must define all these functions:
- get_all_ops(train_examples) -> list of ops
- search_program(train_examples, max_depth, ops, budget) -> program or None
- apply_program(grid, program) -> grid
- deepcopy_grid(grid) -> grid
- grids_equal(a, b) -> bool

Make the solver more powerful. No explanations outside code block."""

    # Tier 1: iGPU (Gemma-4-E4B)
    raw = _igpu_infer(prompt, max_tokens=4096)
    model = "gemma-4-e4b"
    if not raw:
        # Tier 2: CPU fallback
        raw = _cpu_infer(prompt, max_tokens=2048)
        model = "phi4"
        if not raw:
            return "", "none"

    # Extract code
    m = re.search(r"```python\n(.*?)\n```", raw, re.DOTALL)
    code = m.group(1) if m else ""
    return code, model


# ════════════════════════════════════════════════════════════════
# HARNESS
# ════════════════════════════════════════════════════════════════


def _verify_syntax(code: str) -> tuple[bool, str]:
    tmp = Path(f"/tmp/arpao_verify_{uuid.uuid4().hex[:8]}.py")
    tmp.write_text(code)
    try:
        import py_compile

        py_compile.compile(tmp, doraise=True)
        return True, "Syntax OK"
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        tmp.unlink(missing_ok=True)


# ════════════════════════════════════════════════════════════════
# EVALUATION
# ════════════════════════════════════════════════════════════════


def _eval_locally(
    code: str, max_tasks: int = None, timeout: int = BUDGET_SECONDS
) -> tuple[float, int, int, str]:
    """Run eval_arc_solver.py on the variant."""
    tmp = Path(f"/tmp/arpao_solver_{uuid.uuid4().hex[:8]}.py")
    tmp.write_text(code)

    try:
        cmd = [
            sys.executable,
            str(ARC_EVAL_SCRIPT),
            "--solver",
            str(tmp),
            "--budget",
            "3000",
            "--max-depth",
            "3",
        ]
        if max_tasks:
            cmd += ["--max-tasks", str(max_tasks)]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = proc.stdout + proc.stderr

        # Parse SOLVE_RATE and CORRECT lines
        solve_rate = 0.0
        correct = 0
        total = 0
        m = re.search(r"SOLVE_RATE[:\s]+([\d.]+)", output, re.IGNORECASE)
        if m:
            solve_rate = float(m.group(1))
        m = re.search(r"CORRECT[:\s]+(\d+)/(\d+)", output, re.IGNORECASE)
        if m:
            correct = int(m.group(1))
            total = int(m.group(2))

        return solve_rate, correct, total, output
    except subprocess.TimeoutExpired:
        return 0.0, 0, 0, "TIMEOUT"
    except Exception as e:
        _LOGGER.error(f"Eval failed: {e}")
        return 0.0, 0, 0, str(e)
    finally:
        tmp.unlink(missing_ok=True)


# ════════════════════════════════════════════════════════════════
# KAGGLE PUSH
# ════════════════════════════════════════════════════════════════


def _push_to_kaggle(
    code: str, competition: str = "arc-prize-2026-arc-agi-3"
) -> tuple[float, str, str]:
    """Push variant to Kaggle and poll for score."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        solver_path = Path(td) / "arc_solver_variant.py"
        solver_path.write_text(code)

        _LOGGER.info(f"Pushing to Kaggle ({competition})...")
        proc = subprocess.run(
            [
                sys.executable,
                str(KAGGLE_SUBMIT_SCRIPT),
                "--solver",
                str(solver_path),
                "--competition",
                competition,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = proc.stdout + proc.stderr
        _LOGGER.info(f"Push output:\n{output}")

        # Parse score
        m = re.search(r"SCORE[:\s]+([\d.]+)", output, re.IGNORECASE)
        score = float(m.group(1)) if m else 0.0
        m = re.search(r"STATUS[:\s]+(\S+)", output, re.IGNORECASE)
        status = m.group(1) if m else "unknown"
        m = re.search(r"KERNEL[:\s]+(\S+)", output, re.IGNORECASE)
        kernel_id = m.group(1) if m else ""

        return score, status, kernel_id


# ════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ════════════════════════════════════════════════════════════════

_DEFAULT_HYPOTHESES = [
    "add_rotation_transforms_90_180_270",
    "add_mirror_flip_horizontal_vertical",
    "add_gravity_fall_downward",
    "add_color_swap_any_pair",
    "add_connected_components_4_way",
    "add_scale_up_down_by_2",
    "add_pattern_repeat_row_and_col",
    "add_morphological_dilate_erode",
    "add_noise_removal_outlier_replacement",
    "add_bounding_box_crop",
    "increase_search_budget_to_10000",
    "try_max_depth_4",
    "add_composition_chain_2_transforms",
    "add_symmetry_detection_mirror_axis",
    "add_object_count_matching",
    "add_line_detection_horizontal_vertical_diagonal",
    "use_flood_fill_expansion",
    "use_xor_overlay_blending",
    "add_crop_to_content_bbox",
]


def run_arpao(
    iterations: int = 2, push_to_kaggle: bool = True, quick_eval: bool = False
) -> list[ExperimentOutcome]:
    tree = _load_tree()
    state = _load_state()
    outcomes: list[ExperimentOutcome] = []

    # If this is first run, seed hypotheses into tree
    if not tree.get("nodes"):
        tree["nodes"] = {
            h: {"hypothesis": h, "wins": 0, "trials": 0, "metric_values": []}
            for h in _DEFAULT_HYPOTHESES
        }

    for i in range(iterations):
        # Use locally-tested hypotheses from previous runs
        all_h = list(tree["nodes"].keys())
        # If few tested, add more defaults
        tested = [k for k, v in tree["nodes"].items() if v.get("trials", 0) > 0]
        if len(tested) < 3 and state.get("total_experiments", 0) == 0:
            # Use defaults first
            hypothesis = _DEFAULT_HYPOTHESES[i % len(_DEFAULT_HYPOTHESES)]
        else:
            hypothesis = _ucb1_select(tree, all_h)

        _LOGGER.info(f"[{i + 1}/{iterations}] Hypothesis='{hypothesis}'")

        # Generate variant
        code, model = _generate_variant(hypothesis)
        if not code:
            _LOGGER.warning("Code generation failed")
            continue

        # Verify syntax
        ok, msg = _verify_syntax(code)
        if not ok:
            _LOGGER.warning(f"Harness FAILED: {msg}")
            outcome = ExperimentOutcome(
                run_id=f"arpao_{uuid.uuid4().hex[:8]}",
                hypothesis=hypothesis,
                solve_rate=0.0,
                correct=0,
                total=0,
                wall_time_s=0,
                status="error",
                pushed_to_kaggle=False,
                kaggle_score=None,
                model_used=model,
            )
            outcomes.append(outcome)
            _update_tree(tree, outcome)
            continue

        _LOGGER.info(f"Harness PASSED ({msg}). Model={model}")

        # Local evaluation
        max_tasks = 3 if quick_eval else None  # Quick smoke test or full eval
        solve_rate, correct, total, logs = _eval_locally(code, max_tasks=max_tasks)
        wall_time = 0  # TODO: track real wall time

        _LOGGER.info(f"Local eval: solve_rate={solve_rate:.4f}, correct={correct}/{total}")

        best = tree.get("best_solve_rate", 0.0)
        status = "improvement" if solve_rate > best else "regression" if solve_rate > 0 else "error"

        # Kaggle push gate
        pushed = False
        kaggle_score = None
        if push_to_kaggle and solve_rate > KAGGLE_PUSH_THRESHOLD:
            kaggle_score, kaggle_status, kernel_id = _push_to_kaggle(code)
            _LOGGER.info(
                f"Kaggle: score={kaggle_score}, status={kaggle_status}, kernel={kernel_id}"
            )
            pushed = kaggle_status == "complete"
        elif push_to_kaggle:
            _LOGGER.info(
                f"Solve rate {solve_rate:.4f} < threshold {KAGGLE_PUSH_THRESHOLD}; skipping Kaggle push"
            )

        outcome = ExperimentOutcome(
            run_id=f"arpao_{uuid.uuid4().hex[:8]}",
            hypothesis=hypothesis,
            solve_rate=solve_rate,
            correct=correct,
            total=total,
            wall_time_s=wall_time,
            status=status,
            pushed_to_kaggle=pushed,
            kaggle_score=kaggle_score,
            model_used=model,
        )

        _update_tree(tree, outcome)
        _save_tree(tree)

        if status == "improvement":
            # Save winner
            winner_path = WINNER_DIR / f"arc_solver_arpao_{outcome.run_id}.py"
            winner_path.write_text(code)
            _LOGGER.info(f"🎯 NEW BEST solve_rate={solve_rate:.4f} saved to {winner_path.name}")

        outcomes.append(outcome)

        # Update state
        state["total_experiments"] = state.get("total_experiments", 0) + 1
        state["best_solve_rate"] = max(state.get("best_solve_rate", 0.0), solve_rate)
        state["last_hypothesis"] = hypothesis
        state.setdefault("hypotheses_tested", []).append(hypothesis)
        if pushed:
            state["total_pushed"] = state.get("total_pushed", 0) + 1
        _save_state(state)

        # Autocontext: archive to vault
        _archive_to_vault(outcome)

    _LOGGER.info(f"=== ARPAO DONE: {len(outcomes)} experiments ===")
    return outcomes


# ════════════════════════════════════════════════════════════════
# VAULT ARCHIVE
# ════════════════════════════════════════════════════════════════


def _archive_to_vault(outcome: ExperimentOutcome) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    fname = VAULT_DIR / f"arpao_{outcome.run_id}.md"
    body = f"""---
type: arpao
run_id: {outcome.run_id}
hypothesis: {outcome.hypothesis}
solve_rate: {outcome.solve_rate}
correct: {outcome.correct}
total: {outcome.total}
status: {outcome.status}
pushed_to_kaggle: {outcome.pushed_to_kaggle}
kaggle_score: {outcome.kaggle_score or "null"}
model_used: {outcome.model_used}
timestamp: {outcome.timestamp}
---

# ARPAO Experiment {outcome.run_id}

- **Hypothesis**: {outcome.hypothesis}
- **Model**: {outcome.model_used}
- **Solve rate**: {outcome.solve_rate}
- **Correct**: {outcome.correct}/{outcome.total}
- **Status**: {outcome.status}
- **Kaggle pushed**: {outcome.pushed_to_kaggle}
- **Kaggle score**: {outcome.kaggle_score or "N/A"}

---
"""
    fname.write_text(body)


# ════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ARC Prize AutoResearch Orchestrator")
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--no-kaggle", action="store_true", help="Skip Kaggle push")
    parser.add_argument("--quick-eval", action="store_true", help="Fast eval on 3 tasks only")
    args = parser.parse_args()

    _LOGGER.info("╔══════════════════════════════════════════════════════════════╗")
    _LOGGER.info("║ ARPAO v2.0 — ARC Prize AutoResearch Orchestrator           ║")
    _LOGGER.info("║ 3 comps: AGI-3 ($850K), AGI-2 ($700K), Paper ($450K)       ║")
    _LOGGER.info("║ Tri-compute: iGPU Gemma-4 / CPU phi4 / NPU rapid             ║")
    _LOGGER.info("║ Score-as-Reward: solve_rate feeds UCB1 K-Search tree        ║")
    _LOGGER.info("╚══════════════════════════════════════════════════════════════╝")

    outcomes = run_arpao(
        iterations=args.iterations,
        push_to_kaggle=not args.no_kaggle,
        quick_eval=args.quick_eval,
    )

    _LOGGER.info("ARPAO COMPLETE")
