#!/usr/bin/env python3
"""
Re-import all vault data into SurrealDB with embeddings.

Imports: papers, decisions, concepts, patterns (including lessons), experiments
Uses GraphRAGImporter with extended type detection.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.graphrag_helpers import detect_document_type
from mcp_server.graphrag_import import GraphRAGImporter


# Monkey-patch detect_document_type to handle all vault directories
_original_detect = detect_document_type


def extended_detect_document_type(file_path: Path, vault_path: Path) -> str:
    """Extended type detection for all vault directories."""
    rel_path = file_path.relative_to(vault_path)
    first_dir = rel_path.parts[0] if len(rel_path.parts) > 1 else ""

    if first_dir == "cortex":
        return "neuron"
    elif first_dir == "cerebellum":
        return "neuron"
    elif first_dir == "papers":
        return "paper"
    elif first_dir == "concepts":
        return "concept"
    elif first_dir == "decisions":
        return "decision"
    elif first_dir == "patterns":
        # Check if it's in the lessons subdirectory
        if len(rel_path.parts) > 2 and rel_path.parts[1] == "lessons":
            return "lesson"
        return "pattern"
    elif first_dir == "experiments":
        return "experiment"
    else:
        return "document"


# Apply the patch
import mcp_server.graphrag_helpers as helpers_module


helpers_module.detect_document_type = extended_detect_document_type

# Also patch it in the import module since it may have imported it directly
import mcp_server.graphrag_import as import_module


import_module.detect_document_type = extended_detect_document_type


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
OLLAMA_URL = "http://localhost:11434"
SURREALDB_URL = "http://localhost:8001"

# Directories to import (order matters: import targets before sources for edges)
DIRECTORIES = [
    ("cortex", False),  # knowledge neurons (physics, ML, cosmologies, MOCs)
    ("cerebellum", False),  # operational neurons (coordination patterns)
    ("concepts", False),  # non-recursive
    ("papers", False),  # non-recursive
    ("decisions", False),  # non-recursive
    ("patterns/lessons", False),  # lessons subdirectory
    ("patterns", False),  # patterns root (non-recursive to avoid re-importing lessons)
    ("experiments", False),  # non-recursive
]


async def verify_services():
    """Check that SurrealDB and Ollama are reachable."""
    import httpx

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check SurrealDB
        try:
            resp = await client.get(f"{SURREALDB_URL}/health")
            logger.info(f"SurrealDB: OK (status {resp.status_code})")
        except Exception as e:
            logger.error(f"SurrealDB unreachable: {e}")
            return False

        # Check Ollama
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            has_nomic = any("nomic-embed-text" in n for n in model_names)
            logger.info(
                f"Ollama: OK (models: {model_names}, nomic-embed-text: {has_nomic})"
            )
            if not has_nomic:
                logger.error("nomic-embed-text model not available!")
                return False
        except Exception as e:
            logger.error(f"Ollama unreachable: {e}")
            return False

    return True


async def count_records():
    """Count records in vault_memory by type."""
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{SURREALDB_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "NS": "cohezion",
                "DB": "vault",
            },
            auth=("root", "root"),
            content="USE NS cohezion DB vault; SELECT type, count() FROM vault_memory GROUP BY type; SELECT count() FROM vault_memory GROUP ALL; SELECT count() FROM informed_by GROUP ALL;",
        )
        results = resp.json()
        return results


async def main():
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("VAULT RE-IMPORT TO SURREALDB")
    logger.info("=" * 60)

    # Step 1: Verify services
    logger.info("\n--- Verifying services ---")
    if not await verify_services():
        logger.error("Service check failed. Aborting.")
        sys.exit(1)

    # Step 2: Show pre-import counts
    logger.info("\n--- Pre-import counts ---")
    pre_counts = await count_records()
    for r in pre_counts[1:]:
        if r.get("status") == "OK":
            logger.info(f"  {r.get('result', [])}")

    # Step 3: Import all directories
    all_stats = {}
    async with GraphRAGImporter(
        vault_path=VAULT_PATH,
        ollama_url=OLLAMA_URL,
        surrealdb_url=SURREALDB_URL,
        namespace="cohezion",
        database="vault",
        embedding_model="nomic-embed-text:latest",
        max_concurrent=5,  # Conservative to avoid overwhelming Ollama
    ) as importer:
        for directory, recursive in DIRECTORIES:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Importing {directory} (recursive={recursive})...")
            logger.info(f"{'=' * 60}")

            stats = await importer.import_directory(
                directory=directory,
                pattern="*.md",
                recursive=recursive,
            )
            all_stats[directory] = stats
            logger.info(
                f"  Result: {stats['success']}/{stats['total']} imported, {stats['failed']} failed"
            )

    # Step 4: Show post-import counts
    logger.info("\n--- Post-import counts ---")
    post_counts = await count_records()
    for r in post_counts[1:]:
        if r.get("status") == "OK":
            logger.info(f"  {r.get('result', [])}")

    # Step 5: Summary
    elapsed = time.time() - start_time
    logger.info(f"\n{'=' * 60}")
    logger.info("IMPORT SUMMARY")
    logger.info(f"{'=' * 60}")
    total_success = 0
    total_files = 0
    total_failed = 0
    for directory, stats in all_stats.items():
        logger.info(
            f"  {directory:25s}: {stats['success']:3d}/{stats['total']:3d} imported, {stats['failed']} failed"
        )
        total_success += stats["success"]
        total_files += stats["total"]
        total_failed += stats["failed"]
    logger.info(
        f"  {'TOTAL':25s}: {total_success:3d}/{total_files:3d} imported, {total_failed} failed"
    )
    logger.info(f"  Elapsed: {elapsed:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
