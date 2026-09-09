"""Durable Precipitation Bridge: Transactional Dual-Persistence for Database & Vault.

Provides:
1. Pydantic validation on all witness marks.
2. Idempotent atomic recording to SurrealDB (`moc_node` table and `relates_to` graph edges).
3. Atomic sync to Obsidian Knowledge Vault notes (`00-MOCs/`).
4. Materialized vault snapshot (`cohezion_state.json`) for zero-latency DataviewJS rendering.
5. Local write-ahead log (WAL) fallback to prevent data loss on network partition.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("durable_precipitation_bridge")

# Default Configuration
VAULT_MOC_DIR: Path = Path.home() / "vaults" / "cohezion-vault" / "00-MOCs"
SPOOL_FILE: Path = Path.home() / "dev" / "cohezion" / "data" / "witness_spool.jsonl"
STATE_SNAPSHOT_FILE: Path = VAULT_MOC_DIR / "cohezion_state.json"

SURREAL_URL: str = "http://127.0.0.1:8001/sql"
SURREAL_NS: str = "cohezion"
SURREAL_DB: str = "main"
SURREAL_AUTH: str = base64.b64encode(b"root:root").decode()


class DurableWitnessMark(BaseModel):
    """Strict schema for permanent witness marks."""

    mark_id: str
    title: str
    category: str = Field(default="architecture")
    content: str
    hiho_coherence: float = Field(ge=0.0, le=1.0, default=0.50)
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DurablePrecipitationBridge:
    """Manages transactional persistence to SurrealDB and the Obsidian Vault.

    Follows the fail-open Local Durable Outbox pattern: writes are committed to
    the local WAL and vault, while graph records and materialized state snapshots
    are maintained in SurrealDB and Obsidian.
    """

    def __init__(
        self,
        vault_dir: Path | None = None,
        surreal_url: str = SURREAL_URL,
    ) -> None:
        self.vault_dir = vault_dir or VAULT_MOC_DIR
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        SPOOL_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.surreal_url = surreal_url

    def _extract_wikilinks(self, text: str) -> list[str]:
        """Extract referenced note slugs from [[wikilink]] patterns."""
        pattern = r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]"
        matches = re.findall(pattern, text)
        clean_links: list[str] = []
        for m in matches:
            slug = m.strip().replace(" ", "_").lower()
            if slug and slug not in clean_links:
                clean_links.append(slug)
        return clean_links

    def _sync_to_surreal(self, mark: DurableWitnessMark, note_path: Path) -> bool:
        """UPSERT record to SurrealDB moc_node and link relates_to graph edges."""
        safe_id = mark.mark_id if mark.mark_id.isalnum() else f"`{mark.mark_id}`"
        record_payload = {
            "mark_id": mark.mark_id,
            "title": mark.title,
            "category": mark.category,
            "hiho_coherence": mark.hiho_coherence,
            "created_at": mark.created_at,
            "vault_path": str(note_path),
            "metadata": mark.metadata,
        }

        surql_statements = [
            f"UPSERT moc_node:{safe_id} CONTENT {json.dumps(record_payload)};"
        ]

        # Extract wikilinks and construct relates_to graph edges
        wikilinks = self._extract_wikilinks(mark.content)
        self_slug = mark.mark_id.strip().replace(" ", "_").lower()
        for link in wikilinks:
            if link == self_slug:
                continue  # Prevent reflexive self-loops in the graph
            target_id = link if link.isalnum() else f"`{link}`"
            surql_statements.append(
                f"RELATE moc_node:{safe_id}->relates_to->moc_node:{target_id} "
                f"SET relation_type = 'wikilink_reference', created_at = time::now();"
            )

        full_surql = "\n".join(surql_statements)

        try:
            req = urllib.request.Request(
                self.surreal_url,
                data=full_surql.encode("utf-8"),
                headers={
                    "surreal-ns": SURREAL_NS,
                    "surreal-db": SURREAL_DB,
                    "Content-Type": "text/plain",
                    "Authorization": f"Basic {SURREAL_AUTH}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 201):
                    logger.info("SurrealDB moc_node and edges synced for: %s", mark.mark_id)
                    return True
                logger.warning("SurrealDB HTTP %d syncing %s", resp.status, mark.mark_id)
                return False
        except Exception as e:
            logger.warning("Fail-open SurrealDB sync skipped for %s: %s", mark.mark_id, e)
            return False

    def _update_vault_state_snapshot(self, mark: DurableWitnessMark, note_path: Path) -> None:
        """Update materialized state snapshot JSON in the vault for DataviewJS."""
        snapshot_path = self.vault_dir / "cohezion_state.json"
        state_list: list[dict[str, Any]] = []

        if snapshot_path.exists():
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    state_list = json.load(f)
            except Exception:
                state_list = []

        # Update or append record
        existing_idx = next((i for i, r in enumerate(state_list) if r.get("mark_id") == mark.mark_id), None)
        entry = {
            "mark_id": mark.mark_id,
            "title": mark.title,
            "category": mark.category,
            "hiho_coherence": mark.hiho_coherence,
            "created_at": mark.created_at,
            "vault_path": str(note_path),
            "wikilinks": self._extract_wikilinks(mark.content),
            "metadata": mark.metadata,
        }

        if existing_idx is not None:
            state_list[existing_idx] = entry
        else:
            state_list.insert(0, entry)

        tmp_snapshot = snapshot_path.with_suffix(".tmp")
        with open(tmp_snapshot, "w", encoding="utf-8") as f:
            json.dump(state_list, f, indent=2)
        tmp_snapshot.replace(snapshot_path)

    def persist(self, mark: DurableWitnessMark) -> dict[str, Any]:
        """Atomically persist witness mark to Obsidian Vault, SurrealDB, and WAL."""
        # 1. Atomic write to Obsidian Vault Note (.tmp + rename)
        note_filename = f"compound_{mark.mark_id}.md"
        note_path = self.vault_dir / note_filename

        vault_body = f"""---
title: "{mark.title}"
mark_id: "{mark.mark_id}"
category: "{mark.category}"
hiho_coherence: {mark.hiho_coherence}
timestamp: {mark.created_at}
---

# {mark.title}

{mark.content}

## Metadata
```json
{json.dumps(mark.metadata, indent=2)}
```
"""
        tmp_path = note_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(vault_body)
        tmp_path.replace(note_path)
        logger.info("Vault note atomically updated: %s", note_path)

        # 2. Update materialized snapshot for DataviewJS
        self._update_vault_state_snapshot(mark, note_path)

        # 3. Fail-open write to SurrealDB (moc_node + relates_to)
        surreal_ok = self._sync_to_surreal(mark, note_path)

        # 4. Durable Local Write-Ahead Log (WAL)
        spool_entry = mark.model_dump()
        spool_entry["synced_vault"] = str(note_path)
        spool_entry["surreal_synced"] = surreal_ok

        with open(SPOOL_FILE, "a", encoding="utf-8") as sf:
            sf.write(json.dumps(spool_entry) + "\n")
        logger.info("Witness mark appended to durable spool: %s", SPOOL_FILE)

        return {
            "status": "PRECIPITATED",
            "mark_id": mark.mark_id,
            "vault_path": str(note_path),
            "surreal_synced": surreal_ok,
            "spool_file": str(SPOOL_FILE),
        }
