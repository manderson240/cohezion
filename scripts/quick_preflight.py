#!/usr/bin/env python3
"""Quick pre-flight scan: check rotation target and all 3 K-Search trees for degenerate conditions."""
import json, os, sys

ksearch_dir = os.path.expanduser("~/.cohezion-research/ksearch/")
rotation_file = os.path.expanduser("~/.cohezion-research/target_rotation")

# Read current rotation target
try:
    with open(rotation_file) as f:
        current_target = f.read().strip()
except FileNotFoundError:
    print(f"ERROR: Rotation file not found at {rotation_file}")
    sys.exit(1)

print(f"=== Current rotation target: {current_target} ===\n")

# Scan all 3 targets
targets = ["arc_solver", "jepa_world_model", "flume_vae"]
for t in targets:
    path = os.path.join(ksearch_dir, f"{t}.json")
    if not os.path.exists(path):
        print(f"[{t}] K-Search file MISSING at {path}")
        print()
        continue

    with open(path) as f:
        tree = json.load(f)

    nodes = tree.get("nodes", {})
    root_total = tree.get("root_total", 0)
    
    # Handle nodes as dict (actual current state) or list/string keys
    if isinstance(nodes, dict):
        node_count = len(nodes)
        all_scores = []
        unique_scores = set()
        wins_sum = sum(v.get("wins", 0) for v in nodes.values())
        
        for name, data in nodes.items():
            mv = data.get("metric_values", [])
            if isinstance(mv, list):
                all_scores.extend(mv)
                unique_scores.update(round(s, 6) for s in mv)
    else:
        node_count = len(nodes) if isinstance(nodes, (list, set)) else 0
        all_scores = []
        unique_scores = set()
        wins_sum = 0
    
    n_unique = len(unique_scores) if unique_scores else 0
    best_score = max(all_scores) if all_scores else None
    worst_score = min(all_scores) if all_scores else None
    
    # Detection logic from autoharness pitfalls
    stub = "DEGENERATE" if (n_unique <= 2 and len(all_scores) > 5) or n_unique == 0 else ""
    breakout = "BREAKOUT SIGNAL" if n_unique > 2 and any(s > 0 for s in unique_scores) else ""
    
    print(f"[{t}] nodes={node_count} trials(root_total={root_total}) unique_scores={n_unique} best={best_score} worst={worst_score}")
    if all_scores:
        flag = f" <<< {stub}" if stub else (" <<< {breakout}" if breakout else "")
        print(f"   >>> Scores: {all_scores[:10]}{'...' if len(all_scores)>10 else ''}{flag}")
    else:
        print("   >>> Scores: (none)")
    
    # Check if the current target is degenerate
    if t == current_target and stub == "DEGENERATE":
        print(f"   !!! CURRENT TARGET IS DEGENERATE — cycle will waste compute")
    elif t == current_target and n_unique == 0:
        print(f"   !!! CURRENT TARGET HAS NO TRAILS — fresh start possible")
    
    # Check node-level for arc_solver specific patterns
    if t == "arc_solver":
        non_zero_nodes = [(k, v.get("metric_values", [])) for k,v in nodes.items() 
                         if any(round(s,6) > 0 for s in v.get("metric_values", []))]
        zero_dominant = sum(1 for v in nodes.values() for s in v.get("metric_values", []) if round(s,6)==0)
        nz_scores = [round(min(v), 4) if v else None for k, v in non_zero_nodes]
        print(f"   >>> arc_solver non-zero nodes: {len(non_zero_nodes)} (non-zero min scores: {[s for s in nz_scores if s is not None]})")
        print(f"   >>> Total zero-trials across all nodes: ~{zero_dominant}")
    print()

# Check rotation progression via state file
state_file = os.path.expanduser("~/.cohezion-research/tcrao_state.json")
if os.path.exists(state_file):
    prev_targets = []
    with open(state_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                tname = entry.get("target", entry.get("rotation_target"))
                tick = entry.get("tick", 0)
                prev_targets.append((tick, tname))
            except json.JSONDecodeError:
                pass
    
    if prev_targets:
        last_5 = sorted(prev_targets, key=lambda x: x[0])[-5:]
        print(f"Last 5 completed ticks from state file:")
        for tick, tgt in last_5:
            marker = " *** CURRENT ROTATION TARGET ***" if tgt == current_target else ""
            print(f"  tick={tick} target={tgt}{marker}")
