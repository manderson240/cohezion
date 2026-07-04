#!/usr/bin/env python3
"""Pre-flight K-Search health scan — reads all 3 trees, reports unique scores, best/worst, STUB/BREAKOUT flags."""
import json
from pathlib import Path

ksearch_dir = Path("/home/mike-anderson/.cohezion-research/ksearch")
for target in ["arc_solver", "flume_vae", "jepa_world_model"]:
    fpath = ksearch_dir / f"{target}.json"
    if not fpath.exists():
        print(f"{target}: FILE_MISSING")
        continue
    data = json.loads(fpath.read_text())
    nodes = data.get("nodes", {})

    total_trials = 0
    scores = []
    if isinstance(nodes, dict):
        for k, v in nodes.items():
            total_trials += v.get("trials", 0)
            scores.extend(v.get("metric_values", []))
    elif isinstance(nodes, (list, set)):
        for node in nodes:
            if isinstance(node, dict):
                total_trials += node.get("trials", 0)
                scores.extend(node.get("metric_values", []))

    uniq = set(round(s, 6) for s in scores) if scores else {0}
    best = max(scores) if scores else 0.0
    worst = min(scores) if scores else 0.0

    breakouts = sum(1 for v in nodes.values() if isinstance(v, dict) and any(round(s, 6) > 0 for s in v.get("metric_values", [])))
    status_parts = []
    if len(scores) > 2 and breakouts >= 2:
        status_parts.append("BREAKOUT")
    if len(uniq) <= 1:
        status_parts.append("STUB")

    print(f"{target}: trials={total_trials:6d} unique_scores={len(uniq):3d} best={best:.4f} worst={worst:.4f} {' '.join(status_parts)}")
