#!/usr/bin/env python3
"""Phase 3: The Etheric Body — Inject aspect: and neural: frontmatter into vault notes.

Adds two fields to every content note:
  aspect: knower|thinker|doer|connective  (based on directory)
  neural:
    activation: 0.XX   (from SurrealDB)
    stage: embryo|growing|mature|resting|composting|renewed  (from SurrealDB)
    cluster: <country>   (from SurrealDB cluster_id)

Uses targeted string insertion — NOT full YAML parse+dump — to preserve
the original frontmatter formatting and key order.
"""

import json
import re
import sys
from pathlib import Path

import requests

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = ("root", "root")
SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Content-Type": "text/plain",
}

# Directory → aspect
DIR_TO_ASPECT = {
    "cortex": "knower",
    "sensory": "knower",
    "memory": "knower",
    "genome": "knower",
    "prefrontal": "thinker",
    "laboratory": "thinker",
    "cerebellum": "thinker",
    "benchmarks": "thinker",
    "motor": "doer",
    "hippocampus": "doer",
    "thalamus": "doer",
    "missions": "doer",
    "retrospectives": "doer",
    "Agents": "doer",
    "dreaming": "connective",
    "songlines": "connective",
    "subconscious": "connective",
    "metabolism": "connective",
    "visual-cortex": "connective",
}

# Skip these directories (tooling, not content)
SKIP_DIRS = {
    ".git", ".obsidian", ".claude", "tools", "obsidian-plugin",
    "mcp-server", "scripts", "docs", "research", "teleport",
    "meta", "templates", "canvas", ".worktrees",
}


def query_surreal(sql: str) -> list:
    """Execute a SurrealDB query and return results list."""
    resp = requests.post(SURREAL_URL, headers=SURREAL_HEADERS, auth=SURREAL_AUTH, data=sql)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if not data or data[0].get("status") != "OK":
        return []
    return data[0]["result"]


def load_neuron_data() -> dict[str, dict]:
    """Fetch all neuron activation/stage/cluster from SurrealDB.

    Returns dict keyed by relative path.
    """
    print("Loading neuron data from SurrealDB...", file=sys.stderr)
    rows = query_surreal("SELECT path, activation, stage, cluster_id FROM neuron;")
    data = {}
    for row in rows:
        path = row.get("path", "")
        data[path] = {
            "activation": row.get("activation", 0.5),
            "stage": row.get("stage", "embryo"),
            "cluster": row.get("cluster_id") or "",
        }
    print(f"  Loaded {len(data)} neurons from SurrealDB", file=sys.stderr)
    return data


def find_frontmatter_bounds(content: str) -> tuple[int, int] | None:
    """Return (start, end) line indices of frontmatter block (inclusive of --- markers).

    Returns None if no frontmatter found.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (0, i)
    return None


def has_field(frontmatter_lines: list[str], field: str) -> bool:
    """Check if a field exists at top-level in frontmatter lines."""
    prefix = f"{field}:"
    for line in frontmatter_lines:
        if line.startswith(prefix) or line == prefix.rstrip(":"):
            return True
    return False


def inject_frontmatter(content: str, aspect: str, neural: dict | None) -> tuple[str, list[str]]:
    """Inject aspect: and neural: into frontmatter if missing.

    Returns (new_content, list_of_changes).
    Changes is empty if nothing was modified.
    """
    bounds = find_frontmatter_bounds(content)
    changes = []

    if bounds is None:
        # No frontmatter — add a minimal one
        new_fm_lines = ["---", f"aspect: {aspect}"]
        if neural:
            new_fm_lines.extend([
                "neural:",
                f"  activation: {neural['activation']:.3f}",
                f"  stage: {neural['stage']}",
                f"  cluster: {neural['cluster']}",
            ])
        new_fm_lines.append("---")
        new_content = "\n".join(new_fm_lines) + "\n" + content
        changes.append("added frontmatter with aspect + neural")
        return new_content, changes

    lines = content.split("\n")
    start, end = bounds
    fm_lines = lines[start + 1:end]  # lines between the --- markers

    injections = []

    if not has_field(fm_lines, "aspect"):
        injections.append(f"aspect: {aspect}")
        changes.append(f"added aspect: {aspect}")

    if neural and not has_field(fm_lines, "neural"):
        injections.append("neural:")
        injections.append(f"  activation: {neural['activation']:.3f}")
        injections.append(f"  stage: {neural['stage']}")
        if neural["cluster"]:
            injections.append(f"  cluster: {neural['cluster']}")
        changes.append("added neural block")

    if not injections:
        return content, []

    # Insert injections just before the closing ---
    new_lines = lines[: end] + injections + lines[end:]
    return "\n".join(new_lines), changes


def process_vault(dry_run: bool = False) -> None:
    """Walk content directories and inject frontmatter into all notes."""
    neuron_data = load_neuron_data()

    stats = {"processed": 0, "modified": 0, "skipped_no_fm": 0, "errors": 0}
    modified_files = []

    for dir_name, aspect in DIR_TO_ASPECT.items():
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            print(f"  [skip] {dir_name}/ not found", file=sys.stderr)
            continue

        md_files = list(dir_path.rglob("*.md"))
        print(f"\n{dir_name}/ ({aspect}) — {len(md_files)} files", file=sys.stderr)

        for md_file in sorted(md_files):
            rel_path = str(md_file.relative_to(VAULT_PATH))

            # Skip template files but process _index.md
            if md_file.name == "_template.md":
                continue

            stats["processed"] += 1

            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"  ERROR reading {rel_path}: {e}", file=sys.stderr)
                stats["errors"] += 1
                continue

            # Get SurrealDB data for this note
            neural = neuron_data.get(rel_path)

            new_content, changes = inject_frontmatter(content, aspect, neural)

            if changes:
                stats["modified"] += 1
                modified_files.append((rel_path, changes))
                if not dry_run:
                    md_file.write_text(new_content, encoding="utf-8")
                else:
                    print(f"  [dry-run] {rel_path}: {', '.join(changes)}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"Phase 3 Complete: The Etheric Body", file=sys.stderr)
    print(f"  Processed: {stats['processed']}", file=sys.stderr)
    print(f"  Modified:  {stats['modified']}", file=sys.stderr)
    print(f"  Errors:    {stats['errors']}", file=sys.stderr)
    if dry_run:
        print("  (DRY RUN — no files written)", file=sys.stderr)

    # Print JSON summary for piping
    summary = {
        "stats": stats,
        "modified_count": len(modified_files),
        "sample_modifications": modified_files[:20],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN MODE — no files will be modified\n", file=sys.stderr)
    process_vault(dry_run=dry_run)
