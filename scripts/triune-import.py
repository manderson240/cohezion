#!/usr/bin/env python3
"""
Triune Vault Import — Load all vault notes as neurons and wiki-links as synapses.

Scans the vault, extracts frontmatter + wiki-links, computes aspect/stage/activation,
and upserts everything into SurrealDB.

Usage:
    python3 scripts/triune-import.py [--dry-run] [--port 8001]
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml

# ─── Configuration ───────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).resolve().parent.parent
SURREAL_URL = "http://localhost:{port}/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"

# Directories to skip (not content — tooling, build artifacts, non-note files)
SKIP_DIRS = {
    # Hidden / git
    ".git", ".obsidian", ".claude", ".worktrees", ".entire", ".locks",
    ".pytest_cache", ".ruff_cache", ".github", ".vault-journal",
    # Build / tooling
    "node_modules", "htmlcov", "logs", "telemetry", "tools",
    "obsidian-plugin", "mcp-server", "src", "tests", "scripts",
    # Non-content vault dirs
    "attachments", "templates", "skills_index", "checkpoints",
    "archived", "learnings", "data", "skills",
}

# Directory -> Triune Aspect mapping
# Current names first, then old aliases for backward compatibility
DIR_TO_ASPECT = {
    # Knower (awareness, ground truth)
    "cortex": "knower",       # was: concepts
    "sensory": "knower",      # was: papers
    "memory": "knower",       # was: lessons
    "genome": "knower",       # was: specs
    "research": "knower",
    # Old aliases (knower)
    "concepts": "knower",
    "papers": "knower",
    "lessons": "knower",
    "specs": "knower",
    # Thinker (reasoning, judgment)
    "prefrontal": "thinker",  # was: decisions
    "laboratory": "thinker",  # was: experiments
    "cerebellum": "thinker",  # was: patterns
    "benchmarks": "thinker",
    # Old aliases (thinker)
    "decisions": "thinker",
    "experiments": "thinker",
    "patterns": "thinker",
    # Doer (action, lived experience)
    "motor": "doer",          # was: projects
    "hippocampus": "doer",    # was: daily/sessions
    "thalamus": "doer",       # was: inbox
    "missions": "doer",
    "retrospectives": "doer",
    "Agents": "doer",
    # Old aliases (doer)
    "projects": "doer",
    "daily": "doer",
    "sessions": "doer",
    "inbox": "doer",
    # Connective (where all three meet)
    "dreaming": "connective",
    "songlines": "connective",
    "subconscious": "connective",
    "metabolism": "connective",
    "visual-cortex": "connective",  # was: canvas
    "docs": "connective",
    "meta": "connective",
    "assessments": "connective",
    "cycles": "connective",
    "teleport": "connective",
    # Old aliases (connective)
    "canvas": "connective",
}

# Wiki-link regex: [[target]] or [[target|alias]]
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown text."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[end + 3:].strip()
    return fm, body


def extract_wiki_links(text: str) -> list[str]:
    """Extract all wiki-link targets from markdown text."""
    return list(set(WIKI_LINK_RE.findall(text)))


def sanitize_id(path: str) -> str:
    """Convert a file path to a SurrealDB-safe record ID string."""
    return (
        path.replace("/", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace('"', "")
        .lower()
    )


def compute_stage(synapse_count: int, word_count: int, activation: float,
                  days_since_modified: int) -> str:
    """Compute lifecycle stage."""
    if synapse_count < 3 and word_count < 500:
        return "embryo"
    if activation < 0.2 and days_since_modified > 30:
        return "resting"
    if synapse_count >= 10 and word_count >= 500:
        return "mature"
    return "growing"


def compute_activation(word_count: int, synapse_count: int,
                       days_since_modified: int) -> float:
    """Compute activation energy (0.0 - 1.0)."""
    # Base activation from content richness
    content_score = min(word_count / 2000.0, 1.0) * 0.4
    # Connection score
    link_score = min(synapse_count / 20.0, 1.0) * 0.3
    # Recency score (decays over 60 days)
    recency = max(0.0, 1.0 - (days_since_modified / 60.0)) * 0.3
    return round(min(content_score + link_score + recency, 1.0), 3)


def get_directory(path: str) -> str:
    """Get the top-level directory from a relative path."""
    parts = Path(path).parts
    return parts[0] if len(parts) > 1 else ""


def get_aspect(directory: str) -> str:
    """Get the Triune aspect for a directory."""
    return DIR_TO_ASPECT.get(directory, "connective")


# ─── Scanner ─────────────────────────────────────────────────────────────────

def scan_vault() -> list[dict]:
    """Scan all vault markdown files and extract metadata."""
    notes = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        # Filter out skip directories
        rel_root = Path(root).relative_to(VAULT_ROOT)
        top_dir = str(rel_root).split("/")[0] if str(rel_root) != "." else ""

        if top_dir in SKIP_DIRS:
            dirs.clear()
            continue

        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for fname in files:
            if not fname.endswith(".md"):
                continue

            fpath = Path(root) / fname
            rel_path = str(fpath.relative_to(VAULT_ROOT))
            directory = get_directory(rel_path)

            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            fm, body = parse_frontmatter(text)
            links = extract_wiki_links(text)
            word_count = len(body.split())

            # Get file modification time
            stat = fpath.stat()
            modified = datetime.datetime.fromtimestamp(
                stat.st_mtime, tz=datetime.timezone.utc
            )
            created = datetime.datetime.fromtimestamp(
                stat.st_ctime, tz=datetime.timezone.utc
            )
            days_since = (datetime.datetime.now(datetime.timezone.utc) - modified).days

            # Compute neural properties
            synapse_count = len(links)
            activation = compute_activation(word_count, synapse_count, days_since)
            stage = compute_stage(synapse_count, word_count, activation, days_since)
            aspect = get_aspect(directory)

            title = fm.get("title", fname.replace(".md", "").replace("-", " ").title())
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            notes.append({
                "path": rel_path,
                "title": str(title),
                "aspect": aspect,
                "activation": activation,
                "stage": stage,
                "word_count": word_count,
                "synapse_out": synapse_count,
                "tags": tags if isinstance(tags, list) else [],
                "links": links,
                "directory": directory,
                "created": created.isoformat(),
                "modified": modified.isoformat(),
                "cluster_id": directory,  # Initial cluster = directory
                "record_id": sanitize_id(rel_path),
            })

    return notes


# ─── SurrealDB Client ───────────────────────────────────────────────────────

class SurrealClient:
    def __init__(self, port: int = 8001):
        self.url = SURREAL_URL.format(port=port)
        self.session = requests.Session()
        self.session.auth = (SURREAL_USER, SURREAL_PASS)
        self.session.headers.update({
            "Accept": "application/json",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
        })

    def query(self, sql: str) -> list[dict]:
        resp = self.session.post(self.url, data=sql.encode("utf-8"))
        if resp.status_code >= 400:
            # Try to get error detail
            try:
                return resp.json()
            except Exception:
                return [{"status": "ERR", "result": f"HTTP {resp.status_code}: {resp.text[:200]}"}]
        return resp.json()

    def batch_query(self, statements: list[str], batch_size: int = 50) -> int:
        """Execute statements in batches, return total success count."""
        ok = 0
        errors = 0
        for i in range(0, len(statements), batch_size):
            batch = statements[i:i + batch_size]
            # Execute one at a time if batch fails
            sql = ";\n".join(batch)
            results = self.query(sql)
            # Check for batch-level failure
            if len(results) == 1 and results[0].get("status") == "ERR":
                # Fall back to one-at-a-time
                for stmt in batch:
                    r = self.query(stmt)
                    if r and r[0].get("status") == "OK":
                        ok += 1
                    else:
                        errors += 1
                        if errors <= 10:
                            err_msg = r[0].get("result", "") if r else "no response"
                            print(f"  ERR: {str(err_msg)[:200]}", file=sys.stderr)
                            print(f"  STMT: {stmt[:200]}", file=sys.stderr)
            else:
                for r in results:
                    if r.get("status") == "OK":
                        ok += 1
                    else:
                        errors += 1
                        if errors <= 10:
                            print(f"  ERR: {r.get('result', '')[:200]}", file=sys.stderr)
        if errors > 0:
            print(f"  Total errors: {errors}", file=sys.stderr)
        return ok


# ─── Import Logic ────────────────────────────────────────────────────────────

def escape_surql(s: str) -> str:
    """Escape a string for SurrealQL."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def build_neuron_upserts(notes: list[dict]) -> list[str]:
    """Build UPSERT statements for all neurons."""
    stmts = []
    for n in notes:
        title = escape_surql(n["title"])
        path = escape_surql(n["path"])
        tags_json = json.dumps(n["tags"])
        directory = escape_surql(n.get("directory", ""))
        cluster_id = escape_surql(n.get("cluster_id", ""))

        stmt = (
            f"UPSERT neuron:`{n['record_id']}` SET "
            f"path = '{path}', "
            f"title = '{title}', "
            f"aspect = '{n['aspect']}', "
            f"activation = {n['activation']}, "
            f"stage = '{n['stage']}', "
            f"last_fired = d'{n['modified']}', "
            f"cluster_id = '{cluster_id}', "
            f"synapse_out = {n['synapse_out']}, "
            f"synapse_in = 0, "
            f"word_count = {n['word_count']}, "
            f"tags = {tags_json}, "
            f"directory = '{directory}', "
            f"created = d'{n['created']}', "
            f"modified = d'{n['modified']}'"
        )
        stmts.append(stmt)
    return stmts


