import collections
import json


def analyze(filename):
    with open(filename) as f:
        data = json.load(f)

    # Events have "cat": "op", "ts": cycle.
    # Args contain "slot".
    cycles = collections.defaultdict(lambda: collections.defaultdict(int))
    max_cycle = 0

    for event in data:
        if event.get("cat") != "op":
            continue
        ts = event.get("ts")
        name = event.get("name")
        # Name is like "valu-0", "load-1" or specific op name?
        # problem.py trace_slot: name=slot[0] (op name), tid=...
        # Wait, tid maps to engine?
        # trace_slot uses self.tids[(ci, name, i)].
        # Trace events don't have engine name directly in event structure except via tid.
        # But we can infer from Op names?
        # valu ops: +, -, *, etc.
        # load ops: load, vload.
        # alu ops: +, -... intersect with valu.

        # Let's rely on thread_name metadata?
        # Metadata events occur at start.
        pass

    # Actually, problem.py writes thread_name metadata mapping TIDs to names like "valu-0".
    tids = {}
    ops = []

    for event in data:
        if event.get("name") == "thread_name":
            tids[event["tid"]] = event["args"]["name"]
        elif event.get("cat") == "op":
            ops.append(event)
            max_cycle = max(max_cycle, event.get("ts"))

    print(f"Total Cycles: {max_cycle}")

    cycle_stats = collections.defaultdict(lambda: collections.defaultdict(int))

    for op in ops:
        tid = op["tid"]
        if tid >= 100000:
            continue
        ts = op["ts"]
        if tid not in tids:
            continue
        engine_slot = tids[tid]  # e.g. "valu-0"
        engine = engine_slot.split("-")[0]
        cycle_stats[ts][engine] += 1

    # Aggregate
    total_slots = collections.defaultdict(int)
    busy_cycles = collections.defaultdict(int)

    for ts in range(max_cycle + 1):
        stats = cycle_stats[ts]
        for eng, count in stats.items():
            total_slots[eng] += count
            if count > 0:
                busy_cycles[eng] += 1

    print("Utilization:")
    for eng in sorted(total_slots.keys()):
        capacity = 0
        if eng == "alu":
            capacity = 12
        elif eng == "valu":
            capacity = 6
        elif eng == "load":
            capacity = 2
        elif eng == "store":
            capacity = 2
        elif eng == "flow":
            capacity = 1

        avg_util = total_slots[eng] / (max_cycle + 1)
        print(
            f"  {eng}: {total_slots[eng]} ops. Avg {avg_util:.2f}/cycle. (Cap {capacity})"
        )

        # Saturation check
        saturated = 0
        for ts in range(max_cycle + 1):
            if cycle_stats[ts][eng] == capacity:
                saturated += 1
        print(
            f"    Saturated cycles: {saturated} ({saturated / (max_cycle + 1) * 100:.1f}%)"
        )


if __name__ == "__main__":
    analyze("trace.json")
