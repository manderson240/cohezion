import json


def report_arc_status():
    try:
        s = json.load(open("/home/mike-anderson/.cohezion-research/arc_v4.json"))
        print("=== ARC Autoresearch Status ===")
        print(f"Solved: {len(s.get('solved', {}))}/400")
        print(f"Evals: {s.get('total_evals', 0):,}")
        print(f"Rounds: {s.get('round', 0)}")
        if s.get("history"):
            h = s["history"][-1]
            print(
                f"Last round: rate={h.get('rate', 0):.1%} [{h.get('solved', 0)}/{h.get('total', 0)}]"
            )
        print(f"Latest: {s.get('history', [])[-1] if s.get('history') else 'none'}")
    except FileNotFoundError:
        print("ARC Status: File /home/mike-anderson/.cohezion-research/arc_v4.json not found.")
    except Exception as e:
        print(f"ARC Status Error: {e}")


if __name__ == "__main__":
    report_arc_status()
