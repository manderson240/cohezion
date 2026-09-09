#!/usr/bin/env python3
"""Backfill all existing MOC notes into SurrealDB and cohezion_state.json."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from cohezion.data_mesh.durable_precipitation_bridge import (
    DurablePrecipitationBridge,
    DurableWitnessMark,
    VAULT_MOC_DIR,
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("backfill_mocs")


def backfill() -> None:
    bridge = DurablePrecipitationBridge()
    logger.info("Scanning %s for existing compound_*.md notes...", VAULT_MOC_DIR)

    for md_file in sorted(VAULT_MOC_DIR.glob("compound_*.md")):
        slug = md_file.stem.replace("compound_", "")
        content = md_file.read_text(encoding="utf-8")

        # Extract title from first # or frontmatter
        title_match = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            h1_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else slug.replace("_", " ").title()

        # Extract coherence
        coh_match = re.search(r"^hiho_coherence:\s*([0-9.]+)", content, re.MULTILINE)
        coherence = float(coh_match.group(1)) if coh_match else 0.50

        # Extract category
        cat_match = re.search(r"^category:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
        category = cat_match.group(1).strip() if cat_match else "transcendence"

        mark = DurableWitnessMark(
            mark_id=slug,
            title=title,
            category=category,
            content=content,
            hiho_coherence=coherence,
            metadata={"backfilled": True, "source_file": md_file.name},
        )

        res = bridge.persist(mark)
        logger.info("Backfilled %s -> SurrealDB: %s", slug, res["surreal_synced"])


if __name__ == "__main__":
    backfill()
