#!/usr/bin/env python3
"""SurrealDB Vault Learnings Synchronizer.

Scans the Obsidian vault learnings directory, parses frontmatter and body,
and upserts all learning records (neurons) into SurrealDB.
"""

import base64
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

# SurrealDB connection details
SURREALDB_URL = os.environ.get("SURREALDB_URL", "http://localhost:8001/sql")
SURREALDB_USER = os.environ.get("SURREALDB_USER", "root")
SURREALDB_PASS = os.environ.get("SURREALDB_PASS", "root")
NS = "cohezion"
DB = "vault"

VAULT_DIR = "/home/mike-anderson/vaults/cohezion-vault/learnings"


def _sql_str(v: str) -> str:
    """Escape and wrap string for SQL."""
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter and body from markdown content."""
    parts = content.split("---", 2)
    frontmatter = {}
    body = content

    if len(parts) >= 3:
        fm_text = parts[1]
        body = parts[2].strip()
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Strip quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # Parse list format like [a, b, c]
            elif val.startswith("[") and val.endswith("]"):
                items = []
                for item in val[1:-1].split(","):
                    item = item.strip().strip('"').strip("'")
                    if item:
                        items.append(item)
                val = items
            # Parse list format spread over multiple lines (we only handle simple inline list/text for now)
            frontmatter[key] = val

    return frontmatter, body


def sync_learning(learning_id: str, title: str, path: str, tags: list[str], content: str) -> bool:
    """Upsert a learning node (neuron) into SurrealDB.

    Returns True on success, False on failure.
    """
    db_id = f"neurons:{learning_id}"
    tags_json = json.dumps(tags)

    upsert_sql = (
        f"UPSERT {db_id} SET "
        f"title = {_sql_str(title)}, "
        f"path = {_sql_str(path)}, "
        f"tags = {tags_json}, "
        f"content = {_sql_str(content)}, "
        f"stage = 'active', "
        f"updated_at = time::now();"
    )

    try:
        auth = base64.b64encode(f"{SURREALDB_USER}:{SURREALDB_PASS}".encode()).decode()
        req = urllib.request.Request(  # noqa: S310
            SURREALDB_URL,
            data=upsert_sql.encode("utf-8"),
            method="POST",
            headers={
                "surreal-ns": NS,
                "surreal-db": DB,
                "Authorization": f"Basic {auth}",
                "Content-Type": "text/plain",
            },
        )
        response_bytes = urllib.request.urlopen(req, timeout=5).read()  # noqa: S310
        response_json = json.loads(response_bytes)

        if isinstance(response_json, list) and response_json:
            first = response_json[0]
            if isinstance(first, dict) and first.get("status") == "ERR":
                print(f"❌ SurrealDB error for {db_id}: {first.get('result')}", file=sys.stderr)
                return False
        return True
    except Exception as e:
        print(f"⚠️ SurrealDB write failed for {db_id}: {e}", file=sys.stderr)
        return False


def main() -> None:
    print(f"Scanning vault directory: {VAULT_DIR}")
    if not os.path.exists(VAULT_DIR):
        print(f"❌ Vault directory not found: {VAULT_DIR}", file=sys.stderr)
        sys.exit(1)

    search_pattern = os.path.join(VAULT_DIR, "*.md")
    files = glob.glob(search_pattern)
    print(f"Found {len(files)} markdown files.")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        if filename == "INDEX.md" or filename == "canonical_source.md":
            print(f"Skipping master file: {filename}")
            skipped_count += 1
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_content = f.read()

            frontmatter, body = parse_frontmatter(raw_content)

            # Determine ID from frontmatter or filename
            learning_id = frontmatter.get("id")
            if not learning_id:
                # Fallback to filename slug
                name_without_ext = os.path.splitext(filename)[0]
                learning_id = name_without_ext

            title = frontmatter.get("title") or filename
            tags = frontmatter.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]

            # Clean ID to fit SurrealDB table suffix requirements (only allow alphanumeric + underscores)
            clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", learning_id)

            # Sync to SurrealDB
            success = sync_learning(
                learning_id=clean_id,
                title=title,
                path=filepath,
                tags=tags,
                content=body,
            )

            if success:
                print(f"✅ Synced neurons:{clean_id} - '{title[:40]}...'")
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ Failed processing {filename}: {e}", file=sys.stderr)
            fail_count += 1

    print("\n=== Sync Summary ===")
    print(f"Successfully Synced: {success_count}")
    print(f"Failed:              {fail_count}")
    print(f"Skipped:             {skipped_count}")


if __name__ == "__main__":
    main()
