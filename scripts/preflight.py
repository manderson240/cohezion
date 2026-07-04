#!/usr/bin/env python3
"""Post-cycle scan: compare K-Search trees before/after to confirm metric updates."""
import json, os

ksearch_dir = os.path.expanduser("~/.cohezion-research/ksearch/")
rotation_file = os.path.expanduser("~/.cohezion-research/target_rotation")

# Check what the runner advanced rotation to
with open(rotation_file) as f:
    next_target = f.read().strip()

print(f"=== Post-cycle scan ===\n")
print(f"Rotation now at: {next_target}\n")

targets_seen = ["jepa_world_model", "flume_vae", "arc_solver"]
for t in targets_seen:
    path = os.path.join(ksearch_dir, f"{t}.json")
    if not os.path.exists(path):
        print(f"[{t}] MISSING\n")
        continue

    with open(path) as f:
        tree = json.load(f)

    nodes = tree.get("nodes", {})
    root_total = tree.get("root_total", 0)
    
    if isinstance(nodes, dict):
        node_count = len(nodes)
        all_scores = []
        unique_scores = set()
        for name, data in nodes.items():
            mv = data.get("metric_values", [])
            if isinstance(mv, list):
                all_scores.extend(mv)
                unique_scores.update(round(s, 6) for s in mv)
    else:
        node_count = len(nodes) if isinstance(nodes, (list, set)) else 0
        all_scores = []
        unique_scores = set()
    
    n_unique = len(unique_scores) if unique_scores else 0
    best_score = max(all_scores) if all_scores else None
    
    status_flags = []
    if n_unique <= 2 and len(all_scores) > 5:
        status_flags.append("STUB/CONSTANT")
    elif n_unique > 2 and any(s > 0 for s in unique_scores):
        status_flags.append("HAS_SIGNAL")
    
    print(f"[{t}] nodes={node_count} root_total={root_total} trials(len(all))={len(all_scores)} unique={n_unique} best={best_score}")
    if status_flags:
        print(f"   Flag: {', '.join(status_flags)}")
    # Show per-node state for current rotation target
    if t == next_target or n_unique <= 3:
        for name, data in nodes.items() if isinstance(nodes, dict) else []:
            mv = data.get("metric_values", [])
            trials = data.get("trials", 0)
            wins = data.get("wins", 0)
            print(f"   node='{name}' trials={trials} wins={wins} scores=[{', '.join(str(round(s,4)) for s in mv[-3:])}]")
    print()
