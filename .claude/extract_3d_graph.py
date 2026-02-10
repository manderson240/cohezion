#!/usr/bin/env python3
"""Extract 3D Graph data from SurrealDB for Obsidian visualization."""

import json
import sys
import subprocess
from pathlib import Path

# Use direct SurrealQL CLI instead
SURREALDB_URL = "http://localhost:8000"
NAMESPACE = "cohezion"
DATABASE = "vault"

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")


def query_vault_files():
    """Extract vault file structure for graph nodes."""
    
    nodes = []
    node_map = {}
    
    # Scan papers directory
    papers_dir = VAULT_PATH / "papers"
    if papers_dir.exists():
        for paper_file in papers_dir.glob("*.md"):
            node_id = f"papers:{paper_file.stem}"
            title = paper_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": "paper",
                "path": str(paper_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id
    
    # Scan concepts directory
    concepts_dir = VAULT_PATH / "concepts"
    if concepts_dir.exists():
        for concept_file in concepts_dir.glob("*.md"):
            node_id = f"concepts:{concept_file.stem}"
            title = concept_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": "concept",
                "path": str(concept_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id
    
    # Scan decisions directory
    decisions_dir = VAULT_PATH / "decisions"
    if decisions_dir.exists():
        for decision_file in decisions_dir.glob("*.md"):
            node_id = f"decisions:{decision_file.stem}"
            title = decision_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": "decision",
                "path": str(decision_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id
    
    # Scan patterns directory
    patterns_dir = VAULT_PATH / "patterns"
    if patterns_dir.exists():
        for pattern_file in patterns_dir.glob("*.md"):
            node_id = f"patterns:{pattern_file.stem}"
            title = pattern_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": "pattern",
                "path": str(pattern_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id
    
    # Scan experiments directory
    experiments_dir = VAULT_PATH / "experiments"
    if experiments_dir.exists():
        for exp_file in experiments_dir.glob("*.md"):
            node_id = f"experiments:{exp_file.stem}"
            title = exp_file.stem
            nodes.append({
                "id": node_id,
                "label": title,
                "type": "experiment",
                "path": str(exp_file.relative_to(VAULT_PATH)),
            })
            node_map[title.lower()] = node_id
    
    return nodes, node_map


def extract_wikilinks():
    """Extract wikilinks from vault files to build graph edges."""
    
    import re
    
    links = []
    wikilink_pattern = re.compile(r'\[\[([^\]]+)\]\]')
    
    # Scan all markdown files
    for md_file in VAULT_PATH.rglob("*.md"):
        if ".obsidian" in str(md_file) or ".git" in str(md_file):
            continue
        
        try:
            content = md_file.read_text(encoding='utf-8')
            matches = wikilink_pattern.findall(content)
            
            # Source node ID
            rel_path = md_file.relative_to(VAULT_PATH)
            source_type = rel_path.parts[0] if rel_path.parts else "other"
            source_id = f"{source_type}:{md_file.stem}"
            
            for target in matches:
                target_clean = target.split("|")[0].strip()  # Handle [[name|display]]
                target_type = None
                target_id = None
                
                # Determine target type
                if target_clean.startswith("papers/"):
                    target_id = f"papers:{Path(target_clean).stem}"
                    target_type = "paper"
                elif target_clean.startswith("concepts/"):
                    target_id = f"concepts:{Path(target_clean).stem}"
                    target_type = "concept"
                elif target_clean.startswith("decisions/"):
                    target_id = f"decisions:{Path(target_clean).stem}"
                    target_type = "decision"
                elif target_clean.startswith("patterns/"):
                    target_id = f"patterns:{Path(target_clean).stem}"
                    target_type = "pattern"
                elif target_clean.startswith("experiments/"):
                    target_id = f"experiments:{Path(target_clean).stem}"
                    target_type = "experiment"
                else:
                    # Implicit reference - try to find in concepts first
                    target_id = f"concepts:{target_clean}"
                    target_type = "concept"
                
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "strength": 1.0,
                    "type": "wikilink"
                })
        except Exception as e:
            continue
    
    return links


def main():
    """Extract and output 3D Graph data."""
    
    print("Extracting vault structure...", file=sys.stderr)
    nodes, node_map = query_vault_files()
    
    print(f"Found {len(nodes)} nodes", file=sys.stderr)
    print("Extracting wikilinks...", file=sys.stderr)
    links = extract_wikilinks()
    
    print(f"Found {len(links)} links", file=sys.stderr)
    
    # Deduplicate links
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
            "node_types": {}
        }
    }
    
    # Count node types
    for node in nodes:
        node_type = node["type"]
        if node_type not in graph_data["metadata"]["node_types"]:
            graph_data["metadata"]["node_types"][node_type] = 0
        graph_data["metadata"]["node_types"][node_type] += 1
    
    print(json.dumps(graph_data, indent=2))


if __name__ == "__main__":
    main()