def build_synapse_inserts(notes: list[dict], path_to_id: dict) -> list[str]:
    """Build RELATE statements for all wiki-links."""
    stmts = []
    for n in notes:
        from_id = n["record_id"]
        for link_target in n["links"]:
            # Try to resolve the link target to a note
            target_id = resolve_link(link_target, path_to_id)
            if target_id and target_id != from_id:
                stmt = (
                    f"RELATE neuron:`{from_id}`->synapse->neuron:`{target_id}` SET "
                    f"weight = 1.0, "
                    f"link_type = 'explicit', "
                    f"created = d'{n['modified']}'"
                )
                stmts.append(stmt)
    return stmts


def build_inbound_updates(notes: list[dict], path_to_id: dict) -> list[str]:
    """Build UPDATE statements to set synapse_in counts."""
    # Count inbound links per target
    inbound: dict[str, int] = {}
    for n in notes:
        for link_target in n["links"]:
            target_id = resolve_link(link_target, path_to_id)
            if target_id:
                inbound[target_id] = inbound.get(target_id, 0) + 1

    stmts = []
    for record_id, count in inbound.items():
        stmts.append(f"UPDATE neuron:`{record_id}` SET synapse_in = {count}")
    return stmts


def build_history_inserts(notes: list[dict]) -> list[str]:
    """Record initial creation events in the Akashic Records."""
    stmts = []
    for n in notes:
        path = escape_surql(n["path"])
        stmt = (
            f"CREATE neuron_history SET "
            f"neuron = '{n['record_id']}', "
            f"event_type = 'created', "
            f"timestamp = d'{n['created']}', "
            f"detail = 'Initial import: {path}'"
        )
        stmts.append(stmt)
    return stmts


