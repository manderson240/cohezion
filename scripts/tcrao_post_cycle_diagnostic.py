#!/usr/bin/env python3
"""
TCRAO post-cycle diagnostic script.
Run after every autoresearch cycle to detect silent failures, stagnation,
and placeholder evaluator corruption.

Usage:
    python3 scripts/tcrao_post_cycle_diagnostic.py

Exit codes:
    0 — healthy (variance detected, real evaluation likely)
    1 — warning (low variance, possible placeholder/stub)
    2 — critical (zero variance, corrupted K-Search tree)
"""

import json
import sys
from pathlib import Path


STATE = Path.home() / ".cohezion-research" / "tcrao_state.json"
KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch"

EXIT = 0


def probe_state(target, min_runs=5):
    """Check tcrao_state.json for score variance over the last N runs."""
    if not STATE.exists():
        print(f"[SKIP] {target}: no state file")
        return False
    vals = []
    for line in STATE.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("target") == target:
                vals.append(entry.get("best_score"))
        except json.JSONDecodeError:
            continue
    uniques = set(v for v in vals if v is not None)
    print(f"[{target}] state: {len(vals)} total runs, {len(uniques)} unique scores across history")
    if len(vals) < min_runs:
        print(f"  → OK: <{min_runs} runs, not enough data")
        return True
    if len(uniques) <= 1:
        print("  → CRITICAL: zero variance in scores (placeholder evaluator likely)")
        return False
    if len(uniques) <= 2:
        print(f"  → WARNING: only {len(uniques)} distinct scores (low exploration)")
        return True
    print(f"  → OK: {len(uniques)} distinct scores detected")
    return True


def probe_ksearch(target):
    """Check K-Search tree for single-node dominance and variance."""
    p = KSEARCH_DIR / f"{target}.json"
    if not p.exists():
        print(f"[SKIP] {target}: no K-Search tree")
        return False
    t = json.loads(p.read_text())
    total = t.get("total_trials", 0)
    nodes = t.get("nodes", {})
    if not nodes:
        print(f"[WARN] {target}: empty nodes in tree")
        return False

    # Dominant node
    dominant_name, dom_data = max(nodes.items(), key=lambda kv: kv[1].get("trials", 0))
    dom_trials = dom_data.get("trials", 0)
    dom_pct = 100 * dom_trials / total if total else 0

    # Variance across all metric_values
    all_vals = []
    for n in nodes.values():
        all_vals.extend(n.get("metric_values", []))
    unique_vals = len(set(all_vals))

    print(
        f"[{target}] tree: {total} trials, {len(nodes)} nodes, "
        f"{unique_vals} unique metric_values, "
        f"dominant='{dominant_name}' ({dom_pct:.1f}% trials)"
    )

    if dom_pct > 80 and unique_vals <= 1:
        print("  → CRITICAL: single node dominates with zero variance")
        return False
    if dom_pct > 80:
        print("  → WARNING: single node dominates but some variance exists")
        return True
    if unique_vals <= 1:
        print("  → WARNING: zero metric variance across all nodes")
        return True
    print("  → OK: exploration looks active")
    return True


def main():
    global EXIT
    targets = ["arc_solver", "jepa_world_model", "flume_vae"]
    for t in targets:
        ok_state = probe_state(t)
        ok_tree = probe_ksearch(t)
        if not ok_state or not ok_tree:
            EXIT = max(EXIT, 2 if not ok_tree else 1)
        print()
    sys.exit(EXIT)


if __name__ == "__main__":
    main()
