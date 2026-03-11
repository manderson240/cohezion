#!/usr/bin/env python3
"""Generate subconscious report — latent associations between notes that should be linked.

Finds pairs of notes with:
1. Same cluster but no direct synapse (cluster siblings with no link)
2. Similar tags but no direct synapse
3. Both high-activation but unlinked
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
MAX_ASSOCIATIONS = 30

DIR_TO_ASPECT = {
    "cortex": "knower", "sensory": "knower", "memory": "knower", "genome": "knower",
    "prefrontal": "thinker", "laboratory": "thinker", "cerebellum": "thinker", "benchmarks": "thinker",
    "motor": "doer", "hippocampus": "doer", "thalamus": "doer", "missions": "doer",
    "retrospectives": "doer", "Agents": "doer",
    "dreaming": "connective", "songlines": "connective", "subconscious": "connective",
    "metabolism": "connective", "visual-cortex": "connective",
}


def query(sql: str) -> list[dict]:
    req = urllib.request.Request(SURREAL_URL, data=sql.encode("utf-8"), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
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


def load_data():
    """Load neurons, synapses, and tags."""
    neurons = get_results(query(
        'SELECT id, path, title, cluster_id, activation, tags FROM neuron;'
    ))
    synapses = get_results(query('SELECT in, out FROM synapse;'))

    neuron_map = {}
    for n in neurons:
        nid = str(n["id"])
        top_dir = n["path"].split("/")[0]
        n["aspect"] = DIR_TO_ASPECT.get(top_dir, "unknown")
        neuron_map[nid] = n

    # Build set of linked pairs for fast lookup
    linked_pairs: set[frozenset[str]] = set()
    for s in synapses:
        linked_pairs.add(frozenset([str(s["in"]), str(s["out"])]))

    return neuron_map, linked_pairs


def find_cluster_siblings(neuron_map, linked_pairs) -> list[dict]:
    """Notes in the same cluster with high activation but no link."""
    print("  Finding cluster siblings...")
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for nid, n in neuron_map.items():
        if n.get("cluster_id") and n.get("activation", 0) > 0.4:
            by_cluster[n["cluster_id"]].append(n)

    associations = []
    for cluster_id, cluster_neurons in by_cluster.items():
        # Sort by activation desc, take top notes
        cluster_neurons.sort(key=lambda x: x.get("activation", 0), reverse=True)
        top = cluster_neurons[:15]

        for i, a in enumerate(top):
            for b in top[i + 1:]:
                pair = frozenset([str(a["id"]), str(b["id"])])
                if pair not in linked_pairs:
                    score = (a.get("activation", 0) + b.get("activation", 0)) / 2
                    associations.append({
                        "a": a, "b": b,
                        "reason": f"same cluster ({cluster_id}), no link",
                        "score": score,
                    })

    return associations


def find_tag_overlap(neuron_map, linked_pairs) -> list[dict]:
    """Notes sharing 3+ tags but no direct link."""
    print("  Finding tag overlaps...")
    # Index notes by tag
    by_tag: dict[str, list[str]] = defaultdict(list)
    for nid, n in neuron_map.items():
        tags = n.get("tags") or []
        if isinstance(tags, list):
            for tag in tags:
                by_tag[tag].append(nid)

    # Find pairs with 3+ shared tags
    pair_tag_count: dict[frozenset[str], int] = defaultdict(int)
    for tag, nids in by_tag.items():
        if len(nids) > 50:
            continue  # Skip very common tags
        for i, a in enumerate(nids):
            for b in nids[i + 1:]:
                pair_tag_count[frozenset([a, b])] += 1

    associations = []
    for pair, count in pair_tag_count.items():
        if count >= 3 and pair not in linked_pairs:
            ids = list(pair)
            a = neuron_map.get(ids[0])
            b = neuron_map.get(ids[1])
            if a and b:
                associations.append({
                    "a": a, "b": b,
                    "reason": f"{count} shared tags, no link",
                    "score": count * 0.15 + (a.get("activation", 0) + b.get("activation", 0)) / 4,
                })

    return associations


def find_cross_aspect_unlinked(neuron_map, linked_pairs) -> list[dict]:
    """High-activation notes from different aspects with no link."""
    print("  Finding cross-aspect unlinked pairs...")
    by_aspect: dict[str, list[dict]] = defaultdict(list)
    for nid, n in neuron_map.items():
        if n.get("activation", 0) > 0.6 and n["aspect"] != "unknown":
            by_aspect[n["aspect"]].append(n)

    associations = []
    aspects = list(by_aspect.keys())
    for i, asp_a in enumerate(aspects):
        for asp_b in aspects[i + 1:]:
            for a in by_aspect[asp_a][:10]:
                for b in by_aspect[asp_b][:10]:
                    pair = frozenset([str(a["id"]), str(b["id"])])
                    if pair not in linked_pairs:
                        score = (a.get("activation", 0) + b.get("activation", 0)) / 2 * 1.2
                        associations.append({
                            "a": a, "b": b,
                            "reason": f"cross-aspect ({a['aspect']}↔{b['aspect']}), high activation, no link",
                            "score": score,
                        })

    return associations


def write_report(associations: list[dict]) -> Path:
    """Write the subconscious report as a vault note."""
    today = date.today().isoformat()
    subconscious_dir = VAULT_ROOT / "subconscious"
    subconscious_dir.mkdir(exist_ok=True)

    md_lines = [
        "---",
        f'title: "Subconscious — Latent Associations {today}"',
        f"date: {today}",
        "tags: [subconscious, latent-links, dreaming]",
        "aspect: connective",
        "neural:",
        "  activation: 0.750",
        "  stage: growing",
        "  cluster: subconscious",
        "---",
        "",
        f"# Latent Associations — {today}",
        "",
        f"Found {len(associations)} note pairs that *should* be linked but aren't.",
        "These are knowledge connections lurking in the subconscious — similar context,",
        "shared tags, or cross-aspect resonance with no explicit wiki-link.",
        "",
        "## Top Associations",
        "",
    ]

    for i, assoc in enumerate(associations[:MAX_ASSOCIATIONS], 1):
        a = assoc["a"]
        b = assoc["b"]
        slug_a = a["path"].rsplit(".md", 1)[0].split("/")[-1]
        slug_b = b["path"].rsplit(".md", 1)[0].split("/")[-1]
        reason = assoc["reason"]
        score = assoc["score"]

        md_lines.append(f"### {i}. {reason} (score: {score:.2f})")
        md_lines.append("")
        md_lines.append(f"- [[{slug_a}]] *({a.get('cluster_id', '?')}, act={a.get('activation', 0):.2f})*")
        md_lines.append(f"- [[{slug_b}]] *({b.get('cluster_id', '?')}, act={b.get('activation', 0):.2f})*")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## How to Use")
    md_lines.append("")
    md_lines.append("Review these pairs. If they genuinely relate:")
    md_lines.append("1. Add a `[[wiki-link]]` from one to the other")
    md_lines.append("2. The link becomes a synapse in SurrealDB on next sync")
    md_lines.append("3. The pair moves from subconscious to conscious knowledge")
    md_lines.append("")
    md_lines.append("*Generated by `scripts/subconscious-report.py`*")

    out_path = subconscious_dir / f"{today}-latent-associations.md"
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    return out_path


def main():
    print("=== Subconscious Report ===")
    neuron_map, linked_pairs = load_data()
    print(f"Loaded {len(neuron_map)} neurons, {len(linked_pairs)} linked pairs")

    all_associations = []
    all_associations.extend(find_cluster_siblings(neuron_map, linked_pairs))
    all_associations.extend(find_tag_overlap(neuron_map, linked_pairs))
    all_associations.extend(find_cross_aspect_unlinked(neuron_map, linked_pairs))

    print(f"\nTotal raw associations: {len(all_associations)}")

    # Deduplicate and sort by score
    seen: set[frozenset[str]] = set()
    unique = []
    for a in all_associations:
        key = frozenset([str(a["a"]["id"]), str(a["b"]["id"])])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    unique.sort(key=lambda x: x["score"], reverse=True)
    print(f"Unique associations: {len(unique)}")
    print(f"Writing top {min(len(unique), MAX_ASSOCIATIONS)}...")

    out_path = write_report(unique)
    print(f"\n=== Complete: {out_path.relative_to(VAULT_ROOT)} ===")


if __name__ == "__main__":
    main()