def resolve_link(target: str, path_to_id: dict) -> str | None:
    """Resolve a wiki-link target to a neuron record ID."""
    # Obsidian wiki-links use bare filenames (no path, no .md)
    # Try exact match first
    target_clean = target.strip()

    # Check by filename (most common case)
    fname_key = target_clean.lower()
    if fname_key in path_to_id:
        return path_to_id[fname_key]

    # Try with .md
    fname_md = fname_key + ".md" if not fname_key.endswith(".md") else fname_key
    if fname_md in path_to_id:
        return path_to_id[fname_md]

    return None


def build_filename_index(notes: list[dict]) -> dict[str, str]:
    """Build a lookup from filename (lowercase, no ext) -> record_id."""
    index: dict[str, str] = {}
    for n in notes:
        # Index by bare filename without extension
        fname = Path(n["path"]).stem.lower()
        index[fname] = n["record_id"]
        # Also index by filename with .md
        index[fname + ".md"] = n["record_id"]
        # Also index by full relative path
        index[n["path"].lower()] = n["record_id"]
    return index


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Triune Vault Import")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't write to SurrealDB")
    parser.add_argument("--port", type=int, default=8001, help="SurrealDB port")
    args = parser.parse_args()

    print(f"Scanning vault at {VAULT_ROOT}...")
    notes = scan_vault()
    print(f"Found {len(notes)} notes")

    # Stats
    aspects = {}
    stages = {}
    for n in notes:
        aspects[n["aspect"]] = aspects.get(n["aspect"], 0) + 1
        stages[n["stage"]] = stages.get(n["stage"], 0) + 1

    print("\nAspect distribution:")
    for a, c in sorted(aspects.items()):
        print(f"  {a}: {c}")

    print("\nStage distribution:")
    for s, c in sorted(stages.items()):
        print(f"  {s}: {c}")

    # Count total links
    total_links = sum(len(n["links"]) for n in notes)
    print(f"\nTotal wiki-links found: {total_links}")

    if args.dry_run:
        print("\n[DRY RUN] No data written to SurrealDB.")
        return

    # Connect
    db = SurrealClient(port=args.port)

    # Test connection
    test = db.query("SELECT count() FROM neuron GROUP ALL")
    print(f"\nConnected to SurrealDB on port {args.port}")

    # Phase 0: Resolve ID collisions — find existing neurons by path
    # so we UPSERT using their existing ID, not a freshly derived one.
    print("\n[0/5] Resolving existing neuron IDs...")
    existing = db.query("SELECT id, path FROM neuron")
    path_to_existing_id: dict[str, str] = {}
    if existing and existing[0].get("result"):
        for row in existing[0]["result"]:
            raw_id = str(row["id"]).removeprefix("neuron:")
            path_to_existing_id[row["path"]] = raw_id
    print(f"  {len(path_to_existing_id)} existing neurons indexed")

    # Override record_id for notes that already exist under a different ID
    collisions_fixed = 0
    for n in notes:
        if n["path"] in path_to_existing_id:
            existing_id = path_to_existing_id[n["path"]]
            if existing_id != n["record_id"]:
                n["record_id"] = existing_id
                collisions_fixed += 1
    if collisions_fixed:
        print(f"  {collisions_fixed} ID collisions resolved (reusing existing IDs)")

    # Build lookup (after collision resolution)
    path_to_id = build_filename_index(notes)

    # Phase 1: Upsert all neurons
    print("\n[1/5] Upserting neurons...")
    neuron_stmts = build_neuron_upserts(notes)
    ok = db.batch_query(neuron_stmts, batch_size=100)
    print(f"  {ok}/{len(neuron_stmts)} neurons upserted")

    # Phase 2: Replace synapses (delete old, create fresh — ensures idempotency)
    print("\n[2/5] Replacing synapses (wiki-links)...")
    db.query("DELETE synapse")
    synapse_stmts = build_synapse_inserts(notes, path_to_id)
    ok = db.batch_query(synapse_stmts, batch_size=100)
    print(f"  {ok}/{len(synapse_stmts)} synapses created (clean)")

    # Phase 3: Update inbound counts
    print("\n[3/5] Updating inbound synapse counts...")
    inbound_stmts = build_inbound_updates(notes, path_to_id)
    ok = db.batch_query(inbound_stmts, batch_size=100)
    print(f"  {ok}/{len(inbound_stmts)} neurons updated with inbound counts")

    # Phase 4: Replace history (idempotent)
    print("\n[4/5] Recording in Akashic Records (neuron_history)...")
    db.query("DELETE neuron_history")
    history_stmts = build_history_inserts(notes)
    ok = db.batch_query(history_stmts, batch_size=100)
    print(f"  {ok}/{len(history_stmts)} history records created")

    # Phase 5: Clean up orphaned neurons (in DB but not in vault)
    print("\n[5/5] Cleaning orphaned neurons...")
    vault_paths = {n["path"] for n in notes}
    orphaned = [p for p in path_to_existing_id if p not in vault_paths]
    if orphaned:
        for p in orphaned:
            oid = path_to_existing_id[p]
            db.query(f"DELETE neuron:`{oid}`")
        print(f"  {len(orphaned)} orphaned neurons removed")
    else:
        print(f"  0 orphaned neurons (clean)")

    # Verify
    print("\n--- Verification ---")
    r = db.query("SELECT count() FROM neuron GROUP ALL")
    neuron_count = r[0].get("result", [{}])[0].get("count", 0) if r[0].get("result") else 0
    print(f"Neurons in DB: {neuron_count} (vault: {len(notes)})")

    r = db.query("SELECT count() FROM synapse GROUP ALL")
    synapse_count = r[0].get("result", [{}])[0].get("count", 0) if r[0].get("result") else 0
    print(f"Synapses in DB: {synapse_count}")

    r = db.query("SELECT count() FROM neuron_history GROUP ALL")
    history_count = r[0].get("result", [{}])[0].get("count", 0) if r[0].get("result") else 0
    print(f"History records: {history_count}")

    # Aspect distribution in DB
    r = db.query("SELECT aspect, count() FROM neuron GROUP BY aspect")
    if r[0].get("result"):
        print("\nDB aspect distribution:")
        for row in sorted(r[0]["result"], key=lambda x: x.get("aspect", "")):
            print(f"  {row.get('aspect', '?')}: {row.get('count', 0)}")

    # Sanity check: warn if aspect distribution is skewed
    if r[0].get("result"):
        aspects = {row["aspect"]: row["count"] for row in r[0]["result"]}
        connective = aspects.get("connective", 0)
        if connective > neuron_count * 0.6:
            print(f"\n  WARNING: {connective}/{neuron_count} neurons are 'connective' — "
                  "check DIR_TO_ASPECT mapping")

    print("\nImport complete.")


if __name__ == "__main__":
    main()
