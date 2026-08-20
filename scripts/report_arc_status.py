import json


try:
    s = json.load(open("/home/mike-anderson/.cohezion-research/arc_v4.json"))
except FileNotFoundError:
    print("Error: arc_v4.json not found.")
    exit(1)

print("=== ARC Autoresearch Status ===")
print(f"Solved: {len(s.get('solved', {}))}/400")
print(f"Evals: {s.get('total_evals', 0):,}")
print(f"Rounds: {s.get('round', 0)}")

if s.get("history"):
    h = s["history"][-1]
    print(f"Last round: rate={h.get('rate', 0):.1%} [{h.get('solved', 0)}/{h.get('total', 0)}]")

    # Simplified logic for latest print
    latest_data = s["history"][-1]
    print(f"Latest: {latest_data}")
else:
    print("Latest: none")
