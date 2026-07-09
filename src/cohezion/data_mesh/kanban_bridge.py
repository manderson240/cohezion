"""Write-through bridge: Kanban JSON → SurrealDB kanban_item + Obsidian vault.

Every write to ~/.cohezion/work-queue.json calls persist_item() here which:
  1. UPSERTs to SurrealDB `kanban_item` table (entity table, current-state, keyed by id)
  2. Writes ~/vaults/cohezion-vault/kanban/<id>.md (YAML frontmatter + content)

Both sinks are fail-open: if one fails, the other still runs and the
JSON file is already written (source of truth). Returns a dict reporting
what succeeded so callers can log but not panic.

Obsidian sync note: no MCP tools are used — runtime code can't call MCP.
We write directly to the vault filesystem path; Obsidian watches the folder.
"""

from __future__ import annotations

import base64
import json as _json
import logging
import textwrap
import urllib.request
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_NS = "cohezion"
_SURREAL_DB = "main"
_SURREAL_AUTH = base64.b64encode(b"root:root").decode()  # Basic root:root

_VAULT_KANBAN_DIR = Path.home() / "vaults" / "cohezion-vault" / "kanban"


# ── SurrealDB write-through ─────────────────────────────────────────────────

def _surreal_write(item: dict[str, Any]) -> bool:
    """UPSERT item into kanban_item SurrealDB table. Returns True on success."""
    item_id = item.get("id", "")
    if not item_id:
        logger.warning("kanban_bridge: item has no id, skipping SurrealDB write")
        return False

    # SurrealDB record ids with hyphens or other non-alphanumeric chars require
    # backtick quoting: `kanban_item:\`slug-with-hyphens\``
    safe_id = item_id if item_id.isalnum() else f"`{item_id}`"
    surql = f"UPSERT kanban_item:{safe_id} CONTENT {_json.dumps(item)};"
    try:
        req = urllib.request.Request(
            _SURREAL_URL,
            data=surql.encode(),
            headers={
                "surreal-ns": _SURREAL_NS,
                "surreal-db": _SURREAL_DB,
                "Content-Type": "text/plain",
                "Authorization": f"Basic {_SURREAL_AUTH}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            ok = resp.status == 200
            if not ok:
                logger.warning("kanban_bridge: SurrealDB returned %s for %s", resp.status, item_id)
            return ok
    except Exception as exc:
        logger.warning("kanban_bridge: SurrealDB write failed for %s: %s", item_id, exc)
        return False


# ── Obsidian vault write-through ────────────────────────────────────────────

def _obsidian_write(item: dict[str, Any]) -> bool:
    """Write item as YAML-frontmatter Markdown note to vault kanban/ dir. Returns True on success."""
    item_id = item.get("id", "")
    if not item_id:
        return False

    _VAULT_KANBAN_DIR.mkdir(parents=True, exist_ok=True)
    note_path = _VAULT_KANBAN_DIR / f"{item_id}.md"

    title = item.get("title", "Untitled")
    status = item.get("status", "pending_review")
    url = item.get("url", "")
    relevance = item.get("relevance", "")
    domain = item.get("domain", "")
    created_at = item.get("created_at", "")
    approved_at = item.get("approved_at") or ""
    notes = item.get("notes", "")
    description = item.get("description", "")
    feedback = item.get("feedback", "")

    frontmatter_lines = [
        "---",
        "type: kanban",
        f"id: {item_id}",
        f"status: {status}",
        f"relevance: {relevance}",
        f"domain: {domain}",
        f"created_at: {created_at}",
    ]
    if approved_at:
        frontmatter_lines.append(f"approved_at: {approved_at}")
    if url:
        frontmatter_lines.append(f"url: {url}")
    frontmatter_lines.append("---")

    body_parts = ["\n".join(frontmatter_lines), f"\n# {title}\n"]
    if url:
        body_parts.append(f"[Source]({url})\n")
    if description:
        body_parts.append(f"{description}\n")
    if notes:
        body_parts.append(f"\n## Notes\n\n{textwrap.fill(notes, 80)}\n")
    if feedback:
        body_parts.append(f"\n## Feedback\n\n{textwrap.fill(feedback, 80)}\n")

    content = "\n".join(body_parts)
    try:
        note_path.write_text(content, encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("kanban_bridge: Obsidian write failed for %s: %s", item_id, exc)
        return False


# ── Public API ───────────────────────────────────────────────────────────────

def persist_item(item: dict[str, Any]) -> dict[str, bool]:
    """Write item to both SurrealDB and Obsidian. Fail-open on each sink.

    Returns {"surreal": bool, "obsidian": bool} indicating what succeeded.
    """
    surreal_ok = _surreal_write(item)
    obsidian_ok = _obsidian_write(item)
    if not surreal_ok or not obsidian_ok:
        logger.info(
            "kanban_bridge: persist_item(%s) surreal=%s obsidian=%s",
            item.get("id"),
            surreal_ok,
            obsidian_ok,
        )
    return {"surreal": surreal_ok, "obsidian": obsidian_ok}


def backfill_items(items: list[dict[str, Any]]) -> dict[str, int]:
    """Backfill a list of items to both sinks. Returns success counts."""
    surreal_ok = obsidian_ok = total = 0
    for item in items:
        total += 1
        result = persist_item(item)
        if result["surreal"]:
            surreal_ok += 1
        if result["obsidian"]:
            obsidian_ok += 1
    return {"total": total, "surreal_ok": surreal_ok, "obsidian_ok": obsidian_ok}
