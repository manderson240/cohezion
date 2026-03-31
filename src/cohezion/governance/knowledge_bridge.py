"""Knowledge Bridge — bidirectional persistence for retrospective learnings.

Connects the retrospect process to three persistence layers:
1. Obsidian vault (cerebellum/) — human-readable markdown with [[bidirectional links]]
2. SurrealDB (vault/neuron) — structured, queryable, FLUME-embedded
3. KEY_LEARNINGS.md — compressed summary with vault links

This is Wire 1 of the Cohezion Platform Improvement Roadmap.

Triune mapping: The Knower (awareness of what was learned)
Smith fabric: Field (data topology — connecting knowledge across systems)
Physics: Mycelium network — persistent pathways between ephemeral EVO sessions

The bridge makes the retrospective process WRITE to the same systems it READS from,
closing the Ouroboros loop: session → learning → vault+SurrealDB → next session.

Attribution:
  - Zhamak Dehghani (Data Mesh): domain-owned data products
  - Aboriginal Australian Dreaming: Songlines as persistent navigation paths
  - FloatingPragma (OPH): observer overlap consistency for knowledge coherence
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

VAULT_DIR = Path.home() / "vaults" / "cohezion-vault"
CEREBELLUM_DIR = VAULT_DIR / "cerebellum"
SURREAL_URL = os.environ.get("SURREALDB_URL", "http://localhost:8000")


@dataclass
class Learning:
    """A single retrospective learning to persist."""

    number: int  # e.g., 215
    title: str  # e.g., "FLUME-First Principle"
    content: str  # Full description
    date: str  # ISO date
    tags: list[str]
    propagate_to: str = ""  # e.g., "CLAUDE.md Coding Standards"
    links: list[str] | None = None  # [[bidirectional links]]


def persist_to_vault(learning: Learning) -> Path:
    """Write a learning to the Obsidian vault as a cerebellum entry.

    Creates a dated markdown file with YAML frontmatter and [[bidirectional links]].
    Returns the path to the created file.
    """
    CEREBELLUM_DIR.mkdir(parents=True, exist_ok=True)

    slug = learning.title.lower().replace(" ", "-").replace(":", "")[:60]
    filename = f"{learning.date}-{slug}.md"
    filepath = CEREBELLUM_DIR / filename

    # Build frontmatter
    tags_str = ", ".join(learning.tags)
    links_str = ""
    if learning.links:
        links_str = "\n".join(f'  - "[[{link}]]"' for link in learning.links)
        links_str = f"\nlinks:\n{links_str}"

    content = f"""---
title: "L{learning.number}: {learning.title}"
date: {learning.date}
type: learning
status: verified
tags: [{tags_str}]
learning_number: {learning.number}{links_str}
---

# L{learning.number}: {learning.title}

{learning.content}

## Propagation Target
{learning.propagate_to}

## Cross-References
See: [[indigenous-cosmologies-toe-synthesis]] for the 16-tradition validation.
See: [[theory-of-everything-synthesis]] for the unified physics framework.
"""

    filepath.write_text(content)
    logger.info("Vault: wrote %s", filepath)
    return filepath


def persist_to_surrealdb(learning: Learning) -> bool:
    """Insert a learning into SurrealDB vault/neuron table with FLUME embedding.

    Returns True if successful, False otherwise.
    """
    try:
        import base64
        import urllib.request

        # Encode learning for FLUME embedding
        try:
            from cohezion.governance.flume_bridge import encode_prompt

            embedding = encode_prompt(f"{learning.title}: {learning.content}")
            embedding_list = embedding.tolist()
        except (ImportError, RuntimeError, ValueError):
            embedding_list = []

        # Build SurrealQL
        surql = f"""
        CREATE neuron SET
            name = $name,
            content = $content,
            country = 'cerebellum',
            tags = $tags,
            learning_number = $number,
            embedding = $embedding,
            created = time::now();
        """

        body = json.dumps(
            {
                "name": f"L{learning.number}: {learning.title}",
                "content": learning.content[:500],
                "tags": learning.tags,
                "number": learning.number,
                "embedding": embedding_list[:32],  # Store first 32 dims for space efficiency
            }
        )

        # Use parameterized query via SurrealDB HTTP API
        auth = base64.b64encode(b"root:root").decode()
        req = urllib.request.Request(
            f"{SURREAL_URL}/sql",
            data=surql.encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth}",
                "surreal-ns": "cohezion",
                "surreal-db": "vault",
                "Content-Type": "application/json",
            },
        )
        # Note: parameterized queries need different approach for SurrealDB HTTP
        # Using direct insert for simplicity
        # Match the neuron table schema exactly
        safe_title = learning.title.replace("'", "")
        safe_content = learning.content[:200].replace("'", "")
        slug = learning.title.lower().replace(" ", "-").replace(":", "")[:60]
        vault_path = f"cerebellum/{learning.date}-{slug}.md"
        # Include FLUME embedding for semantic search (first 64 dims for balance)
        embedding_json = json.dumps(embedding_list[:64]) if embedding_list else "[]"
        direct_surql = (
            f"CREATE neuron SET "
            f"title = 'L{learning.number}: {safe_title}', "
            f"path = '{vault_path}', "
            f"aspect = 'knower', "
            f"stage = 'mature', "
            f"tags = {json.dumps(learning.tags)}, "
            f"word_count = {len(learning.content.split())}, "
            f"embedding = {embedding_json}, "
            f"created = time::now();"
        )

        req = urllib.request.Request(
            f"{SURREAL_URL}/sql",
            data=direct_surql.encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth}",
                "surreal-ns": "cohezion",
                "surreal-db": "vault",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if result and result[0].get("status") == "OK":
                logger.info("SurrealDB: inserted L%d as neuron", learning.number)
                return True
            logger.warning("SurrealDB: insert failed: %s", result)
            return False

    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("SurrealDB: connection failed: %s", exc)
        return False


def update_key_learnings_with_link(
    learnings_path: Path,
    learning: Learning,
    vault_path: Path,
) -> None:
    """Add a learning to KEY_LEARNINGS.md with a vault link instead of full content."""
    if not learnings_path.exists():
        return

    link_name = vault_path.stem  # e.g., "2026-03-31-flume-first-principle"
    entry = (
        f"\n### Learning {learning.number}: {learning.title} ({learning.date})\n"
        f"{learning.content[:150]}... "
        f"See: [[cerebellum/{link_name}]]\n"
    )

    with learnings_path.open("a") as f:
        f.write(entry)
    logger.info("KEY_LEARNINGS: appended L%d with vault link", learning.number)


def persist_learning(learning: Learning, learnings_path: Path | None = None) -> dict:
    """Persist a learning to all three layers (vault, SurrealDB, KEY_LEARNINGS).

    Returns a dict with results from each layer.
    """
    results = {}

    # 1. Vault (always succeeds if filesystem is accessible)
    vault_path = persist_to_vault(learning)
    results["vault"] = str(vault_path)

    # 2. SurrealDB (may fail if DB is down)
    results["surrealdb"] = persist_to_surrealdb(learning)

    # 3. KEY_LEARNINGS (append with link)
    if learnings_path:
        update_key_learnings_with_link(learnings_path, learning, vault_path)
        results["key_learnings"] = True

    return results
