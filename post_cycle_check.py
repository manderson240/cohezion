import json

kjson = "/home/mike-anderson/.cohezion-research/ksearch/arc_solver.json"
with open(kjson) as f:
    tree = json.load(f)

nodes = tree.get("nodes", {})
root_total = tree.get("root_total", 0)

print("=== POST-CYCLE HEALTH CHECK ===\n")

if not isinstance(nodes, dict):
    print(f"ERROR: nodes is {type(nodes)}, expected dict")
else:
    node_sum = sum(len(n.get("metric_values", [])) for n in nodes.values())
    node_trial_count = sum(n.get("trials", 0) for n in nodes.values())

    print(f"root_total: {root_total}")
    print(f"node_metric_values_sum: {node_sum}")
    print(f"node_trials_sum: {node_trial_count}")
    print(f"Node count: {len(nodes)}")

all_non_zero = []
best_score = 0.0
best_node_name = None

for name, node in nodes.items() if isinstance(nodes, dict) else []:
    vals = node.get("metric_values", [])
    for v in vals:
        r = round(v, 4)
        if r > 0:
            all_non_zero.append((name, round(v, 6)))
            if v > best_score:
                best_score = v
                best_node_name = name

if all_non_zero:
    print(f"\nNon-zero trials found: {len(all_non_zero)}")
    print(f"Best score: {best_score:.4f} (node: {best_node_name})")
else:
    new_nodes_added = len(nodes) - 19  # baseline has 19 nodes
    if new_nodes_added == 0:
        print("\nNo new hypotheses added. Same 19 node.")
    else:
        print(f"\n{new_nodes_added} new hypothesis node(s) added")

    zero_count = sum(len(n.get("metric_values", [])) for n in nodes.values())
    nonzero_from_zero = sum(1 for n in nodes.values()
                           for v in n.get("metric_values", []) if round(v, 4) > 0)
    print(f"Total metric values across all nodes: {zero_count}")

# Check current rotation state
with open("/home/mike-anderson/.cohezion-research/target_rotation") as f:
    rot = f.read().strip()
print(f"\nRotation target after cycle: {rot}")
