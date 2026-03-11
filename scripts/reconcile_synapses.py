#!/usr/bin/env python3
"""Synapse Reconciliation — resolve all wiki-links to SurrealDB synapses.

Strategy:
1. Fetch all neurons from SurrealDB (id + path)
2. Build stem-to-id lookup (how Obsidian resolves [[links]])
3. Parse all vault .md files for wiki-links
4. For each (source, target) pair, create a synapse if not exists
5. Update synapse_out / synapse_in counts on neurons
"""

import base64, hashlib, json, re, sys, urllib.request
from collections import defaultdict
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
SURREAL_URL = "http://localhost:8001/sql"
HDRS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
}
WL = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
CONTENT_DIRS = [
    "cortex", "sensory", "memory", "genome", "prefrontal", "laboratory", "cerebellum",
    "benchmarks", "motor", "hippocampus", "thalamus", "missions", "retrospectives",
    "dreaming", "songlines", "subconscious", "metabolism", "visual-cortex", "Agents",
    "docs", "teleport", "assessments", "canvas", "meta", "skills_index",
]


def query(sql, timeout=120):
    req = urllib.request.Request(
        SURREAL_URL, data=sql.encode("utf-8"), headers=HDRS, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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


def load_neuron_map():
    """Fetch all neurons, build path->id and stem->id lookups."""
    neurons = get_results(query("SELECT id, path FROM neuron;"))
    print(f"  Loaded {len(neurons)} neurons from SurrealDB")

    path_to_id = {}
    stem_to_ids = defaultdict(list)

    for n in neurons:
        nid = str(n["id"])
        path = n["path"]
        path_to_id[path] = nid
        # Extract stem: "cortex/machine-learning.md" -> "machine-learning"
        stem = Path(path).stem
        stem_to_ids[stem].append(nid)

    return path_to_id, stem_to_ids


def resolve_link(target, stem_to_ids):
    """Resolve an Obsidian wiki-link target to a neuron ID.

    Obsidian resolution order:
    1. Exact stem match (most common)
    2. Case-insensitive stem match
    3. Path-included match (e.g., [[cortex/machine-learning]])
    """
    # Normalize: strip .md if present, handle path prefixes
    target_clean = target.replace(".md", "").strip()

    # If target includes a path separator, extract the stem
    if "/" in target_clean:
        target_stem = Path(target_clean).stem
    else:
        target_stem = target_clean

    # Exact stem match
    if target_stem in stem_to_ids:
        return stem_to_ids[target_stem][0]

    # Case-insensitive
    target_lower = target_stem.lower()
    for stem, ids in stem_to_ids.items():
        if stem.lower() == target_lower:
            return ids[0]

    return None


def load_existing_synapses():
    """Fetch all existing synapses as a set of (in_id, out_id) pairs."""
    synapses = get_results(query("SELECT in, out FROM synapse;"))
    existing = set()
    for s in synapses:
        existing.add((str(s["in"]), str(s["out"])))
    print(f"  Loaded {len(existing)} existing synapses")
    return existing


def parse_all_links(path_to_id):
    """Parse all vault files, return list of (source_id, target_text) pairs."""
    pairs = []
    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for f in dp.rglob("*.md"):
            if f.name.startswith("_"):
                continue
            rp = str(f.relative_to(VAULT_ROOT))
            src_id = path_to_id.get(rp)
            if not src_id:
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            targets = set(WL.findall(content))
            for t in targets:
                pairs.append((src_id, t))
    return pairs


def batch_create_synapses(new_synapses, batch_size=100):
    """Create synapses in batches using individual statements."""
    created = 0
    for i in range(0, len(new_synapses), batch_size):
        batch = new_synapses[i : i + batch_size]
        stmts = []
        for src_id, tgt_id in batch:
            stmts.append(
                f'RELATE {src_id}->synapse->{tgt_id} CONTENT '
                f'{{ weight: 1.0, link_type: "explicit", created: time::now() }};'
            )
        combined = "\n".join(stmts)
        results = query(combined)

        # Count successes
        if not results:
            continue
        # If single ERR (batch parse failure), fall back to one-at-a-time
        if len(results) == 1 and results[0].get("status") == "ERR":
            for stmt in stmts:
                r = query(stmt)
                if r and r[0].get("status") == "OK":
                    created += 1
        else:
            created += sum(1 for r in results if r.get("status") == "OK")

        if (i + batch_size) % 500 == 0:
            print(f"    ... {i + batch_size}/{len(new_synapses)}", file=sys.stderr)

    return created


def update_synapse_counts():
    """Recompute synapse_out and synapse_in for all neurons."""
    print("  Updating synapse counts on neurons...")

    # Count outbound per neuron
    out_counts = get_results(
        query("SELECT in AS nid, count() FROM synapse GROUP BY in;")
    )
    for row in out_counts:
        nid = str(row["nid"])
        cnt = row["count"]
        query(f"UPDATE {nid} SET synapse_out = {cnt};")

    # Count inbound per neuron
    in_counts = get_results(
        query("SELECT out AS nid, count() FROM synapse GROUP BY out;")
    )
    for row in in_counts:
        nid = str(row["nid"])
        cnt = row["count"]
        query(f"UPDATE {nid} SET synapse_in = {cnt};")

    print(f"    Updated {len(out_counts)} outbound, {len(in_counts)} inbound counts")


def main():
    print("=== Synapse Reconciliation ===")

    # Check SurrealDB is up
    if not query("INFO FOR DB;"):
        print("ERROR: SurrealDB not reachable", file=sys.stderr)
        sys.exit(1)

    # Step 1: Load neuron map
    print("\n1. Loading neuron map...")
    path_to_id, stem_to_ids = load_neuron_map()

    # Step 2: Load existing synapses
    print("\n2. Loading existing synapses...")
    existing = load_existing_synapses()

    # Step 3: Parse all wiki-links
    print("\n3. Parsing wiki-links from vault files...")
    link_pairs = parse_all_links(path_to_id)
    print(f"  Found {len(link_pairs)} (source, target) link pairs")

    # Step 4: Resolve targets and find new synapses
    print("\n4. Resolving link targets...")
    new_synapses = []
    resolved = 0
    unresolved = set()

    for src_id, target in link_pairs:
        tgt_id = resolve_link(target, stem_to_ids)
        if not tgt_id:
            unresolved.add(target)
            continue
        resolved += 1
        if src_id == tgt_id:
            continue  # skip self-links
        pair = (src_id, tgt_id)
        if pair not in existing:
            new_synapses.append(pair)
            existing.add(pair)  # prevent duplicates within this run

    print(f"  Resolved: {resolved}/{len(link_pairs)}")
    print(f"  Unresolved targets: {len(unresolved)}")
    print(f"  New synapses to create: {len(new_synapses)}")

    if unresolved and len(unresolved) <= 20:
        print(f"  Unresolved: {sorted(unresolved)[:20]}")

    # Step 5: Batch create
    if new_synapses:
        print("\n5. Creating synapses...")
        # Check if synapse is a RELATION table
        test = query(
            f'RELATE {new_synapses[0][0]}->synapse->{new_synapses[0][1]} CONTENT '
            f'{{ weight: 1.0, link_type: "explicit", created: time::now() }};'
        )
        if test and test[0].get("status") == "ERR" and "RELATION" in str(
            test[0].get("result", "")
        ):
            # synapse is NOT a relation table — use CREATE instead
            print("  synapse is not a RELATION table, using CREATE...")
            created = 0
            for i in range(0, len(new_synapses), 100):
                batch = new_synapses[i : i + 100]
                stmts = []
                for src_id, tgt_id in batch:
                    stmts.append(
                        f"CREATE synapse CONTENT {{ in: {src_id}, out: {tgt_id}, "
                        f'weight: 1.0, link_type: "explicit", created: time::now() }};'
                    )
                results = query("\n".join(stmts))
                if results:
                    if len(results) == 1 and results[0].get("status") == "ERR":
                        for stmt in stmts:
                            r = query(stmt)
                            if r and r[0].get("status") == "OK":
                                created += 1
                    else:
                        created += sum(
                            1 for r in results if r.get("status") == "OK"
                        )
                if (i + 100) % 500 == 0:
                    print(f"    ... {i + 100}/{len(new_synapses)}", file=sys.stderr)
        else:
            # RELATE worked — use it for all
            if test and test[0].get("status") == "OK":
                existing.add(new_synapses[0])
                new_synapses = new_synapses[1:]  # skip the test one
                created = 1
            else:
                created = 0
            created += batch_create_synapses(new_synapses)

        print(f"  Created: {created}")
    else:
        print("\n5. No new synapses needed.")

    # Step 6: Update counts
    print("\n6. Updating neuron synapse counts...")
    update_synapse_counts()

    # Final check
    result = get_results(query("SELECT count() FROM synapse GROUP ALL;"))
    total = result[0]["count"] if result else 0
    print(f"\n=== Complete: {total} total synapses ===")


if __name__ == "__main__":
    main()
