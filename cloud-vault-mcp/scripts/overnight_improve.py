#!/usr/bin/env python3
"""
Overnight Continuous Improvement Daemon

Runs until 7 AM EST, performing iterative vault improvements:
1. Detect new/modified vault files → re-import to SurrealDB with fresh embeddings
2. Find missing cross-links via embedding similarity → add wiki-links
3. Detect orphaned notes → suggest connections
4. Log all changes for morning review

Usage:
    python3 scripts/overnight_improve.py
    # Or with custom stop time:
    STOP_HOUR=8 python3 scripts/overnight_improve.py
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

from mcp_server.graphrag_helpers import (
    execute_surreal_async,
    parse_wiki_links,
    slugify,
    escape_sql,
    parse_frontmatter,
    GraphRAGError,
)
from mcp_server.graphrag_import import GraphRAGImporter

# Monkey-patch detect_document_type for full vault coverage
from mcp_server.graphrag_helpers import detect_document_type as _orig_detect
import mcp_server.graphrag_helpers as helpers_module
import mcp_server.graphrag_import as import_module


def extended_detect_document_type(file_path: Path, vault_path: Path) -> str:
    rel_path = file_path.relative_to(vault_path)
    first_dir = rel_path.parts[0] if len(rel_path.parts) > 1 else ""
    type_map = {
        "papers": "paper",
        "concepts": "concept",
        "decisions": "decision",
        "experiments": "experiment",
        "lessons": "lesson",
        "daily": "daily",
        "inbox": "inbox",
    }
    if first_dir == "patterns":
        if len(rel_path.parts) > 2 and rel_path.parts[1] == "lessons":
            return "lesson"
        return "pattern"
    return type_map.get(first_dir, "document")


helpers_module.detect_document_type = extended_detect_document_type
import_module.detect_document_type = extended_detect_document_type


# --- Configuration ---
VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
OLLAMA_URL = "http://localhost:11434"
SURREALDB_URL = "http://localhost:8000"
NAMESPACE = "cohezion"
DATABASE = "vault"
EMBEDDING_MODEL = "nomic-embed-text:latest"
STOP_HOUR = int(os.environ.get("STOP_HOUR", "7"))  # 7 AM EST
CYCLE_INTERVAL = 300  # 5 minutes between cycles
SIMILARITY_THRESHOLD = 0.65  # Min cosine similarity for suggesting links
LOG_DIR = VAULT_PATH / "logs"
EST = timezone(timedelta(hours=-5))

# Directories to scan for changes
CONTENT_DIRS = ["decisions", "experiments", "patterns", "concepts", "papers", "lessons"]

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"overnight-{datetime.now(EST).strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class FileTracker:
    """Track file modification times to detect changes."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.state_file = vault_path / "logs" / ".file_tracker_state.json"
        self.known_files: dict[str, float] = {}
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                self.known_files = json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, OSError):
                self.known_files = {}

    def _save_state(self):
        self.state_file.write_text(json.dumps(self.known_files, indent=2))

    def scan_for_changes(self) -> tuple[list[Path], list[Path]]:
        """Return (new_files, modified_files) since last scan."""
        new_files = []
        modified_files = []

        for dir_name in CONTENT_DIRS:
            dir_path = self.vault_path / dir_name
            if not dir_path.exists():
                continue
            for md_file in dir_path.rglob("*.md"):
                if "_template" in md_file.name:
                    continue
                rel = str(md_file.relative_to(self.vault_path))
                mtime = md_file.stat().st_mtime
                if rel not in self.known_files:
                    new_files.append(md_file)
                    self.known_files[rel] = mtime
                elif mtime > self.known_files[rel]:
                    modified_files.append(md_file)
                    self.known_files[rel] = mtime

        self._save_state()
        return new_files, modified_files


