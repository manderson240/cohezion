#!/usr/bin/env python3
"""Extract 3D Graph data from vault for Obsidian visualization.

Uses the Triune Self directory architecture:
- Knower: cortex, sensory, memory, genome
- Thinker: prefrontal, laboratory, cerebellum
- Doer: motor, hippocampus, thalamus, missions, retrospectives
- Connective: dreaming, songlines, subconscious, metabolism, visual-cortex
"""

import json
import re
import sys
from pathlib import Path

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")

# Directory -> (type_name, aspect)
DIR_CONFIG = {
    # Knower
    "cortex": ("concept", "knower"),
    "sensory": ("paper", "knower"),
    "memory": ("lesson", "knower"),
    "genome": ("spec", "knower"),
    # Thinker
    "prefrontal": ("decision", "thinker"),
    "laboratory": ("experiment", "thinker"),
    "cerebellum": ("pattern", "thinker"),
    "benchmarks": ("benchmark", "thinker"),
    # Doer
    "motor": ("project", "doer"),
    "hippocampus": ("session", "doer"),
    "missions": ("mission", "doer"),
    "retrospectives": ("retrospective", "doer"),
    # Connective
    "dreaming": ("dream", "connective"),
    "songlines": ("songline", "connective"),
}

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")


def query_vault_files():
    """Extract vault file structure for graph nodes."""
    nodes = []
    node_map = {}

    for dir_name, (type_name, aspect) in DIR_CONFIG.items():
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue
        for md_file in dir_path.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            node_id = f"{dir_name}:{md_file.stem}"
            title = md_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": type_name,
                "aspect": aspect,
                "path": str(md_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id

    return nodes, node_map


def extract_wikilinks():
    """Extract wikilinks from vault files to build graph edges."""
    links = []

    for md_file in VAULT_PATH.rglob("*.md"):
        rel = str(md_file.relative_to(VAULT_PATH))
        if any(skip in rel for skip in [".obsidian", ".git", ".claude", "node_modules", ".worktrees"]):
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        rel_path = md_file.relative_to(VAULT_PATH)
        source_type = rel_path.parts[0] if rel_path.parts else "other"
        source_id = f"{source_type}:{md_file.stem}"

        for target in WIKILINK_RE.findall(content):
            target_clean = target.strip()
            # For path-prefixed links, use the directory
            if "/" in target_clean:
                parts = target_clean.split("/", 1)
                target_id = f"{parts[0]}:{Path(parts[1]).stem}"
            else:
                target_id = f"cortex:{target_clean}"

            links.append({
                "source": source_id,
                "target": target_id,
                "strength": 1.0,
                "type": "wikilink",
            })

    return links


def main():
    """Extract and output 3D Graph data."""
    print("Extracting vault structure...", file=sys.stderr)
    nodes, node_map = query_vault_files()
    print(f"Found {len(nodes)} nodes", file=sys.stderr)

    print("Extracting wikilinks...", file=sys.stderr)
    links = extract_wikilinks()
    print(f"Found {len(links)} links", file=sys.stderr)

    # Deduplicate
    unique_links = []
    seen = set()
    for link in links:
        key = (link["source"], link["target"])
        if key not in seen:
            unique_links.append(link)
            seen.add(key)

    print(f"Unique links: {len(unique_links)}", file=sys.stderr)

    graph_data = {
        "nodes": nodes,
        "links": unique_links,
        "metadata": {
            "total_nodes": len(nodes),
            "total_links": len(unique_links),
            "node_types": {},
            "aspects": {},
        },
    }

    for node in nodes:
        t = node["type"]
        a = node["aspect"]
        graph_data["metadata"]["node_types"][t] = graph_data["metadata"]["node_types"].get(t, 0) + 1
        graph_data["metadata"]["aspects"][a] = graph_data["metadata"]["aspects"].get(a, 0) + 1

    print(json.dumps(graph_data, indent=2))


if __name__ == "__main__":
    main()
