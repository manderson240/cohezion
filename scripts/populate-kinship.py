#!/usr/bin/env python3
"""Populate the SurrealDB kinship table with elder/younger, parent/child, and moiety relationships.

Strategy: fetch all neurons and synapses once, compute relationships in Python, batch-create kinship records.
"""

import json
import urllib.request
import base64
from collections import defaultdict

SURREAL_URL = "http://localhost:8001/sql"
HEADERS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
}

DIR_TO_ASPECT = {
    "cortex": "knower", "sensory": "knower", "memory": "knower", "genome": "knower",
    "skills_index": "knower",
    "prefrontal": "thinker", "laboratory": "thinker", "cerebellum": "thinker", "benchmarks": "thinker",
    "assessments": "thinker",
    "motor": "doer", "hippocampus": "doer", "thalamus": "doer", "missions": "doer",
    "retrospectives": "doer", "Agents": "doer", "docs": "doer", "teleport": "doer",
    "dreaming": "connective", "songlines": "connective", "subconscious": "connective",
    "metabolism": "connective", "visual-cortex": "connective", "canvas": "connective",
    "meta": "connective",
}


def query(sql: str, timeout: int = 120) -> list[dict]:
    req = urllib.request.Request(SURREAL_URL, data=sql.encode("utf-8"), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  SurrealDB HTTP {e.code}: {body[:200]}")
        return []


def get_results(data: list[dict], idx: int = 0) -> list[dict]:
    if not data or idx >= len(data):
        return []
    entry = data[idx]
    if entry.get("status") != "OK":
        print(f"  Query error: {entry.get('result', 'unknown')}")
        return []
    return entry.get("result") or []


def load_all_data():
    """Load all neurons and synapses into Python dicts."""
    print("Loading neurons...")
    neuron_sql = 'SELECT id, path, stage, cluster_id, activation FROM neuron;'
    neurons = get_results(query(neuron_sql, timeout=60))
    print(f"  {len(neurons)} neurons loaded")

    neuron_map = {}  # id -> neuron dict
    for n in neurons:
        nid = str(n["id"])
        top_dir = n["path"].split("/")[0]
        n["aspect"] = DIR_TO_ASPECT.get(top_dir, "unknown")
        neuron_map[nid] = n

    print("Loading synapses...")
    synapse_sql = 'SELECT in, out FROM synapse;'
    synapses = get_results(query(synapse_sql, timeout=60))
    print(f"  {len(synapses)} synapses loaded")

    # Build adjacency: out-neighbors per neuron
    out_neighbors: dict[str, list[str]] = defaultdict(list)
    for s in synapses:
        out_neighbors[str(s["in"])].append(str(s["out"]))

    return neuron_map, out_neighbors


def create_kinship_batch(records: list[dict]) -> int:
    """Create kinship records using RELATE (kinship is a RELATION table). Skips duplicates."""
    created = 0
    for rec in records:
        in_id = rec["in"]
        out_id = rec["out"]
        relation = rec["relation"]
        # Check for existing relationship
        check = query(
            f'SELECT count() FROM kinship WHERE in = {in_id} AND out = {out_id}'
            f' AND relation = "{relation}" GROUP ALL;'
        )
        existing = get_results(check)
        if existing and existing[0].get("count", 0) > 0:
            continue

        sql = (
            f'RELATE {in_id}->kinship->{out_id} CONTENT {{'
            f' relation: "{relation}",'
            f' obligation: {json.dumps(rec["obligation"])},'
            f' created: time::now()'
            f' }};'
        )
        result = query(sql)
        if result and result[0].get("status") == "OK":
            created += 1
    return created


def find_elder_younger(neuron_map, out_neighbors) -> list[dict]:
    """Mature notes linked to growing/embryo notes in the same cluster."""
    print("\n--- Elder/Younger ---")
    mature_by_cluster: dict[str, list[dict]] = defaultdict(list)
    for nid, n in neuron_map.items():
        if n["stage"] == "mature" and n.get("cluster_id"):
            mature_by_cluster[n["cluster_id"]].append(n)

    # Sort by activation desc within each cluster
    for cid in mature_by_cluster:
        mature_by_cluster[cid].sort(key=lambda x: x.get("activation", 0), reverse=True)

    records = []
    for cluster_id, elders in mature_by_cluster.items():
        for elder in elders[:5]:  # Top 5 elders per cluster
            eid = str(elder["id"])
            for neighbor_id in out_neighbors.get(eid, []):
                neighbor = neuron_map.get(neighbor_id)
                if not neighbor:
                    continue
                if neighbor.get("cluster_id") == cluster_id and neighbor["stage"] in ("growing", "embryo"):
                    records.append({
                        "in": elder["id"], "out": neighbor["id"],
                        "relation": "elder_younger",
                        "obligation": "consult before changing",
                    })
            if len(records) >= 100:
                break
        if len(records) >= 100:
            break

    print(f"  Candidates: {len(records)}")
    return records


def find_parent_child(neuron_map, out_neighbors) -> list[dict]:
    """Decision→Project, Concept→Pattern, Decision→Experiment links."""
    print("\n--- Parent/Child ---")

    parent_child_rules = [
        ("prefrontal/", "motor/", "update when modified"),
        ("prefrontal/", "laboratory/", "update when modified"),
        ("cortex/", "cerebellum/", "cite together"),
        ("memory/", "cerebellum/", "cite together"),  # Lesson → Pattern
    ]

    records = []
    for parent_prefix, child_prefix, obligation in parent_child_rules:
        # Find neurons matching each prefix
        parents = {nid for nid, n in neuron_map.items() if n["path"].startswith(parent_prefix)}
        children = {nid for nid, n in neuron_map.items() if n["path"].startswith(child_prefix)}

        for pid in parents:
            for neighbor_id in out_neighbors.get(pid, []):
                if neighbor_id in children:
                    records.append({
                        "in": neuron_map[pid]["id"],
                        "out": neuron_map[neighbor_id]["id"],
                        "relation": "parent_child",
                        "obligation": obligation,
                    })

    print(f"  Candidates: {len(records)}")
    return records


def find_moiety(neuron_map, out_neighbors) -> list[dict]:
    """Cross-aspect linked pairs with high activation — complementary pairs."""
    print("\n--- Moiety (Complementary Pairs) ---")

    records = []
    seen: set[tuple[str, str]] = set()

    # Find notes with activation > 0.5 from each aspect
    by_aspect: dict[str, list[str]] = defaultdict(list)
    for nid, n in neuron_map.items():
        if n.get("activation", 0) > 0.5 and n["aspect"] != "unknown":
            by_aspect[n["aspect"]].append(nid)

    # Check links between different aspects
    for aspect, nids in by_aspect.items():
        for nid in nids:
            for neighbor_id in out_neighbors.get(nid, []):
                neighbor = neuron_map.get(neighbor_id)
                if not neighbor or neighbor["aspect"] == aspect or neighbor["aspect"] == "unknown":
                    continue
                if neighbor.get("activation", 0) < 0.5:
                    continue

                key = tuple(sorted([nid, neighbor_id]))
                if key in seen:
                    continue
                seen.add(key)

                records.append({
                    "in": neuron_map[nid]["id"],
                    "out": neighbor["id"],
                    "relation": "moiety",
                    "obligation": "always cite together",
                })
                if len(records) >= 60:
                    break
            if len(records) >= 60:
                break
        if len(records) >= 60:
            break

    print(f"  Candidates: {len(records)}")
    return records


def main():
    print("=== Kinship Population ===")

    result = query('SELECT count() FROM kinship GROUP ALL;')
    existing = get_results(result)
    count = existing[0]["count"] if existing else 0
    print(f"Existing kinship records: {count}")

    neuron_map, out_neighbors = load_all_data()

    all_records = []
    all_records.extend(find_elder_younger(neuron_map, out_neighbors))
    all_records.extend(find_parent_child(neuron_map, out_neighbors))
    all_records.extend(find_moiety(neuron_map, out_neighbors))

    print(f"\nTotal candidates: {len(all_records)}")
    if all_records:
        print("Creating kinship records...")
        created = create_kinship_batch(all_records)
        print(f"Created: {created}")
    else:
        print("No kinship candidates found")

    result = query('SELECT count() FROM kinship GROUP ALL;')
    final = get_results(result)
    final_count = final[0]["count"] if final else 0
    print(f"\n=== Complete: total kinship records: {final_count} ===")


if __name__ == "__main__":
    main()