async def check_services() -> bool:
    """Verify SurrealDB and Ollama are running."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{SURREALDB_URL}/health")
            if not resp.is_success:
                logger.error("SurrealDB health check failed")
                return False
        except Exception as e:
            logger.error(f"SurrealDB unreachable: {e}")
            return False

        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            models = resp.json().get("models", [])
            if not any("nomic-embed-text" in m["name"] for m in models):
                logger.error("nomic-embed-text model not available in Ollama")
                return False
        except Exception as e:
            logger.error(f"Ollama unreachable: {e}")
            return False

    return True


async def reimport_files(files: list[Path]) -> dict:
    """Re-import specific files to SurrealDB with fresh embeddings."""
    if not files:
        return {"imported": 0, "failed": 0}

    imported = 0
    failed = 0

    async with GraphRAGImporter(
        vault_path=VAULT_PATH,
        ollama_url=OLLAMA_URL,
        surrealdb_url=SURREALDB_URL,
        namespace=NAMESPACE,
        database=DATABASE,
        embedding_model=EMBEDDING_MODEL,
        max_concurrent=3,
    ) as importer:
        for file_path in files:
            try:
                doc_id = await importer.import_document(file_path, create_edges=True)
                if doc_id:
                    imported += 1
                    logger.info(f"  Imported: {file_path.relative_to(VAULT_PATH)}")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.warning(f"  Failed: {file_path.name}: {e}")

    return {"imported": imported, "failed": failed}


async def find_similar_documents(
    http_client: httpx.AsyncClient, doc_id: str, top_k: int = 5
) -> list[dict]:
    """Find documents similar to the given one via vector search."""
    query = f"""
    LET $source = (SELECT embedding FROM {doc_id})[0].embedding;
    SELECT id, title, type, path,
        vector::similarity::cosine(embedding, $source) AS score
    FROM vault_memory
    WHERE id != {doc_id}
        AND embedding IS NOT NONE
        AND vector::similarity::cosine(embedding, $source) > {SIMILARITY_THRESHOLD}
    ORDER BY score DESC
    LIMIT {top_k};
    """
    try:
        results = await execute_surreal_async(query, http_client, NAMESPACE, DATABASE)
        # The SELECT result is the second statement
        if len(results) >= 2 and results[1].get("status") == "OK":
            return results[1].get("result", [])
    except Exception as e:
        logger.debug(f"Similarity search failed for {doc_id}: {e}")
    return []


async def find_orphans_and_suggest_links(http_client: httpx.AsyncClient) -> list[dict]:
    """Find orphaned documents and suggest links based on embedding similarity."""
    suggestions = []

    # Find documents with no incoming or outgoing edges
    orphan_query = """
    SELECT id, title, type, path FROM vault_memory
    WHERE id NOT IN (SELECT in FROM informed_by)
        AND id NOT IN (SELECT out FROM informed_by)
        AND embedding IS NOT NONE
    LIMIT 20;
    """
    try:
        results = await execute_surreal_async(
            orphan_query, http_client, NAMESPACE, DATABASE
        )
        orphans = results[0].get("result", []) if results else []
    except Exception as e:
        logger.warning(f"Orphan query failed: {e}")
        return []

    for orphan in orphans:
        orphan_id = orphan.get("id", "")
        similar = await find_similar_documents(http_client, orphan_id, top_k=3)
        if similar:
            suggestions.append(
                {
                    "orphan": orphan,
                    "similar": similar,
                }
            )

    return suggestions


def add_wiki_link_to_file(file_path: Path, target_title: str) -> bool:
    """Add a wiki-link to a file's Related section if not already present."""
    try:
        content = file_path.read_text(encoding="utf-8")
        link = f"[[{target_title}]]"

        # Skip if link already exists
        if link in content:
            return False

        # Find or create Related section
        if "## Related" in content:
            content = content.replace("## Related\n", f"## Related\n- {link}\n", 1)
        else:
            content = content.rstrip() + f"\n\n## Related\n- {link}\n"

        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning(f"Failed to add link to {file_path}: {e}")
        return False


