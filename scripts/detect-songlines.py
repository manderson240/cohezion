#!/usr/bin/env python3
"""Detect songlines — cross-Country knowledge paths in the vault's link graph.

A songline is a chain of linked notes that traverses 3+ different Countries.
We find these by walking the synapse graph from high-activation notes and tracking
which Countries the path crosses.
"""

import json
import urllib.request
import base64
from collections import defaultdict
from pathlib import Path
from datetime import date

SURREAL_URL = "http://localhost:8001/sql"
HEADERS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
}
VAULT_ROOT = Path(__file__).resolve().parent.parent
MIN_COUNTRIES = 3
MAX_PATH_LENGTH = 8
MAX_SONGLINES = 20


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
        return []
    return entry.get("result") or []


def load_graph():
    """Load neurons and synapses into Python."""
    neurons = get_results(query('SELECT id, path, title, cluster_id, activation FROM neuron;'))
    synapses = get_results(query('SELECT in, out FROM synapse;'))

    neuron_map = {}
    for n in neurons:
        nid = str(n["id"])
        neuron_map[nid] = n

    out_neighbors: dict[str, list[str]] = defaultdict(list)
    for s in synapses:
        out_neighbors[str(s["in"])].append(str(s["out"]))

    return neuron_map, out_neighbors


def find_songline_paths(neuron_map, out_neighbors) -> list[list[str]]:
    """BFS from high-activation notes, tracking Country crossings."""
    # Start from top-activation notes across different clusters
    starters = sorted(
        [n for n in neuron_map.values() if n.get("activation", 0) > 0.5 and n.get("cluster_id")],
        key=lambda x: x["activation"],
        reverse=True,
    )[:50]

    songlines: list[list[str]] = []
    seen_path_keys: set[frozenset[str]] = set()

    for starter in starters:
        start_id = str(starter["id"])
        # BFS with Country tracking
        queue: list[tuple[list[str], set[str]]] = [([start_id], {starter["cluster_id"]})]
        visited_from_start: set[str] = {start_id}

        while queue and len(songlines) < MAX_SONGLINES:
            path, countries = queue.pop(0)

            if len(countries) >= MIN_COUNTRIES and len(path) >= MIN_COUNTRIES:
                # Deduplicate: use frozenset of countries crossed
                path_key = frozenset(n for n in path)
                if path_key not in seen_path_keys:
                    seen_path_keys.add(path_key)
                    songlines.append(path)

            if len(path) >= MAX_PATH_LENGTH:
                continue

            current = path[-1]
            for neighbor_id in out_neighbors.get(current, []):
                if neighbor_id in visited_from_start:
                    continue
                neighbor = neuron_map.get(neighbor_id)
                if not neighbor or not neighbor.get("cluster_id"):
                    continue

                visited_from_start.add(neighbor_id)
                new_countries = countries | {neighbor["cluster_id"]}
                queue.append((path + [neighbor_id], new_countries))

        if len(songlines) >= MAX_SONGLINES:
            break

    return songlines


def name_songline(neuron_map, path: list[str]) -> str:
    """Generate a name from the Countries crossed."""
    countries = []
    seen = set()
    for nid in path:
        n = neuron_map.get(nid)
        if n and n.get("cluster_id") and n["cluster_id"] not in seen:
            seen.add(n["cluster_id"])
            countries.append(n["cluster_id"].title())
    return " → ".join(countries)


def persist_songlines(neuron_map, paths: list[list[str]]) -> int:
    """Write songline records to SurrealDB and markdown files."""
    created_db = 0
    today = date.today().isoformat()

    for i, path in enumerate(paths):
        name = name_songline(neuron_map, path)

        # Country crossings
        countries_crossed = []
        seen_c = set()
        for nid in path:
            n = neuron_map.get(nid)
            if n and n.get("cluster_id") and n["cluster_id"] not in seen_c:
                seen_c.add(n["cluster_id"])
                countries_crossed.append(n["cluster_id"])

        # Waypoint IDs for SurrealDB
        waypoint_ids = ", ".join(path[:MAX_PATH_LENGTH])
        country_list = ", ".join(f'"{c}"' for c in countries_crossed)

        sql = (
            f'CREATE songline CONTENT {{'
            f' name: {json.dumps(name)},'
            f' waypoints: [{waypoint_ids}],'
            f' country_crossings: [{country_list}],'
            f' singer: "dreaming-engine",'
            f' walked_count: 0,'
            f' created: time::now()'
            f' }};'
        )
        result = query(sql)
        if result and result[0].get("status") == "OK":
            created_db += 1

    # Write songlines index markdown
    songlines_dir = VAULT_ROOT / "songlines"
    songlines_dir.mkdir(exist_ok=True)

    md_lines = [
        "---",
        f'title: "Songlines — {today}"',
        f"date: {today}",
        "tags: [songline, dreaming, cross-domain]",
        "aspect: connective",
        "neural:",
        "  activation: 0.800",
        "  stage: growing",
        "  cluster: songlines",
        "---",
        "",
        f"# Songlines Discovered — {today}",
        "",
        f"Auto-detected {len(paths)} knowledge paths crossing {MIN_COUNTRIES}+ Countries.",
        "",
    ]

    for i, path in enumerate(paths, 1):
        name = name_songline(neuron_map, path)
        md_lines.append(f"## {i}. {name}")
        md_lines.append("")
        for j, nid in enumerate(path):
            n = neuron_map.get(nid, {})
            slug = n.get("path", "unknown").replace("/", "/").rsplit(".md", 1)[0].split("/")[-1]
            cluster = n.get("cluster_id", "?")
            act = n.get("activation", 0)
            prefix = "→ " if j > 0 else "  "
            md_lines.append(f"{prefix}[[{slug}]] *({cluster}, act={act:.2f})*")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("*Generated by `scripts/detect-songlines.py` — the Dreaming Engine's path finder.*")

    out_path = songlines_dir / f"{today}-songlines.md"
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  Wrote {out_path.relative_to(VAULT_ROOT)}")

    return created_db


def main():
    print("=== Songline Detection ===")

    existing = get_results(query('SELECT count() FROM songline GROUP ALL;'))
    count = existing[0]["count"] if existing else 0
    print(f"Existing songlines: {count}")

    print("Loading graph...")
    neuron_map, out_neighbors = load_graph()
    print(f"  {len(neuron_map)} neurons, {sum(len(v) for v in out_neighbors.values())} edges")

    print("Finding cross-Country paths...")
    paths = find_songline_paths(neuron_map, out_neighbors)
    print(f"  Found {len(paths)} songlines crossing {MIN_COUNTRIES}+ Countries")

    if paths:
        print("Persisting songlines...")
        created = persist_songlines(neuron_map, paths)
        print(f"  SurrealDB records created: {created}")

    final = get_results(query('SELECT count() FROM songline GROUP ALL;'))
    final_count = final[0]["count"] if final else 0
    print(f"\n=== Complete: {final_count} total songlines ===")


if __name__ == "__main__":
    main()
