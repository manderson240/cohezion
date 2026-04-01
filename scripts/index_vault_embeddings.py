"""Offline vault indexing script using Gemini Embedding 2.

Indexes all vault notes, PRIME skills, decisions, and patterns into SurrealDB
using Gemini Embedding 2 vectors. Run once (or after major vault changes).

Cost: Only calls Gemini API for novel content (content-hash deduplication).
After first run: zero API cost for previously-indexed content.

Usage:
    uv run python scripts/index_vault_embeddings.py
    uv run python scripts/index_vault_embeddings.py --vault-path ~/vaults/cohezion-vault
    uv run python scripts/index_vault_embeddings.py --dry-run   # show counts, no API calls
    uv run python scripts/index_vault_embeddings.py --skills-only
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_VAULT_PATH = Path("~/vaults/cohezion-vault").expanduser()
SKILLS_PATH = Path("src/cohezion/skills")
SUPPORTED_EXTENSIONS = {".md", ".txt"}


def find_indexable_files(
    vault_path: Path,
    skills_path: Path,
    skills_only: bool = False,
) -> list[Path]:
    """Collect all files to index."""
    files: list[Path] = []

    if skills_path.exists():
        files.extend(
            p for p in skills_path.rglob("*.md")
            if not p.name.startswith("_")
        )
        logger.info(f"Found {len(files)} PRIME skills in {skills_path}")

    if not skills_only and vault_path.exists():
        vault_files = [
            p for p in vault_path.rglob("*")
            if p.suffix in SUPPORTED_EXTENSIONS and not p.name.startswith(".")
        ]
        logger.info(f"Found {len(vault_files)} vault files in {vault_path}")
        files.extend(vault_files)

    return files


async def index_file(
    path: Path,
    model: "GeminiEmbeddingModel",
    dry_run: bool = False,
) -> tuple[bool, bool]:
    """Index a single file. Returns (success, was_cached)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return False, False

        if dry_run:
            return True, False

        result = await model.encode(text)
        return True, result.cached
    except Exception as e:
        logger.warning(f"Failed to index {path}: {e}")
        return False, False


async def run_indexing(
    vault_path: Path,
    skills_path: Path,
    skills_only: bool = False,
    dry_run: bool = False,
    batch_size: int = 10,
) -> None:
    """Main indexing loop."""
    from cohezion.agentjet.embeddings import FlumeVAEEmbeddingModel, GeminiEmbeddingModel

    fallback = FlumeVAEEmbeddingModel()
    model = GeminiEmbeddingModel(fallback=fallback)

    files = find_indexable_files(vault_path, skills_path, skills_only)
    if not files:
        logger.warning("No files found to index.")
        return

    logger.info(f"Indexing {len(files)} files (dry_run={dry_run})")

    total = len(files)
    success_count = 0
    cached_count = 0
    api_calls = 0

    for i in range(0, total, batch_size):
        batch = files[i : i + batch_size]
        results = await asyncio.gather(
            *[index_file(f, model, dry_run) for f in batch],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch error: {result}")
                continue
            ok, was_cached = result
            if ok:
                success_count += 1
                if was_cached:
                    cached_count += 1
                else:
                    api_calls += 1

        progress = min(i + batch_size, total)
        logger.info(f"Progress: {progress}/{total} ({progress * 100 // total}%)")

    logger.info(
        f"Indexing complete: {success_count}/{total} indexed, "
        f"{cached_count} cache hits, {api_calls} API calls made"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Index vault content with Gemini Embedding 2")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=DEFAULT_VAULT_PATH,
        help="Path to cohezion vault (default: ~/vaults/cohezion-vault)",
    )
    parser.add_argument(
        "--skills-path",
        type=Path,
        default=SKILLS_PATH,
        help="Path to PRIME skills directory",
    )
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="Only index PRIME skills, not full vault",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count files without making API calls",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Concurrent API requests per batch (default: 10)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(
            run_indexing(
                vault_path=args.vault_path,
                skills_path=args.skills_path,
                skills_only=args.skills_only,
                dry_run=args.dry_run,
                batch_size=args.batch_size,
            )
        )
    except KeyboardInterrupt:
        logger.info("Indexing interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