async def apply_similarity_links(
    http_client: httpx.AsyncClient, suggestions: list[dict]
) -> int:
    """Apply wiki-links based on similarity suggestions."""
    links_added = 0

    for suggestion in suggestions:
        orphan = suggestion["orphan"]
        orphan_path = VAULT_PATH / orphan.get("path", "")
        if not orphan_path.exists():
            continue

        for similar in suggestion["similar"]:
            score = similar.get("score", 0)
            if score < SIMILARITY_THRESHOLD:
                continue

            target_title = similar.get("title", "")
            if not target_title:
                continue

            if add_wiki_link_to_file(orphan_path, target_title):
                links_added += 1
                logger.info(
                    f"  +link: {orphan.get('title', '')} → [[{target_title}]] "
                    f"(score={score:.3f})"
                )

            # Also add reverse link
            target_path_str = similar.get("path", "")
            target_path = VAULT_PATH / target_path_str if target_path_str else None
            if target_path and target_path.exists():
                orphan_title = orphan.get("title", "")
                if orphan_title and add_wiki_link_to_file(target_path, orphan_title):
                    links_added += 1

    return links_added


async def create_missing_edges(http_client: httpx.AsyncClient) -> int:
    """Scan vault files for wiki-links that don't have SurrealDB edges."""
    edges_created = 0

    for dir_name in CONTENT_DIRS:
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue

        for md_file in dir_path.rglob("*.md"):
            if "_template" in md_file.name:
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
                links = parse_wiki_links(content)
                if not links:
                    continue

                source_id = f"vault_memory:{slugify(md_file.stem)}"

                for link in links:
                    target_id = f"vault_memory:{slugify(link)}"
                    # Check if edge exists
                    check_query = f"""
                    SELECT count() FROM informed_by
                    WHERE in = {source_id} AND out = {target_id}
                    GROUP ALL;
                    """
                    result = await execute_surreal_async(
                        check_query, http_client, NAMESPACE, DATABASE
                    )
                    count = 0
                    if result and result[0].get("status") == "OK":
                        res_list = result[0].get("result", [])
                        if res_list:
                            count = res_list[0].get("count", 0)

                    if count == 0:
                        # Create edge
                        edge_query = f"""
                        RELATE {source_id}->informed_by->{target_id}
                        SET how = 'wiki-link', created_at = time::now();
                        """
                        try:
                            await execute_surreal_async(
                                edge_query, http_client, NAMESPACE, DATABASE
                            )
                            edges_created += 1
                        except Exception:
                            pass  # Target may not exist in DB

            except Exception as e:
                logger.debug(f"Edge scan failed for {md_file.name}: {e}")

    return edges_created


async def run_cycle(
    cycle_num: int, tracker: FileTracker, http_client: httpx.AsyncClient
) -> dict:
    """Run one improvement cycle."""
    cycle_start = time.time()
    stats = {
        "cycle": cycle_num,
        "new_files": 0,
        "modified_files": 0,
        "imported": 0,
        "links_added": 0,
        "edges_created": 0,
        "orphans_found": 0,
    }

    # Phase 1: Detect changes
    new_files, modified_files = tracker.scan_for_changes()
    stats["new_files"] = len(new_files)
    stats["modified_files"] = len(modified_files)

    changed = new_files + modified_files
    if changed:
        logger.info(f"  Phase 1: {len(new_files)} new, {len(modified_files)} modified")
        result = await reimport_files(changed)
        stats["imported"] = result["imported"]
    else:
        logger.info("  Phase 1: No file changes detected")

    # Phase 2: Find and fix orphans via similarity
    logger.info("  Phase 2: Scanning for orphans...")
    suggestions = await find_orphans_and_suggest_links(http_client)
    stats["orphans_found"] = len(suggestions)

    if suggestions:
        links_added = await apply_similarity_links(http_client, suggestions)
        stats["links_added"] = links_added
        logger.info(
            f"  Phase 2: {links_added} links added from {len(suggestions)} orphans"
        )
        # Update tracker so link-modified files aren't re-imported next cycle
        if links_added > 0:
            tracker.scan_for_changes()
    else:
        logger.info("  Phase 2: No orphans found")

    # Phase 3: Sync wiki-links → SurrealDB edges
    logger.info("  Phase 3: Syncing wiki-links to graph edges...")
    edges = await create_missing_edges(http_client)
    stats["edges_created"] = edges
    if edges:
        logger.info(f"  Phase 3: {edges} new edges created")

    # Convergence check: if nothing changed, report idle
    total_work = stats["imported"] + stats["links_added"] + stats["edges_created"]
    if total_work == 0:
        stats["converged"] = True
        logger.info("  ✓ Vault is converged — no changes needed")

    elapsed = time.time() - cycle_start
    logger.info(
        f"  Cycle {cycle_num} complete in {elapsed:.1f}s: "
        f"+{stats['imported']} imported, +{stats['links_added']} links, "
        f"+{stats['edges_created']} edges"
    )

    return stats


