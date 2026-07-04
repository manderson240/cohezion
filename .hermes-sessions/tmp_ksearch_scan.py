import json
from pathlib import Path

ksearch_path = Path.home() / ".cohezion-research/ksearch/arc_solver.json"
with open(ksearch_path) as f:
    data = json.load(f)

nodes = data.get("nodes", {})
total_trials = sum(n.get("trials", 0) for n in nodes.values())
all_scores = []
active_nodes = []
zero_only_nodes = []
for name, node in nodes.items():
    mv = node.get("metric_values", [])
    total_trials_node = len(mv) if isinstance(mv, list) else 0
    # trials is scalar per pitfall #87 caveat — but metric_values IS the array
    tail_zeros = 0
    for v in reversed(mv):
        if round(v, 6) == 0:
            tail_zeros += 1
        else:
            break
    nonzero_count = sum(1 for v in mv if round(v, 6) != 0)
    all_scores.extend(mv)

    is_zero_only = all(round(v, 6) == 0 for v in mv) if mv else False

    node_info = {
        "name": name,
        "trials_scalar": node.get("trials", "?"),
        "mv_len": len(mv),
        "nonzero": nonzero_count,
        "tail_zeros": tail_zeros,
        "max_score": max(mv) if mv else None,
    }

    if is_zero_only and not (node_info["trials_scalar"] == 0 and len(mv) == 0):
        zero_only_nodes.append(node_info)
    elif nonzero_count > 0:
        active_nodes.append(node_info)

unique_scores = set(round(s, 6) for s in all_scores)
best_score = max(all_scores) if all_scores else 0.0

print("=== arc_solver K-Search Scan ===")
print(f"Nodes: {len(nodes)}")
print(f"Total trials (sum of metric_values lengths): {total_trials}")
print(f"Unique score values: {sorted(unique_scores)}")
print(f"Best score: {best_score}")
print("\n--- Active Signal Nodes (have nonzero) ---")
for n in active_nodes:
    print(
        f"  {n['name']}: trials_scalar={n['trials_scalar']} mv_len={n['mv_len']} nonzero={n['nonzero']} tail_zeros={n['tail_zeros']} max={n['max_score']}"
    )
print("\n--- Zero-Only Nodes (all metric_values zeros) ---")
for n in zero_only_nodes:
    print(
        f"  {n['name']}: trials_scalar={n['trials_scalar']} mv_len={n['mv_len']} nonzero={n['nonzero']} tail_zeros={n['tail_zeros']} max={n['max_score']}"
    )
