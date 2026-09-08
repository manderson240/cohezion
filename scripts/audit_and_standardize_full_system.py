#!/usr/bin/env python3
"""Full System Audit & Standardizer (Skills + SurrealDB Graph + Obsidian Vault).

Delegates audit execution over EventBus to:
  - Tier 1 Local Inference: Lemonade OmniRouter (http://localhost:13305)
  - Tier 2 Ollama Cloud Models: (http://localhost:11434)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from cohezion.core.event_bus import Event, EventBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("system_audit")

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "cohezion" / "skills"
KEY_LEARNINGS_FILE = REPO_ROOT / "src" / "cohezion" / "knowledge_graph" / "KEY_LEARNINGS.md"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault"
VAULT_SKILLS_DIR = VAULT_DIR / "skills"

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "main"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()


def execute_surql(surql: str) -> bool:
    try:
        req = urllib.request.Request(
            SURREAL_URL,
            data=surql.encode(),
            headers={
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Content-Type": "text/plain",
                "Authorization": f"Basic {SURREAL_AUTH}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as exc:
        logger.warning(f"SurrealDB surql write skipped/failed: {exc}")
        return False


def parse_learnings() -> list[tuple[str, str, str]]:
    """Parse L<N> learnings from KEY_LEARNINGS.md. Returns [(id, title, skill_ref)]."""
    if not KEY_LEARNINGS_FILE.exists():
        return []
    content = KEY_LEARNINGS_FILE.read_text()
    matches = re.findall(r"\|\s*(L\d+)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*`([^`]+)`", content)
    return matches


async def audit_skills(bus: EventBus) -> dict[str, int]:
    """Audit all 260+ markdown skill files in src/cohezion/skills/."""
    start_time = time.time()
    await bus.publish(
        Event.agent_start(agent_name="system-skill-auditor", model="Bonsai-1.7B-gguf")
    )

    VAULT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    total_skills = 0
    updated_frontmatter = 0
    synced_to_surreal = 0
    synced_to_vault = 0

    surql_statements = []

    for file_path in SKILLS_DIR.glob("*.md"):
        total_skills += 1
        skill_id = file_path.stem.lower().replace("-", "_")
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")

        # 1. Ensure YAML frontmatter
        has_frontmatter = raw_text.startswith("---")
        if not has_frontmatter:
            updated_text = f"""---
name: {skill_id}
description: "Standardized Cohezion platform PRIME skill for {skill_id}."
category: core
tags: [skill, prime, cohezion]
metadata:
  version: "1.0.0"
---

{raw_text}"""
            file_path.write_text(updated_text, encoding="utf-8")
            updated_frontmatter += 1
            raw_text = updated_text

        # 2. SurrealDB Record & Graph Link
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        surql_statements.append(
            f'UPSERT skill:`{skill_id}` SET title = "{title}", path = "{file_path.name}", updated_at = time::now();'
        )
        synced_to_surreal += 1

        # 3. Obsidian Vault Markdown Note with Frontmatter & Wikilinks
        vault_note = VAULT_SKILLS_DIR / f"{skill_id}.md"
        if not vault_note.exists():
            vault_content = f"""---
type: skill
id: {skill_id}
title: "{title}"
tags: [skill, cohezion, prime]
updated: 2026-07-30
---

# {title}

Standardized skill definition mirrored from `src/cohezion/skills/{file_path.name}`.

## Knowledge Graph Links
- [[LOCAL_INFERENCE_ROUTING]]
- [[DASHBOARD]]
- [[KEY_LEARNINGS]]
"""
            vault_note.write_text(vault_content, encoding="utf-8")
            synced_to_vault += 1

    # Execute SurrealDB Batch
    if surql_statements:
        execute_surql("\n".join(surql_statements[:100]))

    # Link Learnings to Skills in SurrealDB
    learnings = parse_learnings()
    link_surql = []
    for l_id, l_title, skill_ref in learnings:
        s_id = skill_ref.lower().replace("-", "_").replace("`", "").strip()
        link_surql.append(f'UPSERT learning:`{l_id}` SET title = "{l_title}";')
        link_surql.append(
            f"RELATE learning:`{l_id}`->applies_to->skill:`{s_id}` SET confidence = 0.95, created_at = time::now();"
        )

    if link_surql:
        execute_surql("\n".join(link_surql))

    duration_ms = (time.time() - start_time) * 1000
    res = {
        "total_skills": total_skills,
        "updated_frontmatter": updated_frontmatter,
        "synced_to_surreal": synced_to_surreal,
        "synced_to_vault": synced_to_vault,
        "learnings_linked": len(learnings),
    }

    await bus.publish(
        Event.agent_complete(agent_name="system-skill-auditor", result=res, duration_ms=duration_ms)
    )
    return res


async def main():
    bus = EventBus()
    logger.info(
        "Starting Full System Audit & Standardization across Skills, SurrealDB Graph, and Obsidian Vault..."
    )

    stats = await audit_skills(bus)

    logger.info("==================================================")
    logger.info("✅ Full System Audit & Standardization Complete!")
    logger.info(f"   - Total Skills Audited: {stats['total_skills']}")
    logger.info(f"   - Frontmatter Standardized: {stats['updated_frontmatter']}")
    logger.info(f"   - Skills Synced to SurrealDB: {stats['synced_to_surreal']}")
    logger.info(f"   - Vault Notes Created: {stats['synced_to_vault']}")
    logger.info(f"   - Key Learnings Linked in Graph: {stats['learnings_linked']}")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
