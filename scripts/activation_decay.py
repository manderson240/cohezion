#!/usr/bin/env python3
"""Activation Decay — daily 5% decay for neurons not recently fired.

Neurons that haven't been edited (synced) in the last 24 hours lose 5% activation.
Minimum activation is 0.1 (never fully dormant).
Neurons below 0.2 activation are set to 'resting' stage.
"""

import base64, json, sys, urllib.request
from datetime import datetime

SURREAL_URL = "http://localhost:8001/sql"
HDRS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
}


def query(sql):
    req = urllib.request.Request(
        SURREAL_URL, data=sql.encode("utf-8"), headers=HDRS, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Query error: {e}", file=sys.stderr)
        return []


def get_results(data, idx=0):
    if not data or idx >= len(data):
        return []
    entry = data[idx]
    if entry.get("status") != "OK":
        print(f"  SurrealDB error: {entry.get('result', '?')}", file=sys.stderr)
        return []
    return entry.get("result") or []


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Activation Decay — {now} ===")

    # Check SurrealDB
    if not query("INFO FOR DB;"):
        print("ERROR: SurrealDB not reachable", file=sys.stderr)
        sys.exit(1)

    # Get current stats (SurrealDB 3.0: math::mean doesn't work on field refs)
    before = get_results(
        query("SELECT math::sum(activation) / count() AS avg FROM neuron GROUP ALL;")
    )
    avg_before = before[0]["avg"] if before else 0
    print(f"  Avg activation before: {avg_before:.3f}")

    # Count candidates first
    candidates = get_results(
        query("SELECT count() FROM neuron WHERE last_fired < time::now() - 1d GROUP ALL;")
    )
    candidate_count = candidates[0]["count"] if candidates else 0

    # Decay: reduce activation by 5% for neurons not fired in last 24h
    # min activation = 0.1 (SurrealDB 3.0: use IF/THEN/ELSE instead of math::max)
    result = query(
        "UPDATE neuron SET activation = "
        "IF activation * 0.95 > 0.1 THEN activation * 0.95 ELSE 0.1 END "
        "WHERE last_fired < time::now() - 1d;"
    )
    if result and result[0].get("status") == "OK":
        decayed = candidate_count
        print(f"  Decayed: {decayed} neurons (5% reduction)")
    else:
        err = result[0].get("result", "?") if result else "no resp"
        print(f"  Decay failed: {err}", file=sys.stderr)
        sys.exit(1)

    # Set resting stage for very low activation neurons
    resting = query(
        'UPDATE neuron SET stage = "resting" WHERE activation < 0.2;'
    )
    if resting and resting[0].get("status") == "OK":
        resting_count = len(resting[0].get("result", []))
        if resting_count > 0:
            print(f"  Set to resting: {resting_count} neurons")

    # After stats
    after = get_results(
        query("SELECT math::sum(activation) / count() AS avg FROM neuron GROUP ALL;")
    )
    avg_after = after[0]["avg"] if after else 0
    print(f"  Avg activation after: {avg_after:.3f}")

    # Log to neuron_history
    query(
        f'CREATE neuron_history CONTENT {{ '
        f'neuron: neuron:system, event_type: "decay", '
        f'timestamp: time::now(), '
        f'detail: "daily decay: avg {avg_before:.3f} -> {avg_after:.3f}, {decayed} neurons" }};'
    )

    # Stage distribution
    dist = get_results(
        query("SELECT stage, count() FROM neuron GROUP BY stage ORDER BY count DESC;")
    )
    print("\n  Stage distribution:")
    for row in dist:
        print(f"    {row['stage']}: {row['count']}")

    print(f"\n=== Complete ===")


if __name__ == "__main__":
    main()