def should_stop() -> bool:
    """Check if we should stop (past 7 AM EST)."""
    now_est = datetime.now(EST)
    # Stop if it's past STOP_HOUR and before noon (to handle overnight wrap)
    return STOP_HOUR <= now_est.hour < 12


async def main():
    logger.info("=" * 60)
    logger.info("OVERNIGHT CONTINUOUS IMPROVEMENT DAEMON")
    logger.info(f"Stop time: {STOP_HOUR}:00 AM EST")
    logger.info(f"Cycle interval: {CYCLE_INTERVAL}s")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    # Verify services
    if not await check_services():
        logger.error("Service check failed. Ensure SurrealDB and Ollama are running.")
        sys.exit(1)
    logger.info("Services OK (SurrealDB + Ollama)")

    tracker = FileTracker(VAULT_PATH)
    all_stats = []
    cycle_num = 0

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        while not should_stop():
            cycle_num += 1
            now_est = datetime.now(EST)
            logger.info(
                f"\n--- Cycle {cycle_num} [{now_est.strftime('%H:%M:%S')} EST] ---"
            )

            try:
                stats = await run_cycle(cycle_num, tracker, http_client)
                all_stats.append(stats)
            except Exception as e:
                logger.error(f"Cycle {cycle_num} failed: {e}")
                all_stats.append({"cycle": cycle_num, "error": str(e)})

            # If converged, use longer sleep to avoid busy-looping
            sleep_time = (
                CYCLE_INTERVAL * 3 if stats.get("converged") else CYCLE_INTERVAL
            )

            # Wait for next cycle (check stop condition every 30s)
            waited = 0
            while waited < sleep_time and not should_stop():
                await asyncio.sleep(30)
                waited += 30

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("OVERNIGHT SESSION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total cycles: {cycle_num}")

    total_imported = sum(s.get("imported", 0) for s in all_stats)
    total_links = sum(s.get("links_added", 0) for s in all_stats)
    total_edges = sum(s.get("edges_created", 0) for s in all_stats)
    total_new = sum(s.get("new_files", 0) for s in all_stats)
    total_modified = sum(s.get("modified_files", 0) for s in all_stats)

    logger.info(f"Files detected: {total_new} new, {total_modified} modified")
    logger.info(f"Documents imported: {total_imported}")
    logger.info(f"Wiki-links added: {total_links}")
    logger.info(f"Graph edges created: {total_edges}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    # Write summary to vault
    summary_file = (
        VAULT_PATH
        / "logs"
        / f"overnight-summary-{datetime.now(EST).strftime('%Y-%m-%d')}.md"
    )
    summary_file.write_text(
        f"""---
title: "Overnight Improvement Summary"
date: {datetime.now(EST).strftime("%Y-%m-%d")}
type: automated
---

# Overnight Improvement Summary

- **Cycles run**: {cycle_num}
- **Files detected**: {total_new} new, {total_modified} modified
- **Documents imported to SurrealDB**: {total_imported}
- **Wiki-links added**: {total_links}
- **Graph edges created**: {total_edges}
- **Duration**: {datetime.now(EST).strftime("%H:%M")} EST

## Cycle Details

| Cycle | New | Modified | Imported | Links | Edges |
|-------|-----|----------|----------|-------|-------|
"""
        + "\n".join(
            f"| {s.get('cycle', '?')} | {s.get('new_files', 0)} | {s.get('modified_files', 0)} | "
            f"{s.get('imported', 0)} | {s.get('links_added', 0)} | {s.get('edges_created', 0)} |"
            for s in all_stats
        )
        + "\n",
        encoding="utf-8",
    )
    logger.info(f"Summary written to {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
