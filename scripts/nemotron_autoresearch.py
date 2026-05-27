#!/usr/bin/env python3
"""
Nemotron AutoResearch Loop (following Cohezion autoresearch skill)

Manages K-Search tree, verifies kernels with autoharness, submits to Kaggle.

Hypothesis space for improving over baseline 0.49:
1. train_size: [50, 100, 500, 1000, 9500]
2. lr: [1e-4, 2e-4, 5e-4]
3. epochs: [1, 2, 3]
4. grad_accum: [4, 8, 16]
5. teacher_model: [none, deepseek-r1-32b]
6. max_seq_length: [512, 1024]

Base hypothesis: "v20_baseline_50_samples_1e-4"
"""

import json
import math
import subprocess
import sys
from pathlib import Path


KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"
KSEARCH_DIR.mkdir(parents=True, exist_ok=True)
TREE_PATH = KSEARCH_DIR / "nemotron_lora.json"
STATE_PATH = KSEARCH_DIR / "nemotron_autoresearch_state.json"

COMPETITION = "nvidia-nemotron-model-reasoning-challenge"


def load_tree():
    if TREE_PATH.exists():
        return json.loads(TREE_PATH.read_text())
    return {"target": "nemotron_lora", "total_trials": 0, "best_score": 0.0, "nodes": {}}


def save_tree(tree):
    TREE_PATH.write_text(json.dumps(tree, indent=2))


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"runs": 0, "best_score": 0.0, "active_kernel": None}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


UCB_C = 1.414


def select_hypothesis(tree, hypotheses):
    total = max(tree.get("total_trials", 0), 1)
    nodes = tree.get("nodes", {})
    best_score = -float("inf")
    best_h = hypotheses[0]

    for h in hypotheses:
        node = nodes.get(h, {"trials": 0, "wins": 0, "scores": []})
        if node["trials"] == 0:
            return h  # Explore untested
        mean_score = sum(node["scores"]) / len(node["scores"])
        exploration = UCB_C * (math.log(total) / node["trials"]) ** 0.5
        score = mean_score + exploration
        if score > best_score:
            best_score = score
            best_h = h
    return best_h


def update_tree(tree, hypothesis, score):
    tree["total_trials"] = tree.get("total_trials", 0) + 1
    nodes = tree.setdefault("nodes", {})
    node = nodes.setdefault(hypothesis, {"trials": 0, "wins": 0, "scores": []})
    node["trials"] += 1
    node["scores"].append(score)
    if score > tree.get("best_score", 0.0):
        tree["best_score"] = score


def check_kernel_status(kernel_id):
    """Autoharness: check if kernel completed successfully."""
    result = subprocess.run(
        ["kaggle", "kernels", "status", kernel_id], capture_output=True, text=True, timeout=30
    )
    if "COMPLETE" in result.stdout:
        return "complete"
    elif "ERROR" in result.stdout:
        return "error"
    elif "RUNNING" in result.stdout:
        return "running"
    elif "QUEUED" in result.stdout:
        return "queued"
    return "unknown"


def get_kernel_log(kernel_id):
    result = subprocess.run(
        ["kaggle", "kernels", "output", kernel_id, "-p", "/tmp/kaggle_out"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    log_path = Path("/tmp/kaggle_out") / f"{kernel_id.split('/')[-1]}.log"
    if log_path.exists():
        return log_path.read_text()[:5000]
    return ""


def poll_active_kernel(state):
    """Poll an active kernel and handle completion."""
    ok = state.get("active_kernel")
    if not ok:
        return

    status = check_kernel_status(ok)
    print(f"[{ok}] Status: {status}")

    if status == "complete":
        # Kernel succeeded, check if submission available
        # Then check leaderboard
        pass
    elif status == "error":
        # Download error log, analyze with autoharness
        log = get_kernel_log(ok)
        print(f"ERROR log:\n{log[:2000]}")
        tree = load_tree()
        update_tree(tree, state["active_hypothesis"], 0.0)
        save_tree(tree)
        state["active_kernel"] = None
        state["active_hypothesis"] = None
        save_state(state)
    elif status == "running":
        print("Kernel still running. Check again later.")
        sys.exit(0)  # Wait for next cron run


HYPOTHESES = [
    "v20_baseline_50_samples_1e-4",  # v20 baseline
    "v40_more_data_9500_samples_1e-4",  # Train on all data
    "two_epoch_1000_samples_1e-4",  # More epochs, moderate data
    "lr_2e-4_grad_accum_4",  # Different optimization params
    "deepseek_teacher_50_samples_only",  # Teacher model approach
    "symbolic_verified_only_5200",  # Only where symbolic solver works
    "max_seq_len_2048_chat_template",  # Different formatting
]


def main():
    tree = load_tree()
    state = load_state()

    # If there's an active kernel, poll it first
    if state.get("active_kernel"):
        poll_active_kernel(state)
        return

    # No active kernel -- need to pick next hypothesis and push
    hypothesis = select_hypothesis(tree, HYPOTHESES)
    print(f"Selected hypothesis: {hypothesis}")

    # For now, just show selection -- push via user action
    print(f"Ready to push kernel for: {hypothesis}")
    # Future: build kernel from template, push, update state


if __name__ == "__main__":
    main()
